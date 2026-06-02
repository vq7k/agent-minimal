# Frontend

Vite + React + TypeScript + shadcn/ui 风格组件。

## 目录

```text
src/app/                            应用入口、页面路由、agent 导航
src/agents/alpha/                   Alpha 独立前端:page/api/types
src/agents/bravo/                   Bravo 独立前端:page/api/types
src/agents/charlie/                 Charlie 独立前端:page/api/types
src/agents/delta/                   Delta 独立前端:page/api/types
src/components/ui/                  shadcn/ui 风格基础组件
src/lib/utils.ts                    无业务工具,目前仅 cn()
```

协作规则:4 个 agent 负责人只改自己的 `src/agents/<name>/`。不要跨目录 import 其他 agent 的代码；公共聊天逻辑宁可重复，也不要上共享抽象。

## 本地开发

```bash
npm install
npm run dev
```

页面访问 `http://127.0.0.1:5173`。Vite proxy 会把 `/agents` 和 `/healthz` 转发到后端 `http://127.0.0.1:8000`。
