"""セクター分類マッピングモジュール

GICS 11セクター統一の分類体系で、以下を提供:
1. EDINET 33業種 → GICS 11セクター への変換テーブル
2. yfinance sector の正規化（既に GICS だが表記揺れを吸収）
3. stock_analyzer Stage A の日本語セクター名 → GICS マッピング
4. ETF 判定（ETF は別カテゴリ "Index/ETF"）
5. S&P500 ベンチマークセクター比率（ターゲット算出のベースライン）
"""

from typing import Optional


# GICS 11セクター（標準名）
GICS_SECTORS = [
    "Information Technology",
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Health Care",
    "Industrials",
    "Materials",
    "Real Estate",
    "Utilities",
]

# ETF / インデックス用の特別カテゴリ
ETF_CATEGORY = "Index/ETF"


# ──────────────────────────────────────────────
# EDINET 33業種（東証業種分類） → GICS 11セクター
# ──────────────────────────────────────────────
EDINET_TO_GICS = {
    # Technology / Communication
    "情報・通信業": "Communication Services",
    "電気機器": "Information Technology",
    "精密機器": "Information Technology",
    # Consumer Discretionary
    "輸送用機器": "Consumer Discretionary",
    "小売業": "Consumer Discretionary",
    "サービス業": "Consumer Discretionary",
    "その他製品": "Consumer Discretionary",
    # Consumer Staples
    "食料品": "Consumer Staples",
    "水産・農林業": "Consumer Staples",
    "繊維製品": "Consumer Staples",
    "パルプ・紙": "Consumer Staples",
    # Health Care
    "医薬品": "Health Care",
    # Financials
    "銀行業": "Financials",
    "証券、商品先物取引業": "Financials",
    "保険業": "Financials",
    "その他金融業": "Financials",
    # Energy
    "鉱業": "Energy",
    "石油・石炭製品": "Energy",
    # Materials
    "化学": "Materials",
    "鉄鋼": "Materials",
    "非鉄金属": "Materials",
    "金属製品": "Materials",
    "ガラス・土石製品": "Materials",
    "ゴム製品": "Materials",
    # Industrials
    "建設業": "Industrials",
    "機械": "Industrials",
    "倉庫・運輸関連業": "Industrials",
    "陸運業": "Industrials",
    "海運業": "Industrials",
    "空運業": "Industrials",
    # Real Estate
    "不動産業": "Real Estate",
    # Utilities
    "電気・ガス業": "Utilities",
    # Misc / Trading
    "卸売業": "Industrials",  # 商社は産業セクター
}


# ──────────────────────────────────────────────
# yfinance sector の表記揺れ → 標準 GICS
# ──────────────────────────────────────────────
YFINANCE_TO_GICS = {
    "Technology": "Information Technology",
    "Information Technology": "Information Technology",
    "Communication Services": "Communication Services",
    "Communication": "Communication Services",
    "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Discretionary": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples",
    "Consumer Staples": "Consumer Staples",
    "Energy": "Energy",
    "Financial Services": "Financials",
    "Financial": "Financials",
    "Financials": "Financials",
    "Healthcare": "Health Care",
    "Health Care": "Health Care",
    "Industrials": "Industrials",
    "Industrial": "Industrials",
    "Basic Materials": "Materials",
    "Materials": "Materials",
    "Real Estate": "Real Estate",
    "Utilities": "Utilities",
}


