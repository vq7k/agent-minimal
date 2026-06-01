# 构建 React 前端静态文件
FROM node:22-slim AS frontend-build

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com && npm ci
COPY frontend/ ./
RUN npm run lint && npm test -- --run && npm run build

# Python 3.12-slim,跟 ftai-ai 一致
FROM python:3.12-slim

# 用 pip 装 uv(简单稳)
RUN pip install --no-cache-dir uv -i https://mirrors.aliyun.com/pypi/simple

WORKDIR /app

# 先拷 lockfile,装依赖 — 让 docker 缓存这一层,改代码不重装依赖
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 再拷源码
COPY server.py ./
COPY agents/ ./agents/
COPY --from=frontend-build /frontend/dist ./frontend/dist

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# 直接用 venv 里的 uvicorn,不走 uv run(更快、运行时少一层)
CMD [".venv/bin/uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
