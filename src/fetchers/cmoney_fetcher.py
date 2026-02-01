"""
CMoney 台股籌碼面資料爬蟲
改用 FinMind API 作為主要資料源（更穩定可靠）
保留 CMoney 爬蟲作為備用
"""
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
    SCRAPER_AVAILABLE = True
except ImportError:
    SCRAPER_AVAILABLE = False


class CMoneyFetcher:
    """CMoney 台股籌碼資料爬蟲（整合 FinMind API）"""

    # FinMind API（主要資料源）
    FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"

    # CMoney 網站（備用）
    CMONEY_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Safari/537.36',
    }

    def __init__(self, finmind_token: str = None):
        """
        初始化

        Args:
            finmind_token: FinMind API token（可選）
        """
        self.finmind_token = finmind_token
        self.session = requests.Session() if SCRAPER_AVAILABLE else None

    def _fetch_finmind(self, dataset: str, stock_id: str, days: int = 30) -> dict:
        """從 FinMind API 取得資料"""
        if not self.session:
            return {"error": "requests 未安裝"}

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        params = {
            "dataset": dataset,
            "data_id": stock_id,
            "start_date": start_date,
            "end_date": end_date,
        }

        headers = {}
        if self.finmind_token:
            headers["Authorization"] = f"Bearer {self.finmind_token}"

        try:
            resp = self.session.get(
                self.FINMIND_URL,
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

    def get_institutional_trading(self, stock_id: str) -> dict:
        """
        取得三大法人買賣超

        Args:
            stock_id: 股票代碼

        Returns:
            dict: 法人買賣超資料
        """
        result = self._fetch_finmind(
            dataset="TaiwanStockInstitutionalInvestorsBuySell",
            stock_id=stock_id,
            days=30
        )

        if "error" in result:
            return {
                "stock_id": stock_id,
                "error": result["error"],
                "foreign_investors": None,
                "investment_trust": None,
                "dealers": None,
            }

        data = result.get("data", [])
        if not data:
            return {
                "stock_id": stock_id,
                "foreign_investors": None,
                "investment_trust": None,
                "dealers": None,
            }

        # 取最新日期的資料
        latest_date = data[-1].get("date") if data else None
        latest_data = [d for d in data if d.get("date") == latest_date]

        # 整理法人資料
        foreign = {"buy": 0, "sell": 0, "net": 0}
        trust = {"buy": 0, "sell": 0, "net": 0}
        dealers = {"buy": 0, "sell": 0, "net": 0}

        for item in latest_data:
            name = item.get("name", "")
            buy = item.get("buy", 0) or 0
            sell = item.get("sell", 0) or 0
            net = buy - sell

            if "外資" in name or "Foreign" in name:
                foreign["buy"] += buy
                foreign["sell"] += sell
                foreign["net"] += net
            elif "投信" in name or "Investment_Trust" in name:
                trust["buy"] += buy
                trust["sell"] += sell
                trust["net"] += net
            elif "自營商" in name or "Dealer" in name:
                dealers["buy"] += buy
                dealers["sell"] += sell
                dealers["net"] += net

        # 計算連買連賣天數
        foreign_net_history = []
        for d in data:
            if "外資" in d.get("name", "") or "Foreign" in d.get("name", ""):
                buy = d.get("buy", 0) or 0
                sell = d.get("sell", 0) or 0
                foreign_net_history.append({
                    "date": d.get("date"),
                    "net": buy - sell
                })

        # 去重（同一天可能有多筆）
        date_nets = {}
        for item in foreign_net_history:
            date = item["date"]
            if date not in date_nets:
                date_nets[date] = 0
            date_nets[date] += item["net"]

        # 計算連續天數
        sorted_dates = sorted(date_nets.keys(), reverse=True)
        consecutive_days = 0
        if sorted_dates:
            current_sign = 1 if date_nets[sorted_dates[0]] > 0 else -1
            for date in sorted_dates:
                if (date_nets[date] > 0 and current_sign > 0) or \
                   (date_nets[date] < 0 and current_sign < 0):
                    consecutive_days += 1
                else:
                    break

        return {
            "stock_id": stock_id,
            "date": latest_date,
            "foreign_investors": foreign,
            "investment_trust": trust,
            "dealers": dealers,
            "foreign_consecutive_days": consecutive_days if foreign["net"] != 0 else 0,
            "foreign_consecutive_type": "買" if foreign["net"] > 0 else "賣" if foreign["net"] < 0 else "持平",
        }

    def get_margin_trading(self, stock_id: str) -> dict:
        """
        取得融資融券資料

        Args:
            stock_id: 股票代碼

        Returns:
            dict: 融資融券資料
        """
        result = self._fetch_finmind(
            dataset="TaiwanStockMarginPurchaseShortSale",
            stock_id=stock_id,
            days=30
        )

        if "error" in result:
            return {
                "stock_id": stock_id,
                "error": result["error"],
                "margin_buy": None,
                "margin_sell": None,
                "margin_balance": None,
                "short_sell": None,
                "short_cover": None,
                "short_balance": None,
            }

        data = result.get("data", [])
        if not data:
            return {
                "stock_id": stock_id,
                "margin_buy": None,
                "margin_sell": None,
                "margin_balance": None,
                "short_sell": None,
                "short_cover": None,
                "short_balance": None,
            }

        latest = data[-1] if data else {}

        # 計算融資增減
        margin_change = None
        if len(data) >= 2:
            margin_change = (latest.get("MarginPurchaseTodayBalance", 0) or 0) - \
                           (data[-2].get("MarginPurchaseTodayBalance", 0) or 0)

        # 計算融券增減
        short_change = None
        if len(data) >= 2:
            short_change = (latest.get("ShortSaleTodayBalance", 0) or 0) - \
                          (data[-2].get("ShortSaleTodayBalance", 0) or 0)

        return {
            "stock_id": stock_id,
            "date": latest.get("date"),
            "margin_buy": latest.get("MarginPurchaseBuy"),
            "margin_sell": latest.get("MarginPurchaseSell"),
            "margin_balance": latest.get("MarginPurchaseTodayBalance"),
            "margin_change": margin_change,
            "margin_limit": latest.get("MarginPurchaseLimit"),
            "margin_utilization": round(
                (latest.get("MarginPurchaseTodayBalance", 0) or 0) /
                (latest.get("MarginPurchaseLimit", 1) or 1) * 100, 2
            ) if latest.get("MarginPurchaseLimit") else None,
            "short_sell": latest.get("ShortSaleSell"),
            "short_cover": latest.get("ShortSaleBuy"),
            "short_balance": latest.get("ShortSaleTodayBalance"),
            "short_change": short_change,
            "short_limit": latest.get("ShortSaleLimit"),
        }

    def get_shareholding(self, stock_id: str) -> dict:
        """
        取得外資持股比例

        Args:
            stock_id: 股票代碼

        Returns:
            dict: 持股資料
        """
        result = self._fetch_finmind(
            dataset="TaiwanStockShareholding",
            stock_id=stock_id,
            days=30
        )

        if "error" in result:
            return {"stock_id": stock_id, "error": result["error"]}

        data = result.get("data", [])
        if not data:
            return {"stock_id": stock_id, "shareholding": None}

        latest = data[-1] if data else {}

        return {
            "stock_id": stock_id,
            "date": latest.get("date"),
            "foreign_shares": latest.get("ForeignInvestmentShares"),
            "foreign_ratio": latest.get("ForeignInvestmentSharesRatio"),
            "foreign_limit_ratio": latest.get("ForeignInvestmentUpperLimitRatio"),
            "foreign_remain_ratio": latest.get("ForeignInvestmentRemainRatio"),
        }

    def fetch_all(self, stock_ids: list[str], output_dir: Path) -> dict:
        """抓取所有籌碼資料"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "source": "cmoney_finmind",
            "success": False,
            "data": {}
        }

        if not SCRAPER_AVAILABLE:
            result["error"] = "requests 未安裝"
            return result

        try:
            for i, stock_id in enumerate(stock_ids):
                print(f"  [CMoney/FinMind] 抓取 {stock_id} 籌碼...")

                result["data"][stock_id] = {
                    "institutional": self.get_institutional_trading(stock_id),
                    "margin": self.get_margin_trading(stock_id),
                    "shareholding": self.get_shareholding(stock_id),
                }

                # 避免請求過快
                if i < len(stock_ids) - 1:
                    time.sleep(0.5)

            result["success"] = True

            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "cmoney_data.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

        except Exception as e:
            result["error"] = str(e)

        return result


if __name__ == "__main__":
    # 測試
    fetcher = CMoneyFetcher()
    result = fetcher.fetch_all(
        ['2330', '2454'],
        Path('./data/raw/test')
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
