import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from app.models.holding import Holding
from app.models.stock_metrics import StockMetrics
from app.services.screener_reader import ScreenerReader, ScreenerRecord
from app.services.sector_composition_service import (
    SectorAnalysisResult,
    SectorCompositionService,
)
from app.services.stage_a_reader import StageAReader

JST = timezone(timedelta(hours=9))

SELL_THRESHOLD_SCORE = 55.0
BUY_MIN_SCORE = 60.0
MAX_POSITION_PCT = 0.10
ETF_TICKERS = {
    "1475.T",
    "314A.T",
    "1557.T",
    "2558.T",
    "VOO",
    "SPY",
    "QQQ",
    "IVV",
    "VTI",
    "EWJ",
}


@dataclass
class HoldingScore:
    ticker_symbol: str
    security_name: str
    current_value_jpy: float
    weight_pct: float
    unrealized_pnl_pct: float
    composite_score: Optional[float]
    proxy_score: Optional[float]
    effective_score: float
    recommendation_grade: Optional[str]
    screener_scored_at: Optional[str]
    is_etf: bool


@dataclass
class SellCandidate:
    ticker_symbol: str
    security_name: str
    effective_score: float
    reason: str
    current_value_jpy: float
    unrealized_pnl_pct: float
    tax_consideration: str


@dataclass
class BuyCandidate:
    ticker_symbol: str
    company_name: str
    recommendation_grade: str
    composite_score: float
    entry_price_range: Optional[str]
    investment_thesis: Optional[str]
    current_price: Optional[float]
    preset_name: str


@dataclass
class ReplacementProposal:
    sell: SellCandidate
    buy: BuyCandidate
    rationale: str
    score_improvement: float
    estimated_freed_capital: float


@dataclass
class CashInvestmentProposal:
    ticker_symbol: str
    company_name: str
    recommendation_grade: str
    composite_score: float
    entry_price_range: Optional[str]
    investment_thesis: Optional[str]
    current_price: Optional[float]
    suggested_amount_jpy: float
    suggested_quantity: int
    position_pct_after: float
    max_position_warning: bool


@dataclass
class AdvisorResult:
    generated_at: str
    screener_last_run_at: Optional[str]
    screener_available: bool
    holding_scores: List[HoldingScore]
    total_portfolio_value_jpy: float
    sell_candidates: List[SellCandidate]
    buy_candidates: List[BuyCandidate]
    replacement_proposals: List[ReplacementProposal]
    cash_input_jpy: Optional[float]
    cash_proposals: List[CashInvestmentProposal]
    remaining_cash_jpy: Optional[float]
    warnings: List[str] = field(default_factory=list)
    # トップダウン: マクロ・セクター構成分析（Stage A 連携）
    sector_analysis: Optional[SectorAnalysisResult] = None


