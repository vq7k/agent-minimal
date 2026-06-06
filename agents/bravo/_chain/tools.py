"""
Agent 的 tool 定义。

Tool 是 API,而不是能力。
Agent 请求 tool;由系统来执行它们。
"""

from collections.abc import Callable
from functools import partial
from typing import Any


def calculator(a: float, b: float, operation: str = "add") -> float:
    """
    简单的计算器 tool。

    Args:
        a: 第一个数
        b: 第二个数
        operation: "add"、"subtract"、"multiply"、"divide" 之一

    Returns:
        运算结果
    """
    if operation == "divide" and b == 0:
        raise ValueError("除数不能为 0")

    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y,
    }

    if operation not in operations:
        raise ValueError(f"未知运算: {operation}")

    return operations[operation](a, b)


def analyze_emotion(
    text: str,
    reasoning: str,
    topic: str,
    emotion: str,
    polarity: str,
    intensity: int,
    literal_emotion: str,
    suspected_sarcasm: bool,
    confidence: int,
) -> dict:
    """
    情绪/意图识别 tool（纯函数版）。

    关键设计：情绪分析的结果由模型在 function calling 选中本工具时、
    作为【参数】直接填好——"选工具"那一次 LLM 调用顺手就把分析做了。
    本函数不调 LLM，只接收并打包这些字段。一次 agent_step 只一次 API 调用。

    text 是被分析的原文：模型直觉上会想传"要分析的文本"，所以正式收下它，
    既避免模型传 text 时报 TypeError，也让结果里保留原文、更完整。

    为了应对"阴阳怪气/讽刺/谐音攻击"这类字面≠真意的情况，输出区分了
    字面情绪和实际情绪，并显式给出"是否怀疑讽刺"和"置信度"：
    - literal_emotion: 只看字面、不考虑反讽时的情绪
    - emotion:         结合可能的反讽后、推断的实际情绪
    - suspected_sarcasm: 是否怀疑这是阴阳怪气/讽刺/谐音梗
    - confidence:      对实际情绪判断的把握 1~5（越低越说明需要更多上下文）

    Args:
        text: 被分析的原文
        reasoning: 推理过程（也应说明为何怀疑/不怀疑讽刺）
        topic: 这段话的主题（几个字）
        emotion: 结合反讽后推断的实际情绪类别
        polarity: 实际情绪的正负向
        intensity: 实际情绪强度 1~5
        literal_emotion: 字面情绪类别
        suspected_sarcasm: 是否怀疑讽刺/阴阳/谐音
        confidence: 对实际情绪判断的把握 1~5

    Returns:
        含上述全部字段的 dict
    """
    return {
        "text": text,
        "reasoning": reasoning,
        "topic": topic,
        "emotion": emotion,
        "polarity": polarity,
        "intensity": intensity,
        "literal_emotion": literal_emotion,
        "suspected_sarcasm": suspected_sarcasm,
        "confidence": confidence,
    }


def finish(summary: str = "") -> dict:
    """
    结束 tool：模型认为任务已完成时调用它，agent loop 据此终止。

    它本身不"做"任何事，只是一个显式的终止信号，
    顺便带回一句总结。

    Args:
        summary: 对整个任务的简短总结

    Returns:
        {"done": True, "summary": ...}
    """
    return {"done": True, "summary": summary}


def replan(problem: str) -> dict:
    """
    重新规划 tool：模型发现当前计划本身有问题、无法继续时调用。

    和 finish/remember 一样只返回信号；真正的重规划由 Agent 在
    agent_step 检测到本工具被调用后执行。

    Args:
        problem: 当前计划哪里出了问题

    Returns:
        {"replan": True, "problem": problem}
    """
    return {"replan": True, "problem": problem}


def remember(fact: str) -> dict:
    """
    记忆 tool：模型遇到值得【跨任务长期记住】的事实时调用。

    和 finish 一样，本函数不直接写记忆（那样工具就得持有 Agent 的 memory），
    它只返回一个"请记住这条"的信号。真正的写入由 Agent 在 agent_step
    里检测到本工具被调用后执行 self.memory.add(fact)。
    ——工具报告，Agent 执行副作用，保持工具层不依赖 Agent 状态。

    Args:
        fact: 要长期记住的一条事实（如"用户的名字是 Alice"）

    Returns:
        {"remember": fact}
    """
    return {"remember": fact}


