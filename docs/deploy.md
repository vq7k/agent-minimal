# 部署到阿里云轻量服务器(经云效流水线)

整体流程:**push 到云效 Codeup → 流水线 lint + 打包 → 推到轻量服务器 → systemd 重启**。

只需一次性配置。之后 `git push` 自动滚动发布。

---

## 一次性手工步骤

### 1. 服务器初始化(在轻量服务器上跑一次)

SSH 登上服务器(`ssh root@<你的服务器IP>`),按顺序执行:

```bash
# 装 uv(到 /root/.local/bin/uv,后续 systemd 直接用绝对路径)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 建应用目录(首次部署时流水线会自动放代码进来,先建空目录占位)
mkdir -p /opt/agent-minimal

# 把 DEEPSEEK_API_KEY 写到 .env(不入库,只在服务器上)
cat > /opt/agent-minimal/.env <<'EOF'
DEEPSEEK_API_KEY=你的真实 key
EOF
chmod 600 /opt/agent-minimal/.env

# 允许 8000 端口(轻量服务器防火墙)—— 也可以在阿里云控制台配
# ufw allow 8000/tcp        # Ubuntu
# firewall-cmd --add-port=8000/tcp --permanent && firewall-cmd --reload  # CentOS/Alinux
```

> `systemd unit` 不用手动放,流水线**首次部署时会自动**把 `deploy/agent-minimal.service` 拷到 `/etc/systemd/system/` 并 `enable`。

### 2. 云效控制台一次性配置

登录 https://flow.aliyun.com

**(a) 创建主机组**(关联你的轻量服务器)

- 左侧菜单 → **企业管理 / 设置** → **主机组管理** → **新建主机组**
- 类型选「**阿里云 ECS**」或「**自有主机**」(轻量服务器走「自有主机」)
- 添加主机:填**公网 IP**,绑 SSH 凭证(让云效生成密钥,把公钥粘到服务器 `~/.ssh/authorized_keys`,这样云效后续 SSH 免密)
- 主机组创建好后,**复制主机组 ID**(URL 里能看到,或主机组详情页有)
- 替换 [flow.yml](../flow.yml) 里的 `<MACHINE_GROUP_ID>`

**(b) 创建制品仓库服务连接**

- **企业管理 / 设置** → **服务连接** → **新建** → 选「**通用制品仓库**」
- 一般用云效自带的 `flow_generic_repo`,授权后会有个**服务连接 ID**
- 替换 [flow.yml](../flow.yml) 里的 `<SERVICE_CONNECTION_ID>`

**(c) 创建流水线**

- 顶部菜单 → **新建流水线** → 选「**基于 YAML 配置**」
- 关联仓库:**agent-minimal**(刚 push 的那个),分支 `main`
- 流水线源 YAML 路径:`flow.yml`(默认)
- 触发方式:**代码提交触发**(push 到 main 自动跑)

**(d) 跑一次验证**

提交一个改动(比如改 README)→ push → 在流水线页面看三阶段全绿,服务器上 `systemctl status agent-minimal` 看到 active(running)。

```bash
# 在服务器上验证
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/agents
```

外网:`http://<你的服务器IP>:8000/healthz`(防火墙放开后)。

---

## 日常工作流

```
本地改代码 → git push codeup main
                ↓
           云效流水线
        ┌──────┴──────┐
        │ 1. ruff lint │ 失败 → 修了再 push
        │ 2. 打包 tgz  │
        │ 3. 部署:    │
        │    scp tgz   │
        │    uv sync   │
        │    systemctl │
        │    restart   │
        │    curl /healthz │
        └──────┬──────┘
              成功(全绿)
```

回滚:重跑某次历史流水线即可(用旧的 artifact)。

## 排错

- **流水线 lint 阶段红**:本地 `uv run ruff check` 修了再 push。
- **build 阶段红、提示 service connection 找不到**:`<SERVICE_CONNECTION_ID>` 没填或写错。
- **deploy 阶段 SSH 不通**:云效公钥没加到服务器 `authorized_keys`;或服务器防火墙挡了 22 端口。
- **healthz 检查失败**:SSH 到服务器看 `journalctl -u agent-minimal -n 50`,常见是 `.env` 没写或 `DEEPSEEK_API_KEY` 错。
- **8000 外网打不开**:轻量服务器的防火墙(阿里云控制台「**防火墙**」面板)要单独放开 8000,这跟服务器内的 ufw/firewalld 是两套。

## 后续优化(可选,先不做)

- 绑域名 + HTTPS:服务器装 nginx + certbot,把 8000 反代到 443
- 多实例 / 蓝绿:云效流水线分批发布
- 监控告警:云效集成云监控
