#!/usr/bin/env python
"""
データベースリストアスクリプト

Usage:
    python scripts/restore_database.py <backup_file> [options]

Options:
    --force             確認なしで実行
    --no-backup         復元前の自動バックアップをスキップ
"""

import os
import sys
import shutil
import argparse
import gzip
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def confirm_restore():
    """復元実行の確認"""
    print()
    print("[WARNING] この操作は現在のデータベースを上書きします!")
    print("[WARNING] 続行する前に、現在のデータベースがバックアップされます。")
    print()

    response = input("本当に復元を実行しますか? (yes/no): ").lower()
    return response in ['yes', 'y']


def backup_current_db(db_path):
    """現在のデータベースをバックアップ"""
    if not Path(db_path).exists():
        print("[INFO] 現在のデータベースが存在しないため、バックアップをスキップします")
        return None

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = Path('backups')
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_filename = f"stock_pnl_pre_restore_{timestamp}.db"
    backup_path = backup_dir / backup_filename

    try:
        print(f"[INFO] 現在のデータベースをバックアップ中...")
        shutil.copy2(db_path, backup_path)
        print(f"[SUCCESS] バックアップ完了: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"[ERROR] バックアップ失敗: {str(e)}")
        return None


def restore_database(backup_file, db_path, skip_backup=False):
    """バックアップからデータベースを復元"""
    backup_file = Path(backup_file)
    db_path = Path(db_path)

    # バックアップファイルの存在確認
    if not backup_file.exists():
        print(f"[ERROR] バックアップファイルが見つかりません: {backup_file}")
        return False

    # 現在のDBをバックアップ
    if not skip_backup:
        current_backup = backup_current_db(db_path)
        if current_backup is None and db_path.exists():
            print("[ERROR] 復元前のバックアップに失敗しました")
            return False

    # データベースディレクトリを作成
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        print(f"[INFO] データベース復元中: {backup_file}")

        # 圧縮されているか確認
        if backup_file.suffix == '.gz':
            # gzip圧縮されている場合
            print("[INFO] 圧縮ファイルを展開中...")
            with gzip.open(backup_file, 'rb') as f_in:
                with open(db_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            # 通常のファイル
            shutil.copy2(backup_file, db_path)

        # ファイルサイズを取得
        file_size = db_path.stat().st_size / (1024 * 1024)  # MB

        print(f"[SUCCESS] データベース復元完了: {db_path}")
        print(f"[INFO] ファイルサイズ: {file_size:.2f} MB")

        return True

    except Exception as e:
        print(f"[ERROR] データベース復元失敗: {str(e)}")
        return False


def verify_database(db_path):
    """データベースの整合性を確認"""
    try:
        import sqlite3

        print("[INFO] データベースの整合性を確認中...")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # PRAGMA integrity_check
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()

        if result[0] == 'ok':
            print("[SUCCESS] データベースの整合性チェック: OK")

            # テーブル数を確認
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            print(f"[INFO] テーブル数: {table_count}")

            # 主要テーブルのレコード数を確認
            tables = ['transactions', 'holdings', 'realized_pnls', 'dividends']
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"[INFO] {table}: {count}件")
                except:
                    pass

            conn.close()
            return True
        else:
            print(f"[ERROR] データベース整合性チェック失敗: {result[0]}")
            conn.close()
            return False

    except Exception as e:
        print(f"[ERROR] データベース検証エラー: {str(e)}")
        return False


def list_available_backups(backup_dir='backups'):
    """利用可能なバックアップ一覧を表示"""
    backup_dir = Path(backup_dir)

    if not backup_dir.exists():
        print(f"[INFO] バックアップディレクトリが見つかりません: {backup_dir}")
        return []

    backups = sorted(
        backup_dir.glob("stock_pnl_*.db*"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )

    if not backups:
        print("[INFO] バックアップファイルが見つかりません")
        return []

    print()
    print("=" * 80)
    print("利用可能なバックアップ:")
    print("=" * 80)

    for i, backup in enumerate(backups[:20], 1):  # 最新20件
        file_size = backup.stat().st_size / (1024 * 1024)  # MB
        mod_time = datetime.fromtimestamp(backup.stat().st_mtime)

        print(f"{i:2d}. {backup.name}")
        print(f"    サイズ: {file_size:.2f} MB")
        print(f"    日時:   {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

    return backups


def main():
    parser = argparse.ArgumentParser(
        description='Stock P&L Manager データベースリストアツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
    # バックアップ一覧を表示
    python scripts/restore_database.py --list

    # バックアップから復元
    python scripts/restore_database.py backups/stock_pnl_20260111_030000.db

    # 確認なしで復元
    python scripts/restore_database.py backups/stock_pnl_20260111_030000.db --force

    # 復元前のバックアップをスキップ
    python scripts/restore_database.py backups/stock_pnl_20260111_030000.db --no-backup --force
        """
    )

    parser.add_argument(
        'backup_file',
        nargs='?',
        help='リストアするバックアップファイル'
    )

    parser.add_argument(
        '--db-path',
        default='data/stock_pnl.db',
        help='データベースファイルのパス（デフォルト: data/stock_pnl.db）'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='確認なしで実行'
    )

    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='復元前の自動バックアップをスキップ'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='利用可能なバックアップ一覧を表示'
    )

    parser.add_argument(
        '--verify',
        action='store_true',
        help='復元後にデータベースの整合性を確認'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("Stock P&L Manager - データベースリストア")
    print("=" * 80)

    # バックアップ一覧表示
    if args.list:
        list_available_backups()
        sys.exit(0)

    # バックアップファイルが指定されていない場合
    if not args.backup_file:
        print()
        print("[ERROR] バックアップファイルを指定してください")
        print()
        print("利用可能なバックアップ:")
        list_available_backups()
        sys.exit(1)

    # 確認
    if not args.force:
        if not confirm_restore():
            print("[INFO] リストアをキャンセルしました")
            sys.exit(0)

    print()

    # データベース復元
    success = restore_database(
        args.backup_file,
        args.db_path,
        skip_backup=args.no_backup
    )

    if not success:
        print()
        print("[ERROR] データベースリストアに失敗しました")
        sys.exit(1)

    print()

    # 整合性チェック
    if args.verify or not args.no_backup:
        if not verify_database(args.db_path):
            print()
            print("[WARNING] データベースの整合性チェックで問題が見つかりました")
            print("[WARNING] 必要に応じて以前のバックアップから再度復元してください")
            sys.exit(1)

    print()
    print("=" * 80)
    print("リストア処理完了")
    print("=" * 80)
    print()
    print("[INFO] アプリケーションを再起動してください")


if __name__ == '__main__':
    main()
