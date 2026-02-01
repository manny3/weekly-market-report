"""
Finnhub 新聞 Fetcher
抓取美股市場新聞
來源: Finnhub API (https://finnhub.io/)
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    import requests
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False


class FinnhubNewsFetcher:
    """Finnhub 新聞 Fetcher - 抓取美股市場新聞"""

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Finnhub News Fetcher

        Args:
            api_key: Finnhub API Key (預設從環境變數 FINNHUB_API_KEY 讀取)
        """
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY", "")
        self.session = requests.Session() if DEPS_AVAILABLE else None
        if self.session:
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json",
            })

    def _is_within_hours(self, timestamp: int, hours: int = 24) -> bool:
        """檢查時間戳是否在指定小時內"""
        cutoff = datetime.now() - timedelta(hours=hours)
        article_time = datetime.fromtimestamp(timestamp)
        return article_time >= cutoff

    def _format_datetime(self, timestamp: int) -> str:
        """將 Unix 時間戳轉為 ISO 格式"""
        return datetime.fromtimestamp(timestamp).isoformat()

    def get_market_news(self, category: str = "general", count: int = 5, hours: int = 48) -> dict:
        """
        取得市場新聞

        Args:
            category: 新聞類別 (general, forex, crypto, merger)
            count: 要回傳的新聞數量
            hours: 只取最近幾小時內的新聞

        Returns:
            dict: 新聞資料
        """
        if not self.session:
            return {"error": "requests 未安裝"}

        if not self.api_key:
            return {"error": "未設定 FINNHUB_API_KEY 環境變數"}

        try:
            resp = self.session.get(
                f"{self.BASE_URL}/news",
                params={
                    "category": category,
                    "token": self.api_key,
                },
                timeout=30,
            )
            resp.raise_for_status()

            articles = resp.json()

            if not isinstance(articles, list):
                return {"error": f"Unexpected response format: {type(articles)}"}

            # 過濾最近 N 小時內的新聞
            filtered = []
            for article in articles:
                timestamp = article.get("datetime", 0)
                if self._is_within_hours(timestamp, hours):
                    filtered.append({
                        "id": article.get("id"),
                        "headline": article.get("headline", ""),
                        "source": article.get("source", ""),
                        "url": article.get("url", ""),
                        "datetime": self._format_datetime(timestamp),
                        "timestamp": timestamp,
                        "related": article.get("related", ""),
                        "summary": article.get("summary", ""),
                        "image": article.get("image", ""),
                        "category": category,
                    })

            # 按時間排序（最新在前），取前 count 則
            filtered.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            headlines = filtered[:count]

            return {
                "success": True,
                "headlines": headlines,
                "count": len(headlines),
                "total_available": len(filtered),
                "category": category,
                "hours_filter": hours,
            }

        except requests.exceptions.RequestException as e:
            return {"error": f"API 請求失敗: {str(e)}"}
        except Exception as e:
            return {"error": f"處理失敗: {str(e)}"}

    def get_company_news(self, symbol: str, days: int = 7, count: int = 5) -> dict:
        """
        取得個股新聞

        Args:
            symbol: 股票代碼 (e.g. AAPL)
            days: 取最近幾天的新聞
            count: 要回傳的新聞數量

        Returns:
            dict: 新聞資料
        """
        if not self.session:
            return {"error": "requests 未安裝"}

        if not self.api_key:
            return {"error": "未設定 FINNHUB_API_KEY 環境變數"}

        today = datetime.now()
        from_date = (today - timedelta(days=days)).strftime("%Y-%m-%d")
        to_date = today.strftime("%Y-%m-%d")

        try:
            resp = self.session.get(
                f"{self.BASE_URL}/company-news",
                params={
                    "symbol": symbol.upper(),
                    "from": from_date,
                    "to": to_date,
                    "token": self.api_key,
                },
                timeout=30,
            )
            resp.raise_for_status()

            articles = resp.json()

            if not isinstance(articles, list):
                return {"error": f"Unexpected response format: {type(articles)}"}

            headlines = []
            for article in articles[:count]:
                timestamp = article.get("datetime", 0)
                headlines.append({
                    "id": article.get("id"),
                    "headline": article.get("headline", ""),
                    "source": article.get("source", ""),
                    "url": article.get("url", ""),
                    "datetime": self._format_datetime(timestamp) if timestamp else "",
                    "timestamp": timestamp,
                    "summary": article.get("summary", ""),
                    "symbol": symbol.upper(),
                })

            return {
                "success": True,
                "symbol": symbol.upper(),
                "headlines": headlines,
                "count": len(headlines),
                "date_range": {"from": from_date, "to": to_date},
            }

        except requests.exceptions.RequestException as e:
            return {"error": f"API 請求失敗: {str(e)}"}
        except Exception as e:
            return {"error": f"處理失敗: {str(e)}"}

    def fetch_all(self, output_dir: Path, count: int = 5) -> dict:
        """
        抓取市場新聞並儲存

        Args:
            output_dir: 輸出目錄
            count: 要抓取的新聞數量

        Returns:
            dict: 抓取結果
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "source": "finnhub",
            "success": False,
            "data": {},
        }

        if not DEPS_AVAILABLE:
            result["error"] = "需安裝 requests (pip install requests)"
            return result

        if not self.api_key:
            result["error"] = "未設定 FINNHUB_API_KEY 環境變數"
            return result

        try:
            print("  [FinnhubNews] 抓取美股市場新聞...")

            news = self.get_market_news(category="general", count=count)

            if "error" in news:
                result["error"] = news["error"]
                return result

            result["data"] = {
                "headlines": news["headlines"],
                "count": news["count"],
                "fetch_date": datetime.now().strftime("%Y-%m-%d"),
            }
            result["success"] = True

            # 儲存到檔案
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "finnhub_news_data.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)

            print(f"  [FinnhubNews] 取得 {news['count']} 則新聞")

        except Exception as e:
            result["error"] = str(e)

        return result


if __name__ == "__main__":
    # 測試用
    from dotenv import load_dotenv
    load_dotenv("config/.env")

    fetcher = FinnhubNewsFetcher()
    result = fetcher.fetch_all(Path("./data/raw/test/daily"), count=5)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
