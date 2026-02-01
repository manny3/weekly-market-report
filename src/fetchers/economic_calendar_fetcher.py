"""
經濟日曆 Fetcher
抓取 Fed 決策、CPI、PMI 等總經事件
來源: Investing.com (AJAX API)
"""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False


# 事件名稱中英對照
EVENT_NAME_ZH = {
    "Fed Interest Rate Decision": "聯準會利率決議",
    "FOMC Statement": "FOMC 聲明",
    "FOMC Press Conference": "FOMC 記者會",
    "FOMC Economic Projections": "FOMC 經濟預測",
    "FOMC Minutes": "FOMC 會議紀要",
    "Initial Jobless Claims": "初領失業金人數",
    "Continuing Jobless Claims": "續領失業金人數",
    "CPI": "消費者物價指數",
    "CPI (MoM)": "CPI月增率",
    "CPI (YoY)": "CPI年增率",
    "Core CPI": "核心CPI",
    "Core CPI (MoM)": "核心CPI月增率",
    "Core CPI (YoY)": "核心CPI年增率",
    "PPI": "生產者物價指數",
    "PPI (MoM)": "PPI月增率",
    "PPI (YoY)": "PPI年增率",
    "Core PPI (MoM)": "核心PPI月增率",
    "Nonfarm Payrolls": "非農就業人數",
    "Unemployment Rate": "失業率",
    "GDP": "國內生產毛額",
    "GDP (QoQ)": "GDP季增率",
    "GDP Price Index (QoQ)": "GDP物價指數",
    "Retail Sales": "零售銷售",
    "Retail Sales (MoM)": "零售銷售月增率",
    "Core Retail Sales (MoM)": "核心零售銷售月增率",
    "ISM Manufacturing PMI": "ISM製造業PMI",
    "ISM Manufacturing Prices": "ISM製造業物價",
    "ISM Services PMI": "ISM服務業PMI",
    "S&P Global Manufacturing PMI": "標普製造業PMI",
    "S&P Global Services PMI": "標普服務業PMI",
    "Consumer Confidence": "消費者信心指數",
    "CB Consumer Confidence": "諮商會消費者信心",
    "Durable Goods Orders": "耐久財訂單",
    "Durable Goods Orders (MoM)": "耐久財訂單月增率",
    "Core Durable Goods Orders (MoM)": "核心耐久財訂單月增率",
    "PCE Price Index": "PCE物價指數",
    "PCE Price Index (MoM)": "PCE物價指數月增率",
    "PCE Price Index (YoY)": "PCE物價指數年增率",
    "Core PCE Price Index": "核心PCE物價指數",
    "Core PCE Price Index (MoM)": "核心PCE月增率",
    "Core PCE Price Index (YoY)": "核心PCE年增率",
    "Michigan Consumer Sentiment": "密西根消費者信心",
    "Michigan Consumer Expectations": "密西根消費者預期",
    "ADP Nonfarm Employment Change": "ADP非農就業人數",
    "Housing Starts": "新屋開工",
    "Housing Starts (MoM)": "新屋開工月增率",
    "Building Permits": "建築許可",
    "Building Permits (MoM)": "建築許可月增率",
    "Existing Home Sales": "成屋銷售",
    "Existing Home Sales (MoM)": "成屋銷售月增率",
    "New Home Sales": "新屋銷售",
    "New Home Sales (MoM)": "新屋銷售月增率",
    "Trade Balance": "貿易收支",
    "JOLTs Job Openings": "職位空缺數",
    "Personal Income (MoM)": "個人所得月增率",
    "Personal Spending (MoM)": "個人消費月增率",
    "Industrial Production (MoM)": "工業生產月增率",
    "Industrial Production (YoY)": "工業生產年增率",
    "Crude Oil Inventories": "原油庫存",
    "EIA Crude Oil Stocks Change": "EIA原油庫存變化",
}

