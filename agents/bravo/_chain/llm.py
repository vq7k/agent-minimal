"""
LocalLLM —— 对 Qwen Plus(通义千问)API 的简单封装。

本类提供了与语言模型交互的极简接口。原项目使用本地 llama.cpp 推理,
这里改为调用阿里云 DashScope 的 OpenAI 兼容接口(默认模型 qwen-plus),
原因是本地小模型在结构化输出、规划、工具调用等任务上效果不够稳定。

类名与 generate() 接口刻意保持不变,因此 agent/ 与示例代码无需改动。
它刻意不包含任何魔法:
- 没有重试(在第 03 课加入)
- 没有 tool calling(在第 05 课加入)
- 没有记忆(在第 07 课加入)

只是文本进、文本出。

环境变量(都可在项目根目录的 .env 中设置):
- BRAVO_LLM_API_KEY   bravo 专用 key(优先);未设则回退 DASHSCOPE_API_KEY
- DASHSCOPE_API_KEY   阿里云百炼/DashScope 的 API Key(sk- 开头)
- BRAVO_LLM_MODEL     可选,默认 "qwen-plus"(可改 qwen-max / qwen-turbo)
- BRAVO_LLM_BASE_URL  可选,默认 DashScope 的 OpenAI 兼容地址

注:刻意用 BRAVO_ 前缀,与 alpha 的 DEEPSEEK_API_KEY / LLM_BASE_URL 隔离,
互不影响。bravo 沿用 Qwen 是因为本链路依赖 response_format=json_schema(strict)
与强制 tool_choice,这些 DeepSeek 暂不支持。
"""

import json
import os

from openai import OpenAI

try:
    # 自动加载项目根目录下的 .env(若安装了 python-dotenv)
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-plus"


def _resolve_api_key() -> str:
    """按优先级读取 API Key,兼容几种常见环境变量名。

    BRAVO_LLM_API_KEY 放最前:bravo 可用独立 key,与 alpha 的 DEEPSEEK_API_KEY 互不干扰。
    """
    for var in ("BRAVO_LLM_API_KEY", "DASHSCOPE_API_KEY", "LLM_API_KEY", "OPENAI_API_KEY"):
        key = os.getenv(var)
        if key:
            return key
    return ""


