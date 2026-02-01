"""
Threads API 發布模組 (Meta Official API)
"""
import os
import requests
from typing import Optional


class ThreadsAPI:
    """Threads 官方 API 發布器"""

    BASE_URL = "https://graph.threads.net/v1.0"

    def __init__(
        self,
        access_token: str = None,
        user_id: str = None
    ):
        self.access_token = access_token or os.getenv('THREADS_ACCESS_TOKEN')
        self.user_id = user_id or os.getenv('THREADS_USER_ID')

    def is_available(self) -> bool:
        return bool(self.access_token and self.user_id)

    def create_post(
        self,
        text: str,
        image_urls: list[str] = None,
        reply_to_id: str = None
    ) -> Optional[str]:
        """
        發布貼文

        Args:
            text: 貼文內容 (最多 500 字)
            image_urls: 圖片 URL 列表
            reply_to_id: 回覆的貼文 ID

        Returns:
            str: 貼文 ID，失敗返回 None
        """
        if not self.is_available():
            print("[Threads API] 未設定 access_token 或 user_id")
            return None

        try:
            # Step 1: 建立 media container
            container_url = f"{self.BASE_URL}/{self.user_id}/threads"
            payload = {
                "media_type": "TEXT",
                "text": text[:500],  # 限制 500 字
                "access_token": self.access_token,
            }

            if reply_to_id:
                payload["reply_to_id"] = reply_to_id

            if image_urls:
                payload["media_type"] = "IMAGE"
                payload["image_url"] = image_urls[0]

            resp = requests.post(container_url, data=payload, timeout=30)
            resp.raise_for_status()
            container_id = resp.json().get("id")

            if not container_id:
                return None

            # Step 2: 發布
            publish_url = f"{self.BASE_URL}/{self.user_id}/threads_publish"
            publish_resp = requests.post(
                publish_url,
                data={
                    "creation_id": container_id,
                    "access_token": self.access_token,
                },
                timeout=30
            )
            publish_resp.raise_for_status()

            return publish_resp.json().get("id")

        except requests.RequestException as e:
            print(f"[Threads API] 發布失敗: {e}")
            return None

    def create_thread(self, posts: list[str]) -> list[str]:
        """
        發布串文

        Args:
            posts: 貼文內容列表

        Returns:
            list[str]: 貼文 ID 列表
        """
        post_ids = []
        reply_to = None

        for text in posts:
            post_id = self.create_post(text, reply_to_id=reply_to)
            if post_id:
                post_ids.append(post_id)
                reply_to = post_id
            else:
                break

        return post_ids

    def delete_post(self, post_id: str) -> bool:
        """刪除貼文"""
        if not self.is_available():
            return False

        try:
            url = f"{self.BASE_URL}/{post_id}"
            resp = requests.delete(
                url,
                params={"access_token": self.access_token},
                timeout=30
            )
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[Threads API] 刪除失敗: {e}")
            return False