class PortfolioAdvisorService:

    def __init__(self, screener_db_path: str):
        self.screener = ScreenerReader(screener_db_path)
        # Stage A 結果も同じ analyzer.db から読む
        self.sector_service = SectorCompositionService(StageAReader(screener_db_path))

    def analyze(self, cash_jpy: Optional[float] = None) -> AdvisorResult:
        warnings: List[str] = []
        generated_at = datetime.now(JST).isoformat()

        screener_available = self.screener.is_available()
        last_run_info = (
            self.screener.get_last_run_info() if screener_available else None
        )
        screener_last_run_at = last_run_info["run_at"] if last_run_info else None

        if not screener_available:
            warnings.append(
                "スクリーナーDBが見つかりません。stock_analyzer を実行してください。"
            )

        holding_scores, total_value = self._build_holding_scores(warnings)

        screener_results: List[ScreenerRecord] = []
        if screener_available:
            screener_results = self.screener.get_latest_results(
                grades=["A", "B", "C"], within_days=14
            )
            if not screener_results:
                warnings.append(
                    "スクリーナーデータが14日以上古いか、結果がありません。"
                )

        held_tickers = {hs.ticker_symbol for hs in holding_scores}
        buy_candidates = self._identify_buy_candidates(screener_results, held_tickers)
        buy_tickers = {bc.ticker_symbol for bc in buy_candidates}

        sell_candidates = self._identify_sell_candidates(holding_scores, buy_tickers)

        replacement_proposals = self._create_replacement_proposals(
            sell_candidates, buy_candidates
        )

        cash_proposals: List[CashInvestmentProposal] = []
        remaining_cash: Optional[float] = None
        if cash_jpy is not None and cash_jpy > 0:
            cash_proposals, remaining_cash = self._propose_cash_investments(
                cash_jpy, buy_candidates, holding_scores, total_value
            )

        # トップダウン: マクロ・セクター構成分析
        try:
            sector_analysis = self.sector_service.analyze()
            if (
                sector_analysis
                and not sector_analysis.available
                and sector_analysis.note
            ):
                warnings.append(f"セクター分析: {sector_analysis.note}")
        except Exception as e:
            warnings.append(f"セクター分析の実行に失敗しました: {e}")
            sector_analysis = None

        return AdvisorResult(
            generated_at=generated_at,
            screener_last_run_at=screener_last_run_at,
            screener_available=screener_available,
            holding_scores=holding_scores,
            total_portfolio_value_jpy=round(total_value, 0),
            sell_candidates=sell_candidates,
            buy_candidates=buy_candidates,
            replacement_proposals=replacement_proposals,
            cash_input_jpy=cash_jpy,
            cash_proposals=cash_proposals,
            remaining_cash_jpy=(
                round(remaining_cash, 0) if remaining_cash is not None else None
            ),
            warnings=warnings,
            sector_analysis=sector_analysis,
        )

    def _build_holding_scores(
        self, warnings: List[str]
    ) -> Tuple[List[HoldingScore], float]:
        holdings = Holding.query.filter(Holding.total_quantity > 0).all()
        if not holdings:
            return [], 0.0

        tickers = [h.ticker_symbol for h in holdings]
        metrics_map: Dict[str, StockMetrics] = {
            m.ticker_symbol: m
            for m in StockMetrics.query.filter(
                StockMetrics.ticker_symbol.in_(tickers)
            ).all()
        }
        screener_map = self.screener.get_latest_score_for_tickers(tickers)

        total_value = sum(float(h.current_value) for h in holdings if h.current_value)

        result: List[HoldingScore] = []
        for h in holdings:
            ticker = h.ticker_symbol
            current_val = float(h.current_value) if h.current_value else 0.0
            unrealized_pct = (
                float(h.unrealized_pnl_pct) if h.unrealized_pnl_pct else 0.0
            )
            weight_pct = (current_val / total_value * 100) if total_value > 0 else 0.0
            is_etf = self._is_etf(ticker, h.security_name or "")

            screener_rec = screener_map.get(ticker)
            composite_score = screener_rec.composite_score if screener_rec else None
            grade = screener_rec.recommendation_grade if screener_rec else None
            scored_at = screener_rec.scored_at if screener_rec else None

            proxy_score: Optional[float] = None
            if composite_score is None and not is_etf:
                m = metrics_map.get(ticker)
                if m:
                    proxy_score = self._calc_proxy_score(
                        pe=float(m.pe_ratio) if m.pe_ratio else None,
                        pb=float(m.pb_ratio) if m.pb_ratio else None,
                        profit_margin=(
                            float(m.profit_margin) if m.profit_margin else None
                        ),
                        ytd_return=float(m.ytd_return) if m.ytd_return else None,
                        unrealized_pnl_pct=unrealized_pct,
                    )

            if is_etf:
                effective_score = 60.0
            elif composite_score is not None:
                effective_score = composite_score
            elif proxy_score is not None:
                effective_score = proxy_score
            else:
                effective_score = 50.0

            result.append(
                HoldingScore(
                    ticker_symbol=ticker,
                    security_name=h.security_name or ticker,
                    current_value_jpy=round(current_val, 0),
                    weight_pct=round(weight_pct, 2),
                    unrealized_pnl_pct=round(unrealized_pct, 2),
                    composite_score=(
                        round(composite_score, 1)
                        if composite_score is not None
                        else None
                    ),
                    proxy_score=(
                        round(proxy_score, 1) if proxy_score is not None else None
                    ),
                    effective_score=round(effective_score, 1),
                    recommendation_grade=grade,
                    screener_scored_at=scored_at,
                    is_etf=is_etf,
                )
            )

        result.sort(key=lambda x: x.effective_score)
        return result, total_value

    @staticmethod
    def _calc_proxy_score(
        pe: Optional[float],
        pb: Optional[float],
        profit_margin: Optional[float],
        ytd_return: Optional[float],
        unrealized_pnl_pct: float,
    ) -> float:
        def _pe_score(v: Optional[float]) -> float:
            if v is None:
                return 50.0
            if v <= 0:
                return 10.0
            if v <= 10:
                return 100.0
            if v <= 20:
                return 70.0 + (20 - v) * 3.0
            if v <= 30:
                return 50.0 + (30 - v) * 2.0
            if v <= 40:
                return 30.0 + (40 - v) * 2.0
            return max(0.0, 30.0 - (v - 40) * 0.5)

        def _pb_score(v: Optional[float]) -> float:
            if v is None:
                return 50.0
            if v <= 0:
                return 10.0
            if v <= 1:
                return 100.0
            if v <= 2:
                return 75.0 + (2 - v) * 25.0
            if v <= 3:
                return 50.0 + (3 - v) * 25.0
            if v <= 5:
                return 25.0 + (5 - v) * 12.5
            return max(0.0, 25.0 - (v - 5) * 3.0)

        def _margin_score(v: Optional[float]) -> float:
            if v is None:
                return 50.0
            if v >= 0.20:
                return 100.0
            if v >= 0.10:
                return 70.0 + (v - 0.10) / 0.10 * 30.0
            if v >= 0.05:
                return 40.0 + (v - 0.05) / 0.05 * 30.0
            if v >= 0:
                return v / 0.05 * 40.0
            return 0.0

        def _ytd_score(v: Optional[float]) -> float:
            if v is None:
                return 50.0
            if v >= 0.20:
                return 90.0
            if v >= 0.10:
                return 70.0 + (v - 0.10) / 0.10 * 20.0
            if v >= 0:
                return 50.0 + v / 0.10 * 20.0
            if v >= -0.10:
                return 30.0 + (v + 0.10) / 0.10 * 20.0
            return max(0.0, 30.0 + (v + 0.10) / 0.10 * 20.0)

        def _unrealized_score(v: float) -> float:
            if v >= 30:
                return 90.0
            if v >= 10:
                return 65.0 + (v - 10) / 20 * 25.0
            if v >= 0:
                return 50.0 + v / 10 * 15.0
            if v >= -10:
                return 35.0 + (v + 10) / 10 * 15.0
            return max(0.0, 35.0 + (v + 10) / 10 * 15.0)

        val_score = (_pe_score(pe) + _pb_score(pb)) / 2
        prof_score = _margin_score(profit_margin)
        mom_score = (_ytd_score(ytd_return) + _unrealized_score(unrealized_pnl_pct)) / 2

        return round(val_score * 0.35 + prof_score * 0.35 + mom_score * 0.30, 1)

    def _identify_sell_candidates(
        self,
        holding_scores: List[HoldingScore],
        buy_tickers: set,
    ) -> List[SellCandidate]:
        from datetime import datetime as _dt

        candidates = []
        for hs in holding_scores:
            if hs.is_etf:
                continue

            points = 0
            reasons = []

            if hs.effective_score < SELL_THRESHOLD_SCORE:
                points += 2
                reasons.append(
                    f"スコア{hs.effective_score:.0f}点（閾値{SELL_THRESHOLD_SCORE:.0f}点未満）"
                )
            if hs.effective_score < 50.0:
                points += 1

            if hs.ticker_symbol in buy_tickers:
                points += 1
                reasons.append("代替候補あり")

            if hs.unrealized_pnl_pct < 0:
                points += 1
                reasons.append("含み損（損切り検討）")

            if hs.recommendation_grade == "C" and hs.screener_scored_at:
                try:
                    scored = _dt.fromisoformat(
                        hs.screener_scored_at.replace("Z", "+00:00")
                    )
                    days_ago = (datetime.now(JST) - scored.astimezone(JST)).days
                    if days_ago <= 7:
                        points += 1
                        reasons.append("直近7日以内にCグレード")
                except (ValueError, TypeError):
                    pass

            if points < 2:
                continue

            if hs.unrealized_pnl_pct > 5:
                tax_note = (
                    f"含み益{hs.unrealized_pnl_pct:.1f}%あり（売却益に約20.3%課税）"
                )
            elif hs.unrealized_pnl_pct < 0:
                tax_note = f"含み損{hs.unrealized_pnl_pct:.1f}%（損出しで節税効果あり）"
            else:
                tax_note = "損益ほぼゼロ"

            candidates.append(
                SellCandidate(
                    ticker_symbol=hs.ticker_symbol,
                    security_name=hs.security_name,
                    effective_score=hs.effective_score,
                    reason="、".join(reasons),
                    current_value_jpy=hs.current_value_jpy,
                    unrealized_pnl_pct=hs.unrealized_pnl_pct,
                    tax_consideration=tax_note,
                )
            )

        candidates.sort(key=lambda x: x.effective_score)
        return candidates

    @staticmethod
    def _identify_buy_candidates(
        screener_results: List[ScreenerRecord],
        held_tickers: set,
    ) -> List[BuyCandidate]:
        candidates = []
        for r in screener_results:
            if r.ticker in held_tickers:
                continue
            if r.recommendation_grade not in ("A", "B"):
                continue
            if (r.composite_score or 0) < BUY_MIN_SCORE:
                continue
            candidates.append(
                BuyCandidate(
                    ticker_symbol=r.ticker,
                    company_name=r.company_name,
                    recommendation_grade=r.recommendation_grade,
                    composite_score=r.composite_score or 0,
                    entry_price_range=r.entry_price_range,
                    investment_thesis=r.investment_thesis,
                    current_price=r.current_price,
                    preset_name=r.preset_name,
                )
            )

        candidates.sort(
            key=lambda x: (
                -x.composite_score,
                x.priority_rank if hasattr(x, "priority_rank") else 99,
            )
        )
        return candidates[:15]

    @staticmethod
    def _create_replacement_proposals(
        sell_candidates: List[SellCandidate],
        buy_candidates: List[BuyCandidate],
    ) -> List[ReplacementProposal]:
        proposals = []
        n = min(len(sell_candidates), len(buy_candidates), 5)
        for i in range(n):
            sell = sell_candidates[i]
            buy = buy_candidates[i]
            score_diff = buy.composite_score - sell.effective_score
            thesis_short = (buy.investment_thesis or "")[:80]
            rationale = (
                f"{sell.ticker_symbol}（スコア{sell.effective_score:.0f}）を売却し、"
                f"{buy.ticker_symbol}（{buy.recommendation_grade}グレード・"
                f"スコア{buy.composite_score:.0f}）に入替。{thesis_short}"
            )
            proposals.append(
                ReplacementProposal(
                    sell=sell,
                    buy=buy,
                    rationale=rationale,
                    score_improvement=round(score_diff, 1),
                    estimated_freed_capital=sell.current_value_jpy,
                )
            )
        return proposals

    @staticmethod
    def _propose_cash_investments(
        cash_jpy: float,
        buy_candidates: List[BuyCandidate],
        holding_scores: List[HoldingScore],
        total_portfolio_value: float,
    ) -> Tuple[List[CashInvestmentProposal], float]:
        existing_value_map = {
            hs.ticker_symbol: hs.current_value_jpy for hs in holding_scores
        }
        allocated_map: Dict[str, float] = {}
        available_cash = cash_jpy
        proposals: List[CashInvestmentProposal] = []

        grade_a = [b for b in buy_candidates if b.recommendation_grade == "A"]
        grade_b = [b for b in buy_candidates if b.recommendation_grade == "B"]
        ordered = grade_a + grade_b

        for bc in ordered:
            if available_cash <= 0:
                break

            max_position = total_portfolio_value * MAX_POSITION_PCT
            existing = existing_value_map.get(bc.ticker_symbol, 0.0)
            already_allocated = allocated_map.get(bc.ticker_symbol, 0.0)
            room = max_position - existing - already_allocated
            if room <= 0:
                continue

            single_cap = available_cash * 0.40
            invest_amount = min(room, single_cap)
            if invest_amount <= 0:
                continue

            price = bc.current_price
            if price is None and bc.entry_price_range:
                price = PortfolioAdvisorService._parse_entry_price(bc.entry_price_range)

            if price and price > 0:
                qty = math.floor(invest_amount / price)
                if qty <= 0:
                    continue
                actual_amount = qty * price
            else:
                qty = 0
                actual_amount = invest_amount

            available_cash -= actual_amount
            allocated_map[bc.ticker_symbol] = already_allocated + actual_amount

            position_after = (
                (existing + actual_amount) / (total_portfolio_value + cash_jpy) * 100
            )
            max_warn = (
                existing + actual_amount
            ) > total_portfolio_value * MAX_POSITION_PCT

            proposals.append(
                CashInvestmentProposal(
                    ticker_symbol=bc.ticker_symbol,
                    company_name=bc.company_name,
                    recommendation_grade=bc.recommendation_grade,
                    composite_score=bc.composite_score,
                    entry_price_range=bc.entry_price_range,
                    investment_thesis=bc.investment_thesis,
                    current_price=price,
                    suggested_amount_jpy=round(actual_amount, 0),
                    suggested_quantity=qty,
                    position_pct_after=round(position_after, 2),
                    max_position_warning=max_warn,
                )
            )

        return proposals, max(0.0, available_cash)

    @staticmethod
    def _parse_entry_price(entry_price_range: str) -> Optional[float]:
        nums = re.findall(r"[\d,]+(?:\.\d+)?", entry_price_range)
        cleaned = [float(n.replace(",", "")) for n in nums]
        if len(cleaned) >= 2:
            return (cleaned[0] + cleaned[-1]) / 2
        if len(cleaned) == 1:
            return cleaned[0]
        return None

    @staticmethod
    def _is_etf(ticker: str, security_name: str) -> bool:
        if ticker in ETF_TICKERS:
            return True
        name_upper = security_name.upper()
        return any(kw in name_upper for kw in ("ETF", "IS CORE", "ISHARES", "VANGUARD"))
