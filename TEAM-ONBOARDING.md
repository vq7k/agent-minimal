# 团队对齐清单 v3（2026-05-29）

面向「转行 AI 全栈」组队成员的**共同地基**。本清单只回答一个问题：每个人最少要会哪些东西，我们才能开始分工协作。

不是面试技术树，不是岗位路线图——那些各人按方向延伸。

---

## 平台说明

本清单的「**我的栈**」基于 **macOS（Apple M4 Pro）**。

每个模块下给出我在用的具体工具 + 它解决什么问题。

- **macOS 用户**：可以直接照抄我的栈，跨平台减少协作摩擦。
- **Windows 用户**：按每项「**作用**」自行调研对应工具（多数跨平台，少数需要换方案，比如 Homebrew、ClashX、Ghostty 等 macOS-only）。

---

## 进度表

L0 共 5 项（机器协议层）。L1 共 3 项（AI 协作层）。

| 模块 | 我 | 同学 A | 同学 B | ... |
|---|---|---|---|---|
| L0-0 终端/代理 | ✅ | ⬜ | ⬜ | |
| L0-1 包管理 | ✅ | ⬜ | ⬜ | |
| L0-2 Git/GitHub | ✅ | ⬜ | ⬜ | |
| L0-3 Python 工程化 | ✅ | ⬜ | ⬜ | |
| L0-4 HTTP/JSON/API | ✅ | ⬜ | ⬜ | |
| L1-5 Claude Code | ✅ | ⬜ | ⬜ | |
| L1-6 IDE + AI | ✅ | ⬜ | ⬜ | |
| L1-7 共同术语 | ✅ | ⬜ | ⬜ | |

---

## L0 机器协议（每人必装/必会）

### L0-0 终端 + shell + 代理

**目标**：熟悉命令行，配好代理，能稳定连外网 API。

**我的栈**：

| 工具 | 作用 |
|---|---|
| Ghostty | 终端 emulator（运行 shell 的 GUI app） |
| zsh | shell（解释命令、管理环境变量） |
| oh-my-zsh | zsh 配置框架（管插件/主题） |
| powerlevel10k | zsh 主题（prompt 显示 git 状态、路径、时间等） |
| ClashX | 系统代理 app（监听 `127.0.0.1:7890`） |

**通用要点**（与平台无关）：
- HTTP/HTTPS/SOCKS 代理三者的区别
- 环境变量 `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY` 的作用域
- 临时设代理 vs 写进 shell 配置文件 vs 系统全局代理 三种姿势

---

### L0-1 包管理

**目标**：现代统一的包管理。不要再用 `pip install` 裸装、`npm install -g` 污染全局。

**我的栈**：

| 工具 | 作用 |
|---|---|
| Homebrew | macOS 系统级二进制包管理（装 git、ollama、gh 等 CLI） |
| uv | Python 项目和虚拟环境管理（替代 pyenv + pip + venv + poetry 一整套） |
| pnpm | Node 包管理（替代 npm/yarn，省磁盘、装得快） |

**通用要点**：
- 虚拟环境的概念：为什么不能全局装 Python 包
- lockfile 的作用：`uv.lock` / `pnpm-lock.yaml`
- 项目级依赖 vs 全局工具（pipx / `uv tool`）

---

### L0-2 Git + GitHub

**目标**：会基本协作工作流，不是只会 `git add . && git commit -m "update"`。

**我的栈**：

| 工具 | 作用 |
|---|---|
| git | 版本控制 CLI（跨平台都有） |
| GitHub CLI (`gh`) | 在终端里做 PR/review/issue（替代切到浏览器） |

**通用要点**：
- 概念：clone / branch / commit / push / pull / merge / rebase
- 工作流：feature branch → PR → review → merge
- 协作禁忌：不要 force-push 到 main / 不要 commit 大文件 / 不要 commit secrets

---

### L0-3 Python 工程化最小集

**目标**：写出能被别人 `uv sync && uv run pytest` 跑起来的项目，不是 jupyter 散装 `.py`。

**配套范例**：[`python-minimal/`](./python-minimal/)

**我的栈**：

| 工具 | 作用 |
|---|---|
| uv | 依赖与虚拟环境管理（同 L0-1） |
| ruff | lint + format 一把梭（替代 black + isort + flake8） |
| pytest | 单元测试框架 |
| pyproject.toml | 项目元数据 + 依赖 + 工具配置都写这一个文件 |