# ──────────────────────────────────────────────
# stock_analyzer Stage A の日本語セクター名 → GICS
# Stage A は米セクターETF（XL系）+ 日本TOPIX-17 を分析するため、
# 表現の揺れがある: "情報技術・電機精密"、"半導体"、"金融" 等
# ──────────────────────────────────────────────
JP_LABEL_TO_GICS = {
    # IT / Tech
    "情報技術": "Information Technology",
    "情報技術・電機精密": "Information Technology",
    "電機": "Information Technology",
    "半導体": "Information Technology",
    "テクノロジー": "Information Technology",
    # Communication
    "通信": "Communication Services",
    "コミュニケーション": "Communication Services",
    # Consumer Discretionary
    "一般消費財": "Consumer Discretionary",
    "自動車・輸送機": "Consumer Discretionary",
    "小売": "Consumer Discretionary",
    # Consumer Staples
    "生活必需品": "Consumer Staples",
    "食品": "Consumer Staples",
    # Health Care
    "ヘルスケア": "Health Care",
    "ヘルスケア・医薬": "Health Care",
    "医薬": "Health Care",
    "医薬品": "Health Care",
    # Financials
    "金融": "Financials",
    "銀行": "Financials",
    # Energy
    "エネルギー": "Energy",
    "エネルギー資源": "Energy",
    "石油": "Energy",
    # Materials
    "素材": "Materials",
    "素材・化学": "Materials",
    "化学": "Materials",
    "鉄鋼": "Materials",
    # Industrials
    "資本財": "Industrials",
    "産業材": "Industrials",
    "機械": "Industrials",
    "建設": "Industrials",
    "商社・卸売": "Industrials",
    # Real Estate
    "不動産": "Real Estate",
    "REIT": "Real Estate",
    # Utilities
    "公益": "Utilities",
    "電力・ガス": "Utilities",
}


# ──────────────────────────────────────────────
# S&P500 ベンチマークセクター比率（2025年実勢、ベースライン）
# 数値は概算で、合計は約100%（残差は小数誤差）
# ──────────────────────────────────────────────
SP500_SECTOR_WEIGHTS = {
    "Information Technology": 30.0,
    "Financials": 13.5,
    "Health Care": 11.0,
    "Consumer Discretionary": 10.5,
    "Communication Services": 9.0,
    "Industrials": 8.5,
    "Consumer Staples": 6.0,
    "Energy": 3.5,
    "Utilities": 2.5,
    "Real Estate": 2.5,
    "Materials": 2.0,
    ETF_CATEGORY: 0.0,  # ETFは別枠
}


# ──────────────────────────────────────────────
# ETF 判定
# ──────────────────────────────────────────────
# 既知のETFティッカー（プレフィックス・サフィックス・完全一致を含む）
KNOWN_ETF_TICKERS = {
    # 米国ETF
    "VOO",
    "VTI",
    "SPY",
    "QQQ",
    "DIA",
    "IWM",
    "XLK",
    "XLF",
    "XLV",
    "XLE",
    "XLI",
    "XLP",
    "XLY",
    "XLB",
    "XLU",
    "XLRE",
    "XLC",
    "SOXX",
    "SMH",
    "SOXS",
    "GLD",
    "SLV",
    "IAU",
    "AGG",
    "BND",
    "TLT",
    "IEF",
}

# 日本ETFは数字4桁 + .T で、特定の番号レンジが ETF
# 例: 1306-1699（インデックスETF）、1475 (iSTOPIX)、1557 (SPDR S&P500)
JP_ETF_TICKER_PREFIXES = {"13", "14", "15", "16"}


def detect_etf(ticker: str, security_name: str = "") -> bool:
    """ETF / インデックスファンドかどうか判定する

    Args:
        ticker: ティッカーシンボル（例: "VOO", "1475.T"）
        security_name: 銘柄名（"ETF" や "インデックス" を含むかチェック）

    Returns:
        True if ETF
    """
    upper = ticker.upper().split(".")[0].split(",")[0]
    if upper in KNOWN_ETF_TICKERS:
        return True

    # 日本株: 4桁数字で 1xxx 番台は多くがETF
    if ticker.endswith(".T") or ticker.endswith(",T"):
        code = upper.lstrip("0")
        if len(code) == 4 and code[:2] in JP_ETF_TICKER_PREFIXES:
            return True

    # 銘柄名に "ETF" / "インデックス" / "iS" を含む
    name_upper = (security_name or "").upper()
    if any(
        kw in name_upper
        for kw in (
            "ETF",
            "INDEX",
            "ISTOPIX",
            "ISハーゲン",
            "VANGUARD",
            "SPDR",
            "ISHARES",
        )
    ):
        return True
    if any(
        kw in (security_name or "") for kw in ("ETF", "インデックス", "上場投信", "iS")
    ):
        return True

    return False


def detect_region(ticker: str) -> str:
    """ティッカーから地域コードを判定する

    Args:
        ticker: ティッカーシンボル

    Returns:
        "US" / "JP" / "KR" / "OTHER"
    """
    if not ticker:
        return "OTHER"
    upper = ticker.upper()
    if upper.endswith(".T") or upper.endswith(",T"):
        return "JP"
    if upper.endswith(".KS") or upper.endswith(".KQ"):
        return "KR"
    if upper.endswith(".HK"):
        return "HK"
    if upper.endswith(".L"):
        return "GB"
    if "." not in upper:
        return "US"
    return "OTHER"


