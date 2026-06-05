"""
AoT 依赖图执行器 —— 真·动态调度（节点级并行）。

核心：不是"一批跑完再跑下一批"，而是【谁的依赖一满足，谁就立刻启动】。
所以 D 只依赖 A、B 时，A、B 一完成 D 就开跑，不必等还在跑的 C。
这就是 DAG 数据流调度（1960s 的经典算法），这里套在工具调用上。

为什么用线程池而不是 for：
- 节点真正"慢"在 I/O（网络/API）时，多个节点的等待能重叠 → 真省时间。
- 工具是本地瞬时函数时，线程池没坏处，只是收益不明显。
执行的真正逻辑（拓扑调度）不依赖线程；线程只是"同时干活"的肌肉。
"""

import concurrent.futures


def validate_graph(nodes: list[dict]) -> str | None:
    """
    执行前校验图结构（第 10 课强调的"校验式执行"）。

    Returns:
        出错原因字符串；图合法则返回 None。
    """
    if not nodes:
        return "空图"
    ids = [n["id"] for n in nodes]
    if len(ids) != len(set(ids)):
        return "存在重复的节点 id"
    id_set = set(ids)
    for n in nodes:
        for dep in n.get("depends_on", []):
            if dep not in id_set:
                return f"节点 {n['id']} 依赖了不存在的节点 {dep}"
    # 环检测：拓扑排序能否消完所有节点
    indeg = {n["id"]: len(n.get("depends_on", [])) for n in nodes}
    dep_map = {n["id"]: list(n.get("depends_on", [])) for n in nodes}
    ready = [i for i, d in indeg.items() if d == 0]
    seen = 0
    while ready:
        cur = ready.pop()
        seen += 1
        for other, deps in dep_map.items():
            if cur in deps:
                indeg[other] -= 1
                if indeg[other] == 0:
                    ready.append(other)
    if seen != len(nodes):
        return "存在循环依赖（不是 DAG）"
    return None


class GraphExecutor:
    """对一张依赖图做动态调度执行。
    图的调度器"""

    def __init__(self, llm, registry, max_workers: int = 8, on_event=None):
        """
        Args:
            llm: LLMClient，执行节点时用它【动态回填参数】（强制调该节点的工具）
            registry: 工具注册器（有 .execute(name, **args)）
            max_workers: 线程池大小
            on_event: 可选回调 on_event(event:str, node:dict, extra)，用于打日志
        """
        self.llm = llm
        self.registry = registry
        self.max_workers = max_workers
        # 存的是时间发生的时候该调哪个函数
        self.on_event = on_event or (lambda *a, **k: None)

    def run(self, nodes: list[dict]) -> dict:
        """
        执行整张图，返回 {node_id: 该节点工具的执行结果}。

        动态调度核心：
        - 维护 completed（已完成）、running（在跑）两个集合。
        - 只要某节点的 depends_on 全在 completed 里、且自己没跑过 → 立刻提交。
        - 用 wait(FIRST_COMPLETED) 等"任意一个"完成，完成后马上检查谁被解锁，再提交。
          → 这就是"D 不等 C"的关键：每完成一个就重新扫一遍谁能启动。
        """
        err = validate_graph(nodes)
        if err:
            return {"_error": err}

        by_id = {n["id"]: n for n in nodes}
        results: dict = {}
        completed: set = set()
        running: set = set()

        # 检查一个节点的依赖是否全部完成
        def deps_met(node):
            return all(d in completed for d in node.get("depends_on", []))

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            futures = {}  # future -> node_id

            def submit_ready():
                """把所有'依赖已满足、还没跑'的节点提交执行。"""
                for n in nodes:
                    nid = n["id"]
                    if nid in completed or nid in running:
                        continue
                    if deps_met(n):
                        self.on_event("start", n, None)
                        fut = ex.submit(self._run_node, n, results)
                        futures[fut] = nid
                        running.add(nid)

            submit_ready()  # 启动第一批（所有无依赖的节点）

            while futures:
                # 等"任意一个"完成——不是等整批
                done, _ = concurrent.futures.wait(
                    futures, return_when=concurrent.futures.FIRST_COMPLETED
                )
                for fut in done:
                    nid = futures.pop(fut)
                    running.discard(nid)
                    completed.add(nid)
                    results[nid] = fut.result()
                    self.on_event("done", by_id[nid], results[nid])
                # 有节点刚完成 → 可能解锁了下游 → 立刻提交新就绪的
                submit_ready()

        return results

    def _run_node(self, node: dict, results: dict):
        """
        执行单个节点 —— 两阶段设计的第二阶段：动态回填参数 + 执行。

        规划阶段只给了 {tool, subtask, depends_on}，没有参数。
        这里执行时：
        1. 把这一步的子任务描述 + 依赖节点的真实结果，拼成上下文；
        2. 调 LLM 并【强制用本节点指定的工具】（force_tool），让它基于上游
           结果回填参数——OpenAI 会按该工具 schema 强制填全 required 参数；
        3. function_calling 内部已经执行了工具，直接返回结果。
        """
        tool = node["tool"]
        subtask = node.get("subtask", "")

        # 把依赖的上游节点结果拼成可读上下文
        dep_lines = []
        for dep in node.get("depends_on", []):
            dep_lines.append(f"- 上游节点 {dep} 的结果：{results.get(dep)}")
        dep_text = "\n".join(dep_lines)

        prompt = f"当前子任务：{subtask}"
        if dep_text:
            prompt += f"\n你可以使用下列已完成步骤的结果作为参数：\n{dep_text}"

        # 强制调用本节点的工具，让模型只负责回填参数
        out = self.llm.function_calling(prompt, force_tool=tool)
        return out.get("result")
