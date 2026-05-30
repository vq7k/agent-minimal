# 一个文件看懂 Agent：最小 Demo 教学

> **声明**
> 本文档由 AI 生成、经人工审核。
> - 所有**事实性陈述**均以脚注 `[^…]` 标注信息源（见文末参考资料）。
> - 所有 **AI 决策**（主观取舍）均以 `⚠️AI决策` 标记，阅读时请留意——这些可质疑、可推翻。

这篇文档配套 `agent.py`（约 130 行），目标：**零基础也能彻底搞懂一个 Agent 到底怎么转起来的**。读完你能回答三个问题：

1. Agent 和普通聊天差在哪？
2. "工具调用循环"为什么是所有 Agent 框架的内核？
3. 流式输出（stream）下，代码要多处理什么？

> **关于 `⚠️AI决策` 标记**
> 本文档与配套代码由 AI 协助生成。凡标有 **⚠️AI决策** 的地方，是 AI 替你做的**主观取舍**——比如选哪个模型、用哪几个工具、某字段重不重要、给什么练习建议。这些**不是客观事实、也不是官方规范**，你完全可以质疑、推翻、换方案。
> 反之，带 `[^…]` 脚注的才是有官方出处的事实（见文末参考资料）。
>
> ⚠️AI决策（整体结构）：把整个 demo 压成**单文件 `agent.py`**、问题**写死在代码里**（不做交互式命令行），是为"最小、好读、好打断点"做的取舍。

---

## 0. 先跑起来

前置：装好 `uv`[^uv]（`brew install uv`），有一个 DeepSeek API key[^deepseek]。

```bash
cp .env.example .env          # 然后编辑 .env，填入 DEEPSEEK_API_KEY=sk-xxxx
uv sync                       # 装依赖（openai、python-dotenv[^dotenv]）
uv run python agent.py        # 跑
```

你会看到答案**一个字一个字冒出来**，中间还有 `-> 模型调用工具 ...` 的提示。

> ⚠️AI决策：用 **DeepSeek** 的 `deepseek-chat` 模型（你定了用 DeepSeek，具体模型名是 AI 选的）。它是 OpenAI 兼容接口[^deepseek]，所以代码用官方 `openai` SDK、把 `base_url` 指过去即可——换成别的 OpenAI 兼容服务（Ollama、OpenAI 本身等）只改 `base_url` 和 `model` 两处。

> 想换问题？改 `agent.py` 最底下的 `question = "..."` 那一行即可，不用搞交互式命令行。

---

## 1. Agent vs 普通聊天

普通聊天：你问一句，模型答一句，**模型只能用它脑子里的知识**。问它"现在几点"，它只能瞎编，因为它不知道。

Agent：给模型配几个**工具**（就是普通函数，比如"查时间""算数学"）。模型遇到自己搞不定的事，会**主动要求调某个工具**；你的代码执行这个函数，把结果**喂回去**，模型再接着说。

一句话：

> **普通聊天 = 模型自己说。Agent = 模型会喊"帮我调这个函数"，你执行完把结果给它，它再继续。**

模型本身**不会**执行任何代码——它只会"说出"它想调哪个工具、传什么参数。真正动手执行的永远是你的 Python 代码。这点想清楚，整个 Agent 就不神秘了。（这套"模型报工具、你来执行"的机制，官方叫 Function Calling / Tool Calling[^funccall]。）

---

## 2. 三个部分

`agent.py` 从上到下就三段，对应阅读顺序：

### 第 1 部分：工具

每个工具 = **一个普通函数** + **一段给模型看的说明（schema）**。

```python
def calculate(expression: str) -> str:
    return str(eval(expression, {"__builtins__": {}}, {}))

def current_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
```

函数本身平平无奇。关键是要**告诉模型有这些工具**，所以有 `TOOLS` 列表，用一种固定格式（JSON Schema[^jsonschema]）描述每个工具叫什么、收什么参数：

```python
TOOLS = [
    {"type": "function", "function": {
        "name": "calculate",
        "description": "计算一个数学表达式，例如 123 * 456",
        "parameters": {"type": "object",
                       "properties": {"expression": {"type": "string"}},
                       "required": ["expression"]},
    }},
    ...
]
```

还有一个 `TOOL_FUNCTIONS` 字典，把**工具名映射到真正的函数**——因为模型只会报名字（字符串 `"calculate"`），代码得靠它查出该调哪个函数：

```python
TOOL_FUNCTIONS = {"calculate": calculate, "current_time": current_time}
```

> 记住这组对应关系：`TOOLS`（给模型看的说明）↔ `TOOL_FUNCTIONS`（给代码用的查表）。加新工具就是这两处各加一项 + 写个函数。