# function calling 的工具清单：交给模型看，由它决定调哪个。
# 注意 calculator 的参数和上面 calculator() 的签名保持一致。
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_emotion",
            "description": (
                "对一段中文文本做情绪/意图分析。当用户想知道某句话表达了什么情绪、什么意图时使用。"
                "很多话字面是夸、实际是骂（阴阳怪气/讽刺/谐音/拆字攻击）。请主动检查这些套路，但要分级判断，不要疑神疑鬼：\n"
                "【标 suspected_sarcasm=true，且 emotion 按反讽义判】——仅当有【明确文本证据】时：\n"
                "  ① 明确谐音脏话（如'根基吧'整体谐音'根鸡吧'、'雨我无瓜'）——注意：必须是谐音真能成立且改变语义，不要硬把'根基啊''稳定'这种正常词拆成脏话；\n"
                "  ② 异常空格/拆字（如'根 基 吧'）；③ 强反语句式（如'哇你可真是个人才呢''你说得都对'这类高度套路化的反话）。\n"
                "【标 suspected_sarcasm=false，但把 confidence 压到 1~2，并在 reasoning 里写明'可能反讽，需结合上下文'】——当只是【语境上有可能反讽、但没有上述文本证据】时（如'这工作真稳定''你今天来得真早'）。\n"
                "【正常判断】——没有任何可疑迹象时，按字面情绪正常分析。\n"
                "总原则：有文本证据才下反讽结论；只是'有可能'时，用低 confidence 表达不确定，而不是硬判成阴阳。调用时把分析结果直接填进参数。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "被分析的原文，原样填入"},
                    "reasoning": {
                        "type": "string",
                        "description": "推理过程；必须说明是否发现讽刺/谐音/拆字等迹象，以及为何这样判断",
                    },
                    "topic": {"type": "string", "description": "用几个字浓缩这段话的主题"},
                    "literal_emotion": {
                        "type": "string",
                        "enum": [
                            "happy",
                            "sad",
                            "angry",
                            "panic",
                            "resigned",
                            "reluctant",
                            "indifferent",
                            "anxious",
                            "neutral",
                        ],
                        "description": "只看字面、不考虑反讽时的情绪",
                    },
                    "emotion": {
                        "type": "string",
                        "enum": [
                            "happy",
                            "sad",
                            "angry",
                            "panic",
                            "resigned",
                            "reluctant",
                            "indifferent",
                            "anxious",
                            "neutral",
                        ],
                        "description": "结合可能的反讽/谐音后，推断的【实际】情绪。resigned=无奈，reluctant=勉强，indifferent=淡漠，anxious=焦虑。只有确实无情绪倾向才选 neutral。",
                    },
                    "polarity": {
                        "type": "string",
                        "enum": ["positive", "negative", "neutral"],
                        "description": "实际情绪的正负向",
                    },
                    "intensity": {
                        "type": "integer",
                        "enum": [1, 2, 3, 4, 5],
                        "description": "实际情绪强度，1=很弱，5=很强",
                    },
                    "suspected_sarcasm": {
                        "type": "boolean",
                        "description": "是否怀疑这是阴阳怪气/讽刺/谐音梗/拆字攻击。有任何可疑迹象就填 true",
                    },
                    "confidence": {
                        "type": "integer",
                        "enum": [1, 2, 3, 4, 5],
                        "description": "对【实际情绪】判断的把握，1=很不确定（多半需要上下文才能定），5=很确定",
                    },
                    "reason": {
                        "type": "string",
                        "description": "你为什么选择调用这个工具的简短原因",
                    },
                },
                "required": [
                    "text",
                    "reasoning",
                    "topic",
                    "literal_emotion",
                    "emotion",
                    "polarity",
                    "intensity",
                    "suspected_sarcasm",
                    "confidence",
                    "reason",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "做加减乘除四则运算。当用户的问题涉及数字计算时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "第一个数"},
                    "b": {"type": "number", "description": "第二个数"},
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide"],
                        "description": "运算类型",
                    },
                    "reason": {
                        "type": "string",
                        "description": "你为什么选择调用这个工具的简短原因",
                    },
                },
                "required": ["a", "b", "operation", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "当任务已经完成、没有更多工具需要调用时，调用本工具结束。不要在还需要计算或分析时调用它。",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "对整个任务的简短总结"},
                    "reason": {"type": "string", "description": "你为什么认为任务已经完成"},
                },
                "required": ["summary", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "当用户透露了值得【跨任务长期记住】的个人信息或偏好时调用，例如名字、喜好、身份、长期目标等。只记真正值得长期保留的事实，不要记一次性的计算或分析结果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {
                        "type": "string",
                        "description": "要长期记住的一条事实，如'用户的名字是 Alice'",
                    },
                    "reason": {"type": "string", "description": "你为什么选择记住这条"},
                },
                "required": ["fact", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replan",
            "description": "当你发现【当前计划本身有问题】、按它无法继续完成目标时调用（例如某步依赖的前提不成立、步骤顺序错了、缺了关键步骤）。只在计划层面出问题时用；如果只是某次工具调用参数填错，直接重试即可，不要调本工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "problem": {
                        "type": "string",
                        "description": "当前计划哪里出了问题，为什么走不通",
                    },
                    "reason": {"type": "string", "description": "你为什么决定重新规划"},
                },
                "required": ["problem", "reason"],
            },
        },
    },
]


