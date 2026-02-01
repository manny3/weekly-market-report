"""
Goodinfo 台股基本面資料爬蟲
"""
import json
import re
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
    SCRAPER_AVAILABLE = True
except ImportError:
    SCRAPER_AVAILABLE = False


class GoodinfoFetcher:
    """Goodinfo 台股資料爬蟲"""

    BASE_URL = "https://goodinfo.tw/tw"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://goodinfo.tw/tw/index.asp',
    }

    def __init__(self):
        if not SCRAPER_AVAILABLE:
            print("[Goodinfo] requests 或 beautifulsoup4 未安裝")
        self.session = requests.Session() if SCRAPER_AVAILABLE else None
        if self.session:
            self.session.headers.update(self.HEADERS)

    def _safe_float(self, text: str) -> float:
        """安全轉換浮點數"""
        if not text:
            return None
        try:
            # 移除千分位逗號和百分號
            cleaned = text.replace(',', '').replace('%', '').strip()
            if cleaned in ['', '-', 'N/A', '--']:
                return None
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def get_stock_info(self, stock_id: str) -> dict:
        """
        取得台股個股基本資訊

        Args:
            stock_id: 股票代碼，如 '2330'

        Returns:
            dict: 個股資料
        """
        if not self.session:
            return {"stock_id": stock_id, "error": "爬蟲套件未安裝"}

        result = {
            "stock_id": stock_id,
            "name": None,
            "price": None,
            "change": None,
            "change_pct": None,
            "volume": None,
            "pe_ratio": None,
            "pb_ratio": None,
            "dividend_yield": None,
            "eps": None,
            "roe": None,
        }

        try:
            url = f"{self.BASE_URL}/StockDetail.asp?STOCK_ID={stock_id}"
            resp = self.session.get(url, timeout=15)
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'lxml')

            # 從 title 取得股票名稱
            title = soup.find('title')
            if title:
                match = re.match(r'(\d+)\s+(\S+)', title.text)
                if match:
                    result["name"] = match.group(2)

            # 解析主要報價表格
            # Goodinfo 頁面結構：找包含 成交價、PBR、PER 的表格
            text = soup.get_text()

            # 成交價
            price_match = re.search(r'成交價\s*\n?\s*昨收.*?\n(\d[\d,]*\.?\d*)', text)
            if price_match:
                result["price"] = self._safe_float(price_match.group(1))

            # 漲跌價/幅
            change_match = re.search(r'漲跌價\s*\n?\s*漲跌幅.*?\n([-+]?\d[\d,]*\.?\d*)\s*\n?\s*([-+]?\d[\d,]*\.?\d*%?)', text)
            if change_match:
                result["change"] = self._safe_float(change_match.group(1))
                result["change_pct"] = self._safe_float(change_match.group(2))

            # 成交張數
            volume_match = re.search(r'成交張數\s*\n?\s*成交金額.*?\n([\d,]+)', text)
            if volume_match:
                result["volume"] = self._safe_float(volume_match.group(1))

            # PER (本益比)
            per_match = re.search(r'PER\s*\n?\s*PEG?\s*\n?([\d.]+)', text)
            if per_match:
                result["pe_ratio"] = self._safe_float(per_match.group(1))

            # PBR (股價淨值比)
            pbr_match = re.search(r'PBR\s*\n?\s*PER\s*\n?([\d.]+)', text)
            if pbr_match:
                result["pb_ratio"] = self._safe_float(pbr_match.group(1))

            # 嘗試從表格找更精確的數據
            tables = soup.find_all('table')
            for table in tables:
                table_text = table.get_text()

                # 找包含 PBR、PER 的報價表格
                if 'PBR' in table_text and 'PER' in table_text and '成交價' in table_text:
                    rows = table.find_all('tr')
                    for i, row in enumerate(rows):
                        cells = row.find_all(['td', 'th'])
                        cell_texts = [c.get_text(strip=True) for c in cells]

                        # 找 header row 和 data row
                        if 'PBR' in cell_texts and 'PER' in cell_texts:
                            # 下一行是數據
                            if i + 1 < len(rows):
                                data_row = rows[i + 1]
                                data_cells = data_row.find_all(['td', 'th'])
                                data_texts = [c.get_text(strip=True) for c in data_cells]

                                # 根據 header 位置取值
                                for j, header in enumerate(cell_texts):
                                    if j < len(data_texts):
                                        if header == 'PBR':
                                            result["pb_ratio"] = self._safe_float(data_texts[j])
                                        elif header == 'PER':
                                            result["pe_ratio"] = self._safe_float(data_texts[j])

            return result

        except requests.exceptions.Timeout:
            return {"stock_id": stock_id, "error": "連線超時"}
        except Exception as e:
            return {"stock_id": stock_id, "error": str(e)}

    def get_revenue(self, stock_id: str) -> dict:
        """
        取得月營收資料

        Args:
            stock_id: 股票代碼

        Returns:
            dict: 營收資料
        """
        if not self.session:
            return {"stock_id": stock_id, "error": "爬蟲套件未安裝"}

        result = {
            "stock_id": stock_id,
            "revenue": []
        }

        try:
            url = f"{self.BASE_URL}/ShowSaleMonChart.asp?STOCK_ID={stock_id}"
            resp = self.session.get(url, timeout=15)
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'lxml')

            # 找營收表格
            tables = soup.find_all('table')
            for table in tables:
                table_text = table.get_text()

                # 找包含 月營收 的表格
                if '單月營收' in table_text or '月增%' in table_text or '年增%' in table_text:
                    rows = table.find_all('tr')

                    header_idx = {}
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        cell_texts = [c.get_text(strip=True) for c in cells]

                        # 找 header
                        if '年/月' in cell_texts or '年月' in cell_texts:
                            for i, h in enumerate(cell_texts):
                                if '年' in h and '月' in h:
                                    header_idx['date'] = i
                                elif '單月營收' in h or '營收' in h:
                                    header_idx['revenue'] = i
                                elif '月增' in h:
                                    header_idx['mom'] = i
                                elif '年增' in h:
                                    header_idx['yoy'] = i
                            continue

                        # 解析數據行
                        if header_idx and len(cell_texts) > max(header_idx.values(), default=0):
                            try:
                                date_val = cell_texts[header_idx.get('date', 0)] if 'date' in header_idx else None
                                rev_val = cell_texts[header_idx.get('revenue', 1)] if 'revenue' in header_idx else None
                                mom_val = cell_texts[header_idx.get('mom', 2)] if 'mom' in header_idx else None
                                yoy_val = cell_texts[header_idx.get('yoy', 3)] if 'yoy' in header_idx else None

                                if date_val and re.match(r'\d{4}', date_val):
                                    result["revenue"].append({
                                        "date": date_val,
                                        "revenue": self._safe_float(rev_val),
                                        "mom": self._safe_float(mom_val),
                                        "yoy": self._safe_float(yoy_val),
                                    })
                            except (IndexError, KeyError):
                                continue

                    # 取最近 12 筆
                    if result["revenue"]:
                        result["revenue"] = result["revenue"][:12]
                        break

            return result

        except requests.exceptions.Timeout:
            return {"stock_id": stock_id, "error": "連線超時"}
        except Exception as e:
            return {"stock_id": stock_id, "error": str(e)}

    def get_dividend(self, stock_id: str) -> dict:
        """
        取得股利政策

        Args:
            stock_id: 股票代碼

        Returns:
            dict: 股利資料
        """
        if not self.session:
            return {"stock_id": stock_id, "error": "爬蟲套件未安裝"}

        result = {
            "stock_id": stock_id,
            "dividends": []
        }

        try:
            url = f"{self.BASE_URL}/StockDividendPolicy.asp?STOCK_ID={stock_id}"
            resp = self.session.get(url, timeout=15)
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'lxml')

            # 找股利表格
            tables = soup.find_all('table')
            for table in tables:
                table_text = table.get_text()

                if '現金股利' in table_text and '股票股利' in table_text:
                    rows = table.find_all('tr')

                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        cell_texts = [c.get_text(strip=True) for c in cells]

                        # 找年度資料
                        if cell_texts and re.match(r'^\d{4}$', cell_texts[0]):
                            try:
                                year = cell_texts[0]
                                cash_div = self._safe_float(cell_texts[4]) if len(cell_texts) > 4 else None
                                stock_div = self._safe_float(cell_texts[5]) if len(cell_texts) > 5 else None
                                total_div = self._safe_float(cell_texts[6]) if len(cell_texts) > 6 else None
                                yield_rate = self._safe_float(cell_texts[7]) if len(cell_texts) > 7 else None

                                result["dividends"].append({
                                    "year": year,
                                    "cash_dividend": cash_div,
                                    "stock_dividend": stock_div,
                                    "total_dividend": total_div,
                                    "yield_rate": yield_rate,
                                })
                            except (IndexError, ValueError):
                                continue

                    # 取最近 5 年
                    if result["dividends"]:
                        result["dividends"] = result["dividends"][:5]
                        break

            return result

        except Exception as e:
            return {"stock_id": stock_id, "error": str(e)}

    def fetch_all(self, stock_ids: list[str], output_dir: Path) -> dict:
        """抓取所有台股資料"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "source": "goodinfo",
            "success": False,
            "data": {}
        }

        if not SCRAPER_AVAILABLE:
            result["error"] = "爬蟲套件未安裝"
            return result

        try:
            for i, stock_id in enumerate(stock_ids):
                print(f"  [Goodinfo] 抓取 {stock_id}...")

                result["data"][stock_id] = {
                    "info": self.get_stock_info(stock_id),
                    "revenue": self.get_revenue(stock_id),
                    "dividend": self.get_dividend(stock_id),
                }

                # 避免請求過快被封鎖
                if i < len(stock_ids) - 1:
                    time.sleep(1.5)

            result["success"] = True

            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "goodinfo_data.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

        except Exception as e:
            result["error"] = str(e)

        return result


if __name__ == "__main__":
    # 測試
    fetcher = GoodinfoFetcher()
    result = fetcher.fetch_all(
        ['2330', '2454'],
        Path('./data/raw/test')
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
