"""
API endpoints for data operations
"""

from flask import Blueprint, jsonify, request
from app.services import StockPriceFetcher, ExchangeRateFetcher, DividendFetcher
from app.models import Holding, Transaction, Dividend, RealizedPnl

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/stock-price/<ticker>', methods=['GET'])
def get_stock_price(ticker):
    """Get current stock price for a ticker"""
    use_cache = request.args.get('cache', 'true').lower() == 'true'

    price_data = StockPriceFetcher.get_current_price(ticker, use_cache=use_cache)

    if price_data:
        return jsonify({
            'success': True,
            'ticker': ticker,
            'data': price_data
        })
    else:
        return jsonify({
            'success': False,
            'ticker': ticker,
            'error': 'Failed to fetch stock price'
        }), 404


@bp.route('/stock-price/update-all', methods=['POST'])
def update_all_stock_prices():
    """Update stock prices for all holdings"""
    results = StockPriceFetcher.update_all_holdings_prices()

    return jsonify({
        'success': True,
        'results': results
    })


@bp.route('/exchange-rate/multiple', methods=['GET'])
def get_multiple_exchange_rates():
    """Get multiple exchange rates at once"""
    # Get currencies from query params or use defaults
    currencies = request.args.get('currencies', 'USD,KRW').split(',')
    to_currency = request.args.get('to', 'JPY')

    rates = ExchangeRateFetcher.get_multiple_rates(currencies, to_currency)

    return jsonify({
        'success': True,
        'rates': rates,
        'to_currency': to_currency
    })


@bp.route('/exchange-rate/<from_currency>', methods=['GET'])
def get_exchange_rate(from_currency):
    """Get exchange rate from one currency to another"""
    to_currency = request.args.get('to', 'JPY')

    rate_data = ExchangeRateFetcher.get_exchange_rate(from_currency, to_currency)

    if rate_data:
        return jsonify({
            'success': True,
            'data': rate_data
        })
    else:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch exchange rate for {from_currency}/{to_currency}'
        }), 404


@bp.route('/exchange-rate/convert', methods=['POST'])
def convert_currency():
    """Convert amount from one currency to another"""
    data = request.get_json()

    amount = data.get('amount')
    from_currency = data.get('from')
    to_currency = data.get('to', 'JPY')

    if not amount or not from_currency:
        return jsonify({
            'success': False,
            'error': 'Missing required parameters: amount, from'
        }), 400

    result = ExchangeRateFetcher.convert_amount(amount, from_currency, to_currency)

    if result:
        return jsonify({
            'success': True,
            'data': result
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to convert currency'
        }), 500


@bp.route('/dividends/<ticker>', methods=['GET'])
def get_dividends(ticker):
    """Get dividends for a specific ticker"""
    dividends = Dividend.query.filter_by(ticker_symbol=ticker).order_by(
        Dividend.ex_dividend_date.desc()
    ).all()

    return jsonify({
        'success': True,
        'ticker': ticker,
        'count': len(dividends),
        'dividends': [d.to_dict() for d in dividends]
    })


@bp.route('/dividends/fetch/<ticker>', methods=['POST'])
def fetch_dividends(ticker):
    """Fetch and save dividends for a ticker"""
    results = DividendFetcher.save_dividends_to_db(ticker)

    return jsonify({
        'success': True,
        'results': results
    })


@bp.route('/dividends/update-all', methods=['POST'])
def update_all_dividends():
    """Fetch and save dividends for all holdings"""
    results = DividendFetcher.update_all_holdings_dividends()

    return jsonify({
        'success': True,
        'results': results
    })


@bp.route('/dividends/summary', methods=['GET'])
def get_dividend_summary():
    """Get summary of all dividends"""
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    ticker = request.args.get('ticker')

    results = DividendFetcher.calculate_total_dividends(
        ticker_symbol=ticker,
        start_date=start_date,
        end_date=end_date
    )

    return jsonify({
        'success': True,
        'summary': results
    })


@bp.route('/holdings', methods=['GET'])
def get_holdings():
    """Get all holdings"""
    holdings = Holding.query.all()

    return jsonify({
        'success': True,
        'count': len(holdings),
        'holdings': [h.to_dict() for h in holdings]
    })


@bp.route('/holdings/<ticker>', methods=['GET'])
def get_holding(ticker):
    """Get specific holding details"""
    holding = Holding.query.filter_by(ticker_symbol=ticker).first()

    if not holding:
        return jsonify({
            'success': False,
            'error': f'Holding not found: {ticker}'
        }), 404

    return jsonify({
        'success': True,
        'holding': holding.to_dict()
    })


