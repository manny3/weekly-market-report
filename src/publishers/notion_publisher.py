"""
Notion API 發布模組
"""
import os
from datetime import datetime
from typing import Optional

try:
    from notion_client import Client
    NOTION_AVAILABLE = True
except ImportError:
    NOTION_AVAILABLE = False


class NotionPublisher:
    """Notion 週報發布器"""

    def __init__(self, api_key: str = None, database_id: str = None):
        self.api_key = api_key or os.getenv('NOTION_API_KEY')
        self.database_id = database_id or os.getenv('NOTION_DATABASE_ID')
        self.client: Optional[Client] = None

        if NOTION_AVAILABLE and self.api_key:
            self.client = Client(auth=self.api_key)

    def is_available(self) -> bool:
        return self.client is not None

    def create_weekly_report(
        self,
        title: str,
        content: dict,
        date: datetime = None
    ) -> Optional[str]:
        """
        建立週報頁面

        Args:
            title: 頁面標題
            content: 內容區塊
                - market_overview: 大盤趨勢
                - sector_rotation: 板塊輪動
                - watchlist: 觀察清單
                - events: 事件日曆
                - trade_plan: 交易計畫
            date: 報告日期

        Returns:
            str: 頁面 URL，失敗返回 None
        """
        if not self.client:
            print("[Notion] 未設定 API Key 或 notion-client 未安裝")
            return None

        if date is None:
            date = datetime.now()

        try:
            # 構建 Notion blocks
            blocks = self._build_blocks(content)

            # 建立頁面
            page = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties={
                    "Name": {
                        "title": [{"text": {"content": title}}]
                    },
                    "Date": {
                        "date": {"start": date.strftime("%Y-%m-%d")}
                    },
                },
                children=blocks
            )

            return page.get("url")

        except Exception as e:
            print(f"[Notion] 建立頁面失敗: {e}")
            return None

    def _build_blocks(self, content: dict) -> list:
        """將內容轉換為 Notion blocks"""
        blocks = []

        # 大盤趨勢
        if 'market_overview' in content:
            blocks.extend(self._section_block("📊 大盤趨勢", content['market_overview']))

        # 板塊輪動
        if 'sector_rotation' in content:
            blocks.extend(self._section_block("🔄 板塊輪動", content['sector_rotation']))

        # 觀察清單
        if 'watchlist' in content:
            blocks.extend(self._section_block("📋 觀察清單", content['watchlist']))

        # 事件日曆
        if 'events' in content:
            blocks.extend(self._section_block("📅 關鍵事件", content['events']))

        # 交易計畫
        if 'trade_plan' in content:
            blocks.extend(self._section_block("🎯 交易計畫", content['trade_plan']))

        return blocks

    def _section_block(self, heading: str, content: str) -> list:
        """建立區塊"""
        blocks = [
            {
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": heading}}]
                }
            },
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": content}}]
                }
            },
            {
                "type": "divider",
                "divider": {}
            }
        ]
        return blocks

    def update_page(self, page_id: str, content: dict) -> bool:
        """更新現有頁面"""
        if not self.client:
            return False

        try:
            blocks = self._build_blocks(content)

            # 先刪除現有 blocks，再新增
            existing = self.client.blocks.children.list(page_id)
            for block in existing.get("results", []):
                self.client.blocks.delete(block["id"])

            # 新增 blocks
            self.client.blocks.children.append(page_id, children=blocks)
            return True

        except Exception as e:
            print(f"[Notion] 更新頁面失敗: {e}")
            return False
