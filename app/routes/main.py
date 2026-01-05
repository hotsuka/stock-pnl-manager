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


@bp.route('/transactions')
def transactions():
    """Transactions page"""
    return render_template('transactions.html')
