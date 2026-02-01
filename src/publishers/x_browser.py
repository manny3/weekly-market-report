"""
X (Twitter) Playwright MCP 自動化發布模組 (主要方式)

更新日期: 2026-02-01
使用方式: 搭配 Playwright MCP 瀏覽器自動化

注意事項:
- X API v2 需要付費方案才能發文，因此使用 Playwright 瀏覽器自動化
- X 網站 UI 經常變動，選擇器可能需要定期更新
- 串推建議使用 compose dialog 的「加入貼文」按鈕方式，而非回覆串接

串推發布流程 (Playwright MCP 建議方式):
1. 導航至 x.com，若未登入則輸入 X_USERNAME / X_PASSWORD 登入
2. 點擊「發佈」按鈕開啟 compose dialog
3. 輸入第一則推文內容
4. 點擊「加入貼文」按鈕 (ref 可能是「加另一則貼文」)
5. 重複步驟 3-4 直到所有推文輸入完成 (最多 5 則)
6. 點擊「全部發佈」按鈕
7. 若按鈕被 overlay 擋住，使用 JavaScript 強制點擊:
   document.querySelector('[data-testid="tweetButton"]').click()

憑證來源: .env 中的 X_USERNAME / X_PASSWORD
"""
import os
import time
from typing import Optional, List

