import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

JST = timezone(timedelta(hours=9))


@dataclass
class ScreenerRecord:
    run_id: int
    preset_name: str
    run_at: str
    ticker: str
    sec_code: str
    company_name: str
    composite_score: Optional[float]
    technical_score: Optional[float]
    news_score: Optional[float]
    recommendation_grade: Optional[str]
    entry_price_range: Optional[str]
    investment_thesis: Optional[str]
    current_price: Optional[float]
    priority_rank: Optional[int]
    scored_at: str


def _decode_name(value: str) -> str:
    """文字化け対策: latin-1 でデコードされた文字列を cp932 で再デコードを試みる"""
    if not value:
        return value
    try:
        return value.encode("latin-1").decode("cp932")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return value


class ScreenerReader:
    """stock_analyzer の screening_results DB を読み込むブリッジ。Flask の SQLAlchemy とは独立した sqlite3 接続を使用する。"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def is_available(self) -> bool:
        return bool(self.db_path) and os.path.exists(self.db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_last_run_info(self) -> Optional[dict]:
        """最終実行の run_at と preset_name を返す。データがなければ None。"""
        if not self.is_available():
            return None
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT preset_name, run_at FROM screening_runs ORDER BY run_at DESC LIMIT 1"
                ).fetchone()
            if row:
                return {"preset_name": row["preset_name"], "run_at": row["run_at"]}
            return None
        except sqlite3.Error:
            return None

    def _get_latest_run_ids(self, within_days: int) -> List[int]:
        """各 preset の最新 run_id を取得する（within_days 以内のもののみ）。"""
        cutoff = (datetime.now(JST) - timedelta(days=within_days)).isoformat()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT MAX(id) AS run_id
                FROM screening_runs
                WHERE run_at >= ?
                GROUP BY preset_name
                """,
                (cutoff,),
            ).fetchall()
        return [row["run_id"] for row in rows if row["run_id"] is not None]

    def get_latest_results(
        self,
        grades: Optional[List[str]] = None,
        min_score: float = 0.0,
        within_days: int = 14,
        limit: int = 50,
    ) -> List[ScreenerRecord]:
        """各 preset の最新スクリーニング結果を取得する。

        Args:
            grades: 絞り込むグレードリスト（例: ["A", "B"]）。None の場合は全グレード。
            min_score: composite_score の最低値。
            within_days: この日数以内の run のみ対象。
            limit: 最大取得件数。

        Returns:
            composite_score DESC でソートされた ScreenerRecord リスト。
        """
        if not self.is_available():
            return []

        try:
            run_ids = self._get_latest_run_ids(within_days)
            if not run_ids:
                return []

            placeholders = ",".join("?" * len(run_ids))
            params: list = list(run_ids)
            where_clauses = [f"r.run_id IN ({placeholders})"]

            if grades:
                grade_placeholders = ",".join("?" * len(grades))
                where_clauses.append(
                    f"r.recommendation_grade IN ({grade_placeholders})"
                )
                params.extend(grades)

            if min_score > 0:
                where_clauses.append("r.composite_score >= ?")
                params.append(min_score)

            where_sql = " AND ".join(where_clauses)
            params.append(limit)

            with self._connect() as conn:
                rows = conn.execute(
                    f"""
                    SELECT
                        r.run_id, s.preset_name, s.run_at,
                        r.ticker, r.sec_code, r.company_name,
                        r.composite_score, r.technical_score, r.news_score,
                        r.recommendation_grade, r.entry_price_range,
                        r.investment_thesis, r.current_price,
                        r.priority_rank, r.scored_at
                    FROM screening_results r
                    JOIN screening_runs s ON s.id = r.run_id
                    WHERE {where_sql}
                    ORDER BY r.composite_score DESC
                    LIMIT ?
                    """,
                    params,
                ).fetchall()

            return [self._row_to_record(row) for row in rows]
        except sqlite3.Error:
            return []

    def get_latest_score_for_tickers(
        self, tickers: List[str]
    ) -> Dict[str, "ScreenerRecord"]:
        """指定ティッカーの最新スクリーニング結果を辞書で返す。

        Args:
            tickers: 検索するティッカーのリスト（"7203.T" 形式）。

        Returns:
            {"7203.T": ScreenerRecord(...)} 形式の辞書。
        """
        if not self.is_available() or not tickers:
            return {}

        try:
            placeholders = ",".join("?" * len(tickers))
            with self._connect() as conn:
                rows = conn.execute(
                    f"""
                    SELECT
                        r.run_id, s.preset_name, s.run_at,
                        r.ticker, r.sec_code, r.company_name,
                        r.composite_score, r.technical_score, r.news_score,
                        r.recommendation_grade, r.entry_price_range,
                        r.investment_thesis, r.current_price,
                        r.priority_rank, r.scored_at
                    FROM screening_results r
                    JOIN screening_runs s ON s.id = r.run_id
                    WHERE r.ticker IN ({placeholders})
                      AND r.scored_at = (
                          SELECT MAX(r2.scored_at)
                          FROM screening_results r2
                          WHERE r2.ticker = r.ticker
                      )
                    """,
                    tickers,
                ).fetchall()

            return {row["ticker"]: self._row_to_record(row) for row in rows}
        except sqlite3.Error:
            return {}

    def _row_to_record(self, row: sqlite3.Row) -> ScreenerRecord:
        return ScreenerRecord(
            run_id=row["run_id"],
            preset_name=row["preset_name"],
            run_at=row["run_at"],
            ticker=row["ticker"],
            sec_code=row["sec_code"],
            company_name=_decode_name(row["company_name"]),
            composite_score=row["composite_score"],
            technical_score=row["technical_score"],
            news_score=row["news_score"],
            recommendation_grade=row["recommendation_grade"],
            entry_price_range=row["entry_price_range"],
            investment_thesis=(
                _decode_name(row["investment_thesis"])
                if row["investment_thesis"]
                else None
            ),
            current_price=row["current_price"],
            priority_rank=row["priority_rank"],
            scored_at=row["scored_at"],
        )
