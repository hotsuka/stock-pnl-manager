"""
API endpoints for data operations
"""

from flask import Blueprint, jsonify, request, current_app
from app.services import (
    StockPriceFetcher,
    ExchangeRateFetcher,
    DividendFetcher,
    PerformanceService,
    StockMetricsFetcher,
)
from app.models import Holding, Transaction, Dividend, RealizedPnl
from app.utils.errors import (
    ValidationError,
    NotFoundError,
    DatabaseError,
    ExternalAPIError,
    validate_required_fields,
    validate_positive_number,
    validate_date_format,
)
from app.utils.logger import get_logger, log_api_call

bp = Blueprint("api", __name__, url_prefix="/api")
logger = get_logger("api")


@bp.route("/stock-price/<ticker>", methods=["GET"])
def get_stock_price(ticker):
    """Get current stock price for a ticker"""
    try:
        log_api_call(logger, "/stock-price/<ticker>", "GET", {"ticker": ticker})

        if not ticker:
            raise ValidationError("ティッカーシンボルが指定されていません")

        use_cache = request.args.get("cache", "true").lower() == "true"

        price_data = StockPriceFetcher.get_current_price(ticker, use_cache=use_cache)

        if price_data:
            log_api_call(logger, "/stock-price/<ticker>", "GET", {"ticker": ticker}, response_code=200)
            return jsonify({"success": True, "ticker": ticker, "data": price_data})
        else:
            raise NotFoundError(f"株価データを取得できませんでした: {ticker}")

    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        logger.error(f"株価取得エラー ({ticker}): {str(e)}")
        raise ExternalAPIError(f"株価の取得中にエラーが発生しました: {str(e)}")


@bp.route("/stock-price/update-all", methods=["POST"])
def update_all_stock_prices():
    """Update stock prices for all holdings"""
    try:
        log_api_call(logger, "/stock-price/update-all", "POST")

        results = StockPriceFetcher.update_all_holdings_prices()

        log_api_call(logger, "/stock-price/update-all", "POST", response_code=200)
        logger.info(f"株価一括更新完了: 成功={results['success']}, 失敗={results['failed']}")

        return jsonify({"success": True, "results": results})

    except Exception as e:
        logger.error(f"株価一括更新エラー: {str(e)}")
        raise ExternalAPIError(f"株価の一括更新中にエラーが発生しました: {str(e)}")


@bp.route("/exchange-rate/multiple", methods=["GET"])
def get_multiple_exchange_rates():
    """Get multiple exchange rates at once"""
    # Get currencies from query params or use defaults
    currencies = request.args.get("currencies", "USD,KRW").split(",")
    to_currency = request.args.get("to", "JPY")

    rates = ExchangeRateFetcher.get_multiple_rates(currencies, to_currency)

    return jsonify({"success": True, "rates": rates, "to_currency": to_currency})


@bp.route("/exchange-rate/<from_currency>", methods=["GET"])
def get_exchange_rate(from_currency):
    """Get exchange rate from one currency to another"""
    to_currency = request.args.get("to", "JPY")

    rate_data = ExchangeRateFetcher.get_exchange_rate(from_currency, to_currency)

    if rate_data:
        return jsonify({"success": True, "data": rate_data})
    else:
        return (
            jsonify({"success": False, "error": f"Failed to fetch exchange rate for {from_currency}/{to_currency}"}),
            404,
        )


@bp.route("/exchange-rate/convert", methods=["POST"])
def convert_currency():
    """Convert amount from one currency to another"""
    try:
        log_api_call(logger, "/exchange-rate/convert", "POST")

        data = request.get_json()

        if not data:
            raise ValidationError("リクエストボディが空です")

        # 必須フィールドのバリデーション
        validate_required_fields(data, ["amount", "from"])

        amount = data.get("amount")
        from_currency = data.get("from")
        to_currency = data.get("to", "JPY")

        # 金額のバリデーション
        validate_positive_number(amount, "金額")

        result = ExchangeRateFetcher.convert_amount(amount, from_currency, to_currency)

        if result:
            log_api_call(logger, "/exchange-rate/convert", "POST", response_code=200)
            return jsonify({"success": True, "data": result})
        else:
            raise ExternalAPIError(f"通貨変換に失敗しました: {from_currency} → {to_currency}")

    except (ValidationError, ExternalAPIError):
        raise
    except Exception as e:
        logger.error(f"通貨変換エラー: {str(e)}")
        raise ExternalAPIError(f"通貨変換中にエラーが発生しました: {str(e)}")


@bp.route("/dividends", methods=["GET"])
def get_all_dividends():
    """Get all dividends or filter by ticker"""
    ticker = request.args.get("ticker")

    if ticker:
        dividends = Dividend.query.filter_by(ticker_symbol=ticker).order_by(Dividend.ex_dividend_date.desc()).all()
    else:
        dividends = Dividend.query.order_by(Dividend.ex_dividend_date.desc()).all()

    return jsonify({"success": True, "count": len(dividends), "dividends": [d.to_dict() for d in dividends]})


@bp.route("/dividends/<ticker>", methods=["GET"])
def get_dividends(ticker):
    """Get dividends for a specific ticker"""
    dividends = Dividend.query.filter_by(ticker_symbol=ticker).order_by(Dividend.ex_dividend_date.desc()).all()

    return jsonify(
        {"success": True, "ticker": ticker, "count": len(dividends), "dividends": [d.to_dict() for d in dividends]}
    )