> ⚠️AI决策：(1) 工具选了 `calculate`、`current_time` 这两个——纯本地、零外部依赖、最好调试，是为"看清原理"挑的，不是非这俩不可。(2) `calculate` 用 `eval(expr, {"__builtins__": {}})` 简单实现：禁用内置函数挡掉大部分滥用，但**不是真正安全**的做法（生产环境应改用 `ast` 解析或专门的表达式库）。demo 阶段够用，别照搬上线。

### 第 2 部分：工具调用循环（核心中的核心）

整个 Agent 的灵魂就是 `run_agent` 里这个 `while True` 循环。先看不带流式的"心智模型"（伪代码）：

```
messages = [系统提示, 用户问题]
循环：
    把 messages + 工具列表发给模型
    如果模型没要求调工具 → 这就是最终答案，返回
    如果模型要求调工具：
        把模型这条消息（含"我要调 X"）记进 messages
        执行 X，把结果作为一条 messages 追加回去
    回到循环开头（模型这次能看到工具结果了）
```

关键点：**`messages` 这个列表就是 Agent 的"记忆"**。它从 2 条开始，每轮往里加东西，越来越长：

```
轮1: [system, user]
     模型说"我要调 current_time 和 calculate"
轮2: [system, user, assistant(要调工具), tool(时间结果), tool(算数结果)]
     模型看到结果，给出最终答案
```

为什么必须把工具结果加回 `messages` 再发一次？因为**模型是无状态的**——每次调用它只看你发过去的 `messages`，它不记得上一次。你不把时间结果塞回去，它就永远不知道几点。

### 第 3 部分：运行

```python
question = "现在几点？顺便算一下 123 * 456"
run_agent(client, question)
```

就这么简单。调试时把断点打在 `run_agent` 里，单步看 `messages` 怎么一轮轮变长——这是理解 Agent 最直观的方式。

---

## 3. 流式输出（stream）多了什么

### 3.0 先搞清楚：流式到底是什么、谁控制

**一个常见误解：以为"流式"是模型的某种能力。不是。流式是"结果怎么送给你"的传输方式，由你（客户端）用 `stream=True` 这个开关控制[^stream]，跟模型本身无关。**

为什么这么说？因为**不管流不流式，大模型内部永远是一个字一个字（token by token）往外蹦的**——它先算出"今"，再算"天"，再算"几"……这叫自回归生成，是模型的固有工作方式，改不了。

区别只在于：**服务器拿到这些陆续生成的 token 后，怎么交给你。**

| | 非流式（默认，不加 stream） | 流式（`stream=True`） |
|---|---|---|
| 服务器行为 | 等模型**全部生成完**，攒成一整坨，一次性发给你 | 模型**每蹦出一点就立刻转发**给你 |
| 你收到的 | 一个完整 response，`msg.content` 直接是全文 | 一串碎片 chunk，要 `for chunk in stream` 一片片收 |
| 体验 | 静默几秒 → 整段答案突然出现 | 几乎立刻开始，逐字往外冒 |
| 总耗时 | 和流式差不多 | **首字更快**，但总时长和非流式相近 |

**一个比喻**：模型做菜（逐字生成）的速度两种方式完全一样，区别是上菜方式——

- **非流式** = 服务员等**整桌菜做齐**才一起端上来，你前面干等。
- **流式** = 做好一道端一道，你马上能动筷子。

菜没做得更快，但你**等待的"感觉"**好太多。这就是流式存在的唯一理由：**改善体感延迟**，让用户立刻看到"它在动"，而不是盯着空屏幕怀疑是不是卡死了（还记得你第一次跑 demo 时那个"？？"吗——那次就是非流式，静默太久让人以为挂了）。

**谁控制，一句话总结**：

- **你控制** —— 请求里加不加 `stream=True`。加了走流式，不加走非流式。
- **模型不控制** —— 它不知道也不关心你要不要流式，只管逐字生成。
- **代价** —— 流式下结果是碎片，你的代码得自己把碎片拼回完整内容（文字拼、工具调用也拼）。这就是下面要讲的"多处理的两件事"。

### 3.1 代码上多处理什么

普通模式：`create(...)` 一次性返回完整结果，`msg.content` 直接拿到全文，不用拼。

流式模式：`create(..., stream=True)` 返回一个**碎片(chunk)流**，你要 `for chunk in stream` 一片片收，然后自己拼。具体两件事：

### (a) 文字是一片片来的

```python
if delta.content:
    print(delta.content, end="", flush=True)   # 来一片打一片
    content += delta.content                    # 同时攒起来留底
```

