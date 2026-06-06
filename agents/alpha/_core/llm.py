"""_core/llm.py —— alpha 的 LLM 底座（映射③核）。

generate_structured(): 约束 → 调用 → 解析 → 校验 → 重试 → 失败返回 None。
stream_text(): 纯文本逐字流式。

环境变量（与 agents/alpha/__init__.py 一致）：DEEPSEEK_API_KEY 必填 / LLM_BASE_URL / LLM_MODEL
"""

import json
import logging
import os
from collections.abc import Callable, Iterator

import httpx
from openai import APIError, OpenAI

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("alpha.llm")  # 只取 logger、不配 handler；warning+ 默认即可见
_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")


def _client() -> OpenAI:
    # DeepSeek 在国内，trust_env=False 绕开本机代理。
    # 缺 key 抛友好 RuntimeError（属"非预期错误"，会向上抛、不被吞）
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "未设置 DEEPSEEK_API_KEY。请在项目根目录 .env 配置，或导出为环境变量。"
        )
    return OpenAI(
        base_url=os.environ.get("LLM_BASE_URL", "https://api.deepseek.com"),
        api_key=api_key,
        http_client=httpx.Client(trust_env=False),
    )


def _complete_json(user: str) -> str:
    # 唯一对外 IO：json_object 模式保证返回合法 JSON 文本。测试就 mock 这一个函数
    resp = _client().chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": user}],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content or ""


def generate_structured(
    prompt: str,
    schema_hint: str,
    validate: Callable[[dict], bool],
    retries: int = 3,
) -> dict | None:
    """映射③核。

    仅对「外部预期失败」重试并最终降级返回 None：API 调用失败（APIError）、
    JSON 解析失败、输出未过校验。每次失败记 warning，三次全废记 error——失败可见。

    非预期错误不在此吞没：缺 DEEPSEEK_API_KEY、validate 自身的 bug 等照常向上抛，
    交编排层 chat() 兜底成一条友好 text（§5.6）并暴露堆栈。
    """
    user = f"{prompt}\n\n只输出一个 JSON 对象，形状：\n{schema_hint}"
    for attempt in range(1, retries + 1):
        try:
            raw = _complete_json(user)
            data = json.loads(raw)
        except APIError as e:  # 网络/超时/限流/状态码：可重试的外部失败
            logger.warning("结构化调用失败 (%d/%d): %s", attempt, retries, e)
            continue
        except json.JSONDecodeError as e:
            logger.warning(
                "JSON 解析失败 (%d/%d): %s | 原文: %.200s", attempt, retries, e, raw
            )
            continue
        if isinstance(data, dict) and validate(data):  # validate 在 try 外：异常向上抛
            return data
        logger.warning("输出未过校验 (%d/%d): %.200r", attempt, retries, data)
    logger.error("结构化连续 %d 次失败，降级返回 None", retries)
    return None


def stream_text(messages: list[dict], system: str | None = None) -> Iterator[str]:
    """纯文本逐字流式（普通问答 / 拒答 / 行程表输出用）。"""
    convo = [{"role": "system", "content": system}, *messages] if system else messages
    stream = _client().chat.completions.create(
        model=_MODEL, messages=convo, temperature=0.3, stream=True
    )
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
