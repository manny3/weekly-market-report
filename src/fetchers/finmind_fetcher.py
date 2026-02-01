"""
FinMind 台股資料 API 模組
提供台股價格、法人買賣、融資融券、基本面等資料
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    import requests
    import pandas as pd
    FINMIND_AVAILABLE = True
except ImportError:
    FINMIND_AVAILABLE = False


class FinMindFetcher:
    """FinMind 台股資料 API"""

    BASE_URL = "https://api.finmindtrade.com/api/v4/data"

    def __init__(self, api_token: Optional[str] = None):
        """
        初始化 FinMind Fetcher

        Args:
            api_token: FinMind API token（可選，有 token 可提高 rate limit）
        """
        self.api_token = api_token
        self.session = requests.Session() if FINMIND_AVAILABLE else None

    def _fetch(self, dataset: str, data_id: str = None,
               start_date: str = None, end_date: str = None) -> dict:
        """
        通用 API 請求方法

        Args:
            dataset: 資料集名稱
            data_id: 股票代碼
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)

        Returns:
            dict: API 回應
        """
        if not self.session:
            return {"error": "requests 或 pandas 未安裝"}

        params = {"dataset": dataset}
        if data_id:
            params["data_id"] = data_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        headers = {}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        try:
            resp = self.session.get(
                self.BASE_URL,
                params=params,
                headers=headers,
                timeout=30
            )
            data = resp.json()

            if data.get("status") != 200:
                return {"error": data.get("msg", "Unknown error")}

            return {"success": True, "data": data.get("data", [])}

        except Exception as e:
            return {"error": str(e)}

    def get_stock_price(self, stock_id: str, days: int = 60) -> dict:
        """
        取得股票日線資料

        Args:
            stock_id: 股票代碼 (e.g., '2330')
            days: 取得天數

        Returns:
            dict: 股價資料
        """
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        result = self._fetch(
            dataset="TaiwanStockPrice",
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )

        if "error" in result:
            return result

        data = result.get("data", [])
        if not data:
            return {"error": "無資料"}

        # 取得最新一筆
        latest = data[-1] if data else {}

        # 計算技術指標
        closes = [d.get("close", 0) for d in data]
        ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
        ma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
        ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else None

        week_chg = None
        if len(closes) >= 6:
            week_chg = (closes[-1] - closes[-6]) / closes[-6] * 100

        month_chg = None
        if len(closes) >= 22:
            month_chg = (closes[-1] - closes[-22]) / closes[-22] * 100

        return {
            "stock_id": stock_id,
            "date": latest.get("date"),
            "open": latest.get("open"),
            "high": latest.get("max"),
            "low": latest.get("min"),
            "close": latest.get("close"),
            "volume": latest.get("Trading_Volume"),
            "value": latest.get("Trading_money"),
            "change": latest.get("spread"),
            "ma20": round(ma20, 2) if ma20 else None,
            "ma50": round(ma50, 2) if ma50 else None,
            "ma60": round(ma60, 2) if ma60 else None,
            "above_ma20": closes[-1] > ma20 if ma20 and closes else None,
            "above_ma50": closes[-1] > ma50 if ma50 and closes else None,
            "week_change_pct": round(week_chg, 2) if week_chg else None,
            "month_change_pct": round(month_chg, 2) if month_chg else None,
            "history": data[-20:],  # 最近 20 筆
        }

    def get_per_pbr(self, stock_id: str, days: int = 30) -> dict:
        """
        取得本益比、股價淨值比、殖利率

        Args:
            stock_id: 股票代碼
            days: 取得天數

        Returns:
            dict: 估值資料
        """
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        result = self._fetch(
            dataset="TaiwanStockPER",
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )

        if "error" in result:
            return result

        data = result.get("data", [])
        if not data:
            return {"error": "無資料"}

        latest = data[-1] if data else {}

        return {
            "stock_id": stock_id,
            "date": latest.get("date"),
            "pe_ratio": latest.get("PER"),
            "pb_ratio": latest.get("PBR"),
            "dividend_yield": latest.get("dividend_yield"),
        }

    def get_institutional_investors(self, stock_id: str, days: int = 30) -> dict:
        """
        取得三大法人買賣超

        Args:
            stock_id: 股票代碼
            days: 取得天數

        Returns:
            dict: 法人買賣超資料
        """
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        result = self._fetch(
            dataset="TaiwanStockInstitutionalInvestorsBuySell",
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )

        if "error" in result:
            return result

        data = result.get("data", [])
        if not data:
            return {"stock_id": stock_id, "institutional": {}}

        # 整理法人資料（最近一天）
        latest_date = data[-1].get("date") if data else None
        latest_data = [d for d in data if d.get("date") == latest_date]

        institutional = {
            "date": latest_date,
            "foreign_investors": {"buy": 0, "sell": 0, "net": 0},
            "investment_trust": {"buy": 0, "sell": 0, "net": 0},
            "dealers": {"buy": 0, "sell": 0, "net": 0},
        }

        for item in latest_data:
            name = item.get("name", "")
            buy = item.get("buy", 0) or 0
            sell = item.get("sell", 0) or 0
            net = buy - sell

            if "外資" in name or "Foreign" in name:
                institutional["foreign_investors"]["buy"] += buy
                institutional["foreign_investors"]["sell"] += sell
                institutional["foreign_investors"]["net"] += net
            elif "投信" in name or "Investment_Trust" in name:
                institutional["investment_trust"]["buy"] += buy
                institutional["investment_trust"]["sell"] += sell
                institutional["investment_trust"]["net"] += net
            elif "自營商" in name or "Dealer" in name:
                institutional["dealers"]["buy"] += buy
                institutional["dealers"]["sell"] += sell
                institutional["dealers"]["net"] += net

        return {
            "stock_id": stock_id,
            "institutional": institutional,
            "history": data[-10:],  # 最近 10 筆
        }

    def get_margin_trading(self, stock_id: str, days: int = 30) -> dict:
        """
        取得融資融券資料

        Args:
            stock_id: 股票代碼
            days: 取得天數

        Returns:
            dict: 融資融券資料
        """
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        result = self._fetch(
            dataset="TaiwanStockMarginPurchaseShortSale",
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )

        if "error" in result:
            return result

        data = result.get("data", [])
        if not data:
            return {"stock_id": stock_id, "margin": {}}

        latest = data[-1] if data else {}

        return {
            "stock_id": stock_id,
            "date": latest.get("date"),
            "margin": {
                "margin_purchase_buy": latest.get("MarginPurchaseBuy"),
                "margin_purchase_sell": latest.get("MarginPurchaseSell"),
                "margin_purchase_balance": latest.get("MarginPurchaseTodayBalance"),
                "margin_purchase_limit": latest.get("MarginPurchaseLimit"),
                "short_sale_buy": latest.get("ShortSaleBuy"),
                "short_sale_sell": latest.get("ShortSaleSell"),
                "short_sale_balance": latest.get("ShortSaleTodayBalance"),
                "short_sale_limit": latest.get("ShortSaleLimit"),
            },
            "history": data[-10:],
        }

    def get_monthly_revenue(self, stock_id: str, months: int = 12) -> dict:
        """
        取得月營收資料

        Args:
            stock_id: 股票代碼
            months: 取得月數

        Returns:
            dict: 月營收資料
        """
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=months * 35)).strftime("%Y-%m-%d")

        result = self._fetch(
            dataset="TaiwanStockMonthRevenue",
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )

        if "error" in result:
            return result

        data = result.get("data", [])
        if not data:
            return {"stock_id": stock_id, "revenue": []}

        # 取最近 12 筆
        recent = data[-12:] if len(data) >= 12 else data

        revenue_list = []
        for item in recent:
            revenue_list.append({
                "date": item.get("date"),
                "revenue": item.get("revenue"),
                "revenue_yoy": item.get("revenue_year_growth_rate"),
                "revenue_mom": item.get("revenue_month_growth_rate"),
            })

        return {
            "stock_id": stock_id,
            "revenue": revenue_list,
        }

    def get_stock_info(self) -> dict:
        """
        取得台股上市櫃清單

        Returns:
            dict: 股票清單
        """
        result = self._fetch(dataset="TaiwanStockInfo")

        if "error" in result:
            return result

        return {
            "success": True,
            "data": result.get("data", [])
        }

    def fetch_all(self, stock_ids: list[str], output_dir: Path) -> dict:
        """
        抓取所有台股資料

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
            "data": {}
        }

        if not FINMIND_AVAILABLE:
            result["error"] = "requests 或 pandas 未安裝"
            return result

        try:
            for stock_id in stock_ids:
                print(f"  [FinMind] 抓取 {stock_id}...")

                stock_data = {
                    "price": self.get_stock_price(stock_id),
                    "valuation": self.get_per_pbr(stock_id),
                    "institutional": self.get_institutional_investors(stock_id),
                    "margin": self.get_margin_trading(stock_id),
                    "revenue": self.get_monthly_revenue(stock_id),
                }

                result["data"][stock_id] = stock_data

            result["success"] = True

            # 儲存到檔案
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "finmind_data.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)

        except Exception as e:
            result["error"] = str(e)

        return result


if __name__ == "__main__":
    # 測試
    fetcher = FinMindFetcher()
    result = fetcher.fetch_all(
        ['2330', '2454'],
        Path('./data/raw/test')
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