@bp.route("/dividends/fetch/<ticker>", methods=["POST"])
def fetch_dividends(ticker):
    """Fetch and save dividends for a ticker"""
    results = DividendFetcher.save_dividends_to_db(ticker)

    return jsonify({"success": True, "results": results})


@bp.route("/dividends/update-all", methods=["POST"])
def update_all_dividends():
    """Fetch and save dividends for all holdings"""
    try:
        results = DividendFetcher.update_all_holdings_dividends()

        return jsonify(
            {
                "success": True,
                "total_holdings": results["total_holdings"],
                "success": results["success"],
                "failed": results["failed"],
                "details": results["details"],
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/dividends/summary", methods=["GET"])
def get_dividend_summary():
    """Get dividend summary by ticker with yearly breakdown"""
    from decimal import Decimal
    from collections import defaultdict

    # Get all dividends
    dividends = Dividend.query.order_by(Dividend.ticker_symbol, Dividend.ex_dividend_date).all()

    # Group dividends by ticker
    ticker_dividends = defaultdict(list)
    for div in dividends:
        ticker_dividends[div.ticker_symbol].append(div)

    # Get all transactions to get security names and calculate total investment
    transactions = Transaction.query.all()

    # Build ticker info map
    ticker_info = {}
    for t in transactions:
        if t.ticker_symbol not in ticker_info:
            ticker_info[t.ticker_symbol] = {"security_name": t.security_name, "total_investment": Decimal("0")}

        # Calculate total investment (all purchases in JPY)
        if t.transaction_type == "BUY":
            ticker_info[t.ticker_symbol]["total_investment"] += t.settlement_amount

    # Aggregate dividend data
    dividend_summary = []
    total_all_dividends_jpy = Decimal("0")
    yearly_totals_jpy = defaultdict(lambda: Decimal("0"))

    # Get all required exchange rates for dividends
    div_currencies = set(d.currency for d in dividends if d.currency and d.currency not in ["JPY", "日本円"])
    div_rates = ExchangeRateFetcher.get_multiple_rates(list(div_currencies)) if div_currencies else {}

    def div_to_jpy(amount, currency):
        if not amount or not currency:
            return Decimal("0")
        curr = str(currency).strip().upper()
        if curr in ["JPY", "日本円"]:
            return Decimal(str(amount))
        rate_entry = div_rates.get(curr)
        if rate_entry:
            rate = rate_entry.get("rate")
            if rate:
                return Decimal(str(amount)) * Decimal(str(rate))
        return Decimal(str(amount))

    for ticker_symbol, divs in ticker_dividends.items():
        if ticker_symbol not in ticker_info:
            continue

        total_dividends_ticker_jpy = Decimal("0")
        yearly_dividends_ticker_jpy = defaultdict(lambda: Decimal("0"))

        for div in divs:
            div_jpy = div_to_jpy(div.total_dividend, div.currency)
            total_dividends_ticker_jpy += div_jpy

            # Group by year
            year = div.ex_dividend_date.year
            if year <= 2022:
                yearly_dividends_ticker_jpy["2022年以前"] += div_jpy
            else:
                yearly_dividends_ticker_jpy[year] += div_jpy

        # Skip if total dividends is 0
        if total_dividends_ticker_jpy == 0:
            continue

        # Calculate dividend yield (JPY / JPY)
        total_investment = ticker_info[ticker_symbol]["total_investment"]
        dividend_yield = (total_dividends_ticker_jpy / total_investment * 100) if total_investment > 0 else Decimal("0")

        # Add to totals
        total_all_dividends_jpy += total_dividends_ticker_jpy
        for year, amount in yearly_dividends_ticker_jpy.items():
            yearly_totals_jpy[year] += amount

        # Sort years: numeric years descending, then "2022年以前" at the end
        sorted_years = []
        pre_2022_amount = None
        for year, amount in yearly_dividends_ticker_jpy.items():
            if year == "2022年以前":
                pre_2022_amount = ("2022年以前", amount)
            else:
                sorted_years.append((year, amount))

        sorted_years.sort(key=lambda x: x[0], reverse=True)
        if pre_2022_amount:
            sorted_years.append(pre_2022_amount)

        dividend_summary.append(
            {
                "ticker_symbol": ticker_symbol,
                "security_name": ticker_info[ticker_symbol]["security_name"],
                "total_dividends": float(total_dividends_ticker_jpy),
                "total_investment": float(total_investment),
                "dividend_yield": float(dividend_yield),
                "yearly_dividends": {str(year): float(amount) for year, amount in sorted_years},
            }
        )

    # Sort by ticker symbol
    dividend_summary.sort(key=lambda x: x["ticker_symbol"])

    # Calculate overall dividend yield
    total_investment_all = sum(ticker_info[ticker]["total_investment"] for ticker in ticker_info.keys())
    overall_dividend_yield = (
        (total_all_dividends_jpy / total_investment_all * 100) if total_investment_all > 0 else Decimal("0")
    )

    # Sort yearly totals: numeric years descending, then "2022年以前" at the end
    sorted_yearly_totals = []
    pre_2022_total = None
    for year, amount in yearly_totals_jpy.items():
        if year == "2022年以前":
            pre_2022_total = ("2022年以前", amount)
        else:
            sorted_yearly_totals.append((year, amount))

    sorted_yearly_totals.sort(key=lambda x: x[0], reverse=True)
    if pre_2022_total:
        sorted_yearly_totals.append(pre_2022_total)

    return jsonify(
        {
            "success": True,
            "dividends": dividend_summary,
            "totals": {
                "total_dividends": float(total_all_dividends_jpy),
                "total_investment": float(total_investment_all),
                "dividend_yield": float(overall_dividend_yield),
                "yearly_totals": {str(year): float(amount) for year, amount in sorted_yearly_totals},
            },
        }
    )


@bp.route("/holdings", methods=["GET"])
def get_holdings():
    """Get all holdings"""
    holdings = Holding.query.all()

    return jsonify({"success": True, "count": len(holdings), "holdings": [h.to_dict() for h in holdings]})


@bp.route("/holdings/irr", methods=["GET"])
def get_holdings_irr():
    """Get IRR (Internal Rate of Return) for all holdings"""
    from app.services.performance_service import PerformanceService

    try:
        results = PerformanceService.calculate_irr_for_all_holdings()

        return jsonify({"success": True, "irr_data": results})
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/holdings/<ticker>/irr", methods=["GET"])
def get_holding_irr(ticker):
    """Get IRR for a specific holding"""
    from app.services.performance_service import PerformanceService

    try:
        result = PerformanceService.calculate_irr_for_holding(ticker)

        return jsonify(
            {
                "success": True,
                "ticker": ticker,
                "irr": result["irr"],
                "cash_flows": [
                    {
                        "date": cf["date"].isoformat() if hasattr(cf["date"], "isoformat") else str(cf["date"]),
                        "amount": cf["amount"],
                        "type": cf["type"],
                    }
                    for cf in result["cash_flows"]
                ],
                "error": result["error"],
            }
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/holdings/<ticker>", methods=["GET"])
def get_holding(ticker):
    """Get specific holding details"""
    try:
        log_api_call(logger, "/holdings/<ticker>", "GET", {"ticker": ticker})

        holding = Holding.query.filter_by(ticker_symbol=ticker).first()

        if not holding:
            raise NotFoundError(f"保有銘柄が見つかりません: {ticker}")

        log_api_call(logger, "/holdings/<ticker>", "GET", response_code=200)
        return jsonify({"success": True, "holding": holding.to_dict()})

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"保有銘柄取得エラー ({ticker}): {str(e)}")
        raise DatabaseError(f"保有銘柄の取得に失敗しました: {str(e)}")


@bp.route("/holdings/<ticker>", methods=["DELETE"])
def delete_holding(ticker):
    """Delete a holding and all associated transactions"""
    from app import db

    holding = Holding.query.filter_by(ticker_symbol=ticker).first()

    if not holding:
        return jsonify({"success": False, "error": f"保有銘柄が見つかりません: {ticker}"}), 404

    try:
        # Delete all associated transactions
        transactions = Transaction.query.filter_by(ticker_symbol=ticker).all()
        for transaction in transactions:
            db.session.delete(transaction)

        # Delete all associated dividends
        dividends = Dividend.query.filter_by(ticker_symbol=ticker).all()
        for dividend in dividends:
            db.session.delete(dividend)

        # Delete all associated realized P&L records
        realized_pnl_records = RealizedPnl.query.filter_by(ticker_symbol=ticker).all()
        for record in realized_pnl_records:
            db.session.delete(record)

        # Delete the holding
        db.session.delete(holding)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"{ticker} の保有銘柄と関連データを削除しました",
                "deleted": {
                    "ticker": ticker,
                    "transactions": len(transactions),
                    "dividends": len(dividends),
                    "realized_pnl": len(realized_pnl_records),
                },
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"削除に失敗しました: {str(e)}"}), 500