`end=""` 不换行、`flush=True` 立刻刷出，所以你看到逐字效果。

### (b) 工具调用也是碎片化的（最容易踩的坑）

非流式时，模型一次性给你完整的 `tool_calls`。但**流式下，工具的 `name` 和 `arguments` 也被拆成好几片**陆续到达，你得自己按 `index` 拼回来：

```python
tool_calls: dict[int, dict] = {}   # index -> {id, name, arguments}
for tc in delta.tool_calls or []:
    slot = tool_calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
    if tc.id:                slot["id"] = tc.id
    if tc.function.name:     slot["name"] = tc.function.name
    if tc.function.arguments: slot["arguments"] += tc.function.arguments   # 注意是 += 拼接
```

比如 `arguments` 可能分成 `'{"expr'`、`'ession":'`、`' "123*456"}'` 三片，拼起来才是完整 JSON。这就是为什么 `arguments` 用 `+=` 累加。

收完整个流之后，逻辑和非流式一样：没工具调用就返回，有就执行工具、塞回 `messages`、继续循环。

> 想亲眼看碎片长什么样：在 `for chunk in stream:` 那行打断点，单步看每个 `delta`。你会发现文字一两个字一片、工具名和参数拆成好几片。

---

## 4. 在 IDEA 里调试

1. **解释器**：`Settings → Project → Python Interpreter`，选 `.venv/bin/python`（IDEA 通常自动识别）。
2. **打断点**（行号左侧点红点）：
   - `for chunk in stream:` —— 看每个碎片 `delta`
   - `result = TOOL_FUNCTIONS[...](...)` —— 看模型要调的工具名和参数
   - 循环顶部 `stream = client...create(...)` —— 看每轮 `messages` 长什么样
3. 右键 `agent.py` → **Debug**，用 **F8（Step Over）** 单步，盯左下 Variables 面板里的 `messages`、`tool_calls`、`args`。

走完一整轮，你就抓住了 Agent 的本质：**模型不动手，只"指挥";你的代码执行工具、把结果回灌;模型据此再开口——循环往复，直到收工。**

---

## 5. 接下来可以自己练

> ⚠️AI决策：下面这几条是 AI 推荐的练习方向（按"难度递进、贴合本 demo"挑的），不是必经路径，挑你感兴趣的做即可。

- **加一个工具**：写个 `read_file(path)` 函数，在 `TOOLS` 和 `TOOL_FUNCTIONS` 各加一项，问它"读一下 README.md 讲了啥"。
- **改提示词**：调 `messages` 里的 system 内容，看模型行为变化。
- **加错误处理**：工具执行 `try/except`，把报错也作为 tool 结果喂回去，看模型能不能自己纠正。
- **第二步**：把 `run_agent` 包成 HTTP 服务（FastAPI），让别的程序也能调——这是把 demo 变成"可被集成的能力"的关键一步。

---

## 6. 深入：流式碎片(chunk)的完整数据结构

这一节把模型返回的原始数据**逐字段**拆开。你用 `print(chunk.model_dump_json())` 打出来的每一行，就是这里讲的一个 chunk。字段含义以 OpenAI 官方的流式 chunk 对象规范为准[^stream]（DeepSeek 是 OpenAI 兼容接口，沿用同一套结构[^deepseek]）。

### 6.1 一个 chunk 的整体长相

拿一个最普通的"文字碎片"举例（这片只带来一个字"。"）：

```json
{
  "id": "a4c028c7-2645-4c82-86a3-246d456bf5b9",
  "object": "chat.completion.chunk",
  "created": 1780047676,
  "model": "deepseek-v4-flash",
  "choices": [
    {
      "index": 0,
      "delta": { "role": null, "content": "。", "tool_calls": null,
                 "function_call": null, "refusal": null },
      "finish_reason": null,
      "logprobs": null
    }
  ],
  "service_tier": null,
  "system_fingerprint": "fp_8b330d02d0_...",
  "usage": null
}
```

它分**外层（信封）**和**内层（`choices[0]`，真正的内容）**两部分。

### 6.2 外层字段：这片是谁发的

把外层想象成快递信封——重要的是里面的货（`choices`），信封信息大多可忽略。

下表最后一列「要不要关心」**⚠️AI决策**：字段含义是事实[^stream]，但"该不该关心"是 AI 按"本 demo 代码是否用到它"这条标准给的主观判断，不是官方规定，仅供参考。

