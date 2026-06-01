# Frontend

Vite + React + TypeScript + shadcn/ui 风格组件。

## 目录

```text
src/App.tsx                         只挂载 AgentWorkbench
src/features/chat/hooks/            业务逻辑:加载 runtime、发送消息、维护状态
src/features/chat/components/       页面组件:布局、侧栏、消息区、消息气泡
src/features/chat/chat-state.ts     纯状态转换,可单测
src/lib/chat-stream.ts              POST SSE streaming 请求封装
src/components/ui/                  shadcn/ui 风格基础组件
```

## 本地开发

```bash
npm install
npm run dev
```

页面访问 `http://127.0.0.1:5173`。Vite proxy 会把 `/agents` 和 `/healthz` 转发到后端 `http://127.0.0.1:8000`。
