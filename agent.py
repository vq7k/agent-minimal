"""最小 Agent demo —— 一个文件看懂「工具调用循环」。

普通聊天是一问一答；Agent 是模型能「调用工具」：它自己决定要不要调函数，
代码执行后把结果喂回去，模型据此继续，直到给出最终答案。
这个反复的过程就是 Agent 的内核。从上往下读即可：工具 → 循环 → 运行。

跑法：把 DeepSeek key 写进 .env（DEEPSEEK_API_KEY=...），然后
    uv run python agent.py
"""

import json
import os
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

# ---------- 1. 工具：普通函数 + 一段给模型看的说明 ----------


def calculate(expression: str) -> str:
    # 仅供 demo：禁用内置函数，避免 eval 被滥用
    return str(eval(expression, {"__builtins__": {}}, {}))


def current_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 工具名 -> 函数：循环里按模型给的名字查出来执行
TOOL_FUNCTIONS = {"calculate": calculate, "current_time": current_time}

# 告诉模型有哪些工具、各收什么参数
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算一个数学表达式，例如 123 * 456",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "current_time",
            "description": "获取当前日期和时间",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# ---------- 2. 工具调用循环（Agent 内核，断点打这里）----------


def run_agent(client: OpenAI, user_input: str) -> str:
    messages = [
        {"role": "system", "content": "需要算数或查时间就调用工具，不要自己编。"},
        {"role": "user", "content": user_input},
    ]

    log_chunks: list[dict] = []  # 把每个原始碎片攒起来，最后写成格式化 JSON 文件

    while True:
        # 把当前对话 + 工具列表发给模型。stream=True：结果不再一次性返回，
        # 而是变成一串「碎片(chunk)」边生成边吐出来。
        stream = client.chat.completions.create(
            model="deepseek-chat", messages=messages, tools=TOOLS, stream=True
        )

        # 一边收碎片一边攒：文字直接打印，工具调用按 index 拼回完整的。
        content = ""
        tool_calls: dict[int, dict] = {}  # index -> {id, name, arguments}
        for chunk in stream:
            log_chunks.append(chunk.model_dump())  # 收集原始碎片，供事后查看
            delta = chunk.choices[0].delta

            # (a) 文字碎片：来一片打印一片，这就是「流式」效果
            if delta.content:
                print(delta.content, end="", flush=True)
                content += delta.content

            # (b) 工具调用碎片：name/arguments 也是分多片来的，按 index 累加拼好
            for tc in delta.tool_calls or []:
                slot = tool_calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                if tc.id:
                    slot["id"] = tc.id
                if tc.function.name:
                    slot["name"] = tc.function.name
                if tc.function.arguments:
                    slot["arguments"] += tc.function.arguments

        # 没有工具调用 = 这轮就是最终答案（上面已经流式打印完了）
        if not tool_calls:
            print()  # 收尾换行
            # 把收集到的所有碎片写成格式化 JSON 文件：
            #   indent=2          → 缩进 2 空格，层级清晰
            #   ensure_ascii=False → 中文原样输出，不转成 \uXXXX
            with open("log.json", "w", encoding="utf-8") as f:
                json.dump(log_chunks, f, indent=2, ensure_ascii=False)
            return content

        # 模型要调工具：把它这条消息（含拼好的 tool_calls）放回对话
        messages.append(
            {
                "role": "assistant",
                "content": content or None,
                "tool_calls": [
                    {
                        "id": c["id"],
                        "type": "function",
                        "function": {"name": c["name"], "arguments": c["arguments"]},
                    }
                    for c in tool_calls.values()
                ],
            }
        )

        # 逐个执行工具，把结果喂回去，然后回到循环顶部让模型继续
        for c in tool_calls.values():
            args = json.loads(c["arguments"])
            print(f"\n  -> 模型调用工具 {c['name']}({args})")
            result = TOOL_FUNCTIONS[c["name"]](**args)
            messages.append({"role": "tool", "tool_call_id": c["id"], "content": str(result)})


# ---------- 3. 运行：改这里的问题，然后跑/打断点 ----------

if __name__ == "__main__":
    load_dotenv()  # 从 .env 读 DEEPSEEK_API_KEY
    client = OpenAI(
        base_url="https://api.deepseek.com",
        api_key=os.environ["DEEPSEEK_API_KEY"],
    )

    question = "现在几点？顺便算一下 123 * 456"
    print("你>", question)
    print("助手> ", end="")
    run_agent(client, question)  # 答案在 run_agent 里已流式打印，这里不再重复打印返回值
