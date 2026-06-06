"""
Agent 轨迹记录。

Finding     —— 一条记录：agent 走的某一步(一次 function calling)的结果。
Trajectory  —— 容器：一次任务里所有 Finding 的总和，即 agent 走过的完整轨迹。

设计沿用项目里 evals.py 的 dataclass 风格、memory.py 的"容器装 items"风格。
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Finding:
    """
    单步结果：一次 function calling 调用产生的记录。

    字段:
        step:      第几步(从 1 开始)
        tool:      调用的工具名；若模型没调工具(闲聊)则为 None
        reason:    模型给出的"为什么调这个工具"的原因
        arguments: 传给工具的参数(已剔除 reason 这类元信息)
        result:    工具执行结果；闲聊时为模型的文本回复
    """

    step: int
    tool: str | None
    reason: str = ""
    arguments: dict = field(default_factory=dict)
    result: Any = None

    def to_dict(self) -> dict:
        """转成字典，便于序列化 / 构建 prompt。"""
        return {
            "step": self.step,
            "tool": self.tool,
            "reason": self.reason,
            "arguments": self.arguments,
            "result": self.result,
        }

    def __repr__(self) -> str:
        return f"Finding(step={self.step}, tool={self.tool!r}, reason={self.reason!r})"


class Trajectory:
    """
    一次任务里所有 Finding 的总和 —— agent 走过的轨迹。

    用法:
        traj = Trajectory()
        traj.add(finding)
        traj.get_all()        # 取全部
        traj.last()           # 取最近一条
        len(traj)             # 共几步
    """

    def __init__(self):
        self.findings: list[Finding] = []

    def add(self, finding: Finding):
        """追加一条 Finding。"""
        self.findings.append(finding)

    def get_all(self) -> list[Finding]:
        """返回所有 Finding 的副本。"""
        return self.findings.copy()

    def last(self) -> Finding | None:
        """返回最近一条 Finding；没有则返回 None。"""
        return self.findings[-1] if self.findings else None

    def to_list(self) -> list[dict]:
        """把整条轨迹转成字典列表，便于序列化 / 打印。"""
        return [f.to_dict() for f in self.findings]

    def clear(self):
        """清空轨迹。"""
        self.findings = []

    def __len__(self) -> int:
        return len(self.findings)

    def __repr__(self) -> str:
        return f"Trajectory({len(self.findings)} findings)"
