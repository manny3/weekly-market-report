"""
富途牛牛 API 資料抓取模組
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from futu import OpenQuoteContext, KLType, SubType, RET_OK
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False


class FutuFetcher:
    """富途 API 資料抓取器"""

    def __init__(self, host: str = '127.0.0.1', port: int = 11111):
        self.host = host
        self.port = port
        self.ctx: Optional[OpenQuoteContext] = None

    def connect(self, timeout: float = 3.0) -> bool:
        """連接到富途 OpenD（快速失敗）"""
        if not FUTU_AVAILABLE:
            print("[Futu] futu-api 未安裝，請執行 pip install futu-api")
            return False

        # 先用 socket 快速檢測 OpenD 是否運行
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            if result != 0:
                print(f"[Futu] OpenD 未運行 (port {self.port} 無法連接)")
                return False
        except socket.error:
            sock.close()
            print(f"[Futu] OpenD 未運行 (連線超時)")
            return False

        try:
            import signal

            def _timeout_handler(signum, frame):
                raise TimeoutError("OpenQuoteContext 連線超時")

            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(int(timeout) + 2)
            try:
                self.ctx = OpenQuoteContext(host=self.host, port=self.port)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
            return True
        except (TimeoutError, Exception) as e:
            print(f"[Futu] 連接失敗: {e}")
            self.ctx = None
            return False

    def disconnect(self):
        """斷開連接"""
        if self.ctx:
            self.ctx.close()
            self.ctx = None

    def get_market_snapshot(self, symbols: list[str]) -> dict:
        """
        取得即時報價快照

        Args:
            symbols: 股票代碼列表，如 ['US.AAPL', 'US.MSFT']

        Returns:
            dict: 報價資料
        """
        if not self.ctx:
            return {"error": "未連接"}

        ret, data = self.ctx.get_market_snapshot(symbols)
        if ret == RET_OK:
            return data.to_dict('records')
        return {"error": str(data)}

    def get_kline(
        self,
        symbol: str,
        ktype: str = 'K_DAY',
        count: int = 100
    ) -> dict:
        """
        取得 K 線資料

        Args:
            symbol: 股票代碼，如 'US.AAPL'
            ktype: K 線類型 (K_DAY, K_WEEK, K_MON)
            count: 取得筆數

        Returns:
            dict: K 線資料
        """
        if not self.ctx:
            return {"error": "未連接"}

        kl_type = getattr(KLType, ktype, KLType.K_DAY)
        ret, data, _ = self.ctx.request_history_kline(
            symbol,
            ktype=kl_type,
            max_count=count
        )

        if ret == RET_OK:
            return data.to_dict('records')
        return {"error": str(data)}

    def get_us_indices(self) -> dict:
        """取得美股三大指數"""
        indices = ['US.SPY', 'US.QQQ', 'US.DIA']  # ETF 代替指數
        return self.get_market_snapshot(indices)

    def fetch_all(self, symbols: list[str], output_dir: Path) -> dict:
        """
        抓取所有資料並儲存

        Args:
            symbols: 股票代碼列表
            output_dir: 輸出目錄

        Returns:
            dict: 抓取結果摘要
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "source": "futu",
            "success": False,
            "data": {}
        }

        if not self.connect():
            result["error"] = "無法連接到 Futu OpenD"
            return result

        try:
            # 即時報價
            result["data"]["snapshot"] = self.get_market_snapshot(symbols)

            # 日 K 線
            result["data"]["daily_klines"] = {}
            for symbol in symbols:
                result["data"]["daily_klines"][symbol] = self.get_kline(
                    symbol, 'K_DAY', 60
                )

            result["success"] = True

            # 儲存到檔案
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "futu_data.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

        except Exception as e:
            result["error"] = str(e)
        finally:
            self.disconnect()

        return result


if __name__ == "__main__":
    # 測試用
    fetcher = FutuFetcher()
    print(fetcher.fetch_all(
        ['US.AAPL', 'US.MSFT'],
        Path('./data/raw/test')
    ))
