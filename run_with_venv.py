#!/usr/bin/env python
"""仮想環境を使用してアプリケーションを起動"""
import sys
import os
from pathlib import Path

# プロジェクトルート
project_root = Path(__file__).parent.absolute()

# 仮想環境のsite-packagesを最優先でパスに追加
venv_site_packages = project_root / 'venv' / 'Lib' / 'site-packages'

if venv_site_packages.exists():
    # 既存のパスをクリアして仮想環境を最優先に
    sys.path.clear()
    sys.path.append(str(venv_site_packages))
    sys.path.append(str(project_root))
    # 標準ライブラリのパスを追加
    import site
    sys.path.extend(site.getsitepackages())
    sys.path.append(site.USER_SITE)

print("="*60)
print("Stock P&L Manager 起動スクリプト")
print("="*60)
print(f"プロジェクトルート: {project_root}")
print(f"仮想環境: {venv_site_packages}")
print(f"Python: {sys.executable}")
print(f"Python version: {sys.version}")
print()

# 環境変数を設定
os.environ['FLASK_APP'] = 'run.py'
os.environ['FLASK_ENV'] = 'development'

# run.pyを実行
try:
    # run.pyの内容を直接実行
    exec(open(str(project_root / 'run.py')).read())
except Exception as e:
    print(f"\nエラー: {e}")
    import traceback
    traceback.print_exc()

    print("\n" + "="*60)
    print("トラブルシューティング")
    print("="*60)
    print("\n依存パッケージを再インストールしてください:")
    print("  pip install -r requirements.txt")
    print("\nまたは、直接実行してください:")
    print("  python -m flask run")
    sys.exit(1)
