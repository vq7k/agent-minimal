"""delta agent —— 负责人:待认领。

你的任务:实现下面的 chat 函数,接收对话历史,产出 SSE 数据行。

完全自由:用哪家 LLM(DeepSeek / OpenAI / Claude / 本地 Ollama …)、怎么写工具调用循环、
要不要流式、要不要管理记忆、自己加哪些第三方库——都由你定,只要遵守:

  输入:messages = [{"role":"user"|"assistant", "content":"…"}, ...]   # 不含 system
  输出:每个 yield 一条 SSE 行,形如:  'data: {"type":"text","delta":"..."}\\n\\n'
        事件类型见 docs/api-contract.md(text / tool_call / tool_result / done)

铁律:
  - 别 import 别的 agent 模块(agents.alpha / bravo / charlie)
  - 别改 server.py
  - 第三方依赖加到 pyproject 的 [project.dependencies],跑 uv sync
"""

from collections.abc import Iterator


def chat(messages: list[dict]) -> Iterator[str]:
    # TODO: 实现你的 agent
    yield 'data: {"type":"text","delta":"delta 待实现"}\n\n'
    yield 'data: {"type":"done"}\n\n'
