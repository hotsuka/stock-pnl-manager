import os
from dotenv import load_dotenv
from app import create_app, db

# Load environment variables
load_dotenv()

# Create app instance
app = create_app(os.getenv('FLASK_ENV', 'development'))


@app.shell_context_processor
def make_shell_context():
    """Add database instance to shell context"""
    return {'db': db}


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
