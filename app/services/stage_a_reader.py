"""Stage A 結果リーダー

stock_analyzer/data/analyzer.db の weekly_reports テーブルから
最新の Stage A（マクロ・セクターローテーション）分析結果を読み込み、
GICS セクターに正規化された StageAResult dataclass として返す。

実際の summary_json 構造:
{
  "week_end": "2026-04-25",
  "macro_sentiment": "強気" | "中立" | "弱気",
  "macro_score": 68,
  "holdings": [{ticker, grade, score, return_pct}, ...],
  "top_sectors": [{name, reason}, ...]   # 強気・弱気混在の注視セクター
}
"""

import json
import logging
import os
import re
import sqlite3
from dataclasses import dataclass, field
from typing import List, Optional

from app.services.sector_mapping import normalize_to_gics

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# データクラス
# ──────────────────────────────────────────────


@dataclass
class SectorSignal:
    """Stage A の top_sectors を GICS に正規化した結果"""

    raw_name: str  # Stage A 元の日本語ラベル
    gics_sector: Optional[str]  # GICS 11セクター名（マッピング不能なら None）
    direction: str  # "BULLISH" / "BEARISH" / "NEUTRAL"
    reason: str  # Stage A の根拠テキスト


@dataclass
class StageAResult:
    """Stage A（マクロ・セクター）分析結果"""

    week_end: str  # "2026-04-25"
    macro_sentiment: str  # "強気" / "中立" / "弱気"
    macro_score: int  # 0-100
    sector_signals: List[SectorSignal] = field(default_factory=list)
    raw_top_sectors: List[dict] = field(default_factory=list)  # 元データ
    holdings_scores: List[dict] = field(default_factory=list)  # holdings 元データ

    @property
    def bullish_sectors(self) -> List[str]:
        """GICS 強気セクター一覧（重複なし、マッピング成功分のみ）"""
        seen, out = set(), []
        for s in self.sector_signals:
            if s.direction == "BULLISH" and s.gics_sector and s.gics_sector not in seen:
                seen.add(s.gics_sector)
                out.append(s.gics_sector)
        return out

    @property
    def bearish_sectors(self) -> List[str]:
        """GICS 弱気セクター一覧（重複なし、マッピング成功分のみ）"""
        seen, out = set(), []
        for s in self.sector_signals:
            if s.direction == "BEARISH" and s.gics_sector and s.gics_sector not in seen:
                seen.add(s.gics_sector)
                out.append(s.gics_sector)
        return out


# ──────────────────────────────────────────────
# センチメント方向の推定
# ──────────────────────────────────────────────

_BULLISH_KEYWORDS = (
    "リード",
    "上昇",
    "モメンタム",
    "強気",
    "好調",
    "拡大",
    "底堅",
    "買い",
    "上振れ",
    "押し目",
    "切上",
    "高値",
    "上抜け",
    "復活",
    "回復",
    "改善",
    "増",
    "上方",
)
_BEARISH_KEYWORDS = (
    "軟調",
    "下落",
    "弱気",
    "下げ",
    "戻し",
    "失速",
    "戻り売り",
    "下振れ",
    "ピークアウト",
    "減速",
    "後退",
    "悪化",
    "リスク",
    "懸念",
    "警戒",
    "下抜け",
    "下方",
    "減少",
)

_PCT_PATTERN = re.compile(r"([+\-]?)(\d+(?:\.\d+)?)\s*%")


def _detect_direction(reason: str) -> str:
    """根拠テキストから方向性（BULLISH/BEARISH/NEUTRAL）を推定する。

    判定優先順位:
    1. パーセント値の符号合計（+X% > -X% なら BULLISH 寄り）
    2. キーワード出現数の多寡
    3. デフォルトは NEUTRAL
    """
    if not reason:
        return "NEUTRAL"

    # ステップ1: パーセント値
    pct_score = 0.0
    for sign, num in _PCT_PATTERN.findall(reason):
        try:
            v = float(num)
        except ValueError:
            continue
        if sign == "-":
            pct_score -= v
        else:
            pct_score += v

    # ステップ2: キーワード
    bull = sum(1 for k in _BULLISH_KEYWORDS if k in reason)
    bear = sum(1 for k in _BEARISH_KEYWORDS if k in reason)
    kw_score = bull - bear

    # 統合スコア（パーセント差は重み弱め）
    total = pct_score * 0.3 + kw_score * 1.0
    if total >= 0.8:
        return "BULLISH"
    if total <= -0.8:
        return "BEARISH"
    return "NEUTRAL"


# ──────────────────────────────────────────────
# Reader
# ──────────────────────────────────────────────


class StageAReader:
    """analyzer.db.weekly_reports から最新 Stage A 結果を読み出す"""

    def __init__(self, db_path: str):
        """
        Args:
            db_path: analyzer.db への絶対パス（例: config.STOCK_ANALYZER_DB_PATH）
        """
        self.db_path = db_path

    def is_available(self) -> bool:
        """DB ファイルが存在するか"""
        return os.path.exists(self.db_path)

    def get_latest(self) -> Optional[StageAResult]:
        """最新の weekly_reports 行を読み StageAResult に変換する"""
        if not self.is_available():
            logger.warning(f"[StageAReader] DB not found: {self.db_path}")
            return None

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                "SELECT week_end, summary_json FROM weekly_reports "
                "ORDER BY week_end DESC LIMIT 1"
            )
            row = cur.fetchone()
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"[StageAReader] SQLite エラー: {e}")
            return None

        if not row:
            logger.info("[StageAReader] weekly_reports に行がありません")
            return None

        try:
            sj = json.loads(row["summary_json"])
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"[StageAReader] summary_json パース失敗: {e}")
            return None

        # SectorSignal に変換
        signals = []
        for s in sj.get("top_sectors", []):
            raw_name = s.get("name", "")
            reason = s.get("reason", "")
            gics = normalize_to_gics(raw_name, source="jp_label")
            direction = _detect_direction(reason)
            signals.append(
                SectorSignal(
                    raw_name=raw_name,
                    gics_sector=gics,
                    direction=direction,
                    reason=reason,
                )
            )

        return StageAResult(
            week_end=row["week_end"],
            macro_sentiment=sj.get("macro_sentiment", "中立"),
            macro_score=int(sj.get("macro_score", 50)),
            sector_signals=signals,
            raw_top_sectors=sj.get("top_sectors", []),
            holdings_scores=sj.get("holdings", []),
        )
