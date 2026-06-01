# Docker 部署

## 现状

- 公网入口:`https://agent.x-lin7.com`
- 运行方式:轻量服务器 Docker Compose,容器名 `agent-minimal`
- 镜像仓库:`crpi-hych6zm27jhqndgw.cn-hongkong.personal.cr.aliyuncs.com/qv7k/agent-minimal`
- 网络:复用 `from-fullstack-to-ai` 的 `infra_ftai-net`
- 网关:复用 `ftai-caddy`,反代 `agent.x-lin7.com -> agent-minimal:8000`

## 云效流水线

新流水线使用仓库根目录 [flow.yml](../flow.yml):

0. `代码源`:从 Codeup 仓库 `agent-minimal/main` 拉代码,push 到 `main` 自动触发
1. `代码检查`:安装 Python 3.12,执行 `uv sync --frozen`,`ruff check`,`ruff format --check`
2. `镜像构建`:使用 `DockerBuildPushACR` 构建并推送 Docker 镜像
3. `部署包`:上传 `docker-compose.yml` 作为部署制品
4. `主机部署`:VMDeploy 到主机组 `345908`,在 `/opt/agent-minimal` 执行 `docker compose pull && up -d`
5. `验证`:容器内 `/healthz` 和 Caddy 到容器的 `/healthz`

镜像 tag 使用 `${CI_COMMIT_ID}`,不是裸 `latest`。回滚时重跑历史流水线即可。

## 云效变量

YAML 已写死 Codeup 服务连接 `xrhfc959mqp5nqye`、ACR 服务连接 `qej3ipnct3c44kni` 和主机组 `Ygtt0gTV53OffUF7`。

如果服务器 Docker 尚未登录 ACR,再加两个加密变量:

```bash
REGISTRY_USERNAME=<ACR 用户名>
REGISTRY_PASSWORD=<ACR 密码>
```

服务器 `/opt/agent-minimal/.env` 只放应用运行时变量:

```bash
DEEPSEEK_API_KEY=...
```

## 手工检查

```bash
docker ps --filter name=agent-minimal
docker inspect agent-minimal --format '{{.State.Health.Status}}'
docker exec agent-minimal python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/healthz',timeout=3).read().decode())"
docker exec ftai-caddy wget -qO- --timeout=3 http://agent-minimal:8000/healthz
```
