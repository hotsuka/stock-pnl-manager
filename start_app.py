#!/usr/bin/env python
"""アプリケーション起動スクリプト"""
import sys
from pathlib import Path

# プロジェクトルートとvenvのsite-packagesをパスに追加
project_root = Path(__file__).parent.absolute()
venv_site_packages = project_root / 'venv' / 'Lib' / 'site-packages'

print(f"プロジェクトルート: {project_root}")
print(f"仮想環境パス: {venv_site_packages}")
print(f"仮想環境が存在: {venv_site_packages.exists()}")

if venv_site_packages.exists():
    # Windowsの絶対パスとして追加
    sys.path.insert(0, str(venv_site_packages).replace('/', '\\'))
    sys.path.insert(0, str(project_root).replace('/', '\\'))
    print(f"sys.pathに追加しました")
else:
    print(f"警告: 仮想環境が見つかりません: {venv_site_packages}")
    print("システムのPythonパッケージを使用します")

# アプリケーションをインポートして起動
try:
    from app import create_app

    app = create_app('development')

    print("="*60)
    print("Stock P&L Manager - アプリケーション起動中")
    print("="*60)
    print(f"\nデータベース: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"\nアプリケーションURL: http://localhost:5000")
    print(f"ダッシュボード: http://localhost:5000/dashboard")
    print(f"CSV アップロード: http://localhost:5000/upload")
    print("\nサーバーを停止するには Ctrl+C を押してください")
    print("="*60 + "\n")

    # アプリケーション起動
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)

except ImportError as e:
    print(f"\nエラー: 必要なモジュールをインポートできません")
    print(f"詳細: {e}")
    print("\n解決方法:")
    print("1. 仮想環境を作成: python -m venv venv")
    print("2. 依存関係をインストール: pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"\nエラー: アプリケーションの起動に失敗しました")
    print(f"詳細: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
