"""
圖表截圖工具
"""
from pathlib import Path
from typing import Optional

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class ChartScreenshot:
    """圖表截圖工具"""

    def __init__(self):
        self.browser = None
        self.page = None

    def capture_tradingview(
        self,
        symbol: str,
        interval: str = "D",
        output_path: Path = None
    ) -> Optional[Path]:
        """
        截取 TradingView 圖表

        Args:
            symbol: 股票代碼 (如 NASDAQ:AAPL)
            interval: 時間間隔
            output_path: 輸出路徑

        Returns:
            截圖路徑
        """
        if not PLAYWRIGHT_AVAILABLE:
            print("playwright 未安裝")
            return None

        url = f"https://www.tradingview.com/chart/?symbol={symbol}&interval={interval}"

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url)
                page.wait_for_timeout(3000)

                if output_path is None:
                    output_path = Path(f"./{symbol.replace(':', '_')}.png")

                output_path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(output_path))
                browser.close()

                return output_path

        except Exception as e:
            print(f"截圖失敗: {e}")
            return None

    def capture_finviz_heatmap(self, output_path: Path = None) -> Optional[Path]:
        """
        截取 Finviz 熱力圖

        Args:
            output_path: 輸出路徑

        Returns:
            截圖路徑
        """
        if not PLAYWRIGHT_AVAILABLE:
            return None

        url = "https://finviz.com/map.ashx?t=sec_all"

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1920, "height": 1080})
                page.goto(url)
                page.wait_for_timeout(3000)

                if output_path is None:
                    output_path = Path("./finviz_heatmap.png")

                output_path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(output_path))
                browser.close()

                return output_path

        except Exception as e:
            print(f"截圖失敗: {e}")
            return None
