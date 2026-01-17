import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()


def create_app(config_name=None):
    """Application factory pattern"""

    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)

    # Setup logging
    from app.utils.logger import setup_logger

    setup_logger(app)

    # Import models (required for Flask-Migrate)
    with app.app_context():
        from app import models

    # Create upload directory if it doesn't exist
    upload_folder = app.config["UPLOAD_FOLDER"]
    if not upload_folder.exists():
        upload_folder.mkdir(parents=True, exist_ok=True)

    # Create .gitkeep in uploads folder
    gitkeep_file = upload_folder / ".gitkeep"
    if not gitkeep_file.exists():
        gitkeep_file.touch()

    # Auto backup on startup (non-testing environments only)
    if not app.config.get("TESTING"):
        try:
            from app.utils.backup import create_auto_backup

            create_auto_backup(app)
        except Exception as e:
            # バックアップ失敗してもアプリは起動する
            app.logger.warning(f"自動バックアップ失敗: {e}")

    # Register blueprints
    from app.routes import main, upload, api

    app.register_blueprint(main.bp)
    app.register_blueprint(upload.bp)
    app.register_blueprint(api.bp)

    # Register error handlers
    from app.utils.errors import (
        AppError,
        ValidationError,
        NotFoundError,
        DatabaseError,
        ExternalAPIError,
        handle_app_error,
        handle_generic_error,
        handle_404_error,
        handle_405_error,
    )

    app.register_error_handler(AppError, handle_app_error)
    app.register_error_handler(ValidationError, handle_app_error)
    app.register_error_handler(NotFoundError, handle_app_error)
    app.register_error_handler(DatabaseError, handle_app_error)
    app.register_error_handler(ExternalAPIError, handle_app_error)
    app.register_error_handler(404, handle_404_error)
    app.register_error_handler(405, handle_405_error)
    app.register_error_handler(Exception, handle_generic_error)

    # Add a simple index route
    @app.route("/")
    def index():
        return """
        <h1>Stock P&L Manager</h1>
        <p>Application is running!</p>
        <ul>
            <li><a href="/dashboard">Dashboard</a></li>
            <li><a href="/upload">Upload CSV</a></li>
        </ul>
        """

    return app
