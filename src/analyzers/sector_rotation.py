"""
板塊輪動分析模組
"""
from pathlib import Path
import json


class SectorRotationAnalyzer:
    """板塊輪動分析器"""

    SECTOR_NAMES = {
        'XLK': '科技',
        'XLF': '金融',
        'XLE': '能源',
        'XLV': '醫療',
        'XLI': '工業',
        'XLC': '通訊',
        'XLY': '非必需消費',
        'XLP': '必需消費',
        'XLU': '公用事業',
        'XLRE': '房地產',
        'XLB': '原材料',
    }

    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("./data/raw")

    def load_sector_data(self) -> dict:
        """載入板塊資料"""
        dirs = sorted(self.data_dir.glob("*"))
        if not dirs:
            return {}

        latest_dir = dirs[-1]
        yahoo_file = latest_dir / "yahoo_data.json"

        if yahoo_file.exists():
            with open(yahoo_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('data', {}).get('sectors', {})
        return {}

    def analyze(self) -> dict:
        """分析板塊輪動"""
        sectors = self.load_sector_data()

        if not sectors:
            return {"error": "無板塊資料"}

        # 排序
        sorted_sectors = sorted(
            sectors.items(),
            key=lambda x: x[1].get('change_pct', 0) or 0,
            reverse=True
        )

        # 強勢 / 弱勢板塊
        strong = sorted_sectors[:3]
        weak = sorted_sectors[-3:]

        return {
            "strong_sectors": [
                {
                    "symbol": s[0],
                    "name": self.SECTOR_NAMES.get(s[0], s[0]),
                    "change_pct": s[1].get('change_pct', 0)
                }
                for s in strong
            ],
            "weak_sectors": [
                {
                    "symbol": s[0],
                    "name": self.SECTOR_NAMES.get(s[0], s[0]),
                    "change_pct": s[1].get('change_pct', 0)
                }
                for s in weak
            ],
            "all_sectors": [
                {
                    "symbol": s[0],
                    "name": self.SECTOR_NAMES.get(s[0], s[0]),
                    "change_pct": s[1].get('change_pct', 0)
                }
                for s in sorted_sectors
            ]
        }

    def generate_summary(self) -> str:
        """產生板塊輪動摘要"""
        analysis = self.analyze()

        if 'error' in analysis:
            return "❌ 無法取得板塊資料"

        lines = ["🔄 板塊輪動", ""]

        lines.append("【強勢板塊】")
        for s in analysis['strong_sectors']:
            lines.append(f"  📈 {s['name']} ({s['symbol']}): {s['change_pct']:+.2f}%")

        lines.append("")
        lines.append("【弱勢板塊】")
        for s in analysis['weak_sectors']:
            lines.append(f"  📉 {s['name']} ({s['symbol']}): {s['change_pct']:+.2f}%")

        return "\n".join(lines)
