"""
文字格式轉換工具
"""
from typing import Optional


class TextFormatter:
    """文字格式轉換器"""

    @staticmethod
    def to_threads_format(
        content: dict,
        max_length: int = 500
    ) -> str:
        """
        轉換為 Threads 格式

        Args:
            content: 內容字典
            max_length: 最大字數

        Returns:
            格式化的文字
        """
        lines = []

        # 標題
        lines.append(f"📊 {content.get('title', '本週市場觀察')}")
        lines.append("")

        # 摘要
        if 'summary' in content:
            lines.append(content['summary'])
            lines.append("")

        # 重點
        if 'highlights' in content:
            for h in content['highlights'][:3]:
                lines.append(f"• {h}")
            lines.append("")

        # 標籤
        lines.append("#美股 #台股 #投資週報")

        result = "\n".join(lines)

        # 截斷
        if len(result) > max_length:
            result = result[:max_length - 3] + "..."

        return result

    @staticmethod
    def to_x_thread_format(
        content: dict,
        max_posts: int = 5,
        max_chars: int = 280
    ) -> list[str]:
        """
        轉換為 X 串推格式

        Args:
            content: 內容字典
            max_posts: 最大推文數
            max_chars: 每則最大字數

        Returns:
            推文列表
        """
        posts = []

        # 1/N 開場
        posts.append(
            f"📊 {content.get('title', '本週市場觀察')}\n\n"
            f"讓我們開始 👇"
        )

        # 2/N ~ N-1/N 內容
        sections = content.get('sections', [])
        for section in sections[:max_posts - 2]:
            text = f"【{section.get('title', '')}】\n\n{section.get('content', '')}"
            if len(text) > max_chars:
                text = text[:max_chars - 3] + "..."
            posts.append(text)

        # N/N 結尾
        link = content.get('link', '')
        posts.append(
            f"完整分析 👉 {link}\n\n"
            f"#美股 #台股 #週報"
        )

        # 加上編號
        total = len(posts)
        numbered_posts = []
        for i, post in enumerate(posts, 1):
            numbered = f"{i}/{total} {post}"
            if len(numbered) > max_chars:
                # 去掉一些內容以符合限制
                excess = len(numbered) - max_chars + 3
                numbered = f"{i}/{total} {post[:-excess]}..."
            numbered_posts.append(numbered)

        return numbered_posts

    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
        """截斷文字"""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix

    @staticmethod
    def format_number(num: float, decimals: int = 2) -> str:
        """格式化數字"""
        if num is None:
            return "N/A"
        if abs(num) >= 1_000_000_000:
            return f"{num / 1_000_000_000:.{decimals}f}B"
        if abs(num) >= 1_000_000:
            return f"{num / 1_000_000:.{decimals}f}M"
        if abs(num) >= 1_000:
            return f"{num / 1_000:.{decimals}f}K"
        return f"{num:.{decimals}f}"

    @staticmethod
    def format_percent(num: float, decimals: int = 2) -> str:
        """格式化百分比"""
        if num is None:
            return "N/A"
        sign = "+" if num > 0 else ""
        return f"{sign}{num:.{decimals}f}%"
