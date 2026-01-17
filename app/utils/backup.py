"""
データベースバックアップユーティリティ

アプリケーション起動時の自動バックアップと、
テスト実行前のバックアップを提供します。
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger("backup")


def get_backup_dir(app=None):
    """バックアップディレクトリを取得"""
    if app:
        backup_dir = app.config.get("BACKUP_DIR")
        if backup_dir:
            return Path(backup_dir)

    # デフォルトはプロジェクトルートのbackupsフォルダ
    return Path(__file__).resolve().parent.parent.parent / "backups"


def get_db_path(app=None):
    """データベースファイルのパスを取得"""
    if app:
        db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if db_uri.startswith("sqlite:///"):
            return Path(db_uri.replace("sqlite:///", ""))

    # デフォルト
    return Path(__file__).resolve().parent.parent.parent / "data" / "stock_pnl.db"


def get_latest_backup(backup_dir):
    """最新のバックアップファイルを取得"""
    backup_dir = Path(backup_dir)
    if not backup_dir.exists():
        return None

    backup_files = list(backup_dir.glob("stock_pnl_backup_*.db"))
    if not backup_files:
        return None

    # 最新のファイルを返す
    return max(backup_files, key=lambda f: f.stat().st_mtime)


def should_create_backup(backup_dir, hours=24):
    """
    バックアップを作成すべきかどうかを判定

    Args:
        backup_dir: バックアップディレクトリ
        hours: この時間以内にバックアップがあればスキップ

    Returns:
        bool: バックアップを作成すべきかどうか
    """
    latest = get_latest_backup(backup_dir)
    if latest is None:
        return True

    # 最新バックアップの作成時刻を確認
    mtime = datetime.fromtimestamp(latest.stat().st_mtime)
    threshold = datetime.now() - timedelta(hours=hours)

    return mtime < threshold


def create_backup(db_path, backup_dir, prefix="stock_pnl_backup"):
    """
    データベースのバックアップを作成

    Args:
        db_path: データベースファイルのパス
        backup_dir: バックアップ保存先ディレクトリ
        prefix: バックアップファイル名のプレフィックス

    Returns:
        Path: 作成されたバックアップファイルのパス、失敗時はNone
    """
    db_path = Path(db_path)
    backup_dir = Path(backup_dir)

    # データベースファイルが存在しない場合
    if not db_path.exists():
        logger.warning(f"データベースファイルが存在しません: {db_path}")
        return None

    # バックアップディレクトリを作成
    backup_dir.mkdir(parents=True, exist_ok=True)

    # バックアップファイル名を生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{prefix}_{timestamp}.db"
    backup_path = backup_dir / backup_filename

    try:
        shutil.copy2(db_path, backup_path)
        file_size = backup_path.stat().st_size / (1024 * 1024)  # MB
        logger.info(f"バックアップ作成完了: {backup_path} ({file_size:.2f} MB)")
        return backup_path
    except Exception as e:
        logger.error(f"バックアップ作成失敗: {e}")
        return None


def cleanup_old_backups(backup_dir, keep_days=7):
    """
    古いバックアップを削除

    Args:
        backup_dir: バックアップディレクトリ
        keep_days: 保持する日数
    """
    backup_dir = Path(backup_dir)
    if not backup_dir.exists():
        return

    threshold = datetime.now() - timedelta(days=keep_days)
    deleted_count = 0

    for backup_file in backup_dir.glob("stock_pnl_backup_*.db"):
        mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
        if mtime < threshold:
            try:
                backup_file.unlink()
                deleted_count += 1
                logger.info(f"古いバックアップを削除: {backup_file}")
            except Exception as e:
                logger.error(f"バックアップ削除失敗: {backup_file} - {e}")

    if deleted_count > 0:
        logger.info(f"{deleted_count}件の古いバックアップを削除しました")


def create_auto_backup(app):
    """
    アプリケーション起動時の自動バックアップ

    Args:
        app: Flaskアプリケーションインスタンス

    Returns:
        Path: 作成されたバックアップファイルのパス、スキップ時はNone
    """
    # テスト環境ではスキップ
    if app.config.get("TESTING"):
        logger.debug("テスト環境のため自動バックアップをスキップ")
        return None

    # 自動バックアップが無効の場合はスキップ
    if not app.config.get("AUTO_BACKUP_ENABLED", True):
        logger.debug("自動バックアップが無効のためスキップ")
        return None

    backup_dir = get_backup_dir(app)
    db_path = get_db_path(app)

    # 24時間以内にバックアップがあればスキップ
    backup_interval = app.config.get("BACKUP_INTERVAL_HOURS", 24)
    if not should_create_backup(backup_dir, hours=backup_interval):
        logger.info("24時間以内にバックアップ済みのためスキップ")
        return None

    # バックアップ作成
    backup_path = create_backup(db_path, backup_dir)

    # 古いバックアップを削除
    keep_days = app.config.get("BACKUP_RETENTION_DAYS", 7)
    cleanup_old_backups(backup_dir, keep_days=keep_days)

    return backup_path


def create_test_backup(db_path=None, backup_dir=None):
    """
    テスト実行前のバックアップ

    Args:
        db_path: データベースファイルのパス（省略時はデフォルト）
        backup_dir: バックアップ保存先（省略時はデフォルト）

    Returns:
        Path: 作成されたバックアップファイルのパス
    """
    if db_path is None:
        db_path = get_db_path()
    if backup_dir is None:
        backup_dir = get_backup_dir()

    return create_backup(db_path, backup_dir, prefix="test_backup")


def get_backup_status(backup_dir=None):
    """
    バックアップ状況を取得

    Args:
        backup_dir: バックアップディレクトリ

    Returns:
        dict: バックアップ状況の情報
    """
    if backup_dir is None:
        backup_dir = get_backup_dir()

    backup_dir = Path(backup_dir)

    if not backup_dir.exists():
        return {
            "has_backup": False,
            "latest_backup": None,
            "backup_count": 0,
            "total_size_mb": 0,
        }

    backup_files = list(backup_dir.glob("stock_pnl_backup_*.db"))

    if not backup_files:
        return {
            "has_backup": False,
            "latest_backup": None,
            "backup_count": 0,
            "total_size_mb": 0,
        }

    latest = max(backup_files, key=lambda f: f.stat().st_mtime)
    total_size = sum(f.stat().st_size for f in backup_files)

    return {
        "has_backup": True,
        "latest_backup": {
            "filename": latest.name,
            "path": str(latest),
            "created_at": datetime.fromtimestamp(latest.stat().st_mtime).isoformat(),
            "size_mb": latest.stat().st_size / (1024 * 1024),
        },
        "backup_count": len(backup_files),
        "total_size_mb": total_size / (1024 * 1024),
    }
