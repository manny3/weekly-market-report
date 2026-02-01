"""
TradingView 資料抓取模組 (使用 Playwright 截圖)
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from playwright.sync_api import sync_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class TradingViewFetcher:
    """TradingView 圖表截圖工具"""

    BASE_URL = "https://www.tradingview.com/chart"

    # 預設圖表設定
    DEFAULT_SYMBOLS = {
        "us_indices": ["SPX", "NDX", "DJI"],
        "tw_indices": ["TWII", "TPEX"],
    }

    def __init__(self, username: str = None, password: str = None):
        self.username = username
        self.password = password
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    def _launch_browser(self):
        """啟動瀏覽器"""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("playwright 未安裝，請執行 pip install playwright && playwright install")

        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page()

    def _close_browser(self):
        """關閉瀏覽器"""
        if self.browser:
            self.browser.close()
            self.browser = None
            self.page = None

    def _login(self):
        """登入 TradingView (如有帳號)"""
        if not self.username or not self.password:
            return False

        # TODO: 實作登入邏輯
        return False

    def capture_chart(
        self,
        symbol: str,
        interval: str = "D",
        output_path: Path = None
    ) -> Optional[Path]:
        """
        截取圖表

        Args:
            symbol: 股票代碼 (如 NASDAQ:AAPL)
            interval: 時間間隔 (1, 5, 15, 30, 60, 120, 240, D, W, M)
            output_path: 輸出路徑

        Returns:
            Path: 截圖檔案路徑
        """
        if not PLAYWRIGHT_AVAILABLE:
            print("[TradingView] playwright 未安裝")
            return None

        try:
            if not self.page:
                self._launch_browser()

            # 構建 URL
            url = f"https://www.tradingview.com/chart/?symbol={symbol}&interval={interval}"
            self.page.goto(url)
            self.page.wait_for_timeout(3000)  # 等待圖表載入

            # 隱藏不必要的元素 (可選)
            self.page.evaluate("""
                // 隱藏側邊欄和頂部選單
                const sidebar = document.querySelector('[data-name="legend"]');
                if (sidebar) sidebar.style.display = 'none';
            """)

            # 截圖
            if output_path is None:
                output_path = Path(f"./screenshots/{symbol.replace(':', '_')}_{interval}.png")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(output_path), full_page=False)

            return output_path

        except Exception as e:
            print(f"[TradingView] 截圖失敗 ({symbol}): {e}")
            return None

    def capture_multiple(
        self,
        symbols: list[str],
        interval: str = "D",
        output_dir: Path = None
    ) -> dict:
        """
        批次截取多個圖表

        Args:
            symbols: 股票代碼列表
            interval: 時間間隔
            output_dir: 輸出目錄

        Returns:
            dict: 截圖結果
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "interval": interval,
            "screenshots": {}
        }

        if output_dir is None:
            output_dir = Path("./data/raw") / datetime.now().strftime("%Y-%m-%d") / "charts"

        try:
            self._launch_browser()

            for symbol in symbols:
                output_path = output_dir / f"{symbol.replace(':', '_')}_{interval}.png"
                screenshot_path = self.capture_chart(symbol, interval, output_path)

                result["screenshots"][symbol] = {
                    "success": screenshot_path is not None,
                    "path": str(screenshot_path) if screenshot_path else None
                }

        finally:
            self._close_browser()

        return result

    def fetch_all(self, output_dir: Path) -> dict:
        """
        抓取所有預設圖表

        Args:
            output_dir: 輸出目錄

        Returns:
            dict: 抓取結果
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "source": "tradingview",
            "success": False,
            "data": {}
        }

        all_symbols = []
        for category, symbols in self.DEFAULT_SYMBOLS.items():
            all_symbols.extend(symbols)

        charts_dir = output_dir / "charts"
        capture_result = self.capture_multiple(all_symbols, "D", charts_dir)

        result["data"] = capture_result
        result["success"] = any(
            s["success"] for s in capture_result["screenshots"].values()
        )

        # 儲存 metadata
        output_dir.mkdir(parents=True, exist_ok=True)
        metadata_file = output_dir / "tradingview_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result


if __name__ == "__main__":
    # 測試用
    fetcher = TradingViewFetcher()
    print(fetcher.capture_multiple(["NASDAQ:AAPL", "NASDAQ:MSFT"], "D"))