| 字段 | 这片的值 | 含义 | 要不要关心 ⚠️AI决策 |
|---|---|---|---|
| `id` | `"a4c0..."` | 整次回答的唯一编号。**同一次回答的所有碎片共用一个 id** | 偶尔（排查日志时） |
| `object` | `"chat.completion.chunk"` | 数据类型。带 `chunk` = 流式碎片；非流式时是 `chat.completion` | 知道即可 |
| `created` | `1780047676` | 生成时间（Unix 秒级时间戳） | 否 |
| `model` | `"deepseek-v4-flash"` | 实际处理请求的模型（可能和你请求的名字略有出入，因为服务端会路由） | 知道即可 |
| `service_tier` | `null` | 服务档位（按量/优先等），没用到 | 否 |
| `system_fingerprint` | `"fp_..."` | 后端配置指纹，用于复现问题 | 否 |
| `usage` | `null` | token 用量统计。**流式中途全是 null**，一般最后一片或额外一片才给 | 是（算成本时） |

> 一句话：外层只有 `id`（关联同一次回答）和 `usage`（算 token）偶尔用得上，其余扫一眼就过。

### 6.3 内层 `choices[0]`：这片的实际内容

`choices` 是个**列表**，因为理论上模型能一次生成多条候选回答（参数 `n>1` 时）。我们没设 `n`，所以**永远只有一条**，代码里固定取 `choices[0]`。

`choices[0]` 里有 4 个字段：

| 字段 | 含义 | 取值 |
|---|---|---|
| `index` | 第几条候选 | 恒为 `0`（只有一条） |
| `delta` | **这一片新增的内容**（核心，见 6.4） | 见下 |
| `finish_reason` | 这条回答**结束的原因**；没结束就是 `null` | 见 6.5 |
| `logprobs` | 每个 token 的概率（调试模型用） | 没开启，恒 `null` |

### 6.4 `delta`：增量，整个流式的核心

`delta`（增量）= **这一片比之前多出来的东西**。流式的本质就是：模型把回答切成几十上百片，每片的 `delta` 只装一点点新内容，你把所有 `delta` 拼起来 = 完整回答。

`delta` 里 5 个字段，但**每一片通常只有一个非 null**：

| 字段 | 含义 | 什么时候非 null |
|---|---|---|
| `role` | 角色 | **只有第一片**给 `"assistant"`，告诉你"接下来是助手在说"；后续片全是 `null` |
| `content` | 新增的**文字**片段 | 模型在输出文字时（如上例的 `"。"`） |
| `tool_calls` | 新增的**工具调用**片段 | 模型在决定调工具时（见 6.6） |
| `function_call` | 旧版的工具调用字段 | 已废弃，被 `tool_calls` 取代，**永远忽略** |
| `refusal` | 拒答内容 | 模型拒绝回答时才有，一般 `null` |

**关键认知：`content` 和 `tool_calls` 在同一片里互斥**——一片要么在吐文字，要么在吐工具调用，不会两个都有。这就是代码分两路处理的根本原因：

```python
if delta.content:            # 路 A：这片是文字
    print(delta.content, end="", flush=True)
for tc in delta.tool_calls or []:   # 路 B：这片是工具调用
    ...
```

### 6.5 `finish_reason`：流什么时候结束

绝大多数片它是 `null`（还没完）。**非 null 的那一片就是这条回答的最后一片**，值告诉你为什么停：

| 值 | 含义 | 你的代码该做什么 |
|---|---|---|
| `null` | 还没结束，后面还有片 | 继续收 |
| `"stop"` | 模型正常说完了 | 这轮是最终答案，结束循环 |
| `"tool_calls"` | 模型说完"我要调工具"了 | 去执行工具，把结果喂回去，进入下一轮 |
| `"length"` | 撞到最大长度上限被截断 | 内容不完整，可能要加大上限 |

> ⚠️AI决策：代码里没有显式读 `finish_reason`，而是用"收完流后 `tool_calls` 字典是否为空"来判断走哪条路。这是 AI 为少写一个分支做的取舍——效果等价，但读 `finish_reason` 是更标准、更稳的做法，你想改回来完全合理。

### 6.6 工具调用碎片：为什么要"拼"

你贴的另一片长这样（`content` 是 null，`tool_calls` 有值）：

```json
"delta": {
  "content": null,
  "tool_calls": [
    { "index": 0, "id": null, "type": null,
      "function": { "name": null, "arguments": "{}" } }
  ]
}
```

注意：工具调用本身也是**碎片化**的。模型调一个工具的完整信息（id、name、arguments）会拆到**好几片**里陆续发来。一次真实的 `calculate("123 * 456")` 调用，碎片序列可能是：