def normalize_to_gics(
    raw_sector: Optional[str], source: str = "yfinance"
) -> Optional[str]:
    """生のセクター名を標準 GICS セクター名に変換する

    Args:
        raw_sector: 元の sector 文字列（yfinance / EDINET / 日本語ラベル）
        source: "yfinance" / "edinet" / "jp_label"

    Returns:
        GICS セクター名 or None（マッピング不能）
    """
    if not raw_sector:
        return None
    raw = raw_sector.strip()

    if source == "yfinance":
        return YFINANCE_TO_GICS.get(raw)
    if source == "edinet":
        return EDINET_TO_GICS.get(raw)
    if source == "jp_label":
        # 完全一致 → 部分一致 でフォールバック
        if raw in JP_LABEL_TO_GICS:
            return JP_LABEL_TO_GICS[raw]
        for key, gics in JP_LABEL_TO_GICS.items():
            if key in raw or raw in key:
                return gics
        return None

    # 不明 source: 全テーブル横断検索
    for table in (YFINANCE_TO_GICS, EDINET_TO_GICS, JP_LABEL_TO_GICS):
        if raw in table:
            return table[raw]
    return None


def get_baseline_weight(sector: str) -> float:
    """指定 GICS セクターの S&P500 ベンチマーク比率を返す（%）"""
    return SP500_SECTOR_WEIGHTS.get(sector, 0.0)


# ──────────────────────────────────────────────
# EDINET DB HTTP 直接呼び出し（日本株のセクター取得用）
# ──────────────────────────────────────────────


def fetch_edinet_industry(
    ticker_symbol: str, api_key: Optional[str] = None
) -> Optional[str]:
    """EDINET DB から日本株の業種（industry）を取得する。

    Args:
        ticker_symbol: 日本株ティッカー（例: "7203.T"、"8306.T"）
        api_key: EDINET_API_KEY（省略時は環境変数から取得）

    Returns:
        EDINET 業種名（例: "輸送用機器"）or None
    """
    import os
    import requests

    if api_key is None:
        api_key = os.environ.get("EDINET_API_KEY", "")
    if not api_key:
        return None

    # 4桁証券コード抽出（"7203.T" → "7203"）
    code = ticker_symbol.upper().split(".")[0].split(",")[0].lstrip("0")
    if not code.isdigit() or len(code) != 4:
        return None

    url = "https://edinetdb.jp/mcp"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    try:
        # 1. initialize
        init_resp = requests.post(
            url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "stock-pnl-manager", "version": "1.0"},
                },
            },
            headers=headers,
            timeout=15,
        )
        sid = init_resp.headers.get("mcp-session-id")
        h2 = {**headers, "mcp-session-id": sid} if sid else headers

        # 2. notifications/initialized
        if sid:
            requests.post(
                url,
                json={
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {},
                },
                headers=h2,
                timeout=5,
            )

        # 3. search_companies で sec_code を検索 → industry を取得
        tool_resp = requests.post(
            url,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "search_companies",
                    "arguments": {"query": code, "limit": 1},
                },
            },
            headers=h2,
            timeout=15,
        )
        tool_resp.raise_for_status()

        # SSE / JSON 両対応
        ct = tool_resp.headers.get("Content-Type", "")
        if "text/event-stream" in ct:
            import json as _json

            last = None
            for line in tool_resp.text.splitlines():
                if line.startswith("data:"):
                    raw = line[5:].strip()
                    if raw and raw != "[DONE]":
                        try:
                            last = _json.loads(raw)
                        except _json.JSONDecodeError:
                            pass
            rj = last or {}
        else:
            rj = tool_resp.json()

        if "error" in rj:
            return None

        for item in rj.get("result", {}).get("content", []):
            if item.get("type") == "text":
                import json as _json

                try:
                    payload = _json.loads(item["text"])
                except _json.JSONDecodeError:
                    continue
                companies = (
                    payload
                    if isinstance(payload, list)
                    else payload.get("companies", [])
                )
                if companies:
                    return companies[0].get("industry")
        return None

    except Exception:
        return None
