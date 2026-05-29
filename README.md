# python-minimal

最小 Python 工程化范例。演示 **uv + ruff + pytest** 的标准 Python 项目结构。

> **Agent 学习 demo**：`agent.py` + 教学文档 [`docs/agent-tutorial.md`](docs/agent-tutorial.md)——一个文件看懂 Agent 的"工具调用循环"与流式输出。
>
> **文档规范**：本仓库 `docs/` 下由 AI 生成的文档统一遵循——经人工审核；事实性陈述用脚注 `[^…]` 标注信息源；AI 的主观取舍用 `⚠️AI决策` 标记，阅读时注意，可质疑可推翻。

## 包含

- src layout（`src/word_count/`）
- `pyproject.toml`（项目元数据 + dev 依赖 + ruff/pytest 配置都在这一个文件）
- `ruff`（lint + format 一把梭）
- `pytest`（单元测试）
- CLI 入口（标准库 argparse，零运行时依赖）

## 使用

前置：装好 `uv`。macOS: `brew install uv`。Windows：见 uv 官网。

```bash
cd python-minimal

# 同步依赖（首次或拉新代码后）
uv sync

# 跑测试
uv run pytest

# 跑 lint
uv run ruff check
uv run ruff format --check

# 跑 CLI（两种姿势）
echo "hello world" | uv run word-count -
uv run word-count README.md
```

## 项目结构

```
python-minimal/
├── pyproject.toml          # 单一事实源：依赖 + 工具配置
├── .python-version         # uv 用，pin Python 版本
├── .gitignore
├── src/
│   └── word_count/
│       ├── __init__.py
│       ├── core.py         # 纯函数 + dataclass
│       └── cli.py          # argparse CLI
└── tests/
    └── test_core.py        # pytest 测试
```

## 学习要点

1. **单一事实源**：所有元数据 / 依赖 / 工具配置都在 `pyproject.toml`。没有 `setup.py` / `setup.cfg` / `requirements.txt` / `tox.ini` 等散装文件。
2. **src layout**：包代码放在 `src/<pkg>/`，避免"误 import 本地目录而非已安装包"的坑。
3. **lockfile**：`uv sync` 会生成/读 `uv.lock`，保证别人 clone 后依赖完全一致。
4. **scripts entry**：`[project.scripts]` 让 `uv run word-count` 直接调用，不用 `python -m word_count.cli`。
5. **dev 依赖隔离**：`[dependency-groups]` 里的 dev 工具（pytest/ruff）不混入运行时依赖。

## 别人 clone 后跑通的最小命令

```bash
git clone <repo> && cd python-minimal
uv sync                      # 自动装 Python 3.12 + 依赖
uv run pytest                # 全绿
uv run ruff check            # 全绿
```

如果以上三条任一条挂了，说明工程化没对齐。
