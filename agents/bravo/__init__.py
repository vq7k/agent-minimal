"""bravo agent —— 移植自 agents-from-scratch 学习项目的"完整链路"垂直切片。

能力:agent loop(ReAct)+ 工具调用 + 状态/记忆/轨迹 + 重规划 + DAG(AoT)动态调度。
实现代码在自包含子包 ./_chain/(不依赖也不影响其他 agent)。

两种执行模式(看用户这句话的开头):
  - 默认            → DAG 并行调度(run_graph):规划成依赖图,无依赖节点并行跑。
  - 以 /loop 开头   → 线性 agent loop(run_loop):逐步决策,展示状态/记忆/重规划。
  - 以 /dag  开头   → 显式指定 DAG。

可用工具(见 _chain/tools.py):
  - calculator       四则运算
  - analyze_emotion  中文情绪/意图分析(含阴阳怪气/讽刺识别)
  - finish/remember/replan  控制类(结束/记忆/重规划)

LLM:沿用 Qwen(DashScope OpenAI 兼容接口)。需在项目根 .env 配置:
  BRAVO_LLM_API_KEY=sk-xxx        # 或 DASHSCOPE_API_KEY=sk-xxx
  (可选)BRAVO_LLM_MODEL=qwen-plus / BRAVO_LLM_BASE_URL=...
为何不用 DeepSeek:本链路依赖 response_format=json_schema(strict) 与强制 tool_choice,
DeepSeek 暂不支持;Qwen 与 alpha 的 DeepSeek 配置用不同 env 前缀,互不干扰。

SSE:bravo 前端只解析 text/done 事件,所以这里把规划/调度/每步进展/最终汇总
全部转成 text 增量流式吐出。执行过程经"线程 + 队列"实时流式(展示 DAG 并行)。

铁律遵守:不 import 其他 agent、不改 server.py。
"""

import json
import queue
import threading
from collections.abc import Iterator

from ._chain.agent import Agent
from ._chain.memory import Memory

# 进程级长期记忆:跨请求保留,用来演示 remember 工具的"长期记忆"能力。
# (单进程内共享;高并发下是简单的共享列表,演示足够,生产可换持久化存储。)
_MEMORY = Memory()

_DONE = 'data: {"type":"done"}\n\n'


def _sse_text(delta: str) -> str:
    """把一段文本包成一条 SSE text 事件行。"""
    return f"data: {json.dumps({'type': 'text', 'delta': delta}, ensure_ascii=False)}\n\n"


def _last_user_message(messages: list[dict]) -> str:
    """取最后一条用户消息作为本次任务目标(链路是单目标驱动)。"""
    for m in reversed(messages):
        if m.get("role") == "user":
            return (m.get("content") or "").strip()
    return ""


def _parse_mode(goal: str) -> tuple[str, str]:
    """解析开头的模式前缀,返回 (mode, 去掉前缀后的目标)。"""
    for prefix, mode in (("/loop", "loop"), ("/循环", "loop"), ("/dag", "dag")):
        if goal.startswith(prefix):
            return mode, goal[len(prefix) :].strip()
    return "dag", goal  # 默认走 DAG 并行


def chat(messages: list[dict]) -> Iterator[str]:
    goal = _last_user_message(messages)
    if not goal:
        yield _sse_text("(没有收到用户输入)")
        yield _DONE
        return

    mode, goal = _parse_mode(goal)
    if not goal:
        yield _sse_text("(请在 /loop 或 /dag 后面跟上具体任务)")
        yield _DONE
        return

    # 执行过程在后台线程跑,通过线程安全队列把文本增量实时交给本生成器。
    # 原因:run_graph 的并行调度用 on_event 回调上报进展,回调里不能直接 yield,
    # 所以用"队列搭桥"——回调往队列塞,生成器从队列取并 yield 成 SSE。
    q: queue.Queue = queue.Queue()
    _SENTINEL = object()
    def emit(text: str):
        if text:
            q.put(text)

    def worker():
        try:
            agent = Agent(memory=_MEMORY)
            if mode == "loop":
                #下面这两个方法都留了一个hook，可以通过编写emit这个函数，把代码挂在预留的hook上运行
                agent.run_loop_streamed(goal, emit)
            else:
                agent.run_graph_streamed(goal, emit)
        except Exception as e:  # 任何异常都转成可见文本,避免前端干等
            emit(f"\n\n[出错] {type(e).__name__}: {e}")
        finally:
            q.put(_SENTINEL)
    #启动一个线程去执行worker函数里的代码
    threading.Thread(target=worker, daemon=True).start()

    while True:
        item = q.get()
        if item is _SENTINEL:
            break
        yield _sse_text(item)

    yield _DONE