**通用要点**（与平台无关，但仍要做到）：
- 标准项目结构：`src/<pkg>/` + `tests/`
- 不依赖本机绝对路径或个人环境变量
- 别人 clone 后两条命令能跑起来：`uv sync && uv run pytest`

---

### L0-4 HTTP / JSON / API 通识

**目标**：和大模型 API 打交道的基本素养。看到 `401 / 429 / SSE` 不慌。

**我的栈**：

| 工具 | 作用 |
|---|---|
| httpx | Python HTTP 客户端（同步 + 异步 + 流式一把抓） |
| curl | 命令行 HTTP 客户端（快速 debug、看 header） |

**通用要点**（纯概念，全平台一致）：
- HTTP method / status code / header / body
- JSON：什么能/不能放进 JSON（datetime、二进制、循环引用）
- 流式响应（SSE）：为什么 LLM 接口大多用它
- 用 `httpx` 调通一次 Claude 或 OpenAI 流式接口

---

## L1 AI 协作流（队伍统一的开发动作）

### L1-5 Claude Code（队伍主力 Agent CLI）

**目标**：终端里的 Agent 编程。这是这一年最大的生产力差。

**我的栈**：

| 工具 | 作用 |
|---|---|
| Claude Code | Anthropic 的官方 Agent CLI，跑在终端里完成多步任务 |
| `~/.claude/CLAUDE.md` | 全局指令（语言、风格、个人偏好） |
| 项目里的 `CLAUDE.md` | 项目级指令（这个仓的技术栈、约定） |
| skills / hooks / agents | Claude Code 的扩展机制 |

**通用要点**（跨平台）：
- 装：`npm i -g @anthropic-ai/claude-code`
- 配代理：shell alias 里挂 `HTTPS_PROXY` 环境变量
- 概念区分：**autocomplete vs chat vs agent**——能讲清楚三者边界

**备选**（知道差异即可）：Codex CLI / Gemini CLI

---

### L1-6 IDE + AI 集成

**目标**：IDE 内的 AI 协作。和 L1-5 互补，覆盖另一半工作场景。

**我的栈**：

| 工具 | 作用 |
|---|---|
| PyCharm / WebStorm / IntelliJ | JetBrains 系 IDE，Python / 前端 / Java |
| Claude / Codex 插件 | IDE 里直接调 LLM 做 inline edit / chat / agent |

**通用要点**：
- 任选一个 IDE：JetBrains 系 / Cursor / VS Code 都行
- 学三件事：**inline edit / chat side panel / agent mode**
- 知道何时用 IDE、何时用 CLI（短上下文用 IDE，长任务用 CLI）

---

### L1-7 共同术语对齐

**目标**：队伍内部用同一套词说同一件事，避免沟通成本。纯概念，与平台无关。

清单（每个人都能用一句话讲清楚 + 举一个自己干过的例子）：

| 术语 | 一句话定义 |
|---|---|
| Autocomplete | 行内补全，人在主导 |
| Chat | 对话式，人和 AI 轮流出招 |
| Agent | AI 自循环执行，人只看结果/中断 |
| RAG | 把外部知识检索后塞进 prompt |
| Embedding | 文本→向量，用来做相似度/检索 |
| Tool use / Function call | 让模型调用代码函数 |
| MCP | 标准协议，给 AI 暴露工具/数据/prompt |
| Context window | 模型一次能看多少 token |

---

## 完成 L0+L1 之后

这时候团队进入「分工」阶段。我（全栈方向）会牵头：
- 一个共享的项目脚手架仓（前后端 + LLM 集成 + 一键部署）
- 一份「我们队的标准 stack」短文档（FastAPI? Next? PG? Redis? 哪个 LLM API？）

其他人按各自方向开自己的延伸路线，但所有人共享这层地基。

---

## 不在本清单里的（故意的）

- 算法 / 数学 / 深度学习理论 → 各人按方向自学，不强求全员
- 系统设计面试题 → L0+L1 完成后再起独立轮次
- LeetCode → 个人事项，不放团队公共地基
- 本地模型 / Prompt Eval / 推理优化 → 进阶专题

---

*v3 / 2026-05-29 / 维护人：xuelin*
