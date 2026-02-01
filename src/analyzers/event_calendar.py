"""
事件日曆模組
"""
from datetime import datetime, timedelta
from typing import Optional
import json


class EventCalendar:
    """關鍵事件日曆"""

    # 固定事件 (月份, 週次)
    RECURRING_EVENTS = {
        "FOMC": "每 6 週，週三",
        "就業數據": "每月第一個週五",
        "CPI": "每月中旬",
        "月度期權到期": "每月第三個週五",
        "季度期權到期": "3/6/9/12 月第三個週五",
    }

    def __init__(self):
        self.custom_events = []

    def add_event(
        self,
        date: datetime,
        title: str,
        impact: str = "medium",
        symbol: str = None
    ):
        """新增事件"""
        self.custom_events.append({
            "date": date,
            "title": title,
            "impact": impact,  # low, medium, high
            "symbol": symbol,
        })

    def get_weekly_events(self, start_date: datetime = None) -> list[dict]:
        """取得本週事件"""
        if start_date is None:
            start_date = datetime.now()

        # 找到週一
        monday = start_date - timedelta(days=start_date.weekday())
        friday = monday + timedelta(days=4)

        events = []

        # 過濾自訂事件
        for event in self.custom_events:
            if monday <= event['date'] <= friday:
                events.append(event)

        # 排序
        events.sort(key=lambda x: x['date'])

        return events

    def generate_summary(self, week_start: datetime = None) -> str:
        """產生事件日曆摘要"""
        events = self.get_weekly_events(week_start)

        lines = ["📅 關鍵事件日曆", ""]

        if not events:
            lines.append("本週無重大事件")
        else:
            impact_icons = {
                "high": "⚠️",
                "medium": "🔔",
                "low": "📌",
            }

            for event in events:
                date_str = event['date'].strftime("%m/%d (%a)")
                icon = impact_icons.get(event['impact'], "📌")
                symbol_str = f" [{event['symbol']}]" if event.get('symbol') else ""
                lines.append(f"{icon} {date_str}: {event['title']}{symbol_str}")

        lines.append("")
        lines.append("【固定事件提醒】")
        for name, schedule in self.RECURRING_EVENTS.items():
            lines.append(f"  • {name}: {schedule}")

        return "\n".join(lines)

    def load_earnings_calendar(self, symbols: list[str]) -> list[dict]:
        """
        載入財報日曆

        TODO: 整合 yfinance 或其他 API 取得財報日期
        """
        # 暫時回傳空列表
        return []
