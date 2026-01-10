"""
WSGI Entry Point for Production Server

本番環境用のWSGIエントリーポイント
Waitress（Windows）またはGunicorn（Linux/macOS）から呼び出されます
"""
import os
from app import create_app

# 本番環境用のアプリケーションを作成
app = create_app('production')

if __name__ == '__main__':
    # 直接実行時は開発サーバーを起動
    app.run(debug=False, host='0.0.0.0', port=8000)
