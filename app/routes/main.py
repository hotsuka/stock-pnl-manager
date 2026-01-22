from flask import Blueprint, render_template

bp = Blueprint("main", __name__)


@bp.route("/")
@bp.route("/dashboard")
def dashboard():
    """Dashboard page"""
    return render_template("dashboard.html")


@bp.route("/upload")
def upload():
    """CSV upload page"""
    return render_template("upload.html")


@bp.route("/holdings")
def holdings():
    """Holdings page"""
    return render_template("holdings.html")


@bp.route("/realized-pnl")
def realized_pnl():
    """Realized P&L (Sold Securities) page"""
    return render_template("realized_pnl.html")


@bp.route("/dividends")
def dividends():
    """Dividends page"""
    return render_template("dividends.html")


@bp.route("/transactions")
def transactions():
    """Transactions page"""
    return render_template("transactions.html")


@bp.route("/performance")
def performance():
    """Performance History page"""
    return render_template("performance.html")


@bp.route("/test-performance")
def test_performance():
    """Performance API Test page"""
    return render_template("test_performance.html")


@bp.route("/price-override")
def price_override():
    """Stock Price Override page"""
    return render_template("price_override.html")
