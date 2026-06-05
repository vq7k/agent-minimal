"""
Agent —— 移植自 agents-from-scratch 的"完整链路"垂直切片。

本文件只保留你深改过的那条路径所需的能力,去掉了与该切片无关的早期课程脚手架:
- agent loop(ReAct):run_loop / agent_step —— 每步让模型基于进展决定调哪个工具
- 工具调用 + 注册器:见 tools.py
- 状态:AgentState(步数、计划、游标、重规划次数、上一步动作)
- 记忆:Memory(由 remember 工具触发,跨任务长期保留)
- 轨迹:Trajectory / Finding(本轮每一步的记录)
- 重规划:_replan(执行出错或模型主动 replan 时,只重排剩余步骤)
- DAG(AoT)动态调度:run_graph —— 规划成依赖图,无依赖节点并行,依赖一满足即启动

另加两个"流式驱动"方法(原版没有),把执行过程通过 emit 回调实时吐出,
供 bravo 的 SSE chat() 使用:run_loop_streamed / run_graph_streamed。
"""

import time

from .llm import LLMClient
from .memory import Memory
from .state import AgentState
from .trajectory import Finding, Trajectory


def _short(value, limit: int = 80) -> str:
    """把任意结果压成一行短文本,便于流式展示。"""
    text = str(value).replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + "…"


