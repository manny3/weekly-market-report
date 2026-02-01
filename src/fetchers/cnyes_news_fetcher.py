"""
鉅亨網 (Cnyes) 台股新聞 Fetcher
抓取台股市場新聞
來源: cnyes.com API
"""
import json
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


class CnyesNewsFetcher:
    """鉅亨網台股新聞 Fetcher"""

    # 鉅亨網 API
    API_BASE_URL = "https://api.cnyes.com/media/api/v1/newslist/category"

    # Fallback: 網頁爬蟲
    WEB_URL = "https://news.cnyes.com/news/cat/tw_stock_news"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    }

    def __init__(self):
        """初始化 Cnyes News Fetcher"""
        self.session = requests.Session() if DEPS_AVAILABLE else None
        if self.session:
            self.session.headers.update(self.HEADERS)

    def _format_timestamp(self, ts: int) -> str:
        """將 Unix 時間戳轉為 ISO 格式"""
        try:
            return datetime.fromtimestamp(ts).isoformat()
        except (ValueError, TypeError, OSError):
            return ""

    def get_tw_headlines(self, category: str = "tw_stock", count: int = 5) -> dict:
        """
        從 API 取得台股新聞

        Args:
            category: 新聞類別 (tw_stock, tw_stock_news, intl_stock)
            count: 要回傳的新聞數量

        Returns:
            dict: 新聞資料
        """
        if not self.session:
            return {"error": "requests 未安裝"}

        try:
            resp = self.session.get(
                f"{self.API_BASE_URL}/{category}",
                params={
                    "limit": count * 2,
                    "page": 1,
                },
                timeout=30,
            )
            resp.raise_for_status()

            data = resp.json()

            # cnyes API 回傳格式: {"items": {"data": [...]}} 或 {"data": [...]}
            items = []
            if isinstance(data, dict):
                if "items" in data and isinstance(data["items"], dict):
                    items = data["items"].get("data", [])
                elif "items" in data and isinstance(data["items"], list):
                    items = data["items"]
                elif "data" in data and isinstance(data["data"], list):
                    items = data["data"]

            headlines = []
            for item in items[:count]:
                headline = {
                    "newsId": item.get("newsId") or item.get("id", ""),
                    "title": item.get("title", ""),
                    "url": "",
                    "publishAt": "",
                    "categoryName": item.get("categoryName", "台股新聞"),
                    "summary": item.get("summary", item.get("content", ""))[:200],
                }

                # 建構 URL
                news_id = headline["newsId"]
                if news_id:
                    headline["url"] = f"https://news.cnyes.com/news/id/{news_id}"

                # 處理時間
                pub_at = item.get("publishAt") or item.get("pubAt") or item.get("created_at", 0)
                if isinstance(pub_at, (int, float)) and pub_at > 0:
                    headline["publishAt"] = self._format_timestamp(int(pub_at))
                elif isinstance(pub_at, str):
                    headline["publishAt"] = pub_at

                headlines.append(headline)

            return {
                "success": True,
                "headlines": headlines,
                "count": len(headlines),
                "category": category,
            }

        except requests.exceptions.RequestException as e:
            # API 失敗，嘗試 fallback 爬蟲
            print(f"  [CnyesNews] API 失敗: {e}，嘗試網頁爬蟲...")
            return self._fallback_scrape(count)
        except Exception as e:
            return {"error": f"處理失敗: {str(e)}"}

    def _fallback_scrape(self, count: int = 5) -> dict:
        """
        Fallback: 用 BeautifulSoup 爬鉅亨網新聞頁面

        Args:
            count: 要回傳的新聞數量

        Returns:
            dict: 新聞資料
        """
        if not BS4_AVAILABLE:
            return {"error": "需安裝 beautifulsoup4 (pip install beautifulsoup4)"}

        if not self.session:
            return {"error": "requests 未安裝"}

        try:
            resp = self.session.get(self.WEB_URL, timeout=30)
            resp.raise_for_status()
            resp.encoding = "utf-8"

            soup = BeautifulSoup(resp.text, "html.parser")

            headlines = []
            # 嘗試多種可能的選擇器
            articles = (
                soup.select("a._2wbz") or      # 新版
                soup.select("a[href*='/news/id/']") or  # 通用
                soup.select(".listItem a") or   # 舊版
                []
            )

            seen_titles = set()
            for article in articles:
                title = article.get_text(strip=True)
                href = article.get("href", "")

                if not title or title in seen_titles:
                    continue

                seen_titles.add(title)

                url = href
                if href and not href.startswith("http"):
                    url = f"https://news.cnyes.com{href}"

                headlines.append({
                    "newsId": "",
                    "title": title,
                    "url": url,
                    "publishAt": "",
                    "categoryName": "台股新聞",
                    "summary": "",
                })

                if len(headlines) >= count:
                    break

            return {
                "success": True,
                "headlines": headlines,
                "count": len(headlines),
                "category": "tw_stock",
                "method": "web_scrape",
            }

        except Exception as e:
            return {"error": f"網頁爬蟲失敗: {str(e)}"}

    def fetch_all(self, output_dir: Path, count: int = 5) -> dict:
        """
        抓取台股新聞並儲存

        Args:
            output_dir: 輸出目錄
            count: 要抓取的新聞數量

        Returns:
            dict: 抓取結果
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "source": "cnyes",
            "success": False,
            "data": {},
        }

        if not DEPS_AVAILABLE:
            result["error"] = "需安裝 requests (pip install requests)"
            return result

        try:
            print("  [CnyesNews] 抓取台股新聞...")

            news = self.get_tw_headlines(category="tw_stock", count=count)

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
            output_file = output_dir / "cnyes_news_data.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)

            print(f"  [CnyesNews] 取得 {news['count']} 則新聞")

        except Exception as e:
            result["error"] = str(e)

        return result


if __name__ == "__main__":
    fetcher = CnyesNewsFetcher()
    result = fetcher.fetch_all(Path("./data/raw/test/daily"), count=5)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
