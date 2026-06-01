"""FastAPI 服务 —— 只做路由分发,把每个 /agents/{name}/chat 接到对应模块的 chat()。

约定:每个 agent 模块导出一个 `chat(messages) -> Iterator[str]`,产出 SSE 数据行
(每行形如 'data: {...}\\n\\n')。具体怎么实现(用哪家 LLM、怎么调工具、要不要
流式、要不要记忆)由各 agent 模块自己决定,本文件不关心。

新增 agent 步骤:
  1. 在 agents/ 下加一个子目录,实现 chat()
  2. 在下面 AGENTS 里加一行注册
"""

from collections.abc import Callable, Iterator
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents import alpha, bravo, charlie, delta

# 注册表:agent 名 -> 该模块的 chat 函数
AGENTS: dict[str, Callable[[list[dict]], Iterator[str]]] = {
    "alpha": alpha.chat,
    "bravo": bravo.chat,
    "charlie": charlie.chat,
    "delta": delta.chat,
}

FRONTEND_DIST = Path(__file__).resolve().parent / "frontend" / "dist"


class ChatRequest(BaseModel):
    messages: list[dict]


def create_app(frontend_dist: Path = FRONTEND_DIST) -> FastAPI:
    app = FastAPI(title="agent-minimal")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 联调放开,上线按前端域名收紧
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz() -> dict:
        # 给云效流水线 / nginx / 监控用,只判进程在不在
        return {"status": "ok"}

    @app.get("/agents")
    def list_agents() -> dict:
        return {"agents": sorted(AGENTS)}

    @app.post("/agents/{name}/chat")
    def chat(name: str, req: ChatRequest) -> StreamingResponse:
        handler = AGENTS.get(name)
        if handler is None:
            raise HTTPException(status_code=404, detail=f"unknown agent: {name}")

        stream: Iterator[str] = handler(req.messages)
        return StreamingResponse(stream, media_type="text/event-stream")

    index_html = frontend_dist / "index.html"
    assets_dir = frontend_dist / "assets"
    if index_html.exists():
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/")
        def frontend_index() -> FileResponse:
            return FileResponse(index_html, media_type="text/html")

        @app.get("/{full_path:path}")
        def frontend_fallback(full_path: str) -> FileResponse:
            requested_file = frontend_dist / full_path
            if requested_file.is_file():
                return FileResponse(requested_file)
            return FileResponse(index_html, media_type="text/html")

    return app


app = create_app()