class Agent:
    """能力随课程成长的 agent —— 这里取"完整链路"切片。"""

    def __init__(self, model_path: str = None, memory: Memory = None):
        # 第 01 课:LLM 客户端(已封装为 Qwen / OpenAI 兼容 API)
        self.llm = LLMClient(model_path)
        # 第 06 课:状态
        self.state = AgentState()
        # 第 06 课:轨迹(两条路径统一往这里记:线性 loop 与 DAG 调度)
        self.trajectory = Trajectory()
        # 第 07 课:记忆。允许外部注入共享 memory(进程级长期记忆)
        self.memory = memory if memory is not None else Memory()
        # 第 10 课:DAG 跑完后的复盘数据(可观测)。
        # last_graph    = 规划出的依赖图;last_schedule = 每个节点的起止时间线
        self.last_graph: list = []
        self.last_schedule: list = []

    # ============================================================
    # 第 06 课:agent loop
    # ============================================================

    def agent_step(self, user_input: str) -> Finding:
        """执行 agent loop 的一步:观察(历史)→ 决策(选工具)→ 行动(执行)。"""
        history = self._format_history()
        result = self.llm.function_calling(user_input, history=history)

        self.state.increment_step()

        finding = Finding(
            step=self.state.steps,
            tool=result["tool"],
            reason=result.get("reason", ""),
            arguments=result.get("arguments", {}),
            result=result.get("result", result.get("reply")),
        )

        # 防空转:这步与上一步同工具同参数 → 模型在原地打转,直接终止
        prev = self.state.last_action
        is_repeat = (
            prev is not None and prev.tool == finding.tool and prev.arguments == finding.arguments
        )

        self.trajectory.add(finding)
        self.state.last_action = finding

        # remember 工具 → Agent 真正写入长期记忆
        if finding.tool == "remember":
            fact = finding.arguments.get("fact")
            if fact:
                self.memory.add(fact)

        # 模型主动认为计划有问题 → 重新规划剩余步骤
        if finding.tool == "replan":
            problem = (
                finding.arguments.get("problem") or finding.reason or "模型判断当前计划无法继续"
            )
            self._replan(user_input, problem=problem)
            return finding

        # 工具执行报错 → 也触发重规划
        if self._looks_failed(finding):
            self._replan(
                user_input, problem=f"执行第{self.state.plan_cursor + 1}步时出错：{finding.result}"
            )
            return finding

        # 正常完成 → 计划游标前移
        if finding.tool not in ("finish", "replan"):
            self.state.plan_cursor += 1

        # 终止:模型调 finish,或检测到重复空转
        if finding.tool == "finish" or is_repeat:
            self.state.mark_done()

        return finding

    def _looks_failed(self, finding: Finding) -> bool:
        """工具层失败判定:只看结果里的 ok 字段(registry 失败时统一返回 ok=False)。"""
        r = finding.result
        return isinstance(r, dict) and r.get("ok") is False

    def _replan(self, goal: str, problem: str):
        """重新规划剩余步骤。已完成的保留,只重排没做的;有次数上限防死循环。"""
        if self.state.replan_count >= 2:
            print(
                f"[重规划] 已达上限({self.state.replan_count} 次)仍未解决,终止任务。问题：{problem}"
            )
            self.state.mark_done()
            return
        self.state.replan_count += 1

        done_steps = (self.state.current_plan or [])[: self.state.plan_cursor]
        print(f"[重规划 #{self.state.replan_count}] 触发原因：{problem}")

        remaining = self.llm.make_plan(goal, done_steps=done_steps, problem=problem)
        if remaining:
            self.state.current_plan = done_steps + remaining
        else:
            print("           重规划失败(未生成新步骤),终止任务。")
            self.state.mark_done()

    def _format_history(self) -> str:
        """拼给模型看的上下文:长期记忆 + 当前计划(导航)+ 本轮轨迹。"""
        parts = []

        memories = self.memory.get_all()
        if memories:
            mem_lines = "\n".join(f"- {m}" for m in memories)
            parts.append(f"【你记得的事(长期记忆)】\n{mem_lines}")

        if self.state.current_plan:
            plan_lines = []
            for i, step in enumerate(self.state.current_plan):
                mark = (
                    "▶"
                    if i == self.state.plan_cursor
                    else ("✓" if i < self.state.plan_cursor else "·")
                )
                plan_lines.append(f"  {mark} {i + 1}. {step}")
            plan_done = self.state.plan_cursor >= len(self.state.current_plan)
            if plan_done:
                guide = (
                    "\n计划里所有步骤都已完成(全部为 ✓),请直接调用 finish 结束,不要重复任何步骤。"
                )
            else:
                guide = "\n请执行 ▶ 指向的这一步。若发现计划本身有问题、无法继续,调用 replan 重新规划剩余步骤。"
            parts.append("【当前计划】(▶=该做的这一步,✓=已完成)\n" + "\n".join(plan_lines) + guide)

        if len(self.trajectory) > 0:
            traj_lines = "\n".join(
                f"第{f.step}步: 调用 {f.tool}({f.reason})→ 结果: {f.result}"
                for f in self.trajectory.get_all()
            )
            parts.append(f"【本次任务已完成的步骤】\n{traj_lines}")

        return "\n\n".join(parts)

    def run_loop(self, user_input: str, max_steps: int = 6) -> dict:
        """运行 agent loop 多步,返回 {"trajectory": [...], "result": 汇总文本}。"""
        self.state.reset()
        self.trajectory.clear()
        self.state.current_plan = self.llm.make_plan(user_input)
        while not self.state.done and self.state.steps < max_steps:
            self.agent_step(user_input)
        final_result = self.llm.summarize(user_input, self._format_trajectory())
        return {"trajectory": self.trajectory.get_all(), "result": final_result}

    def _format_trajectory(self) -> str:
        return "\n".join(
            f"第{f.step}步: 调用 {f.tool}({f.reason})→ 结果: {f.result}"
            for f in self.trajectory.get_all()
        )

    # ============================================================
    # 第 10 课:AoT —— 依赖图 + 动态调度执行
    # ============================================================

    def _execute_graph(self, nodes: list, display) -> dict:
        """执行依赖图,并把调度状态【接进 Agent 的统一状态】。

        这是"两条路径状态统一"的关键:DAG 调度本身的 completed/running 仍由
        GraphExecutor 内部管(那是它的私事),但【每个节点的完成】会被这里:
          1. 记进 self.trajectory(和线性 loop 一样,事后能复盘每一步);
          2. 推进 self.state.steps(共用同一个步数计数器);
          3. 记进 self.last_schedule(起止时间线,用来看谁和谁真并行了)。
        on_event 由 GraphExecutor 在【单一调度线程】里串行回调,所以这里直接
        改 trajectory/state 是线程安全的,不必加锁。

        Args:
            nodes: 依赖图节点列表
            display: 展示回调 display(event, node, extra, entry) —— 由调用方决定
                     是 print 还是 emit;entry 是该节点的 schedule 记录(done 时才有)
        Returns:
            GraphExecutor 的结果 {node_id: result}(或 {"_error": ...})
        """
        from .graph_executor import GraphExecutor
        from .tools import build_default_registry

        # 每次图执行前重置本轮状态(memory 不动,它是跨任务的)
        self.state.reset()
        self.trajectory.clear()
        self.last_graph = list(nodes)
        self.last_schedule = []

        t0 = time.perf_counter()
        started_at: dict = {}

        def on_event(event, node, extra):
            nid = node["id"]
            now = time.perf_counter() - t0
            if event == "start":
                started_at[nid] = now
                display("start", node, None, None)
            elif event == "done":
                begin = started_at.get(nid, now)
                entry = {
                    "node_id": nid,
                    "tool": node["tool"],
                    "subtask": node.get("subtask", ""),
                    "depends_on": list(node.get("depends_on", [])),
                    "started_ms": round(begin * 1000),
                    "finished_ms": round(now * 1000),
                    "duration_ms": round((now - begin) * 1000),
                }
                self.last_schedule.append(entry)
                # 接进统一状态:步数 + 轨迹(step = 完成顺序)
                self.state.increment_step()
                self.trajectory.add(
                    Finding(
                        step=self.state.steps,
                        tool=node["tool"],
                        reason=node.get("subtask", ""),
                        arguments={"node_id": nid, "depends_on": entry["depends_on"]},
                        result=extra,
                    )
                )
                display("done", node, extra, entry)

        registry = build_default_registry()
        executor = GraphExecutor(self.llm, registry, on_event=on_event)
        return executor.run(nodes)

    def _format_parallel_summary(self) -> str:
        """根据 last_schedule 算出哪些节点【时间区间重叠】= 真并行,生成复盘文本。"""
        sched = self.last_schedule
        lines = []
        for e in sorted(sched, key=lambda x: x["finished_ms"]):
            overlaps = [
                o["node_id"]
                for o in sched
                if o["node_id"] != e["node_id"]
                and o["started_ms"] < e["finished_ms"]
                and e["started_ms"] < o["finished_ms"]
            ]
            tag = ("  ∥ 与 " + "、".join(overlaps) + " 并行") if overlaps else "  (无重叠)"
            lines.append(
                f"  #{e['node_id']}({e['tool']}) [{e['started_ms']}–{e['finished_ms']}ms]{tag}"
            )
        return "\n".join(lines) + "\n"

    def run_graph(self, user_input: str, verbose: bool = True) -> dict:
        """AoT 版执行:规划成依赖图 → 动态调度执行器跑(无依赖并行)。

        返回值新增 trajectory / schedule,使 DAG 路径和线性路径一样【事后可复盘】。
        """
        nodes = self.llm.make_graph(user_input)
        if not nodes:
            return {
                "graph": [],
                "results": {},
                "result": "规划失败:没有生成有效的图。",
                "trajectory": [],
                "schedule": [],
            }

        def display(event, node, extra, entry):
            if not verbose:
                return
            if event == "start":
                print(f"  ▶ 启动 {node['id']}({node['tool']})")
            elif event == "done":
                print(f"  ✓ 完成 {node['id']}({entry['duration_ms']}ms)→ {_short(extra)}")

        results = self._execute_graph(nodes, display)
        if isinstance(results, dict) and "_error" in results:
            return {
                "graph": nodes,
                "results": results,
                "result": f"图校验失败:{results['_error']}",
                "trajectory": self.trajectory.get_all(),
                "schedule": self.last_schedule,
            }

        traj_text = "\n".join(
            f"{n['id']}({n['tool']})→ 结果: {results.get(n['id'])}" for n in nodes
        )
        final_result = self.llm.summarize(user_input, traj_text)
        return {
            "graph": nodes,
            "results": results,
            "result": final_result,
            "trajectory": self.trajectory.get_all(),
            "schedule": self.last_schedule,
        }

    # ============================================================
    # 流式驱动(为 SSE chat() 新增):通过 emit 回调把过程实时吐出
    # ============================================================

    def run_loop_streamed(self, user_input: str, emit, max_steps: int = 6):
        """线性 agent loop 的流式版:每步进展 + 最终汇总都经 emit(text) 吐出。"""
        self.state.reset()
        self.trajectory.clear()

        emit("🧭 正在规划步骤…\n")
        self.state.current_plan = self.llm.make_plan(user_input)
        if self.state.current_plan:
            emit(
                "📋 计划：\n"
                + "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(self.state.current_plan))
                + "\n\n"
            )

        while not self.state.done and self.state.steps < max_steps:
            before_replan = self.state.replan_count
            finding = self.agent_step(user_input)
            emit(
                f"第{finding.step}步 → 调用 `{finding.tool}`"
                + (f"({finding.reason})" if finding.reason else "")
                + f"\n   结果: {_short(finding.result)}\n"
            )
            if self.state.replan_count > before_replan:
                emit(f"   ⚠️ 触发重规划(第 {self.state.replan_count} 次),已重排剩余步骤\n")

        if self.memory.get_all():
            emit("🧠 长期记忆: " + "；".join(self.memory.get_all()) + "\n")

        emit("\n💬 ")
        for delta in self.llm.summarize_stream(user_input, self._format_trajectory()):
            emit(delta)

    def run_graph_streamed(self, user_input: str, emit):
        """DAG(AoT)动态调度的流式版:规划 → 并行调度过程 → 复盘 → 最终汇总,全经 emit 吐出。"""
        emit("🧭 正在规划依赖图…\n")
        nodes = self.llm.make_graph(user_input)
        if not nodes:
            emit("规划失败:没有生成有效的依赖图。")
            return

        emit("📋 依赖图(参数执行时再填):\n")
        for n in nodes:
            dep = "、".join(n.get("depends_on", [])) or "无"
            emit(f"  {n['id']}: {n['tool']} — {n.get('subtask', '')}(依赖: {dep})\n")
        emit("\n⚙️ 开始动态调度(无依赖的并行跑,依赖一满足即启动):\n")

        def display(event, node, extra, entry):
            if event == "start":
                emit(f"  ▶ 启动 {node['id']}({node['tool']})\n")
            elif event == "done":
                emit(f"  ✓ 完成 {node['id']}({entry['duration_ms']}ms)→ {_short(extra)}\n")

        results = self._execute_graph(nodes, display)

        if isinstance(results, dict) and "_error" in results:
            emit(f"\n图校验失败:{results['_error']}")
            return

        # 调度复盘(可观测):用各节点的起止区间,标出谁和谁真正并行了
        emit("\n🔭 调度复盘(完成顺序 / 区间ms / 并行情况):\n")
        emit(self._format_parallel_summary())

        traj_text = "\n".join(
            f"{n['id']}({n['tool']})→ 结果: {results.get(n['id'])}" for n in nodes
        )
        emit("\n💬 ")
        for delta in self.llm.summarize_stream(user_input, traj_text):
            emit(delta)
