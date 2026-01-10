#!/usr/bin/env python
"""
古いデータクリーンアップスクリプト

Usage:
    python scripts/cleanup_old_data.py [options]

Options:
    --log-days DAYS     ログファイル保存期間（デフォルト: 30日）
    --backup-days DAYS  バックアップ保存期間（デフォルト: 90日）
    --cache-days DAYS   キャッシュ保存期間（デフォルト: 7日）
    --dry-run           実際には削除せずに表示のみ
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def cleanup_logs(log_dir, keep_days, dry_run=False):
    """古いログファイルを削除"""
    log_dir = Path(log_dir)

    if not log_dir.exists():
        print(f"[INFO] ログディレクトリが見つかりません: {log_dir}")
        return 0

    cutoff_date = datetime.now() - timedelta(days=keep_days)
    deleted_count = 0
    total_size = 0

    print(f"[INFO] {keep_days}日以前のログファイルをクリーンアップ中...")

    # .logファイル
    for log_file in log_dir.glob("*.log"):
        file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)

        if file_mtime < cutoff_date:
            file_size = log_file.stat().st_size
            total_size += file_size

            if dry_run:
                print(f"[DRY-RUN] 削除対象: {log_file.name} ({file_size / 1024:.2f} KB)")
            else:
                try:
                    log_file.unlink()
                    print(f"[INFO] 削除: {log_file.name} ({file_size / 1024:.2f} KB)")
                    deleted_count += 1
                except Exception as e:
                    print(f"[WARNING] 削除失敗 ({log_file.name}): {str(e)}")

    # .log.gzファイル（圧縮済みログ）
    for gz_file in log_dir.glob("*.log.gz"):
        file_mtime = datetime.fromtimestamp(gz_file.stat().st_mtime)

        if file_mtime < cutoff_date:
            file_size = gz_file.stat().st_size
            total_size += file_size

            if dry_run:
                print(f"[DRY-RUN] 削除対象: {gz_file.name} ({file_size / 1024:.2f} KB)")
            else:
                try:
                    gz_file.unlink()
                    print(f"[INFO] 削除: {gz_file.name} ({file_size / 1024:.2f} KB)")
                    deleted_count += 1
                except Exception as e:
                    print(f"[WARNING] 削除失敗 ({gz_file.name}): {str(e)}")

    if dry_run:
        print(f"[DRY-RUN] 削除対象: {deleted_count}ファイル, {total_size / (1024 * 1024):.2f} MB")
    else:
        if deleted_count > 0:
            print(f"[SUCCESS] {deleted_count}個のログファイルを削除 ({total_size / (1024 * 1024):.2f} MB解放)")
        else:
            print("[INFO] 削除対象のログファイルはありませんでした")

    return deleted_count


def cleanup_old_backups(backup_dir, keep_days, dry_run=False):
    """古いバックアップファイルを削除"""
    backup_dir = Path(backup_dir)

    if not backup_dir.exists():
        print(f"[INFO] バックアップディレクトリが見つかりません: {backup_dir}")
        return 0

    cutoff_date = datetime.now() - timedelta(days=keep_days)
    deleted_count = 0
    total_size = 0

    print(f"[INFO] {keep_days}日以前のバックアップファイルをクリーンアップ中...")

    for backup_file in backup_dir.glob("stock_pnl_*.db*"):
        file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)

        if file_mtime < cutoff_date:
            file_size = backup_file.stat().st_size
            total_size += file_size

            if dry_run:
                print(f"[DRY-RUN] 削除対象: {backup_file.name} ({file_size / (1024 * 1024):.2f} MB)")
            else:
                try:
                    backup_file.unlink()
                    print(f"[INFO] 削除: {backup_file.name} ({file_size / (1024 * 1024):.2f} MB)")
                    deleted_count += 1
                except Exception as e:
                    print(f"[WARNING] 削除失敗 ({backup_file.name}): {str(e)}")

    if dry_run:
        print(f"[DRY-RUN] 削除対象: {deleted_count}ファイル, {total_size / (1024 * 1024):.2f} MB")
    else:
        if deleted_count > 0:
            print(f"[SUCCESS] {deleted_count}個のバックアップを削除 ({total_size / (1024 * 1024):.2f} MB解放)")
        else:
            print("[INFO] 削除対象のバックアップファイルはありませんでした")

    return deleted_count


def cleanup_uploads(upload_dir, dry_run=False):
    """アップロードされた一時CSVファイルを削除"""
    upload_dir = Path(upload_dir)

    if not upload_dir.exists():
        print(f"[INFO] アップロードディレクトリが見つかりません: {upload_dir}")
        return 0

    deleted_count = 0
    total_size = 0

    print("[INFO] アップロード済みCSVファイルをクリーンアップ中...")

    for csv_file in upload_dir.glob("*.csv"):
        # .gitkeepは除外
        if csv_file.name == '.gitkeep':
            continue

        file_size = csv_file.stat().st_size
        total_size += file_size

        if dry_run:
            print(f"[DRY-RUN] 削除対象: {csv_file.name} ({file_size / 1024:.2f} KB)")
        else:
            try:
                csv_file.unlink()
                print(f"[INFO] 削除: {csv_file.name} ({file_size / 1024:.2f} KB)")
                deleted_count += 1
            except Exception as e:
                print(f"[WARNING] 削除失敗 ({csv_file.name}): {str(e)}")

    if dry_run:
        print(f"[DRY-RUN] 削除対象: {deleted_count}ファイル, {total_size / 1024:.2f} KB")
    else:
        if deleted_count > 0:
            print(f"[SUCCESS] {deleted_count}個のCSVファイルを削除 ({total_size / 1024:.2f} KB解放)")
        else:
            print("[INFO] 削除対象のCSVファイルはありませんでした")

    return deleted_count


def cleanup_cache(cache_dir, keep_days, dry_run=False):
    """古いキャッシュファイルを削除"""
    cache_dir = Path(cache_dir)

    if not cache_dir.exists():
        print(f"[INFO] キャッシュディレクトリが見つかりません: {cache_dir}")
        return 0

    cutoff_date = datetime.now() - timedelta(days=keep_days)
    deleted_count = 0
    total_size = 0

    print(f"[INFO] {keep_days}日以前のキャッシュファイルをクリーンアップ中...")

    for cache_file in cache_dir.rglob("*"):
        if not cache_file.is_file():
            continue

        file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)

        if file_mtime < cutoff_date:
            file_size = cache_file.stat().st_size
            total_size += file_size

            if dry_run:
                print(f"[DRY-RUN] 削除対象: {cache_file.relative_to(cache_dir)} ({file_size / 1024:.2f} KB)")
            else:
                try:
                    cache_file.unlink()
                    print(f"[INFO] 削除: {cache_file.relative_to(cache_dir)} ({file_size / 1024:.2f} KB)")
                    deleted_count += 1
                except Exception as e:
                    print(f"[WARNING] 削除失敗 ({cache_file.name}): {str(e)}")

    if dry_run:
        print(f"[DRY-RUN] 削除対象: {deleted_count}ファイル, {total_size / 1024:.2f} KB")
    else:
        if deleted_count > 0:
            print(f"[SUCCESS] {deleted_count}個のキャッシュファイルを削除 ({total_size / 1024:.2f} KB解放)")
        else:
            print("[INFO] 削除対象のキャッシュファイルはありませんでした")

    return deleted_count


def cleanup_pycache():
    """__pycache__ディレクトリを削除"""
    project_root = Path(__file__).parent.parent
    deleted_count = 0

    print("[INFO] __pycache__ディレクトリをクリーンアップ中...")

    for pycache_dir in project_root.rglob("__pycache__"):
        try:
            import shutil
            shutil.rmtree(pycache_dir)
            print(f"[INFO] 削除: {pycache_dir.relative_to(project_root)}")
            deleted_count += 1
        except Exception as e:
            print(f"[WARNING] 削除失敗: {str(e)}")

    if deleted_count > 0:
        print(f"[SUCCESS] {deleted_count}個の__pycache__ディレクトリを削除")
    else:
        print("[INFO] __pycache__ディレクトリはありませんでした")

    return deleted_count


def main():
    parser = argparse.ArgumentParser(
        description='Stock P&L Manager データクリーンアップツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
    # 全データクリーンアップ
    python scripts/cleanup_old_data.py

    # ログのみクリーンアップ（30日保存）
    python scripts/cleanup_old_data.py --log-days 30

    # ドライラン（削除せずに確認のみ）
    python scripts/cleanup_old_data.py --dry-run

    # バックアップを90日保存
    python scripts/cleanup_old_data.py --backup-days 90
        """
    )

    parser.add_argument(
        '--log-days',
        type=int,
        default=30,
        help='ログファイル保存期間（デフォルト: 30日）'
    )

    parser.add_argument(
        '--backup-days',
        type=int,
        default=90,
        help='バックアップ保存期間（デフォルト: 90日）'
    )

    parser.add_argument(
        '--cache-days',
        type=int,
        default=7,
        help='キャッシュ保存期間（デフォルト: 7日）'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='実際には削除せずに表示のみ'
    )

    parser.add_argument(
        '--skip-logs',
        action='store_true',
        help='ログクリーンアップをスキップ'
    )

    parser.add_argument(
        '--skip-backups',
        action='store_true',
        help='バックアップクリーンアップをスキップ'
    )

    parser.add_argument(
        '--skip-uploads',
        action='store_true',
        help='アップロードファイルクリーンアップをスキップ'
    )

    parser.add_argument(
        '--skip-cache',
        action='store_true',
        help='キャッシュクリーンアップをスキップ'
    )

    parser.add_argument(
        '--cleanup-pycache',
        action='store_true',
        help='__pycache__ディレクトリを削除'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Stock P&L Manager - データクリーンアップ")
    print("=" * 60)

    if args.dry_run:
        print()
        print("[DRY-RUN MODE] 実際には削除されません")
        print()

    print(f"[INFO] 開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    total_deleted = 0

    # ログファイルクリーンアップ
    if not args.skip_logs:
        print()
        print("-" * 60)
        deleted = cleanup_logs('logs', args.log_days, dry_run=args.dry_run)
        total_deleted += deleted

    # バックアップクリーンアップ
    if not args.skip_backups:
        print()
        print("-" * 60)
        deleted = cleanup_old_backups('backups', args.backup_days, dry_run=args.dry_run)
        total_deleted += deleted

    # アップロードファイルクリーンアップ
    if not args.skip_uploads:
        print()
        print("-" * 60)
        deleted = cleanup_uploads('data/uploads', dry_run=args.dry_run)
        total_deleted += deleted

    # キャッシュクリーンアップ
    if not args.skip_cache:
        print()
        print("-" * 60)
        deleted = cleanup_cache('.cache', args.cache_days, dry_run=args.dry_run)
        total_deleted += deleted

    # __pycache__クリーンアップ
    if args.cleanup_pycache:
        print()
        print("-" * 60)
        deleted = cleanup_pycache()
        total_deleted += deleted

    # サマリー
    print()
    print("=" * 60)
    print("クリーンアップサマリー")
    print("=" * 60)

    if args.dry_run:
        print(f"[DRY-RUN] 削除対象ファイル総数: {total_deleted}")
    else:
        print(f"[INFO] 削除したファイル総数: {total_deleted}")

    print(f"[INFO] 完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == '__main__':
    main()
