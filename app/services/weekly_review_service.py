from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional

from app import db
from app.models.benchmark_price import BenchmarkPrice
from app.models.dividend import Dividend
from app.models.holding import Holding
from app.models.realized_pnl import RealizedPnl
from app.models.stock_metrics import StockMetrics
from app.models.stock_price import StockPrice


@dataclass
class HoldingWeeklyPerf:
    ticker_symbol: str
    security_name: str
    currency: str
    weight_pct: float
    week_return_pct: Optional[float]
    unrealized_pnl_pct: float
    pe_ratio: Optional[float]
    pb_ratio: Optional[float]
    profit_margin: Optional[float]
    beta: Optional[float]
    quality_label: str
    quality_reasons: List[str] = field(default_factory=list)


@dataclass
class BenchmarkWeeklyPerf:
    benchmark_key: str
    name: str
    week_return_pct: Optional[float]


@dataclass
class WeeklyReviewResult:
    week_start: date
    week_end: date
    generated_at: str
    total_portfolio_value_jpy: float
    portfolio_week_return_pct: Optional[float]
    benchmarks: List[BenchmarkWeeklyPerf]
    alpha_vs_topix: Optional[float]
    alpha_vs_sp500: Optional[float]
    holdings_perf: List[HoldingWeeklyPerf]
    weekly_realized_pnl: float
    weekly_dividend_income: float
    good_count: int
    watch_count: int
    review_count: int


