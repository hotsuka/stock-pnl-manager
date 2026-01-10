#!/usr/bin/env python
"""
データベースバックアップスクリプト

Usage:
    python scripts/backup_database.py [options]

Options:
    --output-dir DIR    バックアップ保存先ディレクトリ（デフォルト: backups）
    --keep-days DAYS    保存期間（デフォルト: 30日）
    --compress          バックアップを圧縮（gzip）
    --upload-cloud      クラウドストレージにアップロード（AWS S3）
"""

import os
import sys
import shutil
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()


def create_backup(db_path, output_dir, compress=False):
    """データベースのバックアップを作成"""
    # タイムスタンプ
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 出力ディレクトリを作成
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # バックアップファイル名
    if compress:
        backup_filename = f"stock_pnl_{timestamp}.db.gz"
    else:
        backup_filename = f"stock_pnl_{timestamp}.db"

    backup_path = output_dir / backup_filename

    # データベースファイルの存在確認
    if not Path(db_path).exists():
        print(f"[ERROR] データベースファイルが見つかりません: {db_path}")
        return None

    # バックアップ実行
    try:
        print(f"[INFO] バックアップ開始: {db_path}")

        if compress:
            # gzipで圧縮
            import gzip
            with open(db_path, 'rb') as f_in:
                with gzip.open(backup_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            # 通常のコピー
            shutil.copy2(db_path, backup_path)

        # ファイルサイズを取得
        file_size = backup_path.stat().st_size / (1024 * 1024)  # MB

        print(f"[SUCCESS] バックアップ完了: {backup_path}")
        print(f"[INFO] ファイルサイズ: {file_size:.2f} MB")

        return backup_path

    except Exception as e:
        print(f"[ERROR] バックアップ失敗: {str(e)}")
        return None


def cleanup_old_backups(output_dir, keep_days):
    """古いバックアップを削除"""
    output_dir = Path(output_dir)

    if not output_dir.exists():
        return

    cutoff_date = datetime.now() - timedelta(days=keep_days)
    deleted_count = 0

    print(f"[INFO] {keep_days}日以前のバックアップを削除中...")

    for backup_file in output_dir.glob("stock_pnl_*.db*"):
        # ファイルの最終更新日時を取得
        file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)

        if file_mtime < cutoff_date:
            try:
                backup_file.unlink()
                print(f"[INFO] 削除: {backup_file.name}")
                deleted_count += 1
            except Exception as e:
                print(f"[WARNING] 削除失敗 ({backup_file.name}): {str(e)}")

    if deleted_count > 0:
        print(f"[SUCCESS] {deleted_count}個の古いバックアップを削除しました")
    else:
        print("[INFO] 削除対象のバックアップはありませんでした")


def upload_to_cloud(backup_path, cloud_service='s3'):
    """クラウドストレージにアップロード"""
    if cloud_service == 's3':
        try:
            import boto3

            bucket_name = os.getenv('AWS_S3_BUCKET')
            if not bucket_name:
                print("[WARNING] AWS_S3_BUCKET環境変数が設定されていません")
                return False

            print(f"[INFO] AWS S3にアップロード中: {bucket_name}")

            s3_client = boto3.client('s3')
            s3_key = f"stock-pnl-backups/{backup_path.name}"

            s3_client.upload_file(str(backup_path), bucket_name, s3_key)

            print(f"[SUCCESS] S3アップロード完了: s3://{bucket_name}/{s3_key}")
            return True

        except ImportError:
            print("[ERROR] boto3がインストールされていません")
            print("  pip install boto3")
            return False
        except Exception as e:
            print(f"[ERROR] S3アップロード失敗: {str(e)}")
            return False

    elif cloud_service == 'gcs':
        try:
            from google.cloud import storage

            bucket_name = os.getenv('GCS_BUCKET')
            if not bucket_name:
                print("[WARNING] GCS_BUCKET環境変数が設定されていません")
                return False

            print(f"[INFO] Google Cloud Storageにアップロード中: {bucket_name}")

            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(f"stock-pnl-backups/{backup_path.name}")

            blob.upload_from_filename(str(backup_path))

            print(f"[SUCCESS] GCSアップロード完了: gs://{bucket_name}/stock-pnl-backups/{backup_path.name}")
            return True

        except ImportError:
            print("[ERROR] google-cloud-storageがインストールされていません")
            print("  pip install google-cloud-storage")
            return False
        except Exception as e:
            print(f"[ERROR] GCSアップロード失敗: {str(e)}")
            return False

    return False


def main():
    parser = argparse.ArgumentParser(
        description='Stock P&L Manager データベースバックアップツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
    # 基本的なバックアップ
    python scripts/backup_database.py

    # 圧縮して保存
    python scripts/backup_database.py --compress

    # 保存期間を7日に設定
    python scripts/backup_database.py --keep-days 7

    # クラウドにアップロード
    python scripts/backup_database.py --compress --upload-cloud
        """
    )

    parser.add_argument(
        '--output-dir',
        default='backups',
        help='バックアップ保存先ディレクトリ（デフォルト: backups）'
    )

    parser.add_argument(
        '--keep-days',
        type=int,
        default=30,
        help='バックアップ保存期間（デフォルト: 30日）'
    )

    parser.add_argument(
        '--compress',
        action='store_true',
        help='バックアップをgzipで圧縮'
    )

    parser.add_argument(
        '--upload-cloud',
        action='store_true',
        help='クラウドストレージにアップロード（AWS S3）'
    )

    parser.add_argument(
        '--cloud-service',
        choices=['s3', 'gcs'],
        default='s3',
        help='クラウドサービス（デフォルト: s3）'
    )

    parser.add_argument(
        '--db-path',
        default='data/stock_pnl.db',
        help='データベースファイルのパス（デフォルト: data/stock_pnl.db）'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Stock P&L Manager - データベースバックアップ")
    print("=" * 60)
    print()

    # バックアップ作成
    backup_path = create_backup(
        args.db_path,
        args.output_dir,
        compress=args.compress
    )

    if not backup_path:
        sys.exit(1)

    print()

    # 古いバックアップを削除
    cleanup_old_backups(args.output_dir, args.keep_days)

    print()

    # クラウドにアップロード
    if args.upload_cloud and backup_path:
        upload_to_cloud(backup_path, cloud_service=args.cloud_service)
        print()

    print("=" * 60)
    print("バックアップ処理完了")
    print("=" * 60)


if __name__ == '__main__':
    main()
