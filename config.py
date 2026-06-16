import os
from pathlib import Path

# Base directory - resolve()を使用してシンボリックリンクを解決
BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Base configuration"""

    # Secret key for session management
    SECRET_KEY = (
        os.environ.get("SECRET_KEY") or "dev-secret-key-please-change-in-production"
    )

    # Database configuration
    # Railway Persistent Volume対応: RAILWAY_VOLUME_MOUNT_PATHが設定されている場合はそのパスを使用
    _volume_path = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
    if _volume_path:
        _data_dir = Path(_volume_path)
        _db_path = (_data_dir / "stock_pnl.db").as_posix()
    else:
        _data_dir = BASE_DIR / "data"
        # Windows環境でのパス区切り文字の問題を解決するため、as_posix()を使用
        _db_path = (_data_dir / "stock_pnl.db").as_posix()
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or f"sqlite:///{_db_path}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File upload configuration
    UPLOAD_FOLDER = (
        Path(_volume_path) / "uploads"
        if _volume_path
        else BASE_DIR / "data" / "uploads"
    )
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max file size
    ALLOWED_EXTENSIONS = {"csv"}

    # Flask-WTF configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No time limit for CSRF tokens

    # Application settings
    APP_NAME = "Stock P&L Manager"
    ITEMS_PER_PAGE = 50

    # Backup configuration
    BACKUP_DIR = (
        Path(_volume_path) / "backups" if _volume_path else BASE_DIR / "backups"
    )
    AUTO_BACKUP_ENABLED = True
    BACKUP_RETENTION_DAYS = 7  # バックアップ保持日数
    BACKUP_INTERVAL_HOURS = 24  # バックアップ間隔（時間）

    # stock_analyzer DBパス（デフォルト: 同階層の stock_analyzer/data/analyzer.db）
    SCREENER_DB_PATH = os.environ.get(
        "SCREENER_DB_PATH",
        str(BASE_DIR.parent / "stock_analyzer" / "data" / "analyzer.db"),
    )


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    TESTING = False

    # Override SECRET_KEY from environment in production
    # Make sure to set SECRET_KEY environment variable when deploying
    SECRET_KEY = os.environ.get("SECRET_KEY") or Config.SECRET_KEY


class TestingConfig(Config):
    """Testing configuration"""

    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    AUTO_BACKUP_ENABLED = False  # テスト環境では自動バックアップ無効
    SCREENER_DB_PATH = ""  # テスト時はスクリーナーDBにアクセスしない


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
