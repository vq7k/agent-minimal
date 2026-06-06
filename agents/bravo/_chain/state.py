"""
Agent 状态管理。

状态是显式的、可检视的、可修改的。
它不会隐藏在对话历史里,也不会藏在某种神秘的上下文中。
"""


class AgentState:
    """
    表示 Agent 的当前状态。

    随着课程推进、不断增加能力,它也会随之扩展:
    - 第 06 课:基础状态(steps、done)
    - 第 07 课:加入记忆追踪
    - 第 08 课:加入规划状态
    - 第 09 课:加入执行状态
    - 第 10 课:加入依赖追踪
    """

    def __init__(self):
        """初始化一个新的 Agent 状态。"""
        self.steps = 0
        self.done = False
        # agent的未来地图：步骤文字列表
        self.current_plan = None
        # 当前进行到计划的第几步（0 基）
        self.plan_cursor = 0
        # 已经重新规划过几次（防止无限重规划）
        self.replan_count = 0
        # agent的这个状态的上一步执行的行动
        self.last_action = None

    def increment_step(self):
        """让步数计数器加一。"""
        self.steps += 1

    def mark_done(self):
        """将 Agent 的任务标记为完成。"""
        self.done = True

    def reset(self):
        """为新任务重置状态。"""
        self.steps = 0
        self.done = False
        self.current_plan = None
        self.plan_cursor = 0
        self.replan_count = 0
        self.last_action = None

    def to_dict(self) -> dict:
        """
        将状态转换为字典,用于序列化或构建 prompt。

        Returns:
            状态的字典表示
        """
        return {
            "steps": self.steps,
            "done": self.done,
            "current_plan": self.current_plan,
            "last_action": self.last_action,
        }

    def __repr__(self) -> str:
        """状态的字符串表示。"""
        return f"AgentState(steps={self.steps}, done={self.done})"
