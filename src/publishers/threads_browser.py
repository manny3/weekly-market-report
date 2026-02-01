"""
Threads Playwright MCP 發布模組 (主要方式)

更新日期: 2026-02-01
使用方式: 搭配 Playwright MCP 瀏覽器自動化

登入流程:
1. 導航至 threads.com
2. 點擊「建立」按鈕，若未登入會顯示登入對話框
3. 點擊「使用 Instagram 帳號繼續」(重要：不要直接輸入帳密)
4. 在 Instagram 登入頁面輸入 THREADS_USERNAME / THREADS_PASSWORD (Instagram 帳密)
5. 若出現「儲存登入資料」提示，點擊「稍後再說」
6. 登入成功後自動跳轉回 Threads

注意事項:
- THREADS_USERNAME / THREADS_PASSWORD 是 Instagram 帳號密碼
- 不支援 Threads 直接登入（會顯示密碼錯誤）
- 建議使用 Playwright MCP 手動操作，此模組為備用參考
"""
import os
from typing import Optional

try:
    from playwright.sync_api import sync_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class ThreadsBrowser:
    """Threads 瀏覽器自動化發布器 (主要方式，透過 Instagram OAuth 登入)"""

    LOGIN_URL = "https://www.threads.com/login"
    POST_URL = "https://www.threads.com"

    # Threads 登入頁面 selectors
    # 優先使用已儲存的 Instagram 帳號按鈕（含帳號名稱）
    SEL_IG_CONTINUE_BTN = 'button:has-text("使用 Instagram 帳號繼續")'
    # 備用：直接輸入帳密的欄位
    SEL_USERNAME = 'input[autocomplete="username"]'
    SEL_PASSWORD = 'input[autocomplete="current-password"]'

    # Instagram 登入頁面 selectors（支援不同版本的登入頁面）
    SEL_IG_USERNAME = 'input[name="username"], input[name="email"]'
    SEL_IG_PASSWORD = 'input[name="password"], input[name="pass"]'
    SEL_IG_LOGIN_BTN = 'div[role="button"]:has-text("登入")'
    SEL_IG_LOGIN_BTN_EN = 'div[role="button"]:has-text("Log in"), button:has-text("Log in"), button:has-text("登入")'

    # 發文相關 selectors（支援中英文介面）
    SEL_NEW_POST_BTN = 'button[aria-label="建立"], button[aria-label="Create"]'
    SEL_POST_EDITOR = 'div[role="textbox"]'
    SEL_SUBMIT_BTN = 'button:has-text("發佈"), button:has-text("Post")'
    SEL_FILE_INPUT = 'input[type="file"][accept*="image"]'

    def __init__(self, username: str = None, password: str = None):
        self.username = username or os.getenv('THREADS_USERNAME')
        self.password = password or os.getenv('THREADS_PASSWORD')
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._playwright = None
        self._logged_in = False

    def is_available(self) -> bool:
        return PLAYWRIGHT_AVAILABLE and bool(self.username and self.password)

    def _launch_browser(self, headless: bool = True):
        """啟動瀏覽器"""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("playwright 未安裝")

        self._playwright = sync_playwright().start()
        self.browser = self._playwright.chromium.launch(headless=headless)
        context = self.browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="zh-TW",
        )
        self.page = context.new_page()

    def _close_browser(self):
        """關閉瀏覽器"""
        if self.browser:
            self.browser.close()
            self.browser = None
            self.page = None
            self._logged_in = False
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def login(self) -> bool:
        """
        登入 Threads（透過 Instagram OAuth 流程）

        流程：
        1. 前往 threads.com/login
        2. 嘗試使用已儲存的 Instagram 帳號（如有）
        3. 或點擊「使用 Instagram 帳號繼續」後輸入帳密
        4. 自動跳轉回 Threads
        """
        if not self.page:
            self._launch_browser()

        try:
            self.page.goto(self.LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
            self.page.wait_for_timeout(2000)

            # 優先檢查是否有已儲存的 Instagram 帳號按鈕
            saved_account_btn = self.page.locator('button:has-text("使用 Instagram 帳號繼續")').first
            if saved_account_btn.count() > 0:
                try:
                    saved_account_btn.click(timeout=5000)
                    self.page.wait_for_timeout(3000)

                    # 檢查是否已登入成功
                    current_url = self.page.url
                    if "threads.com" in current_url and "/login" not in current_url:
                        self._logged_in = True
                        print("[Threads Browser] 使用已儲存帳號登入成功")
                        return True
                except Exception:
                    pass

            # 如果沒有已儲存帳號，嘗試直接在頁面輸入帳密
            username_input = self.page.locator(self.SEL_USERNAME)
            if username_input.count() > 0:
                username_input.fill(self.username)
                self.page.locator(self.SEL_PASSWORD).fill(self.password)
                self.page.get_by_role("button", name="登入").click()
                self.page.wait_for_timeout(5000)

            # 如果還沒登入，嘗試 Instagram OAuth 流程
            if "/login" in self.page.url:
                ig_btn = self.page.locator(self.SEL_IG_CONTINUE_BTN).first
                if ig_btn.count() > 0:
                    ig_btn.click()
                    self.page.wait_for_selector(self.SEL_IG_USERNAME, timeout=30000)

                    self.page.fill(self.SEL_IG_USERNAME, self.username)
                    self.page.fill(self.SEL_IG_PASSWORD, self.password)

                    login_btn = self.page.locator(self.SEL_IG_LOGIN_BTN)
                    if login_btn.count() == 0:
                        login_btn = self.page.locator(self.SEL_IG_LOGIN_BTN_EN)
                    login_btn.first.click()

                    self.page.wait_for_timeout(8000)

                    # 處理「儲存登入資料」彈窗
                    try:
                        save_later = self.page.get_by_text("稍後再說", exact=True)
                        if save_later.count() > 0:
                            save_later.click(timeout=5000)
                            self.page.wait_for_timeout(2000)
                    except Exception:
                        pass

            # 等待跳轉回 Threads
            try:
                self.page.wait_for_url("**/threads.com/**", wait_until="domcontentloaded", timeout=30000)
            except Exception:
                pass

            # 確認已在 Threads
            current_url = self.page.url
            if "threads.com" in current_url and "/login" not in current_url:
                self._logged_in = True
                print("[Threads Browser] 登入成功")
                return True

            print("[Threads Browser] 登入失敗：未能成功跳轉")
            return False

        except Exception as e:
            print(f"[Threads Browser] 登入失敗: {e}")
            try:
                self.page.screenshot(path="threads_login_failed.png")
            except Exception:
                pass
            return False

    def create_post(self, text: str, image_paths: list[str] = None) -> bool:
        """
        發布貼文

        Args:
            text: 貼文內容（注意：多行內容會被轉換為單行，使用 | 分隔）
            image_paths: 本地圖片路徑列表

        Returns:
            bool: 是否成功
        """
        if not self._logged_in:
            if not self.login():
                return False

        try:
            # 如果不在 Threads，導航到首頁
            if "threads.com" not in self.page.url or "/login" in self.page.url:
                self.page.goto(self.POST_URL, wait_until="domcontentloaded", timeout=30000)
                self.page.wait_for_timeout(2000)

            # 點擊新增貼文按鈕
            new_post_btn = self.page.locator(self.SEL_NEW_POST_BTN).first
            new_post_btn.wait_for(timeout=15000)
            new_post_btn.click()
            self.page.wait_for_timeout(1500)

            # 等待編輯器出現（使用 role="textbox"）
            editor = self.page.get_by_role("textbox").first
            editor.wait_for(timeout=10000)

            # 轉換多行文字為單行（Threads API 不接受多行內容）
            single_line_text = text.replace('\n\n', ' | ').replace('\n', ' ')

            # 輸入內容
            editor.fill(single_line_text)
            self.page.wait_for_timeout(500)

            # 上傳圖片 (如有)
            if image_paths:
                file_input = self.page.locator(self.SEL_FILE_INPUT).first
                for path in image_paths[:10]:  # 最多 10 張
                    file_input.set_input_files(path)
                    self.page.wait_for_timeout(1500)

            # 發布（點擊 dialog 內的發佈按鈕）
            submit_btn = self.page.get_by_role("button", name="發佈")
            submit_btn.click()

            # 等待發布完成
            self.page.wait_for_timeout(3000)

            # 確認沒有錯誤訊息
            error_msg = self.page.get_by_text("無法上傳貼文")
            if error_msg.count() > 0:
                print("[Threads Browser] 發布失敗：無法上傳貼文")
                return False

            print("[Threads Browser] 貼文發布成功")
            return True

        except Exception as e:
            print(f"[Threads Browser] 發布失敗: {e}")
            try:
                self.page.screenshot(path="threads_post_failed.png")
                print("[Threads Browser] 已儲存失敗截圖: threads_post_failed.png")
            except Exception:
                pass
            return False

    def create_thread(self, posts: list[str]) -> bool:
        """發布串文"""
        for i, text in enumerate(posts):
            if i == 0:
                success = self.create_post(text)
            else:
                # TODO: 實作回覆功能
                success = True

            if not success:
                return False

        return True

    def __del__(self):
        self._close_browser()