def get_tool_schema() -> dict:
    """
    获取可用 tool 的 schema。

    这是 agent 在决定调用哪个 tool 时所看到的内容。

    Returns:
        tool 名称到其 schema 的字典
    """
    return {
        "calculator": {
            "description": "Perform basic arithmetic operations",
            "parameters": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"},
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "The operation to perform",
                },
            },
            "required": ["a", "b"],
        }
    }


def execute_tool(tool_name: str, arguments: dict) -> Any:
    """
    按名称并使用给定参数执行一个 tool。

    Args:
        tool_name: 要执行的 tool 名称
        arguments: tool 的参数字典

    Returns:
        tool 执行的结果

    Raises:
        ValueError: 如果 tool 不存在
    """
    tools = {
        "calculator": calculator,
    }

    if tool_name not in tools:
        raise ValueError(f"Unknown tool: {tool_name}")

    return tools[tool_name](**arguments)


# ============================================================
# 工具注册器
# ============================================================


class ToolRegistry:
    """
    工具注册器：把"工具名 → 可执行函数"集中管理。

    用法:
        registry = ToolRegistry()
        registry.register("calculator", calculator)
        result = registry.execute("calculator", a=1, b=2, operation="add")

    为什么需要它:
        有些工具(如 calculator)的参数完全来自模型;
        但有些工具(如 analyze_emotion)还需要 client/model 这类
        "模型给不了、得由系统注入"的依赖。注册时可以用 register 的
        额外关键字参数把这些依赖预先绑定进去,这样 execute() 时
        只需传模型给的参数,所有工具调用方式就统一了。
    """

    def __init__(self):
        self.tools: dict[str, Callable] = {}

    def register(self, name: str, func: Callable, **fixed_kwargs):
        """
        注册一个工具。

        Args:
            name: 工具名(要和 TOOL_DEFINITIONS 里的 name 一致)
            func: 工具函数
            **fixed_kwargs: 预先绑定的固定参数(如 client=..., model=...);
                            这些不会来自模型,而是系统注入的依赖
        """
        # 用 partial 把固定依赖绑进去,对外就只剩"模型给的参数"
        self.tools[name] = partial(func, **fixed_kwargs) if fixed_kwargs else func

    def execute(self, name: str, **kwargs):
        """
        执行工具。

        Args:
            name: 工具名
            **kwargs: 模型给出的参数(如 a=42, b=7, operation="multiply")

        Returns:
            工具执行结果；失败时统一返回 {"ok": False, "error": ...} 结构，
            便于上层用 ok 字段判断成败，而不是猜字符串。
        """
        if name not in self.tools:
            return {"ok": False, "error": f"未知工具: {name}"}
        try:
            return self.tools[name](**kwargs)
        except Exception as e:
            # 工具执行抛错（如除零、参数缺失）→ 规范成失败标记
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def build_default_registry() -> ToolRegistry:
    """
    构造一个注册好内置工具的注册器。

    现在三个工具（calculator / analyze_emotion / finish）都是纯函数，
    参数全部来自模型，不需要注入 client 等外部依赖，所以本函数无参。
    （若以后有工具又要依赖 client，可在 register 时用 fixed_kwargs 绑回去。）

    Returns:
        已注册好的 ToolRegistry
    """
    registry = ToolRegistry()
    registry.register("calculator", calculator)
    registry.register("analyze_emotion", analyze_emotion)
    registry.register("finish", finish)
    registry.register("remember", remember)
    registry.register("replan", replan)
    return registry
