from dataclasses import asdict
from datetime import date

from flask import Blueprint, current_app, jsonify, render_template, request

from app.services.portfolio_advisor_service import PortfolioAdvisorService
from app.services.weekly_review_service import WeeklyReviewService
from app.utils.logger import get_logger

bp = Blueprint("advisor", __name__, url_prefix="/advisor")
logger = get_logger("advisor")


@bp.route("/")
def advisor_page():
    return render_template("advisor.html")


@bp.route("/api/weekly-review")
def get_weekly_review():
    """週次振り返りデータを返す。

    Query params:
        week_end: YYYY-MM-DD（省略時: 今日）
    """
    try:
        week_end_str = request.args.get("week_end")
        week_end = date.fromisoformat(week_end_str) if week_end_str else None
        result = WeeklyReviewService.get_weekly_review(week_end)
        return jsonify({"success": True, "data": _review_to_dict(result)})
    except Exception as e:
        logger.error(f"週次レビューエラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/analyze", methods=["POST"])
def get_advisor():
    """ポートフォリオ入替提案・余剰現金投資提案を返す。

    Request body (JSON):
        cash_jpy: float（省略可能）
    """
    try:
        data = request.get_json(silent=True) or {}
        cash_jpy = data.get("cash_jpy")
        if cash_jpy is not None:
            cash_jpy = float(cash_jpy)

        screener_db_path = current_app.config.get("SCREENER_DB_PATH", "")
        service = PortfolioAdvisorService(screener_db_path)
        result = service.analyze(cash_jpy=cash_jpy)
        return jsonify({"success": True, "data": _advisor_to_dict(result)})
    except Exception as e:
        logger.error(f"アドバイザーエラー: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def _review_to_dict(result) -> dict:
    return {
        "week_start": result.week_start.isoformat(),
        "week_end": result.week_end.isoformat(),
        "generated_at": result.generated_at,
        "total_portfolio_value_jpy": result.total_portfolio_value_jpy,
        "portfolio_week_return_pct": result.portfolio_week_return_pct,
        "alpha_vs_topix": result.alpha_vs_topix,
        "alpha_vs_sp500": result.alpha_vs_sp500,
        "weekly_realized_pnl": result.weekly_realized_pnl,
        "weekly_dividend_income": result.weekly_dividend_income,
        "good_count": result.good_count,
        "watch_count": result.watch_count,
        "review_count": result.review_count,
        "benchmarks": [
            {
                "benchmark_key": b.benchmark_key,
                "name": b.name,
                "week_return_pct": b.week_return_pct,
            }
            for b in result.benchmarks
        ],
        "holdings_perf": [
            {
                "ticker_symbol": h.ticker_symbol,
                "security_name": h.security_name,
                "currency": h.currency,
                "weight_pct": h.weight_pct,
                "week_return_pct": h.week_return_pct,
                "unrealized_pnl_pct": h.unrealized_pnl_pct,
                "pe_ratio": h.pe_ratio,
                "pb_ratio": h.pb_ratio,
                "profit_margin": h.profit_margin,
                "beta": h.beta,
                "quality_label": h.quality_label,
                "quality_reasons": h.quality_reasons,
            }
            for h in result.holdings_perf
        ],
    }


def _advisor_to_dict(result) -> dict:
    return {
        "generated_at": result.generated_at,
        "screener_last_run_at": result.screener_last_run_at,
        "screener_available": result.screener_available,
        "total_portfolio_value_jpy": result.total_portfolio_value_jpy,
        "cash_input_jpy": result.cash_input_jpy,
        "remaining_cash_jpy": result.remaining_cash_jpy,
        "warnings": result.warnings,
        "holding_scores": [
            {
                "ticker_symbol": h.ticker_symbol,
                "security_name": h.security_name,
                "current_value_jpy": h.current_value_jpy,
                "weight_pct": h.weight_pct,
                "unrealized_pnl_pct": h.unrealized_pnl_pct,
                "composite_score": h.composite_score,
                "proxy_score": h.proxy_score,
                "effective_score": h.effective_score,
                "recommendation_grade": h.recommendation_grade,
                "is_etf": h.is_etf,
            }
            for h in result.holding_scores
        ],
        "sell_candidates": [
            {
                "ticker_symbol": s.ticker_symbol,
                "security_name": s.security_name,
                "effective_score": s.effective_score,
                "reason": s.reason,
                "current_value_jpy": s.current_value_jpy,
                "unrealized_pnl_pct": s.unrealized_pnl_pct,
                "tax_consideration": s.tax_consideration,
            }
            for s in result.sell_candidates
        ],
        "buy_candidates": [
            {
                "ticker_symbol": b.ticker_symbol,
                "company_name": b.company_name,
                "recommendation_grade": b.recommendation_grade,
                "composite_score": b.composite_score,
                "entry_price_range": b.entry_price_range,
                "investment_thesis": b.investment_thesis,
                "current_price": b.current_price,
                "preset_name": b.preset_name,
            }
            for b in result.buy_candidates
        ],
        "replacement_proposals": [
            {
                "sell_ticker": p.sell.ticker_symbol,
                "sell_name": p.sell.security_name,
                "sell_score": p.sell.effective_score,
                "sell_value_jpy": p.sell.current_value_jpy,
                "sell_unrealized_pct": p.sell.unrealized_pnl_pct,
                "sell_tax": p.sell.tax_consideration,
                "buy_ticker": p.buy.ticker_symbol,
                "buy_name": p.buy.company_name,
                "buy_grade": p.buy.recommendation_grade,
                "buy_score": p.buy.composite_score,
                "buy_entry_range": p.buy.entry_price_range,
                "buy_thesis": p.buy.investment_thesis,
                "rationale": p.rationale,
                "score_improvement": p.score_improvement,
                "freed_capital": p.estimated_freed_capital,
            }
            for p in result.replacement_proposals
        ],
        "cash_proposals": [
            {
                "ticker_symbol": c.ticker_symbol,
                "company_name": c.company_name,
                "recommendation_grade": c.recommendation_grade,
                "composite_score": c.composite_score,
                "entry_price_range": c.entry_price_range,
                "investment_thesis": c.investment_thesis,
                "current_price": c.current_price,
                "suggested_amount_jpy": c.suggested_amount_jpy,
                "suggested_quantity": c.suggested_quantity,
                "position_pct_after": c.position_pct_after,
                "max_position_warning": c.max_position_warning,
            }
            for c in result.cash_proposals
        ],
    }