@bp.route("/transactions", methods=["GET"])
def get_transactions():
    """Get all transactions"""
    ticker = request.args.get("ticker")
    limit = request.args.get("limit", type=int)

    query = Transaction.query

    if ticker:
        query = query.filter_by(ticker_symbol=ticker)

    query = query.order_by(Transaction.transaction_date.desc())

    # Get total count before applying limit
    total_count = query.count()

    if limit:
        query = query.limit(limit)

    transactions = query.all()

    return jsonify(
        {
            "success": True,
            "count": len(transactions),
            "total_count": total_count,
            "transactions": [t.to_dict() for t in transactions],
        }
    )


@bp.route("/transactions/<int:transaction_id>", methods=["GET"])
def get_transaction(transaction_id):
    """Get a single transaction by ID"""
    transaction = Transaction.query.get(transaction_id)

    if not transaction:
        return jsonify({"success": False, "error": "取引が見つかりません"}), 404

    return jsonify({"success": True, "transaction": transaction.to_dict()})


@bp.route("/transactions/<int:transaction_id>", methods=["PUT"])
def update_transaction(transaction_id):
    """Update a transaction"""
    from app import db
    from app.services import TransactionService

    try:
        log_api_call(logger, f"/transactions/{transaction_id}", "PUT")

        transaction = Transaction.query.get(transaction_id)

        if not transaction:
            raise NotFoundError(f"取引が見つかりません (ID: {transaction_id})")

        data = request.get_json()

        if not data:
            raise ValidationError("更新データが指定されていません")

        # 更新前のティッカーを保存（再計算用）
        old_ticker = transaction.ticker_symbol

        # 更新可能なフィールド
        if "transaction_date" in data:
            transaction.transaction_date = validate_date_format(data["transaction_date"], "取引日")

        if "ticker_symbol" in data:
            if not data["ticker_symbol"]:
                raise ValidationError("ティッカーシンボルは必須です")
            transaction.ticker_symbol = data["ticker_symbol"]

        if "security_name" in data:
            transaction.security_name = data["security_name"]

        if "transaction_type" in data:
            from app.utils.errors import validate_transaction_type

            validate_transaction_type(data["transaction_type"])
            transaction.transaction_type = data["transaction_type"]

        if "quantity" in data:
            validate_positive_number(data["quantity"], "数量")
            transaction.quantity = float(data["quantity"])

        if "unit_price" in data:
            validate_positive_number(data["unit_price"], "単価")
            transaction.unit_price = float(data["unit_price"])

        if "commission" in data:
            if data["commission"] < 0:
                raise ValidationError("手数料は0以上である必要があります")
            transaction.commission = float(data["commission"])

        if "settlement_amount" in data:
            validate_positive_number(data["settlement_amount"], "受渡金額")
            transaction.settlement_amount = float(data["settlement_amount"])

        if "currency" in data:
            from app.utils.errors import validate_currency

            validate_currency(data["currency"])
            transaction.currency = data["currency"]

        db.session.commit()
        logger.info(f"取引更新完了 (ID: {transaction_id})")

        # 影響を受けた銘柄の再計算
        affected_tickers = {old_ticker, transaction.ticker_symbol}
        for ticker in affected_tickers:
            TransactionService.recalculate_holding(ticker)

        log_api_call(logger, f"/transactions/{transaction_id}", "PUT", response_code=200)

        return jsonify(
            {
                "success": True,
                "message": "取引を更新しました",
                "transaction": transaction.to_dict(),
                "affected_tickers": list(affected_tickers),
            }
        )

    except (ValidationError, NotFoundError):
        db.session.rollback()
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f"取引更新エラー (ID: {transaction_id}): {str(e)}")
        raise DatabaseError(f"取引の更新に失敗しました: {str(e)}")


