# agent-minimal

最小**多 Agent 后端骨架**:FastAPI 路由 + 4 个完全独立的 agent 模块,经 SSE 对外供前端调用。

各 agent 用什么 LLM、怎么调工具、怎么管理记忆,完全由各负责人自己决定。骨架只负责路由 + 契约。

## 结构

```
server.py             FastAPI 路由,把 /agents/{name}/chat 分发到对应模块的 chat()
agents/               4 个独立模块,互不 import
├── alpha/__init__.py     def chat(messages) -> Iterator[str]
├── bravo/__init__.py
├── charlie/__init__.py
└── delta/__init__.py
docs/api-contract.md  前端对接契约(REST + SSE 事件格式)
```

## 跑起来

```bash
uv sync
uv run uvicorn server:app --reload
```

冒烟:

```bash
curl http://127.0.0.1:8000/agents
curl -N -X POST http://127.0.0.1:8000/agents/alpha/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"hi"}]}'
```

完整接口见 [docs/api-contract.md](docs/api-contract.md)。

## 给 agent 负责人

只改 `agents/<你的名字>/__init__.py`,实现:

```python
def chat(messages: list[dict]) -> Iterator[str]:
    yield 'data: {"type":"text","delta":"..."}\n\n'
    yield 'data: {"type":"done"}\n\n'
```

铁律:**别 import 别人的 agent 模块**、**别改 server.py**。需要新依赖加到 `pyproject.toml` 的 `[project.dependencies]`,跑 `uv sync`。
