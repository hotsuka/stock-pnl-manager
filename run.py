import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# デフォルト環境をdevelopmentに設定
if not os.environ.get('FLASK_ENV'):
    os.environ['FLASK_ENV'] = 'development'

# Windows環境でのSQLiteパス問題を回避するため、DATABASE_URLを明示的に設定
if not os.environ.get('DATABASE_URL'):
    base_dir = Path(__file__).resolve().parent
    db_path = (base_dir / 'data' / 'stock_pnl.db').as_posix()
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'

from app import create_app, db

# Create app instance
app = create_app(os.getenv('FLASK_ENV', 'development'))


@app.shell_context_processor
def make_shell_context():
    """Add database instance to shell context"""
    return {'db': db}


if __name__ == '__main__':
    # use_reloader=Falseにしてreloaderのパス問題を回避
    # 開発中のコード変更は手動でサーバー再起動が必要
    app.run(debug=True, host='0.0.0.0', port=8000, use_reloader=False)