try:
    from playwright.sync_api import sync_playwright, Browser, Page, Playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class XBrowser:
    """X (Twitter) 瀏覽器自動化發布器 (主要方式)"""

    LOGIN_URL = "https://x.com/login"
    HOME_URL = "https://x.com/home"
    COMPOSE_URL = "https://x.com/compose/post"

    # 選擇器常數 (方便維護)
    SELECTORS = {
        # 登入相關
        'username_input': 'input[autocomplete="username"], input[name="text"]',
        'password_input': 'input[type="password"], input[name="password"]',
        'next_button': 'button:has-text("Next"), button:has-text("下一步"), button:has-text("下一個")',
        'login_button': 'button:has-text("Log in"), button:has-text("登入")',

        # 發文相關
        'tweet_textbox': '[data-testid="tweetTextarea_0"]',
        'tweet_button': '[data-testid="tweetButton"]',
        'reply_button': '[data-testid="tweetButtonInline"]',

        # 對話框相關
        'dismiss_button': 'button:has-text("稍後再說"), button:has-text("Not now"), button:has-text("Maybe later")',
        'close_button': '[data-testid="xMigrationBottomBar"] button, [aria-label="Close"], [aria-label="關閉"]',
    }

    def __init__(self, username: str = None, password: str = None):
        self.username = username or os.getenv('X_USERNAME')
        self.password = password or os.getenv('X_PASSWORD')
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._logged_in = False
        self._last_tweet_url: Optional[str] = None

    def is_available(self) -> bool:
        """檢查是否可用"""
        return PLAYWRIGHT_AVAILABLE and bool(self.username and self.password)

    def _launch_browser(self, headless: bool = True):
        """啟動瀏覽器"""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("playwright 未安裝，請執行: pip install playwright && playwright install chromium")

        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        context = self.browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        self.page = context.new_page()

    def _close_browser(self):
        """關閉瀏覽器"""
        if self.browser:
            self.browser.close()
            self.browser = None
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
        self.page = None
        self._logged_in = False

    def _safe_click(self, selector: str, timeout: int = 5000) -> bool:
        """
        安全點擊 - 處理可能被遮擋的情況

        Args:
            selector: 選擇器
            timeout: 超時時間 (毫秒)

        Returns:
            bool: 是否成功
        """
        try:
            self.page.click(selector, timeout=timeout)
            return True
        except Exception:
            # 嘗試用 JavaScript 強制點擊
            try:
                self.page.evaluate(f'''
                    const el = document.querySelector('{selector}');
                    if (el) el.click();
                ''')
                return True
            except Exception:
                return False

    def _dismiss_dialogs(self):
        """關閉可能出現的對話框 (Premium 推廣等)"""
        try:
            # 嘗試關閉 Premium 推廣
            dismiss = self.page.locator(self.SELECTORS['dismiss_button']).first
            if dismiss.is_visible(timeout=1000):
                dismiss.click()
                self.page.wait_for_timeout(500)
        except Exception:
            pass

        try:
            # 嘗試關閉其他對話框
            close = self.page.locator(self.SELECTORS['close_button']).first
            if close.is_visible(timeout=500):
                close.click()
        except Exception:
            pass

    def _wait_for_navigation(self, url_contains: str, timeout: int = 10000) -> bool:
        """等待頁面跳轉"""
        start = time.time()
        while time.time() - start < timeout / 1000:
            if url_contains in self.page.url:
                return True
            self.page.wait_for_timeout(500)
        return False

    def login(self, headless: bool = True) -> bool:
        """
        登入 X

        Args:
            headless: 是否無頭模式 (除錯時可設為 False)

        Returns:
            bool: 是否成功
        """
        if self._logged_in:
            return True

        if not self.page:
            self._launch_browser(headless=headless)

        try:
            print("[X Browser] 開始登入...")
            self.page.goto(self.LOGIN_URL)
            self.page.wait_for_timeout(3000)

            # 步驟 1: 輸入用戶名
            username_input = self.page.locator(self.SELECTORS['username_input']).first
            username_input.fill(self.username)
            self.page.wait_for_timeout(500)

            # 步驟 2: 點擊下一步
            next_btn = self.page.locator(self.SELECTORS['next_button']).first
            next_btn.click()
            self.page.wait_for_timeout(2000)

            # 步驟 3: 輸入密碼
            password_input = self.page.locator(self.SELECTORS['password_input']).first
            password_input.fill(self.password)
            self.page.wait_for_timeout(500)

            # 步驟 4: 點擊登入
            login_btn = self.page.locator(self.SELECTORS['login_button']).first
            login_btn.click()

            # 等待跳轉至首頁
            if self._wait_for_navigation("home", timeout=15000):
                self._logged_in = True
                print("[X Browser] 登入成功!")
                self._dismiss_dialogs()
                return True

            print("[X Browser] 登入失敗: 未跳轉至首頁")
            return False

        except Exception as e:
            print(f"[X Browser] 登入失敗: {e}")
            return False

    def create_tweet(self, text: str, image_paths: List[str] = None) -> Optional[str]:
        """
        發布單則推文

        Args:
            text: 推文內容
            image_paths: 本地圖片路徑列表 (最多 4 張)

        Returns:
            str: 推文 URL (失敗則返回 None)
        """
        if not self._logged_in:
            if not self.login():
                return None

        try:
            # 前往發文頁面
            self.page.goto(self.COMPOSE_URL)
            self.page.wait_for_timeout(2000)
            self._dismiss_dialogs()

            # 找到發文輸入框並填入內容
            tweet_box = self.page.locator(self.SELECTORS['tweet_textbox']).first
            tweet_box.fill(text)
            self.page.wait_for_timeout(500)

            # 上傳圖片 (如有)
            if image_paths:
                file_input = self.page.locator('input[type="file"][accept*="image"]').first
                for path in image_paths[:4]:
                    if os.path.exists(path):
                        file_input.set_input_files(path)
                        self.page.wait_for_timeout(1500)

            # 點擊發布按鈕
            if not self._safe_click(self.SELECTORS['tweet_button']):
                print("[X Browser] 點擊發布按鈕失敗")
                return None

            self.page.wait_for_timeout(3000)
            self._dismiss_dialogs()

            # 嘗試獲取推文 URL
            self._last_tweet_url = self._extract_tweet_url()

            print(f"[X Browser] 推文發布成功: {self._last_tweet_url}")
            return self._last_tweet_url

        except Exception as e:
            print(f"[X Browser] 發布失敗: {e}")
            return None

    def _extract_tweet_url(self) -> Optional[str]:
        """從頁面提取剛發布的推文 URL"""
        try:
            # 方法 1: 從通知訊息中提取
            view_link = self.page.locator('a:has-text("查看"), a:has-text("View")').first
            if view_link.is_visible(timeout=2000):
                href = view_link.get_attribute('href')
                if href and '/status/' in href:
                    return f"https://x.com{href}" if href.startswith('/') else href
        except Exception:
            pass

        try:
            # 方法 2: 從頁面 URL 提取
            if '/status/' in self.page.url:
                return self.page.url
        except Exception:
            pass

        return None

    def _reply_to_tweet(self, tweet_url: str, text: str) -> Optional[str]:
        """
        回覆指定推文

        Args:
            tweet_url: 要回覆的推文 URL
            text: 回覆內容

        Returns:
            str: 新推文 URL (失敗則返回 None)
        """
        try:
            # 前往推文詳情頁
            self.page.goto(tweet_url)
            self.page.wait_for_timeout(2000)
            self._dismiss_dialogs()

            # 找到回覆輸入框並填入內容
            reply_box = self.page.locator(self.SELECTORS['tweet_textbox']).first
            reply_box.fill(text)
            self.page.wait_for_timeout(500)

            # 點擊回覆按鈕
            if not self._safe_click(self.SELECTORS['reply_button']):
                # 備案: 用 JavaScript 點擊
                self.page.evaluate('''
                    document.querySelector('[data-testid="tweetButtonInline"]')?.click();
                ''')

            self.page.wait_for_timeout(3000)
            self._dismiss_dialogs()

            # 獲取新推文 URL
            new_url = self._extract_tweet_url()
            return new_url

        except Exception as e:
            print(f"[X Browser] 回覆失敗: {e}")
            return None

    def create_thread(self, tweets: List[str]) -> Optional[str]:
        """
        發布推文串 (使用回覆方式串接)

        Args:
            tweets: 推文內容列表 (每則最多 280 字)

        Returns:
            str: 首則推文 URL (失敗則返回 None)
        """
        if not tweets:
            return None

        if not self._logged_in:
            if not self.login():
                return None

        try:
            print(f"[X Browser] 開始發布 {len(tweets)} 則串推...")

            # 發布第一則
            first_url = self.create_tweet(tweets[0])
            if not first_url:
                print("[X Browser] 首則推文發布失敗")
                return None

            print(f"[X Browser] 1/{len(tweets)} 已發布")
            current_url = first_url

            # 依序回覆剩餘推文
            for i, tweet_text in enumerate(tweets[1:], start=2):
                self.page.wait_for_timeout(1000)  # 避免太快

                new_url = self._reply_to_tweet(current_url, tweet_text)
                if new_url:
                    current_url = new_url
                    print(f"[X Browser] {i}/{len(tweets)} 已發布")
                else:
                    print(f"[X Browser] 第 {i} 則發布失敗，嘗試繼續...")

            print(f"[X Browser] 串推發布完成: {first_url}")
            return first_url

        except Exception as e:
            print(f"[X Browser] 發布串推失敗: {e}")
            return None

    def __enter__(self):
        """Context manager 進入"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 退出"""
        self._close_browser()

    def __del__(self):
        """解構時關閉瀏覽器"""
        self._close_browser()
