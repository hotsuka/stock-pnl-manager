from flask import Blueprint, render_template

bp = Blueprint('main', __name__)


@bp.route('/')
@bp.route('/dashboard')
def dashboard():
    """Dashboard page"""
    return render_template('dashboard.html')


@bp.route('/upload')
def upload():
    """CSV upload page"""
    return render_template('upload.html')


@bp.route('/holdings')
def holdings():
    """Holdings page"""
    return render_template('holdings.html')


@bp.route('/realized-pnl')
def realized_pnl():
    """Realized P&L (Sold Securities) page"""
    return render_template('realized_pnl.html')


@bp.route('/dividends')
def dividends():
    """Dividends page"""
    return render_template('dividends.html')


@bp.route('/transactions')
def transactions():
    """Transactions page"""
    return render_template('transactions.html')
