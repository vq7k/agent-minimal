# API 契约(前端对接)

后端为 REST + SSE 流式。**无状态**:对话历史由前端持有,每次请求带完整 `messages`。

Base URL(本地):`http://127.0.0.1:8000`

## GET /agents

列出可用 agent。

```json
{ "agents": ["alpha", "bravo", "charlie", "delta"] }
```

## POST /agents/{name}/chat

与某个 agent 对话,**SSE 流式**返回。

请求体:

```json
{
  "messages": [
    { "role": "user", "content": "你好" },
    { "role": "assistant", "content": "你好,我能帮你什么？" },
    { "role": "user", "content": "现在几点？" }
  ]
}
```

- `messages`:完整历史(不含 system,由后端各 agent 自行注入)。
- 角色:`user` / `assistant`。

响应:`Content-Type: text/event-stream`,每个事件一行 `data: {json}\n\n`。

事件类型(各 agent 至少要发 `text` 和 `done`,其余按需):

| type | 字段 | 含义 |
|------|------|------|
| `text` | `delta` | 模型输出的文字增量,前端拼接显示 |
| `tool_call` | `name`, `arguments` | 正在调用某工具(可显示"思考中…") |
| `tool_result` | `name`, `content` | 工具返回结果 |
| `done` | — | 本轮结束,前端可发下一轮 |

示例流:

```
data: {"type":"text","delta":"当前"}
data: {"type":"text","delta":"时间是"}
data: {"type":"tool_call","name":"current_time","arguments":{}}
data: {"type":"tool_result","name":"current_time","content":"2026-06-01 12:00:00"}
data: {"type":"text","delta":"12:00。"}
data: {"type":"done"}
```

错误:未知 agent → `404 {"detail":"unknown agent: xxx"}`。

## 前端示例(fetch + ReadableStream)

EventSource 只支持 GET,这里 POST,用 fetch 读流:

```js
async function chat(name, messages, onText) {
  const res = await fetch(`/agents/${name}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "", reply = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const blocks = buf.split("\n\n");
    buf = blocks.pop();                     // 末尾可能是半条,留到下次
    for (const b of blocks) {
      if (!b.startsWith("data: ")) continue;
      const ev = JSON.parse(b.slice(6));
      if (ev.type === "text") { reply += ev.delta; onText(reply); }
      else if (ev.type === "done") return reply;
    }
  }
  return reply;
}
```

多轮:把返回的 `reply` 作为 `{ role: "assistant", content: reply }` 追加进 `messages`,下轮带上。

## CORS

`server.py` 默认放开所有来源(`*`);上线按前端域名收紧。
