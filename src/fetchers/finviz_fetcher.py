"""
Finviz 美股篩選器
"""
import json
from datetime import datetime
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
    SCRAPER_AVAILABLE = True
except ImportError:
    SCRAPER_AVAILABLE = False


class FinvizFetcher:
    """Finviz 美股篩選器"""

    BASE_URL = "https://finviz.com"
    SCREENER_URL = f"{BASE_URL}/screener.ashx"
    HEATMAP_URL = f"{BASE_URL}/map.ashx"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Safari/537.36',
    }

    def __init__(self):
        if not SCRAPER_AVAILABLE:
            print("[Finviz] requests 或 beautifulsoup4 未安裝")
        self.session = requests.Session() if SCRAPER_AVAILABLE else None

    def screen_stocks(self, filters: dict = None) -> list[dict]:
        """
        美股篩選

        Args:
            filters: 篩選條件
                - market_cap: 市值 (e.g., "mega", "large", "mid")
                - pe_ratio: 本益比範圍
                - revenue_growth: 營收成長

        Returns:
            list[dict]: 符合條件的股票
        """
        if not self.session:
            return [{"error": "爬蟲套件未安裝"}]

        # 構建篩選 URL
        filter_params = []
        if filters:
            if 'market_cap' in filters:
                cap_map = {"mega": "cap_mega", "large": "cap_large", "mid": "cap_mid"}
                cap = cap_map.get(filters['market_cap'], '')
                if cap:
                    filter_params.append(cap)

        params = {
            'v': '111',  # Overview view
            'f': ','.join(filter_params) if filter_params else '',
        }

        try:
            resp = self.session.get(
                self.SCREENER_URL,
                params=params,
                headers=self.HEADERS,
                timeout=10
            )
            # TODO: 解析篩選結果
            return []
        except Exception as e:
            return [{"error": str(e)}]

    def get_sector_performance(self) -> dict:
        """取得板塊表現"""
        # TODO: 實作板塊表現抓取
        return {}

    def fetch_all(self, output_dir: Path) -> dict:
        """抓取所有 Finviz 資料"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "source": "finviz",
            "success": False,
            "data": {}
        }

        try:
            result["data"]["screener"] = self.screen_stocks({
                "market_cap": "large"
            })
            result["data"]["sectors"] = self.get_sector_performance()
            result["success"] = True

            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "finviz_data.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

        except Exception as e:
            result["error"] = str(e)

        return result