@bp.route("/transactions/manual", methods=["POST"])
def create_manual_transaction():
    """個別入力による取引の登録"""
    from app.services import TransactionService
    from datetime import datetime

    try:
        log_api_call(logger, "/transactions/manual", "POST")

        data = request.get_json()
        if not data:
            raise ValidationError("リクエストボディが空です")

        # 必須フィールドのバリデーション
        validate_required_fields(
            data,
            ["transaction_date", "transaction_type", "ticker_symbol", "quantity", "unit_price", "settlement_amount"],
        )

        # 取引種別のバリデーション
        if data["transaction_type"] not in ["BUY", "SELL"]:
            raise ValidationError("取引種別は'BUY'または'SELL'である必要があります")

        # 数値のバリデーション
        validate_positive_number(data["quantity"], "数量")
        validate_positive_number(data["unit_price"], "単価")
        validate_positive_number(data["settlement_amount"], "受渡金額")

        # 日付の解析
        transaction_date = validate_date_format(data["transaction_date"], "取引日")

        # ティッカーシンボルの正規化
        ticker = data["ticker_symbol"].upper().strip()
        # 数字のみの場合は日本株として.Tを付ける
        if ticker.isdigit():
            ticker = f"{ticker}.T"

        # 通貨の推定（指定がない場合）
        currency = data.get("currency", "JPY")
        if not currency:
            if ticker.endswith(".T"):
                currency = "JPY"
            elif ticker.endswith(".KS") or ticker.endswith(".KQ"):
                currency = "KRW"
            elif ticker.endswith(".HK"):
                currency = "HKD"
            elif ticker.endswith(".L"):
                currency = "GBP"
            else:
                currency = "USD"

        # 取引データを構築（Decimal型を使用してDB型と一致させる）
        from decimal import Decimal

        transaction_data = {
            "transaction_date": transaction_date,
            "ticker_symbol": ticker,
            "security_name": data.get("security_name"),
            "transaction_type": data["transaction_type"],
            "quantity": Decimal(str(data["quantity"])),
            "unit_price": Decimal(str(data["unit_price"])),
            "currency": currency,
            "commission": Decimal(str(data.get("commission", 0))),
            "exchange_rate": Decimal(str(data["exchange_rate"])) if data.get("exchange_rate") else None,
            "settlement_amount": Decimal(str(data["settlement_amount"])),
            "settlement_currency": "JPY",
        }

        # 保存
        result = TransactionService.save_transactions([transaction_data])

        if result["success"] > 0:
            log_api_call(logger, "/transactions/manual", "POST", response_code=201)
            # レスポンス用にDecimalとdateを変換
            response_data = {
                "transaction_date": transaction_date.isoformat(),
                "ticker_symbol": ticker,
                "security_name": data.get("security_name"),
                "transaction_type": data["transaction_type"],
                "quantity": float(data["quantity"]),
                "unit_price": float(data["unit_price"]),
                "currency": currency,
                "commission": float(data.get("commission", 0)),
                "settlement_amount": float(data["settlement_amount"]),
            }
            return jsonify({"success": True, "message": "取引を登録しました", "transaction": response_data}), 201
        else:
            error_msg = result["errors"][0]["error"] if result["errors"] else "取引の登録に失敗しました"
            raise ValidationError(error_msg)

    except (ValidationError, NotFoundError):
        raise
    except Exception as e:
        logger.error(f"取引登録エラー: {str(e)}")
        raise DatabaseError(f"取引の登録に失敗しました: {str(e)}")


