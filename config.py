import os
from pathlib import Path

# Base directory - resolve()を使用してシンボリックリンクを解決
BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Base configuration"""

    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-please-change-in-production'

    # Database configuration
    # Windows環境でのパス区切り文字の問題を解決するため、as_posix()を使用
    _db_path = (BASE_DIR / "data" / "stock_pnl.db").as_posix()
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{_db_path}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File upload configuration
    UPLOAD_FOLDER = BASE_DIR / 'data' / 'uploads'
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max file size
    ALLOWED_EXTENSIONS = {'csv'}

    # Flask-WTF configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No time limit for CSRF tokens

    # Application settings
    APP_NAME = 'Stock P&L Manager'
    ITEMS_PER_PAGE = 50

    # Backup configuration
    BACKUP_DIR = BASE_DIR / 'backups'
    AUTO_BACKUP_ENABLED = True
    BACKUP_RETENTION_DAYS = 7  # バックアップ保持日数
    BACKUP_INTERVAL_HOURS = 24  # バックアップ間隔（時間）


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
    SECRET_KEY = os.environ.get('SECRET_KEY') or Config.SECRET_KEY


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    AUTO_BACKUP_ENABLED = False  # テスト環境では自動バックアップ無効


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
