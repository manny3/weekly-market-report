"""
營收亮點 Fetcher
偵測營收創新高、年增率等 highlight
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


# 台股股票名稱對照 (常用個股)
STOCK_NAME_MAP = {
    "2330": "台積電", "2454": "聯發科", "2317": "鴻海", "2308": "台達電",
    "2412": "中華電", "2881": "富邦金", "2882": "國泰金", "2891": "中信金",
    "2886": "兆豐金", "2884": "玉山金", "2002": "中鋼", "1301": "台塑",
    "1303": "南亞", "1326": "台化", "2603": "長榮", "2609": "陽明",
    "2615": "萬海", "3037": "欣興", "8046": "南電", "6153": "嘉聯益",
    "2353": "宏碁", "2382": "廣達", "6669": "緯穎", "3017": "奇鋐",
    "2356": "英業達", "2409": "友達", "3481": "群創", "6116": "彩晶",
    "2327": "國巨", "2492": "華新科", "2344": "華邦電", "8299": "群聯",
    "4967": "十銓", "2395": "研華", "6121": "新普", "6244": "茂迪",
    "3576": "聯合再生", "6443": "元晶", "4743": "合一", "6446": "藥華藥",
    "1760": "寶齡富錦", "2379": "瑞昱", "2303": "聯電", "3711": "日月光投控",
}


def _format_revenue(revenue: float) -> str:
    """格式化營收數字（轉為億/千萬）"""
    if revenue >= 1e11:  # 千億
        return f"{revenue / 1e8:,.0f}億"
    elif revenue >= 1e8:  # 億
        return f"{revenue / 1e8:,.1f}億"
    elif revenue >= 1e7:  # 千萬
        return f"{revenue / 1e7:,.1f}千萬"
    else:
        return f"{revenue:,.0f}"


class RevenueHighlightsFetcher:
    """營收亮點 Fetcher - 偵測營收新高、YoY 亮點"""

    FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"

    def __init__(self, api_token: Optional[str] = None):
        """
        初始化 Revenue Highlights Fetcher

        Args:
            api_token: FinMind API token
        """
        self.api_token = api_token or os.getenv("FINMIND_API_TOKEN", "")
        self.session = requests.Session() if REQUESTS_AVAILABLE else None
        self.historical_records = self._load_historical_records()

    def _load_historical_records(self) -> dict:
        """載入歷史營收紀錄"""
        records_path = Path(__file__).parent.parent.parent / "data" / "historical" / "revenue_records.json"
        if records_path.exists():
            with open(records_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_historical_records(self):
        """儲存歷史營收紀錄"""
        records_path = Path(__file__).parent.parent.parent / "data" / "historical" / "revenue_records.json"
        records_path.parent.mkdir(parents=True, exist_ok=True)
        with open(records_path, "w", encoding="utf-8") as f:
            json.dump(self.historical_records, f, ensure_ascii=False, indent=2)

    def _fetch_revenue(self, stock_id: str, months: int = 36) -> list:
        """取得月營收資料（最近 N 個月）"""
        if not self.session:
            return []

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=months * 35)).strftime("%Y-%m-%d")

        params = {
            "dataset": "TaiwanStockMonthRevenue",
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

    def _get_stock_name(self, stock_id: str) -> str:
        """取得股票名稱"""
        return STOCK_NAME_MAP.get(stock_id, stock_id)

    def _detect_highlights(self, stock_id: str, revenue_data: list) -> Optional[dict]:
        """偵測單一股票的營收亮點"""
        if not revenue_data:
            return None

        # 取得最新一筆
        latest = revenue_data[-1]
        revenue = latest.get("revenue", 0)
        yoy_pct = latest.get("revenue_year_growth_rate")
        mom_pct = latest.get("revenue_month_growth_rate")
        report_month = latest.get("date", "")[:7]  # YYYY-MM

        # 檢查是否為歷史新高
        all_revenues = [d.get("revenue", 0) for d in revenue_data if d.get("revenue")]
        historical_max = max(all_revenues[:-1]) if len(all_revenues) > 1 else 0
        is_record_high = revenue > historical_max and historical_max > 0

        # 更新歷史紀錄
        if is_record_high:
            self.historical_records[stock_id] = {
                "record_high": revenue,
                "record_month": report_month,
                "updated_at": datetime.now().isoformat(),
            }

        # 產生標籤
        tags = []
        if is_record_high:
            tags.append("創歷史新高")
        if yoy_pct is not None:
            if yoy_pct >= 100:
                tags.append(f"年增{yoy_pct:.0f}%")
            elif yoy_pct >= 50:
                tags.append(f"年增{yoy_pct:.0f}%")
            elif yoy_pct >= 30:
                tags.append(f"年增{yoy_pct:.0f}%")
            elif yoy_pct <= -30:
                tags.append(f"年減{abs(yoy_pct):.0f}%")

        # 只保留有亮點的
        if not tags:
            return None

        return {
            "stock_id": stock_id,
            "name": self._get_stock_name(stock_id),
            "revenue": revenue,
            "revenue_formatted": _format_revenue(revenue),
            "yoy_pct": round(yoy_pct, 2) if yoy_pct is not None else None,
            "mom_pct": round(mom_pct, 2) if mom_pct is not None else None,
            "is_record_high": is_record_high,
            "report_month": report_month,
            "tags": tags,
        }

    def get_highlights(self, stock_ids: list[str]) -> dict:
        """
        取得營收亮點

        Args:
            stock_ids: 股票代碼列表

        Returns:
            dict: 營收亮點資料
        """
        if not self.session:
            return {"error": "requests 未安裝"}

        highlights = []
        record_highs = []
        yoy_stars = []

        for stock_id in stock_ids:
            revenue_data = self._fetch_revenue(stock_id)
            highlight = self._detect_highlights(stock_id, revenue_data)

            if highlight:
                highlights.append(highlight)
                if highlight["is_record_high"]:
                    record_highs.append(highlight)
                if highlight.get("yoy_pct") and highlight["yoy_pct"] >= 50:
                    yoy_stars.append(highlight)

        # 排序：先歷史新高，再按年增率
        highlights.sort(key=lambda x: (
            not x["is_record_high"],
            -(x["yoy_pct"] or 0),
        ))

        # 取得最新報告月份
        report_month = highlights[0]["report_month"] if highlights else datetime.now().strftime("%Y-%m")

        return {
            "success": True,
            "report_month": report_month,
            "highlights": highlights,
            "summary": {
                "total_highlights": len(highlights),
                "record_highs": len(record_highs),
                "yoy_over_50_pct": len(yoy_stars),
            },
            "record_high_stocks": record_highs[:10],  # 最多 10 檔
            "yoy_stars": yoy_stars[:10],
        }

    def fetch_all(self, stock_ids: list[str], output_dir: Path) -> dict:
        """
        抓取營收亮點並儲存

        Args:
            stock_ids: 股票代碼列表
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
            print(f"  [Revenue] 分析 {len(stock_ids)} 檔股票營收...")
            highlights = self.get_highlights(stock_ids)

            if "error" in highlights:
                result["error"] = highlights["error"]
                return result

            result["data"] = highlights
            result["success"] = True

            # 儲存歷史紀錄
            self._save_historical_records()

            # 儲存到檔案
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "tw_revenue_highlights.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)

        except Exception as e:
            result["error"] = str(e)

        return result


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / "config" / ".env")

    fetcher = RevenueHighlightsFetcher()
    result = fetcher.fetch_all(
        ["2330", "2454", "2317", "2603", "3037"],
        Path("./data/raw/test"),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