@bp.route("/transactions/delete", methods=["POST"])
def delete_transactions():
    """Delete multiple transactions by IDs"""
    from app import db
    from app.services import TransactionService

    data = request.get_json()
    transaction_ids = data.get("transaction_ids", [])

    if not transaction_ids:
        return jsonify({"success": False, "error": "削除する取引が選択されていません"}), 400

    try:
        deleted_count = 0
        affected_tickers = set()

        for transaction_id in transaction_ids:
            transaction = Transaction.query.get(transaction_id)
            if transaction:
                affected_tickers.add(transaction.ticker_symbol)
                db.session.delete(transaction)
                deleted_count += 1

        db.session.commit()

        # Recalculate holdings for affected tickers
        for ticker in affected_tickers:
            TransactionService.recalculate_holding(ticker)

        return jsonify(
            {
                "success": True,
                "message": f"{deleted_count}件の取引を削除しました",
                "deleted_count": deleted_count,
                "affected_tickers": list(affected_tickers),
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"削除に失敗しました: {str(e)}"}), 500


@bp.route("/realized-pnl/irr", methods=["GET"])
def get_realized_pnl_irr():
    """Get IRR (Internal Rate of Return) for all realized positions"""
    from app.services.performance_service import PerformanceService

    try:
        results = PerformanceService.calculate_irr_for_all_realized()

        return jsonify({"success": True, "irr_data": results})
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/realized-pnl/<ticker>/irr", methods=["GET"])
def get_realized_pnl_ticker_irr(ticker):
    """Get IRR for a specific realized position"""
    from app.services.performance_service import PerformanceService

    try:
        result = PerformanceService.calculate_irr_for_realized(ticker)

        return jsonify(
            {
                "success": True,
                "ticker": ticker,
                "irr": result["irr"],
                "cash_flows": [
                    {
                        "date": cf["date"].isoformat() if hasattr(cf["date"], "isoformat") else str(cf["date"]),
                        "amount": cf["amount"],
                        "type": cf["type"],
                    }
                    for cf in result["cash_flows"]
                ],
                "error": result["error"],
            }
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/realized-pnl", methods=["GET"])
def get_realized_pnl():
    """Get all realized P&L records grouped by ticker"""
    from sqlalchemy import func
    from app import db
    from decimal import Decimal

    # Get all realized P&L records with all details
    realized_records = RealizedPnl.query.all()

    # Group by ticker
    ticker_data = {}
    for record in realized_records:
        ticker = record.ticker_symbol
        if ticker not in ticker_data:
            ticker_data[ticker] = {"ticker_symbol": ticker, "currency": record.currency, "records": []}
        ticker_data[ticker]["records"].append(record)

    realized_pnl_list = []
    for ticker, data in ticker_data.items():
        # Get security name from transaction
        transaction = Transaction.query.filter_by(ticker_symbol=ticker).first()
        security_name = transaction.security_name if transaction else None

        # Determine correct currency based on ticker symbol
        if ticker.endswith(".T"):
            currency = "JPY"
        elif ticker.endswith(".KS"):
            currency = "KRW"
        else:
            currency = "USD"

        # Get all SELL transactions for this ticker (from realized_pnl records)
        realized_pnl_records = data["records"]

        # Calculate total quantity sold
        total_quantity = sum(float(r.quantity) for r in realized_pnl_records)

        # Calculate total cost from RealizedPnl records
        # Note: RealizedPnl.average_cost might be in JPY (incorrect), need to handle this
        total_cost_from_records = sum(float(r.average_cost) * float(r.quantity) for r in realized_pnl_records)
        total_proceeds_stock_currency = sum(float(r.sell_price) * float(r.quantity) for r in realized_pnl_records)

        # Get SELL transactions to get settlement amounts (in JPY)
        sell_transactions = Transaction.query.filter_by(ticker_symbol=ticker, transaction_type="SELL").all()

        # Calculate sale proceeds in JPY from settlement amounts
        # Note: settlement_amount is always in JPY regardless of settlement_currency value
        total_sale_proceeds_jpy = sum(float(tx.settlement_amount) for tx in sell_transactions if tx.settlement_amount)

        # For cost, we need to calculate from the RealizedPnl data
        # The RealizedPnl.average_cost is in JPY for all stocks (due to old data)
        # We need to convert to the correct currency for non-JPY stocks
        if currency == "USD":
            # For US stocks, calculate implied exchange rate from sell transactions
            # settlement_amount (JPY) / (quantity * sell_price (USD)) = exchange rate
            total_exchange_rate = 0
            total_sell_qty = 0
            for tx in sell_transactions:
                if tx.settlement_amount and tx.unit_price:
                    qty = float(tx.quantity)
                    usd_amount = qty * float(tx.unit_price)
                    if usd_amount > 0:
                        implicit_rate = float(tx.settlement_amount) / usd_amount
                        total_exchange_rate += implicit_rate * qty
                        total_sell_qty += qty

            avg_exchange_rate = total_exchange_rate / total_sell_qty if total_sell_qty > 0 else 150

            # total_cost_from_records is in JPY, convert to USD
            total_cost_usd = total_cost_from_records / avg_exchange_rate

            # Convert back to JPY for total_cost display
            total_cost_jpy = total_cost_from_records

            # Average unit price in USD
            average_unit_price = total_cost_usd / total_quantity if total_quantity > 0 else 0
        elif currency == "KRW":
            # For Korean stocks, similar logic
            total_exchange_rate = 0
            total_sell_qty = 0
            for tx in sell_transactions:
                if tx.settlement_amount and tx.unit_price:
                    qty = float(tx.quantity)
                    krw_amount = qty * float(tx.unit_price)
                    if krw_amount > 0:
                        implicit_rate = float(tx.settlement_amount) / krw_amount
                        total_exchange_rate += implicit_rate * qty
                        total_sell_qty += qty

            avg_exchange_rate = total_exchange_rate / total_sell_qty if total_sell_qty > 0 else 0.1

            # total_cost_from_records is in JPY, convert to KRW
            total_cost_krw = total_cost_from_records / avg_exchange_rate

            # Keep JPY for total_cost display
            total_cost_jpy = total_cost_from_records

            # Average unit price in KRW
            average_unit_price = total_cost_krw / total_quantity if total_quantity > 0 else 0
        else:
            # For JPY stocks, cost is already in JPY
            total_cost_jpy = total_cost_from_records
            average_unit_price = total_cost_jpy / total_quantity if total_quantity > 0 else 0

        # Calculate sale unit price in stock's currency
        if currency == "USD":
            # For USD stocks, calculate from JPY sale proceeds
            sale_unit_price = (
                (total_sale_proceeds_jpy / avg_exchange_rate) / total_quantity if total_quantity > 0 else 0
            )
        elif currency == "KRW":
            # For KRW stocks, calculate from JPY sale proceeds
            sale_unit_price = (
                (total_sale_proceeds_jpy / avg_exchange_rate) / total_quantity if total_quantity > 0 else 0
            )
        else:
            # For JPY stocks, calculate directly
            sale_unit_price = total_sale_proceeds_jpy / total_quantity if total_quantity > 0 else 0

        # Calculate realized P&L in JPY
        realized_pnl_jpy = total_sale_proceeds_jpy - total_cost_jpy

        # Calculate P&L percentage
        pnl_pct = (realized_pnl_jpy / total_cost_jpy * 100) if total_cost_jpy > 0 else 0

        realized_pnl_list.append(
            {
                "ticker_symbol": ticker,
                "security_name": security_name,
                "total_quantity": total_quantity,
                "average_cost": average_unit_price,
                "sale_unit_price": sale_unit_price,
                "total_cost": total_cost_jpy,
                "sale_proceeds": total_sale_proceeds_jpy,
                "realized_pnl": realized_pnl_jpy,
                "realized_pnl_pct": pnl_pct,
                "currency": currency,
            }
        )

    return jsonify({"success": True, "count": len(realized_pnl_list), "realized_pnl": realized_pnl_list})


@bp.route("/dashboard/summary", methods=["GET"])
def get_dashboard_summary():
    """Get dashboard summary data with detailed breakdown"""
    from sqlalchemy import func

    # Get data
    holdings = Holding.query.filter(Holding.total_quantity > 0).all()
    realized_records = RealizedPnl.query.all()
    dividends = Dividend.query.all()

    # Get required exchange rates for market value
    currencies = set(h.currency for h in holdings if h.currency and h.currency not in ["JPY", "日本円"])
    rates = ExchangeRateFetcher.get_multiple_rates(list(currencies)) if currencies else {}

    def to_jpy(amount, currency):
        if not amount or not currency:
            return 0.0
        curr = str(currency).strip().upper()
        if curr in ["JPY", "日本円"]:
            return float(amount)

        rate_entry = rates.get(curr)
        if rate_entry:
            rate = rate_entry.get("rate")
            if rate:
                return float(amount) * float(rate)
        return float(amount)

    # 1. 投資実績銘柄数
    holding_tickers = {h.ticker_symbol for h in holdings}
    sold_tickers = {r.ticker_symbol for r in realized_records}
    total_tickers_count = len(holding_tickers | sold_tickers)
    active_tickers_count = len(holding_tickers)
    realized_only_count = len(sold_tickers - holding_tickers)

    # 2. 総投資額
    holdings_cost_jpy = sum(float(h.total_cost or 0) for h in holdings)
    realized_cost_jpy = sum(float(r.average_cost or 0) * float(r.quantity or 0) for r in realized_records)
    total_investment_jpy = holdings_cost_jpy + realized_cost_jpy

    # 3. 総評価額
    holdings_value_jpy = sum(float(h.current_value or 0) for h in holdings)  # current_value is already in JPY
    # 売却額 = 確定損益 + 取得コスト (既に JPY)
    realized_proceeds_jpy = sum(
        float(r.realized_pnl or 0) + (float(r.average_cost or 0) * float(r.quantity or 0)) for r in realized_records
    )

    # 配当の合計 (各レコードを円換算)
    total_dividends_jpy = 0.0
    for d in dividends:
        # total_dividend は現地通貨建ての場合があるため、取引時のレートまたは最新レートで換算が必要
        # ここでは簡易的に現在のレートを使用（または本来は配当時レートを保持すべきだが、現状のスキーマに合わせて対応）
        total_dividends_jpy += to_jpy(d.total_dividend, d.currency)

    total_evaluation_jpy = holdings_value_jpy + realized_proceeds_jpy + total_dividends_jpy

    # 4. 総合損益
    total_pnl_jpy = total_evaluation_jpy - total_investment_jpy
    total_pnl_pct = (total_pnl_jpy / total_investment_jpy * 100) if total_investment_jpy > 0 else 0

    return jsonify(
        {
            "success": True,
            "summary": {
                "ticker_counts": {
                    "total": total_tickers_count,
                    "active": active_tickers_count,
                    "realized": realized_only_count,
                },
                "investment": {
                    "total": total_investment_jpy,
                    "holdings": holdings_cost_jpy,
                    "realized": realized_cost_jpy,
                },
                "evaluation": {
                    "total": total_evaluation_jpy,
                    "holdings": holdings_value_jpy,
                    "realized": realized_proceeds_jpy,
                    "dividends": total_dividends_jpy,
                },
                "total_pnl": {"amount": total_pnl_jpy, "percentage": round(total_pnl_pct, 2)},
                "currency": "JPY",
            },
        }
    )


@bp.route("/dashboard/portfolio-composition", methods=["GET"])
def get_portfolio_composition():
    """Get portfolio composition data for pie chart"""
    holdings = Holding.query.all()

    # Get required exchange rates for conversion
    currencies = set(h.currency for h in holdings if h.currency and h.currency not in ["JPY", "日本円"])
    rates = ExchangeRateFetcher.get_multiple_rates(list(currencies)) if currencies else {}

    def to_jpy(amount, currency):
        if not amount or not currency:
            return 0.0
        curr = str(currency).strip().upper()
        if curr in ["JPY", "日本円"]:
            return float(amount)

        rate_entry = rates.get(curr)
        if rate_entry:
            rate = rate_entry.get("rate")
            if rate:
                return float(amount) * float(rate)
        return float(amount)

    composition_data = []
    for holding in holdings:
        value_jpy = to_jpy(holding.current_value, holding.currency)
        if value_jpy > 0:
            composition_data.append(
                {
                    "ticker": holding.ticker_symbol,
                    "name": holding.security_name or holding.ticker_symbol,
                    "value": value_jpy,
                    "percentage": 0,  # Will be calculated on frontend
                }
            )

    return jsonify({"success": True, "data": composition_data})


@bp.route("/dashboard/pnl-history", methods=["GET"])
def get_pnl_history():
    """Get P&L history data for trend chart"""
    from datetime import datetime, timedelta
    from sqlalchemy import func

    period = request.args.get("period", "30d")  # 30d, 1y, all

    # Get all transactions ordered by date
    transactions = Transaction.query.order_by(Transaction.transaction_date).all()

    if not transactions:
        return jsonify({"success": True, "data": []})

    # Calculate date range
    end_date = datetime.now().date()
    if period == "30d":
        start_date = end_date - timedelta(days=30)
    elif period == "1y":
        start_date = end_date - timedelta(days=365)
    else:  # 'all'
        start_date = transactions[0].transaction_date

    # Get realized P&L within date range
    realized_records = (
        RealizedPnl.query.filter(RealizedPnl.sell_date >= start_date, RealizedPnl.sell_date <= end_date)
        .order_by(RealizedPnl.sell_date)
        .all()
    )

    # Build daily P&L data
    pnl_history = []
    current_date = start_date

    while current_date <= end_date:
        # Calculate cumulative realized P&L up to this date
        cumulative_realized = sum(float(r.realized_pnl or 0) for r in realized_records if r.sell_date <= current_date)

        pnl_history.append(
            {
                "date": current_date.isoformat(),
                "pnl": cumulative_realized,  # Simplified - only showing realized P&L for now
            }
        )

        current_date += timedelta(days=1)

    return jsonify({"success": True, "data": pnl_history})


@bp.route("/performance/history", methods=["GET"])
def get_performance_history():
    """Get investment performance history (daily or monthly) with optional benchmark comparison"""
    try:
        period = request.args.get("period", "1m")  # '1m' for daily, '1y' for monthly
        include_benchmarks = request.args.get("benchmarks", "true").lower() == "true"
        benchmark_keys = request.args.getlist("benchmark_keys") or ["TOPIX", "SP500"]

        if include_benchmarks:
            # ベンチマーク比較データを含む損益推移を取得
            if period == "1y":
                # 1年の場合は月次データを返す
                portfolio_data = PerformanceService.get_monthly_performance_history()
                # ベンチマークは日次で取得
                data = PerformanceService.get_performance_history_with_benchmark(
                    days=365, benchmark_keys=benchmark_keys
                )
                # ポートフォリオデータを月次に置き換え
                data["portfolio"] = portfolio_data

                # ベンチマークデータを月末のみにフィルタリング
                from collections import defaultdict

                for benchmark_key in data["benchmarks"]:
                    daily_benchmark = data["benchmarks"][benchmark_key]
                    monthly_benchmark = defaultdict(lambda: None)

                    # 各月の最終日データを抽出
                    for entry in daily_benchmark:
                        month_key = entry["date"][:7]  # YYYY-MM
                        if monthly_benchmark[month_key] is None or entry["date"] > monthly_benchmark[month_key]["date"]:
                            monthly_benchmark[month_key] = entry.copy()
                            # 月次データに合わせて日付をYYYY-MM形式に変更
                            monthly_benchmark[month_key]["date"] = month_key

                    # 月順にソートして配列に変換
                    sorted_months = sorted(monthly_benchmark.keys())
                    data["benchmarks"][benchmark_key] = [monthly_benchmark[m] for m in sorted_months]
            else:
                # 1か月の場合は日次データ
                data = PerformanceService.get_performance_history_with_benchmark(days=30, benchmark_keys=benchmark_keys)
        else:
            # 既存の処理（ベンチマークなし）
            if period == "1y":
                portfolio_data = PerformanceService.get_monthly_performance_history()
            else:
                portfolio_data = PerformanceService.get_performance_history(days=30)

            data = {"portfolio": portfolio_data, "benchmarks": {}}

        return jsonify({"success": True, "period": period, "data": data})
    except Exception as e:
        import traceback

        error_detail = traceback.format_exc()
        print(f"ERROR in get_performance_history: {error_detail}")
        return jsonify({"success": False, "error": str(e), "detail": error_detail}), 500


@bp.route("/performance/detail", methods=["GET"])
def get_performance_detail():
    """Get detailed breakdown for a specific date"""
    date = request.args.get("date")

    if not date:
        return jsonify({"success": False, "error": "Date parameter is required"}), 400

    try:
        details = PerformanceService.get_daily_detail(date)

        return jsonify({"success": True, "date": date, "details": details})
    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        print(f"Error in get_daily_detail: {error_details}")
        return jsonify({"success": False, "error": str(e), "traceback": error_details}), 500


@bp.route("/dashboard/yearly-stats", methods=["GET"])
def get_yearly_stats():
    """Get yearly investment performance stats"""
    from collections import defaultdict

    # Yearly Realized PnL stats from RealizedPnl records
    realized_records = RealizedPnl.query.all()

    stats = defaultdict(lambda: {"total_cost": 0.0, "total_proceeds": 0.0, "realized_pnl": 0.0})

    for r in realized_records:
        if not r.sell_date:
            continue

        year = r.sell_date.year
        cost = float(r.average_cost or 0) * float(r.quantity or 0)
        pnl = float(r.realized_pnl or 0)
        proceeds = cost + pnl

        stats[year]["total_cost"] += cost
        stats[year]["total_proceeds"] += proceeds
        stats[year]["realized_pnl"] += pnl

    years = sorted(stats.keys(), reverse=True)

    response_data = []
    total_all = {"year": "合計", "total_cost": 0.0, "total_proceeds": 0.0, "realized_pnl": 0.0, "pnl_pct": 0.0}

    for year in years:
        s = stats[year]
        pnl_pct = (s["realized_pnl"] / s["total_cost"] * 100) if s["total_cost"] > 0 else 0

        item = {
            "year": str(year),
            "total_cost": s["total_cost"],
            "total_proceeds": s["total_proceeds"],
            "realized_pnl": s["realized_pnl"],
            "pnl_pct": round(pnl_pct, 2),
        }
        response_data.append(item)

        total_all["total_cost"] += s["total_cost"]
        total_all["total_proceeds"] += s["total_proceeds"]
        total_all["realized_pnl"] += s["realized_pnl"]

    if total_all["total_cost"] > 0:
        total_all["pnl_pct"] = round((total_all["realized_pnl"] / total_all["total_cost"] * 100), 2)

    return jsonify({"success": True, "yearly_stats": response_data, "total": total_all})


@bp.route("/holdings/metrics", methods=["GET"])
def get_holdings_metrics():
    """全保有銘柄の評価指標を取得"""
    try:
        log_api_call(logger, "/holdings/metrics", "GET")

        holdings = Holding.query.all()
        ticker_symbols = [h.ticker_symbol for h in holdings]

        if not ticker_symbols:
            return jsonify({"success": True, "count": 0, "metrics": []})

        metrics_dict = StockMetricsFetcher.get_multiple_metrics(ticker_symbols, use_cache=True)

        log_api_call(logger, "/holdings/metrics", "GET", response_code=200)
        logger.info(f"評価指標取得完了: {len(metrics_dict)}/{len(ticker_symbols)}件")

        return jsonify({"success": True, "count": len(metrics_dict), "metrics": list(metrics_dict.values())})

    except Exception as e:
        logger.error(f"評価指標取得エラー: {str(e)}")
        raise ExternalAPIError(f"評価指標の取得中にエラーが発生しました: {str(e)}")


@bp.route("/stock-metrics/update-all", methods=["POST"])
def update_all_stock_metrics():
    """全保有銘柄の評価指標を更新"""
    try:
        log_api_call(logger, "/stock-metrics/update-all", "POST")

        results = StockMetricsFetcher.update_all_holdings_metrics()

        log_api_call(logger, "/stock-metrics/update-all", "POST", response_code=200)
        logger.info(f"評価指標一括更新完了: 成功={results['success']}, 失敗={results['failed']}")

        return jsonify({"success": True, "results": results})

    except Exception as e:
        logger.error(f"評価指標一括更新エラー: {str(e)}")
        raise ExternalAPIError(f"評価指標の一括更新中にエラーが発生しました: {str(e)}")


@bp.route("/health", methods=["GET"])
def health_check():
    """ヘルスチェックエンドポイント"""
    from datetime import datetime
    from app import db
    from sqlalchemy import text

    health_status = {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "version": "1.0.0", "checks": {}}

    # データベース接続チェック
    try:
        db.session.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {"status": "healthy", "message": "Database connection successful"}
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}",
        }

    # レコード数チェック
    try:
        transaction_count = Transaction.query.count()
        holding_count = Holding.query.count()
        health_status["checks"]["data"] = {
            "status": "healthy",
            "transactions": transaction_count,
            "holdings": holding_count,
        }
    except Exception as e:
        health_status["checks"]["data"] = {"status": "warning", "message": f"Failed to get record counts: {str(e)}"}

    # アプリケーション稼働時間
    try:
        import os

        if os.name == "posix":
            import subprocess

            uptime_output = subprocess.check_output(["uptime", "-p"]).decode("utf-8").strip()
            health_status["checks"]["uptime"] = {"status": "info", "message": uptime_output}
    except:
        pass  # Windows or uptime not available

    # HTTPステータスコード
    status_code = 200 if health_status["status"] == "healthy" else 503

    return jsonify(health_status), status_code
