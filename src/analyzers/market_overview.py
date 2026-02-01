"""
大盤趨勢分析模組
"""
from datetime import datetime
from pathlib import Path
import json


class MarketOverviewAnalyzer:
    """大盤趨勢分析器"""

    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("./data/raw")

    def load_latest_data(self) -> dict:
        """載入最新資料"""
        # 找到最新的資料目錄
        dirs = sorted(self.data_dir.glob("*"))
        if not dirs:
            return {}

        latest_dir = dirs[-1]
        data = {}

        # 載入 Yahoo 資料
        yahoo_file = latest_dir / "yahoo_data.json"
        if yahoo_file.exists():
            with open(yahoo_file, 'r', encoding='utf-8') as f:
                data['yahoo'] = json.load(f)

        return data

    def analyze_us_indices(self, data: dict) -> dict:
        """分析美股三大指數"""
        yahoo_data = data.get('yahoo', {}).get('data', {})
        indices = yahoo_data.get('us_indices', {})

        result = {
            "spx": self._analyze_index(indices.get("^GSPC", {})),
            "ndx": self._analyze_index(indices.get("^IXIC", {})),
            "dji": self._analyze_index(indices.get("^DJI", {})),
        }

        # 整體趨勢判斷
        bullish_count = sum(1 for v in result.values() if v.get('trend') == 'bullish')
        if bullish_count >= 2:
            result['overall_trend'] = 'bullish'
        elif bullish_count == 0:
            result['overall_trend'] = 'bearish'
        else:
            result['overall_trend'] = 'mixed'

        return result

    def _analyze_index(self, index_data: dict) -> dict:
        """分析單一指數"""
        if not index_data or 'error' in index_data:
            return {"error": "無資料"}

        price = index_data.get('price')
        change_pct = index_data.get('change_pct', 0) or 0
        high_52w = index_data.get('52w_high')
        low_52w = index_data.get('52w_low')

        # 趨勢判斷
        if change_pct > 1:
            trend = 'bullish'
        elif change_pct < -1:
            trend = 'bearish'
        else:
            trend = 'neutral'

        # 相對位置
        if high_52w and low_52w and price:
            position = (price - low_52w) / (high_52w - low_52w)
        else:
            position = None

        return {
            "name": index_data.get('index_name', ''),
            "price": price,
            "change_pct": change_pct,
            "trend": trend,
            "52w_position": position,
        }

    def generate_summary(self) -> str:
        """產生大盤摘要"""
        data = self.load_latest_data()
        us_analysis = self.analyze_us_indices(data)

        lines = ["📊 大盤趨勢總覽", ""]

        # 美股
        lines.append("【美股】")
        for key, name in [("spx", "S&P 500"), ("ndx", "NASDAQ"), ("dji", "道瓊")]:
            idx = us_analysis.get(key, {})
            if 'error' not in idx:
                trend_icon = {"bullish": "📈", "bearish": "📉", "neutral": "➡️"}.get(idx.get('trend'), "")
                lines.append(f"- {name}: {idx.get('price', 'N/A')} ({idx.get('change_pct', 0):+.2f}%) {trend_icon}")

        lines.append("")
        lines.append(f"整體趨勢: {us_analysis.get('overall_trend', 'unknown')}")

        return "\n".join(lines)
