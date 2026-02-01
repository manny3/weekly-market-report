"""
台股產業族群表現分析 Fetcher
分析 12 大產業族群漲跌幅、偵測熱門/冷門族群
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# 產業分類定義
INDUSTRY_MAP = {
    "半導體": {
        "stocks": ["2330", "2454", "2379", "2303", "3711"],
        "description": "晶圓代工、IC設計、封測",
    },
    "PCB/ABF載板": {
        "stocks": ["3037", "8046", "6153", "2353"],
        "description": "印刷電路板、ABF載板",
    },
    "AI伺服器": {
        "stocks": ["2382", "6669", "3017", "2356"],
        "description": "AI伺服器、散熱、機殼",
    },
    "航運": {
        "stocks": ["2603", "2609", "2615"],
        "description": "貨櫃航運、散裝航運",
    },
    "金融": {
        "stocks": ["2881", "2882", "2891", "2886"],
        "description": "金控、銀行、壽險",
    },
    "生技": {
        "stocks": ["4743", "6446", "1760"],
        "description": "新藥、醫療器材",
    },
    "面板": {
        "stocks": ["2409", "3481", "6116"],
        "description": "LCD面板、觸控面板",
    },
    "被動元件": {
        "stocks": ["2327", "3037", "2492"],
        "description": "電阻、電容、電感",
    },
    "記憶體": {
        "stocks": ["2344", "8299", "4967"],
        "description": "DRAM、NAND Flash、SSD",
    },
    "電動車": {
        "stocks": ["2308", "2395", "6121"],
        "description": "電動車零組件、電池",
    },
    "綠能": {
        "stocks": ["6244", "3576", "6443"],
        "description": "太陽能、風電、儲能",
    },
    "傳產": {
        "stocks": ["1301", "1303", "1326"],
        "description": "塑化、鋼鐵、紡織",
    },
}

# 股票名稱對照
STOCK_NAME_MAP = {
    "2330": "台積電", "2454": "聯發科", "2379": "瑞昱", "2303": "聯電",
    "3711": "日月光投控", "3037": "欣興", "8046": "南電", "6153": "嘉聯益",
    "2353": "宏碁", "2382": "廣達", "6669": "緯穎", "3017": "奇鋐",
    "2356": "英業達", "2603": "長榮", "2609": "陽明", "2615": "萬海",
    "2881": "富邦金", "2882": "國泰金", "2891": "中信金", "2886": "兆豐金",
    "4743": "合一", "6446": "藥華藥", "1760": "寶齡富錦",
    "2409": "友達", "3481": "群創", "6116": "彩晶",
    "2327": "國巨", "2492": "華新科",
    "2344": "華邦電", "8299": "群聯", "4967": "十銓",
    "2308": "台達電", "2395": "研華", "6121": "新普",
    "6244": "茂迪", "3576": "聯合再生", "6443": "元晶",
    "1301": "台塑", "1303": "南亞", "1326": "台化",
}


class TwIndustryFetcher:
    """台股產業族群表現分析"""

    FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"

    def __init__(self, api_token: Optional[str] = None):
        """
        初始化 TW Industry Fetcher

        Args:
            api_token: FinMind API token
        """
        self.api_token = api_token or os.getenv("FINMIND_API_TOKEN", "")
        self.session = requests.Session() if REQUESTS_AVAILABLE else None

    def _fetch_stock_price(self, stock_id: str, days: int = 10) -> list:
        """取得個股日線資料"""
        if not self.session:
            return []

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        params = {
            "dataset": "TaiwanStockPrice",
            "data_id": stock_id,
            "start_date": start_date,
            "end_date": end_date,
        }

        headers = {}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        try:
            resp = self.session.get(
                self.FINMIND_URL,
                params=params,
                headers=headers,
                timeout=30,
            )
            data = resp.json()
            if data.get("status") == 200:
                return data.get("data", [])
        except Exception:
            pass
        return []

    def _calc_week_change(self, price_data: list) -> Optional[float]:
        """計算週漲跌幅"""
        if len(price_data) < 2:
            return None

        latest_close = price_data[-1].get("close")
        # 取最近 5 個交易日前的收盤價
        idx = max(0, len(price_data) - 6)
        prev_close = price_data[idx].get("close")

        if latest_close and prev_close and prev_close > 0:
            return round((latest_close - prev_close) / prev_close * 100, 2)
        return None

    def get_industry_performance(self) -> dict:
        """
        計算各產業族群表現

        Returns:
            dict: 產業族群表現資料
        """
        if not self.session:
            return {"error": "requests 未安裝"}

        industries = []
        all_stocks_seen = set()

        for industry_name, config in INDUSTRY_MAP.items():
            stock_ids = config["stocks"]
            stock_changes = []
            top_gainers = []

            for stock_id in stock_ids:
                if stock_id in all_stocks_seen:
                    continue
                all_stocks_seen.add(stock_id)

                price_data = self._fetch_stock_price(stock_id)
                change_pct = self._calc_week_change(price_data)

                if change_pct is not None:
                    stock_changes.append(change_pct)
                    top_gainers.append({
                        "stock_id": stock_id,
                        "name": STOCK_NAME_MAP.get(stock_id, stock_id),
                        "change_pct": change_pct,
                    })

            if not stock_changes:
                continue

            avg_change = round(sum(stock_changes) / len(stock_changes), 2)
            top_gainers.sort(key=lambda x: x["change_pct"], reverse=True)

            industries.append({
                "industry_name": industry_name,
                "description": config["description"],
                "week_change_pct": avg_change,
                "stock_count": len(stock_changes),
                "top_gainers": top_gainers[:3],
                "top_losers": list(reversed(top_gainers[-2:])) if len(top_gainers) > 2 else [],
            })

        # 按漲幅排序
        industries.sort(key=lambda x: x["week_change_pct"], reverse=True)

        # 偵測熱門/冷門族群
        hot_threshold = 2.0
        cold_threshold = -2.0
        hot_industries = [i["industry_name"] for i in industries if i["week_change_pct"] > hot_threshold]
        cold_industries = [i["industry_name"] for i in industries if i["week_change_pct"] < cold_threshold]

        return {
            "success": True,
            "industries": industries,
            "hot_industries": hot_industries,
            "cold_industries": cold_industries,
            "summary": {
                "total_industries": len(industries),
                "hot_count": len(hot_industries),
                "cold_count": len(cold_industries),
                "best": industries[0]["industry_name"] if industries else None,
                "worst": industries[-1]["industry_name"] if industries else None,
            },
        }

    def fetch_all(self, output_dir: Path) -> dict:
        """
        抓取台股族群表現並儲存

        Args:
            output_dir: 輸出目錄

        Returns:
            dict: 抓取結果
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "source": "finmind",
            "success": False,
            "data": {},
        }

        if not REQUESTS_AVAILABLE:
            result["error"] = "requests 未安裝"
            return result

        try:
            print("  [Industry] 分析台股產業族群表現...")
            performance = self.get_industry_performance()

            if "error" in performance:
                result["error"] = performance["error"]
                return result

            result["data"] = performance
            result["success"] = True

            # 儲存到檔案
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "tw_industry_performance.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)

        except Exception as e:
            result["error"] = str(e)

        return result


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / "config" / ".env")

    fetcher = TwIndustryFetcher()
    result = fetcher.fetch_all(Path("./data/raw/test"))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
