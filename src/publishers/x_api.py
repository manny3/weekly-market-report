"""
X (Twitter) API v2 發布模組
"""
import os
from typing import Optional

try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False


class XAPI:
    """X (Twitter) API v2 發布器"""

    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        access_token: str = None,
        access_token_secret: str = None,
        bearer_token: str = None
    ):
        self.api_key = api_key or os.getenv('X_API_KEY')
        self.api_secret = api_secret or os.getenv('X_API_SECRET')
        self.access_token = access_token or os.getenv('X_ACCESS_TOKEN')
        self.access_token_secret = access_token_secret or os.getenv('X_ACCESS_TOKEN_SECRET')
        self.bearer_token = bearer_token or os.getenv('X_BEARER_TOKEN')

        self.client: Optional[tweepy.Client] = None
        self._init_client()

    def _init_client(self):
        """初始化 Tweepy 客戶端"""
        if not TWEEPY_AVAILABLE:
            print("[X API] tweepy 未安裝，請執行 pip install tweepy")
            return

        if all([self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
            self.client = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
            )

    def is_available(self) -> bool:
        return self.client is not None

    def create_tweet(
        self,
        text: str,
        reply_to_id: str = None,
        media_ids: list[str] = None
    ) -> Optional[str]:
        """
        發布推文

        Args:
            text: 推文內容 (最多 280 字)
            reply_to_id: 回覆的推文 ID
            media_ids: 媒體 ID 列表

        Returns:
            str: 推文 ID，失敗返回 None
        """
        if not self.client:
            print("[X API] 客戶端未初始化")
            return None

        try:
            response = self.client.create_tweet(
                text=text[:280],
                in_reply_to_tweet_id=reply_to_id,
                media_ids=media_ids
            )
            return response.data.get("id")
        except tweepy.TweepyException as e:
            print(f"[X API] 發布失敗: {e}")
            return None

    def create_thread(self, tweets: list[str]) -> list[str]:
        """
        發布推文串

        Args:
            tweets: 推文內容列表

        Returns:
            list[str]: 推文 ID 列表
        """
        tweet_ids = []
        reply_to = None

        for text in tweets:
            tweet_id = self.create_tweet(text, reply_to_id=reply_to)
            if tweet_id:
                tweet_ids.append(tweet_id)
                reply_to = tweet_id
            else:
                break

        return tweet_ids

    def delete_tweet(self, tweet_id: str) -> bool:
        """刪除推文"""
        if not self.client:
            return False

        try:
            self.client.delete_tweet(tweet_id)
            return True
        except tweepy.TweepyException as e:
            print(f"[X API] 刪除失敗: {e}")
            return False

    def upload_media(self, file_path: str) -> Optional[str]:
        """
        上傳媒體檔案

        注意：需要使用 API v1.1 進行媒體上傳
        """
        if not TWEEPY_AVAILABLE:
            return None

        try:
            # API v1.1 for media upload
            auth = tweepy.OAuthHandler(self.api_key, self.api_secret)
            auth.set_access_token(self.access_token, self.access_token_secret)
            api = tweepy.API(auth)

            media = api.media_upload(file_path)
            return media.media_id_string
        except Exception as e:
            print(f"[X API] 媒體上傳失敗: {e}")
            return None