class WeeklyReviewService:

    JP_THRESHOLDS = {
        "pe_good": 20.0,
        "pe_watch": 35.0,
        "pb_good": 2.0,
        "pb_watch": 3.5,
        "margin_good": 0.08,
        "margin_watch": 0.03,
    }
    US_THRESHOLDS = {
        "pe_good": 30.0,
        "pe_watch": 50.0,
        "pb_good": 5.0,
        "pb_watch": 10.0,
        "margin_good": 0.10,
        "margin_watch": 0.03,
    }

    @staticmethod
    def get_weekly_review(week_end_date: Optional[date] = None) -> WeeklyReviewResult:
        from datetime import datetime, timezone, timedelta

        JST = timezone(timedelta(hours=9))
        if week_end_date is None:
            week_end_date = datetime.now(JST).date()
        week_start_date = week_end_date - timedelta(days=7)

        holdings = Holding.query.filter(Holding.total_quantity > 0).all()

        metrics_map = (
            {
                m.ticker_symbol: m
                for m in StockMetrics.query.filter(
                    StockMetrics.ticker_symbol.in_([h.ticker_symbol for h in holdings])
                ).all()
            }
            if holdings
            else {}
        )

        total_value = sum(float(h.current_value) for h in holdings if h.current_value)

        tickers = [h.ticker_symbol for h in holdings]
        start_prices = WeeklyReviewService._get_prices_for_date(
            tickers, week_start_date
        )
        end_prices = WeeklyReviewService._get_prices_for_date(tickers, week_end_date)

        holdings_perf: List[HoldingWeeklyPerf] = []
        weighted_return_sum = 0.0
        weighted_return_weight = 0.0

        for h in holdings:
            ticker = h.ticker_symbol
            current_val = float(h.current_value) if h.current_value else 0.0
            weight_pct = (current_val / total_value * 100) if total_value > 0 else 0.0
            unrealized_pct = (
                float(h.unrealized_pnl_pct) if h.unrealized_pnl_pct else 0.0
            )

            start_p = start_prices.get(ticker)
            end_p = end_prices.get(ticker)
            week_return: Optional[float] = None
            if start_p and end_p and start_p > 0:
                week_return = (end_p / start_p - 1) * 100
                weighted_return_sum += week_return * weight_pct
                weighted_return_weight += weight_pct

            m = metrics_map.get(ticker)
            pe = float(m.pe_ratio) if m and m.pe_ratio else None
            pb = float(m.pb_ratio) if m and m.pb_ratio else None
            margin = float(m.profit_margin) if m and m.profit_margin else None
            beta = float(m.beta) if m and m.beta else None

            label, reasons = WeeklyReviewService._evaluate_quality(
                ticker, pe, pb, margin, unrealized_pct
            )

            holdings_perf.append(
                HoldingWeeklyPerf(
                    ticker_symbol=ticker,
                    security_name=h.security_name or ticker,
                    currency=h.currency,
                    weight_pct=round(weight_pct, 2),
                    week_return_pct=(
                        round(week_return, 2) if week_return is not None else None
                    ),
                    unrealized_pnl_pct=round(unrealized_pct, 2),
                    pe_ratio=round(pe, 2) if pe is not None else None,
                    pb_ratio=round(pb, 2) if pb is not None else None,
                    profit_margin=round(margin, 4) if margin is not None else None,
                    beta=round(beta, 2) if beta is not None else None,
                    quality_label=label,
                    quality_reasons=reasons,
                )
            )

        holdings_perf.sort(
            key=lambda x: x.week_return_pct if x.week_return_pct is not None else -9999,
            reverse=True,
        )

        portfolio_week_return: Optional[float] = None
        if weighted_return_weight > 0:
            portfolio_week_return = round(
                weighted_return_sum / weighted_return_weight, 2
            )

        benchmarks = WeeklyReviewService._get_benchmark_returns(
            week_start_date, week_end_date
        )

        topix_return = next(
            (b.week_return_pct for b in benchmarks if b.benchmark_key == "TOPIX"), None
        )
        sp500_return = next(
            (b.week_return_pct for b in benchmarks if b.benchmark_key == "SP500"), None
        )

        alpha_topix: Optional[float] = None
        if portfolio_week_return is not None and topix_return is not None:
            alpha_topix = round(portfolio_week_return - topix_return, 2)

        alpha_sp500: Optional[float] = None
        if portfolio_week_return is not None and sp500_return is not None:
            alpha_sp500 = round(portfolio_week_return - sp500_return, 2)

        weekly_realized = float(
            db.session.query(db.func.sum(RealizedPnl.realized_pnl))
            .filter(
                RealizedPnl.sell_date >= week_start_date,
                RealizedPnl.sell_date <= week_end_date,
            )
            .scalar()
            or 0
        )

        weekly_dividend = float(
            db.session.query(db.func.sum(Dividend.total_dividend))
            .filter(
                Dividend.ex_dividend_date >= week_start_date,
                Dividend.ex_dividend_date <= week_end_date,
            )
            .scalar()
            or 0
        )

        good_count = sum(1 for h in holdings_perf if h.quality_label == "Good")
        watch_count = sum(1 for h in holdings_perf if h.quality_label == "Watch")
        review_count = sum(1 for h in holdings_perf if h.quality_label == "要検討")

        return WeeklyReviewResult(
            week_start=week_start_date,
            week_end=week_end_date,
            generated_at=datetime.now(JST).isoformat(),
            total_portfolio_value_jpy=round(total_value, 0),
            portfolio_week_return_pct=portfolio_week_return,
            benchmarks=benchmarks,
            alpha_vs_topix=alpha_topix,
            alpha_vs_sp500=alpha_sp500,
            holdings_perf=holdings_perf,
            weekly_realized_pnl=round(weekly_realized, 0),
            weekly_dividend_income=round(weekly_dividend, 0),
            good_count=good_count,
            watch_count=watch_count,
            review_count=review_count,
        )

    @staticmethod
    def _get_prices_for_date(tickers: List[str], target_date: date) -> dict:
        """StockPrice テーブルから指定日以前の最新価格を一括取得する（7日以内）。"""
        if not tickers:
            return {}
        from_date = target_date - timedelta(days=7)
        rows = (
            StockPrice.query.filter(
                StockPrice.ticker_symbol.in_(tickers),
                StockPrice.price_date >= from_date,
                StockPrice.price_date <= target_date,
            )
            .order_by(StockPrice.ticker_symbol, StockPrice.price_date.desc())
            .all()
        )
        result = {}
        for row in rows:
            if row.ticker_symbol not in result:
                result[row.ticker_symbol] = float(row.close_price)
        return result

    @staticmethod
    def _get_benchmark_returns(
        week_start: date, week_end: date
    ) -> List[BenchmarkWeeklyPerf]:
        """TOPIX / SP500 の週間リターンを計算する。"""
        benchmarks_def = [
            ("TOPIX", "TOPIX"),
            ("SP500", "S&P500"),
        ]
        result = []
        for key, name in benchmarks_def:
            from_date = week_start - timedelta(days=7)
            rows = (
                BenchmarkPrice.query.filter(
                    BenchmarkPrice.benchmark_key == key,
                    BenchmarkPrice.price_date >= from_date,
                    BenchmarkPrice.price_date <= week_end,
                )
                .order_by(BenchmarkPrice.price_date)
                .all()
            )
            start_p: Optional[float] = None
            end_p: Optional[float] = None
            for r in rows:
                if r.price_date <= week_start:
                    start_p = float(r.close_price)
                if r.price_date <= week_end:
                    end_p = float(r.close_price)

            week_return: Optional[float] = None
            if start_p and end_p and start_p > 0:
                week_return = round((end_p / start_p - 1) * 100, 2)

            result.append(
                BenchmarkWeeklyPerf(
                    benchmark_key=key,
                    name=name,
                    week_return_pct=week_return,
                )
            )
        return result

    @staticmethod
    def _evaluate_quality(
        ticker: str,
        pe: Optional[float],
        pb: Optional[float],
        margin: Optional[float],
        unrealized_pct: float,
    ) -> tuple:
        is_jp = ticker.endswith(".T") or ticker.endswith(".KS")
        t = (
            WeeklyReviewService.JP_THRESHOLDS
            if is_jp
            else WeeklyReviewService.US_THRESHOLDS
        )

        score = 0
        reasons = []

        if pe is not None:
            if pe <= t["pe_good"]:
                score += 1
                reasons.append(f"PER={pe:.1f}（割安）")
            elif pe <= t["pe_watch"]:
                reasons.append(f"PER={pe:.1f}（適正）")
            else:
                score -= 1
                reasons.append(f"PER={pe:.1f}（割高）")
        else:
            reasons.append("PER=データなし")

        if pb is not None:
            if pb <= t["pb_good"]:
                score += 1
                reasons.append(f"PBR={pb:.1f}（割安）")
            elif pb <= t["pb_watch"]:
                reasons.append(f"PBR={pb:.1f}（適正）")
            else:
                score -= 1
                reasons.append(f"PBR={pb:.1f}（割高）")
        else:
            reasons.append("PBR=データなし")

        if margin is not None:
            margin_pct = margin * 100
            if margin >= t["margin_good"]:
                score += 1
                reasons.append(f"利益率={margin_pct:.1f}%（良好）")
            elif margin >= t["margin_watch"]:
                reasons.append(f"利益率={margin_pct:.1f}%（普通）")
            else:
                score -= 1
                reasons.append(f"利益率={margin_pct:.1f}%（低い）")
        else:
            reasons.append("利益率=データなし")

        if score >= 2:
            label = "Good"
        elif score <= -1:
            label = "要検討"
        else:
            label = "Watch"

        return label, reasons
