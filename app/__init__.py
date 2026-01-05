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
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models (required for Flask-Migrate)
    with app.app_context():
        from app import models

    # Create upload directory if it doesn't exist
    upload_folder = app.config['UPLOAD_FOLDER']
    if not upload_folder.exists():
        upload_folder.mkdir(parents=True, exist_ok=True)

    # Create .gitkeep in uploads folder
    gitkeep_file = upload_folder / '.gitkeep'
    if not gitkeep_file.exists():
        gitkeep_file.touch()

    # Register blueprints
    from app.routes import main, upload, api
    app.register_blueprint(main.bp)
    app.register_blueprint(upload.bp)
    app.register_blueprint(api.bp)

    # Add a simple index route
    @app.route('/')
    def index():
        return '''
        <h1>Stock P&L Manager</h1>
        <p>Application is running!</p>
        <ul>
            <li><a href="/dashboard">Dashboard</a></li>
            <li><a href="/upload">Upload CSV</a></li>
        </ul>
        '''

    return app