class LLMClient:
    """
    基于 Qwen Plus API 的极简封装。

    实际调用的是远程 API(DashScope 的 OpenAI 兼容接口),而非本地模型。
    """

    def __init__(
        self,
        model_path: str = None,
        temperature: float = 0,
        max_tokens: int = 2000,
        n_ctx: int = 2048,
    ):
        """
        初始化 LLM 客户端。

        Args:
            model_path: 兼容旧接口而保留。若传入的是 .gguf 路径会被忽略;
                        否则会被当作 Qwen 模型名使用(如 "qwen-plus"、"qwen-max")。
            temperature: 采样温度(0.0 = 确定性,1.0 = 有创造性)
            max_tokens: 每次响应生成的最大 token 数
            n_ctx: 兼容旧接口而保留,API 模式下无意义
        """
        # 解析模型名:忽略遗留的 gguf 路径(如 "models/llama-3-8b-instruct.gguf"),
        # 普通字符串按模型名用,否则回退到环境变量 / 默认值
        mp = str(model_path) if model_path else ""
        if mp and not mp.endswith(".gguf") and "\\" not in mp and not mp.startswith("models/"):
            self.model = mp
        else:
            self.model = os.getenv("BRAVO_LLM_MODEL", DEFAULT_MODEL)

        api_key = _resolve_api_key()
        if not api_key:
            raise RuntimeError(
                "未找到 bravo 的 LLM API Key。请在项目根目录 .env 设置 "
                "BRAVO_LLM_API_KEY 或 DASHSCOPE_API_KEY,或导出为环境变量。"
                "可从 https://bailian.console.aliyun.com/ 获取。"
            )

        base_url = os.getenv("BRAVO_LLM_BASE_URL", DEFAULT_BASE_URL)
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.temperature = temperature
        self.max_tokens = max_tokens

    def function_calling(self, prompt: str, history: str = None, force_tool: str = None) -> dict:
        """
        让模型在多个工具间自行选择并调用。

        流程（标准 function calling 两步走）：
        1. 把 prompt + 工具清单发给模型，模型决定调哪个工具、给什么参数
        2. 本地真正执行那个工具，返回结构化结果

        Args:
            prompt: 用户的请求
            history: 可选，之前几步走过的轨迹文本。传入后会作为 system 上下文，
                     让模型基于"已经做了什么"来决定下一步（多步 agent loop 用）。
            force_tool: 可选，强制调用指定名字的工具（tool_choice 锁定）。
                        AoT 节点执行时用：节点已经定了用哪个工具，这里只让模型
                        基于上游结果回填【参数】。好处是 OpenAI 会按该工具的
                        schema 强制填全 required 参数。

        Returns:
            {"tool": 工具名, "reason": 调用原因, "arguments": 参数, "result": 执行结果}；
            若模型没调用任何工具，返回 {"tool": None, "reason": "", "reply": 模型的文本回复}
        """
        # 工具 schema 和注册器都在 agent/tools.py。
        # 注册器里 analyze_emotion 的 client/model 依赖已经预先绑好，
        # 所以这里执行任何工具都只需传"模型给的参数"，分发逻辑统一。
        from .tools import TOOL_DEFINITIONS, build_default_registry

        registry = build_default_registry()

        # 组装 messages。
        # 关键经验：模型的注意力主要落在【最后一条 user 消息】上。若每步都只发原始
        # 目标（如"帮我算25×4"），即使把"已经算过了"写进 system，模型也会像第一次听到
        # 一样反复调同一个工具。所以有进展时，把"进展 + 现在该判断什么"写进 user 消息，
        # 让模型基于【当前状态】决策，而不是基于【最初的指令】。（已用对照实验验证。）
        messages = [
            {
                "role": "system",
                "content": "你是一个分步执行任务的 agent。每一步只调用一个工具。"
                "用户的真实目标一旦达成（看已完成步骤里的实际结果），立刻调用 finish 结束；"
                "绝不重复已经做过、已经有结果的步骤。",
            }
        ]
        if history:
            user_content = (
                f"原始目标：{prompt}\n\n"
                f"目前的进展：\n{history}\n\n"
                "请判断：上面的进展是否已经达成原始目标？\n"
                "- 已达成（想做的事在进展里已经有结果）→ 调用 finish 结束，不要重复。\n"
                "- 未达成 → 调用对应工具，去做还【没做】的那一件事。"
            )
        else:
            user_content = prompt
        messages.append({"role": "user", "content": user_content})

        # tool_choice：默认 auto 让模型自选；force_tool 时锁定到指定工具
        tool_choice = "auto"
        if force_tool:
            tool_choice = {"type": "function", "function": {"name": force_tool}}

        # 第 1 步：让模型决定调哪个工具（force_tool 时只让它回填参数）
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice=tool_choice,
            temperature=0,
        )
        message = response.choices[0].message

        # 模型没调工具（比如普通闲聊），直接返回它的文本
        if not message.tool_calls:
            return {"tool": None, "reason": "", "reply": message.content}

        # 第 2 步：本地执行模型选中的那个工具——交给注册器统一分发
        call = message.tool_calls[0]
        name = call.function.name

        # 模型偶尔会在字符串值里塞未转义的真实换行符，标准 json 会报错。
        # strict=False 允许字符串内出现裸控制字符（换行/制表符），不改动内容本身。
        try:
            args = json.loads(call.function.arguments, strict=False)
        except json.JSONDecodeError as e:
            return {
                "tool": name,
                "reason": "",
                "arguments": {},
                "result": {"ok": False, "error": f"工具参数 JSON 解析失败: {e}"},
            }

        # reason 是元信息（模型给的"为什么调"），不是工具真正的参数，
        # 先抽出来，避免把它传进 calculator()/analyze_emotion() 导致报错。
        reason = args.pop("reason", "")
        result = registry.execute(name, **args)

        return {"tool": name, "reason": reason, "arguments": args, "result": result}

    def make_plan(self, goal: str, done_steps: list[str] = None, problem: str = None) -> list[str]:
        """
        为目标生成一个分步计划（纯结构化输出，不走 function calling）。

        两种用法：
        - 初次规划：只传 goal，返回完整步骤清单。
        - 重新规划：额外传 done_steps（已完成的步骤）和 problem（出了什么问题），
          模型据此只规划【剩余】步骤，绕开已知问题。

        Args:
            goal: 总目标
            done_steps: 已经完成的步骤描述（重规划时用）
            problem: 触发重规划的问题描述（重规划时用）

        Returns:
            步骤文字描述的列表；失败返回 []
        """
        schema = {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "完成目标所需的步骤，每步一句话，可执行、有顺序",
                },
            },
            "required": ["steps"],
            "additionalProperties": False,
        }

        if done_steps or problem:
            sys = (
                "你是规划助手。原计划执行中遇到了问题，请【重新规划剩余步骤】。"
                "不要重复已完成的步骤，并设法绕开已发生的问题。只输出 JSON。"
            )
            user = (
                f"总目标：{goal}\n"
                f"已完成的步骤：\n" + "\n".join(f"- {s}" for s in (done_steps or [])) + "\n"
                f"遇到的问题：{problem}\n"
                f"请给出剩余步骤。"
            )
        else:
            sys = (
                "你是规划助手。把用户的目标拆成有顺序、可执行的步骤。\n"
                "可用的能力（每一步最多对应其中一个）：计算器、情绪/意图分析、记住事实。\n"
                "重要规则：\n"
                "1. 一步 = 一次能力调用就能完成的事。【一次能完成的，绝不拆成多步】。\n"
                "   例：'算 25×4' 就是【一步】，不要拆成'写竖式→计算→验证'。\n"
                "   例：'分析这句话情绪' 就是【一步】，不要拆成'读句子→判断→总结'。\n"
                "2. 不要加'验证结果''总结'这类多余步骤——能力调用本身已给出结果。\n"
                "3. 简单目标通常就 1 步。只有目标确实包含多件独立的事时，才给多步。\n"
                "只输出 JSON。"
            )
            user = f"目标：{goal}"

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
            max_tokens=self.max_tokens,
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "plan", "schema": schema, "strict": True},
            },
        )
        try:
            data = json.loads(response.choices[0].message.content, strict=False)
            return data.get("steps", [])
        except json.JSONDecodeError:
            return []

    def make_graph(self, goal: str, memory: list[str] = None) -> list[dict]:
        """
        把目标规划成一张【依赖图】（AoT），只规划"步骤 + 依赖关系"，不填参数。

        这是两阶段设计的第一阶段：
        - 此处：只决定有哪些步骤、每步用哪个工具、谁依赖谁（结构）。
        - 执行阶段：跑到每个节点时，再基于上游结果【动态回填参数】并执行。
        所以节点里没有 arguments，只有 subtask（这一步要做什么的文字描述）。

        Args:
            goal: 总目标
            memory: 可选，已记住的长期事实。传入后规划时会把它当已知条件，
                    可直接把事实写进 subtask（如"计算 7+10"），不必再安排步骤去获取。

        Returns:
            节点列表，每个形如：
            {"id": "n1", "tool": "calculator",
             "subtask": "计算 12 加 8", "depends_on": []}
            失败返回 []
        """
        # 让模型知道有哪些工具可用
        from .tools import TOOL_DEFINITIONS

        tool_lines = []
        for t in TOOL_DEFINITIONS:
            fn = t["function"]
            tool_lines.append(f"- {fn['name']}: {fn['description'][:50]}")
        tools_desc = "\n".join(tool_lines)

        schema = {
            "type": "object",
            "properties": {
                "nodes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "节点唯一编号，如 n1/n2"},
                            "tool": {"type": "string", "description": "这个节点要调用的工具名"},
                            "subtask": {
                                "type": "string",
                                "description": "这一步具体要做什么（文字描述，不含参数细节）",
                            },
                            "depends_on": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "必须先完成的节点 id 列表，无依赖填 []",
                            },
                        },
                        "required": ["id", "tool", "subtask", "depends_on"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["nodes"],
            "additionalProperties": False,
        }

        sys = (
            "你是任务编排助手。把用户目标拆成一张依赖图：每个节点是一次工具调用，"
            "用 subtask 描述这一步做什么，并声明它依赖哪些前置节点。【不要填具体参数】，"
            "参数会在执行时再确定。\n"
            "关键：相互独立的事要拆成【各自的节点、depends_on 都为空】，这样它们能并行；"
            "只有真正需要前一步结果的，才写进 depends_on。\n"
            f"可用工具：\n{tools_desc}\n"
            "只输出 JSON。"
        )
        user = f"目标：{goal}"
        if memory:
            user += "\n\n【你已经记住的事实（规划时可直接引用，不必再安排步骤去获取）】\n" + "\n".join(
                f"- {m}" for m in memory
            )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
            max_tokens=self.max_tokens,
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "graph", "schema": schema, "strict": True},
            },
        )
        try:
            data = json.loads(response.choices[0].message.content, strict=False)
            return data.get("nodes", [])
        except json.JSONDecodeError:
            return []

    def summarize(self, goal: str, trajectory_text: str, memory: list[str] = None) -> str:
        """
        把整条执行轨迹汇总成给用户的最终结果。

        agent loop 跑完后，trajectory 里是一步步的工具调用记录（比较碎），
        这里让模型基于"目标 + 完整轨迹"写一段连贯的最终回复。

        Args:
            goal: 用户最初的目标
            trajectory_text: 整条轨迹的文本（每步调了什么、结果是什么）
            memory: 可选，已记住的长期事实，回答时可引用

        Returns:
            面向用户的最终总结文本
        """
        sys = (
            "你是结果汇总助手。下面是为完成用户目标而执行的一系列步骤及结果。"
            "请基于这些步骤，给用户一个连贯、直接的最终回复：综合各步结果回答目标，"
            "不要罗列工具调用细节，就像直接回答用户一样。"
        )
        user = f"用户目标：{goal}\n\n执行过程：\n{trajectory_text}\n\n请给出最终回复。"
        if memory:
            user = "【你记得的事实】\n" + "\n".join(f"- {m}" for m in memory) + "\n\n" + user
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
            max_tokens=self.max_tokens,
            temperature=0.3,
        )
        return (response.choices[0].message.content or "").strip()

    def summarize_stream(self, goal: str, trajectory_text: str, memory: list[str] = None):
        """summarize 的流式版本:逐字 yield 最终回复的文本增量。

        用于把汇总结果按 token 流式吐给前端(和 alpha 的逐字体验一致),
        逻辑与 summarize 完全相同,只是 stream=True。memory 同 summarize。
        """
        sys = (
            "你是结果汇总助手。下面是为完成用户目标而执行的一系列步骤及结果。"
            "请基于这些步骤,给用户一个连贯、直接的最终回复:综合各步结果回答目标,"
            "不要罗列工具调用细节,就像直接回答用户一样。"
        )
        user = f"用户目标：{goal}\n\n执行过程：\n{trajectory_text}\n\n请给出最终回复。"
        if memory:
            user = "【你记得的事实】\n" + "\n".join(f"- {m}" for m in memory) + "\n\n" + user
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
            max_tokens=self.max_tokens,
            temperature=0.3,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    def generate(self, prompt: str, temperature: float = None, stop: list[str] = None) -> str:
        """
        根据 prompt 生成文本。

        Args:
            prompt: 输入的文本 prompt
            temperature: 可选的温度覆盖值
            stop: 一个停止序列列表停止序列列表

        Returns:
            生成的文本字符串
        """
        # 字段顺序 = 模型生成顺序：先 reasoning（想），后 emotion（答）
        # 让模型"先推理再下结论"，比"先结论再补理由"更准（chain-of-thought）
        schema = {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "分析说话者的语气、用词、语境，推断其情绪的过程",
                },
                "topic": {"type": "string", "description": "用几个字浓缩这段话的主题"},
                "emotion": {
                    "type": "string",
                    "enum": ["happy", "sad", "angry", "panic", "neutral"],
                },
            },
            "required": ["reasoning", "topic", "emotion"],
            "additionalProperties": False,
        }

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "你是情绪分析师。给定一段话，完成：1) reasoning：分析语气、用词、语境，推断说话者的情绪；2) topic：用几个字概括主题；3) emotion：从 [happy, sad, angry, panic, neutral] 中选一个最贴切的。要求：先写 reasoning 再下 emotion 结论，只输出 JSON。",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.max_tokens,
            temperature=temperature if temperature is not None else self.temperature,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "qingxu_output",
                    "schema": schema,
                    "strict": True,
                },
            },
            stop=stop,
        )
        # .strip去除多余的换行符
        return (response.choices[0].message.content or "").strip()