@bp.route('/holdings/<ticker>', methods=['DELETE'])
def delete_holding(ticker):
    """Delete a holding and all associated transactions"""
    from app import db

    holding = Holding.query.filter_by(ticker_symbol=ticker).first()

    if not holding:
        return jsonify({
            'success': False,
            'error': f'保有銘柄が見つかりません: {ticker}'
        }), 404

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

        return jsonify({
            'success': True,
            'message': f'{ticker} の保有銘柄と関連データを削除しました',
            'deleted': {
                'ticker': ticker,
                'transactions': len(transactions),
                'dividends': len(dividends),
                'realized_pnl': len(realized_pnl_records)
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'削除に失敗しました: {str(e)}'
        }), 500


@bp.route('/transactions', methods=['GET'])
def get_transactions():
    """Get all transactions"""
    ticker = request.args.get('ticker')
    limit = request.args.get('limit', type=int)

    query = Transaction.query

    if ticker:
        query = query.filter_by(ticker_symbol=ticker)

    query = query.order_by(Transaction.transaction_date.desc())

    # Get total count before applying limit
    total_count = query.count()

    if limit:
        query = query.limit(limit)

    transactions = query.all()

    return jsonify({
        'success': True,
        'count': len(transactions),
        'total_count': total_count,
        'transactions': [t.to_dict() for t in transactions]
    })


@bp.route('/transactions/delete', methods=['POST'])
def delete_transactions():
    """Delete multiple transactions by IDs"""
    from app import db
    from app.services import TransactionService

    data = request.get_json()
    transaction_ids = data.get('transaction_ids', [])

    if not transaction_ids:
        return jsonify({
            'success': False,
            'error': '削除する取引が選択されていません'
        }), 400

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

        return jsonify({
            'success': True,
            'message': f'{deleted_count}件の取引を削除しました',
            'deleted_count': deleted_count,
            'affected_tickers': list(affected_tickers)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'削除に失敗しました: {str(e)}'
        }), 500


@bp.route('/dashboard/summary', methods=['GET'])
def get_dashboard_summary():
    """Get dashboard summary data"""
    from sqlalchemy import func

    # Get all holdings
    holdings = Holding.query.all()

    # Calculate totals
    total_cost = sum(float(h.total_cost or 0) for h in holdings)
    total_value = sum(float(h.current_value or 0) for h in holdings)
    unrealized_pnl = sum(float(h.unrealized_pnl or 0) for h in holdings)

    # Get realized P&L
    realized_pnl_records = RealizedPnl.query.all()
    realized_pnl = sum(float(r.realized_pnl or 0) for r in realized_pnl_records)

    # Get total dividends
    dividends = Dividend.query.all()
    total_dividends = sum(float(d.total_dividend or 0) for d in dividends)

    # Calculate total P&L
    total_pnl = unrealized_pnl + realized_pnl + total_dividends
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    return jsonify({
        'success': True,
        'summary': {
            'total_asset_value': total_value,
            'total_investment': total_cost,
            'total_pnl': total_pnl,
            'total_pnl_pct': round(total_pnl_pct, 2),
            'unrealized_pnl': unrealized_pnl,
            'realized_pnl': realized_pnl,
            'dividend_total': total_dividends,
            'holdings_count': len(holdings),
            'currency': 'JPY'
        }
    })


@bp.route('/dashboard/portfolio-composition', methods=['GET'])
def get_portfolio_composition():
    """Get portfolio composition data for pie chart"""
    holdings = Holding.query.all()

    composition_data = []
    for holding in holdings:
        if holding.current_value and float(holding.current_value) > 0:
            composition_data.append({
                'ticker': holding.ticker_symbol,
                'name': holding.security_name or holding.ticker_symbol,
                'value': float(holding.current_value),
                'percentage': 0  # Will be calculated on frontend
            })

    return jsonify({
        'success': True,
        'data': composition_data
    })


@bp.route('/dashboard/pnl-history', methods=['GET'])
def get_pnl_history():
    """Get P&L history data for trend chart"""
    from datetime import datetime, timedelta
    from sqlalchemy import func

    period = request.args.get('period', '30d')  # 30d, 1y, all

    # Get all transactions ordered by date
    transactions = Transaction.query.order_by(Transaction.transaction_date).all()

    if not transactions:
        return jsonify({
            'success': True,
            'data': []
        })

    # Calculate date range
    end_date = datetime.now().date()
    if period == '30d':
        start_date = end_date - timedelta(days=30)
    elif period == '1y':
        start_date = end_date - timedelta(days=365)
    else:  # 'all'
        start_date = transactions[0].transaction_date

    # Get realized P&L within date range
    realized_records = RealizedPnl.query.filter(
        RealizedPnl.sell_date >= start_date,
        RealizedPnl.sell_date <= end_date
    ).order_by(RealizedPnl.sell_date).all()

    # Build daily P&L data
    pnl_history = []
    current_date = start_date

    while current_date <= end_date:
        # Calculate cumulative realized P&L up to this date
        cumulative_realized = sum(
            float(r.realized_pnl or 0)
            for r in realized_records
            if r.sell_date <= current_date
        )

        pnl_history.append({
            'date': current_date.isoformat(),
            'pnl': cumulative_realized  # Simplified - only showing realized P&L for now
        })

        current_date += timedelta(days=1)

    return jsonify({
        'success': True,
        'data': pnl_history
    })
