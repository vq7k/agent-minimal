# alpha · S4 DB 部署方案

| 项 | 内容 |
|---|---|
| 文档版本 | v0.2 |
| 日期 | 2026-06-06 |
| 目标 | 先补持久化会话记忆的 DB 底座 |
| 结论 | 共享 PostgreSQL + 独立 database/role |

---

## 1. 背景

原 S4「记忆微调」只利用页面会话内的完整 `messages`。
这不是持久化记忆，页面刷新后历史会丢失。

infra 已提供共享 PostgreSQL：`ftai-postgres`。
隔离模型是“一个项目 = 一个独立 database + 一个独立 role(owner)”。

因此 S4 先改为 DB 底座：让 alpha 能把会话消息保存到 PostgreSQL，
后续再基于 DB 历史做偏好抽取和增量调整。

参考：

```text
/Users/xuelin/projects/from-fullstack-to-ai/infra/docs/shared-database.md
```

---

## 2. 选型

| 方案 | 结论 | 原因 |
|---|---|---|
| 共享 PostgreSQL | 采用 | 已有实例、生产可直接走 Docker 内网、隔离模型清晰 |
| SQLite | 不采用 | 单文件虽轻，但现有 infra 已有共享 PG，生产部署不必再维护文件 volume |
| Redis | 不采用 | 偏缓存，不适合最小持久化历史 |
| localStorage | 不采用 | 只在前端，不是真后端记忆 |

---

## 3. 项目标识

项目名：

```text
agent_minimal
```

它同时作为：

- database 名：`agent_minimal`
- role 名：`agent_minimal`

开通由 infra 侧执行一次：

```bash
PROJ_PASSWORD='请填 >=16 位强密码' \
bash infra/scripts/provision-shared-db.sh agent_minimal
```

业务侧只保存本项目 role 密码，不接触 superuser。

---

## 4. 连接方式

本地开发：

```bash
DATABASE_URL=postgresql://agent_minimal:<密码>@localhost:5450/agent_minimal
```

生产容器：

```bash
DATABASE_URL=postgresql://agent_minimal:<密码>@ftai-postgres:5432/agent_minimal
```

原因：

- 本地走 host 端口映射 `localhost:5450`。
- 生产和 `ftai-postgres` 在同一个 Docker 网络 `infra_ftai-net`。
- 不开放公网数据库端口。

---

## 5. Docker Compose 调整

当前 `docker-compose.yml` 已经加入：

```yaml
networks:
  ftai-net:
    external: true
    name: infra_ftai-net
```

因此 S4 不需要新增 DB 容器，也不需要 volume。

只需要在服务器 `/opt/agent-minimal/.env` 增加：

```bash
DATABASE_URL=postgresql://agent_minimal:<密码>@ftai-postgres:5432/agent_minimal
```

本地 `.env` 可使用：

```bash
DATABASE_URL=postgresql://agent_minimal:<密码>@localhost:5450/agent_minimal
```

---

## 6. 应用依赖

PostgreSQL 不能用 Python stdlib 直连。
实现时新增一个轻量驱动：

```toml
psycopg[binary]>=3
```

不用 SQLAlchemy，不引入 ORM。

理由：

- 只需要建表、插入消息、按会话读取消息。
- SQL 很少，直接写更清楚。
- 避免为了一个消息表引入重框架。

---

## 7. 数据表

只先存消息，不存复杂 profile。

```sql
CREATE TABLE IF NOT EXISTS alpha_messages (
  id BIGSERIAL PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_alpha_messages_conversation_id_id
ON alpha_messages (conversation_id, id);
```

说明：

- `conversation_id` 由前端生成并保存。
- `role/content` 复用现有消息结构。
- 不使用 UUID 类型，避免额外扩展；UUID 字符串直接存 TEXT。

---

## 8. API 影响

后续实现时新增会话维度。

发送请求：

```json
{
  "conversation_id": "uuid",
  "message": "周六去杭州玩一天"
}
```

历史接口：

```text
GET /agents/alpha/conversations/{conversation_id}/messages
```

后端流程：

```text
读取 conversation_id 历史
追加本轮 user message
调用 alpha.chat(full_messages)
收集 assistant reply
写入 assistant message
返回 SSE
```

页面刷新后：

```text
前端保留 conversation_id
调用历史接口
恢复 messages
```

---

## 9. 安全与隔离

- 使用 `agent_minimal` role 连接 `agent_minimal` database。
- 不保存、不使用 `ftai` superuser。
- 不开放公网数据库端口。
- 生产只走 Docker 内网 `ftai-postgres:5432`。
- 远程排查生产库时走 SSH 隧道，不改安全组。

---

## 10. 备份与回滚

备份单库：

```bash
docker exec ftai-postgres pg_dump \
  -U agent_minimal \
  -d agent_minimal \
  -Fc \
  -f /tmp/agent_minimal.dump
```

回滚镜像不会删除 DB，因为数据库在共享 PostgreSQL 实例内。

如果要清空 alpha 历史：

```sql
TRUNCATE TABLE alpha_messages;
```

---

## 11. 最小验收

| 场景 | 期望 |
|---|---|
| 容器重启 | 历史仍在 |
| 页面刷新 | 同一 conversation_id 能恢复历史 |
| 新会话 | 新 conversation_id 不混入旧历史 |
| 数据库不可用 | 返回明确错误，不静默丢消息 |

---

## 12. 连通性 demo

本仓库提供一个安全 demo：

```text
scripts/demo_online_db.py
```

它只读取连接信息，并创建 `TEMP TABLE` 测试写权限；事务结束后临时表自动清理。
不会创建或修改持久业务表。

本地测本机共享 PG：

```bash
DATABASE_URL='postgresql://agent_minimal:<密码>@localhost:5450/agent_minimal' \
  uv run --with 'psycopg[binary]>=3' python scripts/demo_online_db.py
```

本地测生产 PG，先开 SSH 隧道：

```bash
ssh -i "$SSH_KEY" -N -L 15432:127.0.0.1:5450 "$SSH_USER@$SSH_HOST"
```

另开终端执行：

```bash
DATABASE_URL='postgresql://agent_minimal:<密码>@localhost:15432/agent_minimal' \
  uv run --with 'psycopg[binary]>=3' python scripts/demo_online_db.py
```

---

## 13. 后续切片

DB 底座完成后，再做：

1. storage 模块：建表、写入、读取。
2. 后端会话消息 API。
3. 前端保存 `conversation_id` 并恢复历史。
4. 基于 DB 历史做偏好抽取与增量调整。