```
片1: tool_calls=[{index:0, id:"call_abc", function:{name:"calculate", arguments:""}}]
片2: tool_calls=[{index:0, id:null,       function:{name:null,        arguments:"{\"expr"}}]
片3: tool_calls=[{index:0, id:null,       function:{name:null,        arguments:"ession\": "}}]
片4: tool_calls=[{index:0, id:null,       function:{name:null,        arguments:"\"123 * 456\"}"}}]
```

看出规律了吗：
- `id` 和 `name` 通常**只在第一片给一次**，后续是 `null` → 代码用 `if tc.id: slot["id"] = tc.id` 只在非空时覆盖。
- `arguments` 是**一段段拼**出来的 → 代码用 `slot["arguments"] += tc.function.arguments` 累加，最后才是完整 JSON 字符串 `{"expression": "123 * 456"}`。
- `index` 是**工具的序号**：模型可能同时要调 2 个工具（`index:0` 和 `index:1`），碎片靠这个 index 归位到对应的工具，别拼串了。

这正是代码里那段的全部用意：

```python
tool_calls: dict[int, dict] = {}        # index -> 一个工具的拼装中状态
for tc in delta.tool_calls or []:
    slot = tool_calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
    if tc.id:                 slot["id"] = tc.id            # id 只来一次，非空才存
    if tc.function.name:      slot["name"] = tc.function.name   # name 同理
    if tc.function.arguments: slot["arguments"] += tc.function.arguments  # arguments 拼接
```

收完整个流，`tool_calls` 字典里每个 index 就是一个**拼装完整**的工具调用，可以 `json.loads(arguments)` 解析参数、查 `TOOL_FUNCTIONS` 执行了。

### 6.7 一次完整对话的碎片全景

把 "现在几点？算 123*456" 这一问，按时间顺序看流：

```
==== 第 1 轮 create（模型决定调工具）====
片: delta.role="assistant"                         ← 开场，宣告身份
片: delta.content="好的，我先查一下…"  （若干片）   ← 模型先说了句铺垫（流式打印出来）
片: delta.tool_calls=[index0: current_time 的碎片]  （若干片，拼出工具0）
片: delta.tool_calls=[index1: calculate 的碎片]     （若干片，拼出工具1）
片: finish_reason="tool_calls"                      ← 这轮结束，要调工具

   → 代码执行 current_time() 和 calculate("123*456")，结果塞回 messages

==== 第 2 轮 create（模型看到结果，给最终答案）====
片: delta.role="assistant"
片: delta.content="当前时间是…"  （几十片，逐字）   ← 最终答案，流式打印
片: finish_reason="stop"                            ← 正常说完，循环结束
```

把这张图和 6.1~6.6 对上，你就完全看懂"为什么循环要跑两轮、每片该往哪走、工具为什么要拼"了。

> **动手验证**：跑一次后打开生成的 `log.json`（代码里 `run_agent` 会把所有碎片格式化写进去），对照这张全景图逐片确认——哪片是 role、哪片是 content、哪片是 tool_calls、哪片带 finish_reason。看明白后把收集碎片那行删掉即可。
>
> 懒得跑也行：仓库里 [`docs/sample-log.json`](./sample-log.json) 是一份现成样例，直接对照着看。（根目录的 `log.json` 是运行产物，不入库。）

> ⚠️AI决策（log.json 的写法）：选了"先把碎片攒进列表、收尾一次性 `json.dump(..., indent=2, ensure_ascii=False)`"——这样得到合法且可折叠的 JSON 数组、中文不转义。也可以逐片追加（NDJSON）或不缩进，看你想要什么；每次跑会覆盖旧文件也是 AI 定的（用 `"w"` 模式）。

---

## 参考资料

文中标了 `[^…]` 的事实性说法，依据来自以下官方文档（"初学者要不要关心某字段"那类**主观判断**不在此列，仅代表本 demo 的取舍）：

[^uv]: uv 官方文档（Python 包与项目管理器）— https://docs.astral.sh/uv/
[^deepseek]: DeepSeek API 文档（base_url、模型名、工具调用、OpenAI 兼容性）— https://api-docs.deepseek.com/
[^dotenv]: python-dotenv（从 `.env` 读环境变量）— https://github.com/theskumar/python-dotenv
[^funccall]: OpenAI Function Calling / Tool Calling 指南 — https://platform.openai.com/docs/guides/function-calling
[^jsonschema]: JSON Schema 规范（工具参数的描述格式）— https://json-schema.org/
[^stream]: OpenAI Chat API 流式响应与 chunk 对象字段定义 — https://platform.openai.com/docs/api-reference/chat/streaming
