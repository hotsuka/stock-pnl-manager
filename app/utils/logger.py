"""
ロギング設定
"""

import logging
import os
from pathlib import Path
from datetime import datetime


def setup_logger(app):
    """
    ロガーをセットアップ

    Args:
        app: Flask application instance
    """
    # ログディレクトリの作成
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    # ログファイル名（日付付き）
    log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"

    # ログフォーマット
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # ファイルハンドラー
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # コンソールハンドラー（開発環境のみ）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if app.debug else logging.WARNING)
    console_handler.setFormatter(formatter)

    # Flaskアプリケーションのロガー設定
    app.logger.setLevel(logging.DEBUG if app.debug else logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    # 既存のハンドラーを削除（重複防止）
    if app.logger.hasHandlers():
        for handler in app.logger.handlers[:-2]:  # 最後の2つ（上で追加したもの）以外を削除
            app.logger.removeHandler(handler)

    app.logger.info("=" * 70)
    app.logger.info(f"Application started - Environment: {os.environ.get('FLASK_ENV', 'development')}")
    app.logger.info("=" * 70)

    return app.logger


def get_logger(name):
    """
    名前付きロガーを取得

    Args:
        name: ロガー名

    Returns:
        logging.Logger: ロガーインスタンス
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        # ログディレクトリの作成
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)

        # ログファイル名
        log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"

        # フォーマッター
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        # ファイルハンドラー
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)

    return logger


def log_api_call(logger, endpoint, method, params=None, response_code=None, error=None):
    """
    API呼び出しをログに記録

    Args:
        logger: ロガーインスタンス
        endpoint: エンドポイント
        method: HTTPメソッド
        params: パラメータ（オプション）
        response_code: レスポンスコード（オプション）
        error: エラーメッセージ（オプション）
    """
    log_msg = f"{method} {endpoint}"

    if params:
        log_msg += f" - Params: {params}"

    if response_code:
        log_msg += f" - Response: {response_code}"

    if error:
        logger.error(f"{log_msg} - Error: {error}")
    else:
        logger.info(log_msg)


def log_database_operation(logger, operation, table, details=None, error=None):
    """
    データベース操作をログに記録

    Args:
        logger: ロガーインスタンス
        operation: 操作タイプ（INSERT, UPDATE, DELETE等）
        table: テーブル名
        details: 詳細情報（オプション）
        error: エラーメッセージ（オプション）
    """
    log_msg = f"Database {operation} on {table}"

    if details:
        log_msg += f" - {details}"

    if error:
        logger.error(f"{log_msg} - Error: {error}")
    else:
        logger.info(log_msg)


def log_external_api_call(logger, service, endpoint, params=None, success=True, error=None):
    """
    外部API呼び出しをログに記録

    Args:
        logger: ロガーインスタンス
        service: サービス名（yfinance, exchange rate API等）
        endpoint: エンドポイント
        params: パラメータ（オプション）
        success: 成功フラグ
        error: エラーメッセージ（オプション）
    """
    log_msg = f"External API call to {service} - {endpoint}"

    if params:
        log_msg += f" - Params: {params}"

    if not success:
        logger.error(f"{log_msg} - FAILED - {error}")
    else:
        logger.info(f"{log_msg} - SUCCESS")
