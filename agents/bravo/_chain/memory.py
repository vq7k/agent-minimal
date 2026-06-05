"""
Agent 记忆系统。

记忆是显式的存储,而不是某种意识。
它是能跨 Agent 步骤持续保存、并可被查询的数据。
"""


class Memory:
    """
    Agent 的简单记忆存储。

    它刻意保持基础,并会在课程中逐步扩展:
    - 第 07 课:基于列表的基础记忆
    - 未来:加入语义搜索、持久化等
    """

    def __init__(self):
        """初始化空记忆。"""
        self.items = []

    def add(self, item: str):
        """
        向记忆中添加一条内容。

        Args:
            item: 要记住的字符串
        """
        if item and item not in self.items:
            self.items.append(item)

    def get_all(self) -> list[str]:
        """
        检索所有记忆条目。

        Returns:
            所有已存储条目的列表
        """
        return self.items.copy()

    def get_recent(self, n: int = 5) -> list[str]:
        """
        获取最近的 n 条记忆条目。

        Args:
            n: 要检索的最近条目数量

        Returns:
            最近条目的列表
        """
        return self.items[-n:] if self.items else []

    def search(self, query: str) -> list[str]:
        """
        在记忆条目中做简单搜索。

        Args:
            query: 要搜索的字符串

        Returns:
            包含该查询词的条目列表
        """
        query_lower = query.lower()
        return [item for item in self.items if query_lower in item.lower()]

    def clear(self):
        """清空所有记忆。"""
        self.items = []

    def __len__(self) -> int:
        """返回记忆中的条目数量。"""
        return len(self.items)

    def __repr__(self) -> str:
        """记忆的字符串表示。"""
        return f"Memory({len(self.items)} items)"
