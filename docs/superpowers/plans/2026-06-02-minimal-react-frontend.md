# Minimal React Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal React chat workbench for `agent-minimal` and deploy it with the existing Docker/Flow pipeline.

**Architecture:** The frontend lives in `frontend/` as a Vite React TypeScript app using shadcn/ui components. Production build output is copied into the existing FastAPI image and served by `server.py` on `/`, while API routes remain `/agents/*` and `/healthz`.

**Tech Stack:** Vite, React, TypeScript, shadcn/ui-style components, Tailwind CSS, lucide-react, FastAPI static files, Docker multi-stage build, 云效 Flow.

---

### Task 1: Backend Static Hosting

**Files:**
- Modify: `server.py`
- Modify: `pyproject.toml`
- Create: `tests/test_static_frontend.py`

- [ ] Add a failing FastAPI test that expects `/` to return a generated frontend `index.html` when `frontend/dist` exists.
- [ ] Run `uv run pytest tests/test_static_frontend.py -q` and verify it fails because static hosting is not implemented.
- [ ] Implement static file mounting after API routes, with SPA fallback to `index.html`.
- [ ] Run the backend test and `uv run ruff check && uv run ruff format --check`.

### Task 2: Frontend Project

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/package-lock.json`
- Create: `frontend/index.html`
- Create: `frontend/src/*`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/tsconfig*.json`

- [ ] Add a failing Vitest test for parsing POST SSE events from a streamed response.
- [ ] Run `npm test -- --run` in `frontend/` and verify it fails because the parser is missing.
- [ ] Implement `chatStream()` using native `fetch` and `ReadableStream`.
- [ ] Build the single-page chat workbench with shadcn-style components: agent select, message list, input, send button, status badge.
- [ ] Run `npm test -- --run`, `npm run build`, and `npm run lint`.

### Task 3: Docker and Flow Deployment

**Files:**
- Modify: `Dockerfile`
- Modify: `flow.yml`
- Modify: `docs/deploy.md`
- Modify: `README.md`

- [ ] Update `Dockerfile` to build frontend assets in a Node stage and copy `frontend/dist` into the Python runtime image.
- [ ] Update Flow lint stage to include frontend install, lint, test, and build checks.
- [ ] Update docs with local frontend development and production URL.
- [ ] Run local verification: backend tests, frontend checks, Docker build.
- [ ] Commit, push to `codeup/main`, monitor 云效 run, and verify `https://agent.x-lin7.com/`.
