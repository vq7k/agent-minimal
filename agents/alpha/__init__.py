"""alpha agent —— 基础聊天(DeepSeek,流式,无工具)。

通过 OpenAI 兼容 SDK 调 DeepSeek,把模型逐字 chunk 转成 SSE text 事件输出。
要加工具调用 / 换模型 / 换 LLM,改本文件即可,不要影响别人。

环境变量(从 .env 自动加载):
  DEEPSEEK_API_KEY  必填
  LLM_BASE_URL      可选,默认 https://api.deepseek.com
  LLM_MODEL         可选,默认 deepseek-chat
"""

import json
import os
from collections.abc import Iterator

import httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # 模块加载时读一次 .env,后续 os.environ 就能拿到

SYSTEM_PROMPT = "你是一个友好的中文助手,回答简洁。"


def chat(messages: list[dict]) -> Iterator[str]:
    client = OpenAI(
        base_url=os.environ.get("LLM_BASE_URL", "https://api.deepseek.com"),
        api_key=os.environ["DEEPSEEK_API_KEY"],
        # DeepSeek 在国内,无需走代理:忽略环境的 HTTP(S)_PROXY/ALL_PROXY
        http_client=httpx.Client(trust_env=False),
    )

    convo = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]
    stream = client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "deepseek-chat"),
        messages=convo,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            event = {"type": "text", "delta": delta.content}
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    yield 'data: {"type":"done"}\n\n'