# 高影響事件關鍵字
HIGH_IMPACT_KEYWORDS = [
    "Fed", "FOMC", "Interest Rate", "CPI", "Nonfarm Payrolls",
    "GDP", "PCE", "Unemployment Rate", "ISM",
]

# 分類對應
CATEGORY_MAP = {
    "interest_rate": ["Interest Rate", "FOMC", "Fed"],
    "inflation": ["CPI", "PPI", "PCE", "Inflation"],
    "employment": ["Payroll", "Unemployment", "Jobless", "ADP", "Employment", "JOLTs"],
    "gdp": ["GDP"],
    "manufacturing": ["PMI", "ISM", "Manufacturing", "Industrial", "Durable"],
    "consumer": ["Retail", "Consumer", "Confidence", "Sentiment", "Spending"],
    "housing": ["Housing", "Home Sales", "Building"],
    "trade": ["Trade Balance", "Export", "Import"],
    "energy": ["Crude Oil", "EIA", "Natural Gas"],
}


class EconomicCalendarFetcher:
    """經濟日曆 Fetcher - 使用 Investing.com AJAX API"""

    AJAX_URL = "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData"

    def __init__(self):
        """初始化 Economic Calendar Fetcher"""
        self.session = requests.Session() if DEPS_AVAILABLE else None
        if self.session:
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "en-US,en;q=0.9",
            })

    def _classify_event(self, event_name: str) -> str:
        """分類經濟事件"""
        for category, keywords in CATEGORY_MAP.items():
            for keyword in keywords:
                if keyword.lower() in event_name.lower():
                    return category
        return "other"

    def _get_event_name_zh(self, event_name: str) -> str:
        """取得事件中文名稱"""
        # 精確比對
        if event_name in EVENT_NAME_ZH:
            return EVENT_NAME_ZH[event_name]
        # 模糊比對
        for en, zh in EVENT_NAME_ZH.items():
            if en.lower() in event_name.lower():
                return zh
        return event_name

    def _get_impact_level(self, event_name: str, impact_stars: int = 0) -> str:
        """判斷影響程度"""
        if impact_stars >= 3:
            return "high"
        if impact_stars == 2:
            return "medium"
        if any(kw.lower() in event_name.lower() for kw in HIGH_IMPACT_KEYWORDS):
            return "high"
        return "low"

    def _parse_ajax_response(self, html: str) -> list:
        """解析 AJAX 回傳的 HTML"""
        soup = BeautifulSoup(html, "html.parser")
        events = []

        rows = soup.find_all("tr", {"class": re.compile(r"js-event-item")})

        for row in rows:
            try:
                # 國家
                country_elem = row.find("td", {"class": "flagCur"})
                country = ""
                if country_elem:
                    flag_span = country_elem.find("span")
                    if flag_span and flag_span.get("title"):
                        country = flag_span.get("title", "")

                # 只保留美國事件
                if "United States" not in country:
                    continue

                # 時間
                time_elem = row.find("td", {"class": re.compile(r"time")})
                event_time = time_elem.get_text(strip=True) if time_elem else ""

                # 事件名稱
                event_elem = row.find("td", {"class": "event"})
                event_name = ""
                if event_elem:
                    event_link = event_elem.find("a")
                    if event_link:
                        event_name = event_link.get_text(strip=True)

                if not event_name:
                    continue

                # 影響程度 (星星數)
                impact_elem = row.find("td", {"class": "sentiment"})
                impact_stars = 0
                if impact_elem:
                    # 計算填滿的星星
                    bulls = impact_elem.find_all("i", {"class": re.compile(r"grayFullBullishIcon|newSiteIconsSprite")})
                    impact_stars = len(bulls)

                # 數值
                actual_elem = row.find("td", {"class": re.compile(r"act|bold")})
                actual = actual_elem.get_text(strip=True) if actual_elem else None

                forecast_elem = row.find("td", {"class": "fore"})
                forecast = forecast_elem.get_text(strip=True) if forecast_elem else None

                previous_elem = row.find("td", {"class": "prev"})
                previous = previous_elem.get_text(strip=True) if previous_elem else None

                # 日期 (從 row attribute 取)
                date_attr = row.get("data-event-datetime", "")
                date_str = date_attr[:10].replace("/", "-") if date_attr else ""

                events.append({
                    "event_name": event_name,
                    "event_name_zh": self._get_event_name_zh(event_name),
                    "date": date_str,
                    "time": event_time,
                    "country": "US",
                    "impact": self._get_impact_level(event_name, impact_stars),
                    "impact_stars": impact_stars,
                    "category": self._classify_event(event_name),
                    "previous": previous if previous and previous.strip() else None,
                    "forecast": forecast if forecast and forecast.strip() else None,
                    "actual": actual if actual and actual.strip() else None,
                })

            except Exception:
                continue

        return events

    def get_calendar(self, from_date: str = None, to_date: str = None) -> dict:
        """
        取得經濟日曆

        Args:
            from_date: 開始日期 (YYYY-MM-DD)
            to_date: 結束日期 (YYYY-MM-DD)

        Returns:
            dict: 經濟日曆資料
        """
        if not self.session:
            return {"error": "requests 或 beautifulsoup4 未安裝"}

        today = datetime.now()
        if not from_date:
            monday = today - timedelta(days=today.weekday())
            from_date = monday.strftime("%Y-%m-%d")
        if not to_date:
            monday = today - timedelta(days=today.weekday())
            next_friday = monday + timedelta(days=11)
            to_date = next_friday.strftime("%Y-%m-%d")

        try:
            # 使用 AJAX API
            data = {
                "country[]": "5",  # US = 5
                "dateFrom": from_date,
                "dateTo": to_date,
                "currentTab": "custom",
                "limit_from": "0",
            }

            resp = self.session.post(
                self.AJAX_URL,
                data=data,
                timeout=30,
            )
            resp.raise_for_status()

            json_resp = resp.json()
            html_data = json_resp.get("data", "")

            events = self._parse_ajax_response(html_data)

            # 按日期+時間排序
            events.sort(key=lambda x: (x.get("date", ""), x.get("time", "")))

            # 篩選高影響事件
            high_impact = [e for e in events if e["impact"] == "high"]

            return {
                "success": True,
                "events": events,
                "high_impact_events": high_impact,
                "date_range": {"from": from_date, "to": to_date},
                "total_count": len(events),
                "high_impact_count": len(high_impact),
            }

        except Exception as e:
            return {"error": str(e)}

    def fetch_all(self, output_dir: Path) -> dict:
        """
        抓取經濟日曆並儲存

        Args:
            output_dir: 輸出目錄

        Returns:
            dict: 抓取結果
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "source": "investing.com",
            "success": False,
            "data": {},
        }

        if not DEPS_AVAILABLE:
            result["error"] = "需安裝 beautifulsoup4 (pip install beautifulsoup4)"
            return result

        try:
            print("  [EconCal] 抓取經濟日曆...")
            calendar = self.get_calendar()

            if "error" in calendar:
                result["error"] = calendar["error"]
                return result

            result["data"] = {
                "events": calendar["events"],
                "high_impact_events": calendar["high_impact_events"],
                "date_range": calendar["date_range"],
                "summary": {
                    "total_events": calendar["total_count"],
                    "high_impact_events": calendar["high_impact_count"],
                },
            }
            result["success"] = True

            # 儲存到檔案
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "economic_calendar.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)

            print(f"  [EconCal] 找到 {calendar['total_count']} 個事件 ({calendar['high_impact_count']} 高影響)")

        except Exception as e:
            result["error"] = str(e)

        return result


if __name__ == "__main__":
    fetcher = EconomicCalendarFetcher()
    result = fetcher.fetch_all(Path("./data/raw/test"))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
