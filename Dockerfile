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

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# 直接用 venv 里的 uvicorn,不走 uv run(更快、运行时少一层)
CMD [".venv/bin/uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
