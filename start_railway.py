"""Railway startup script"""

import os
import sys

# Ensure directories exist before app initialization
data_dir = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "/app/data")
os.makedirs(os.path.join(data_dir, "uploads"), exist_ok=True)
os.makedirs(os.path.join(data_dir, "backups"), exist_ok=True)
os.makedirs("/app/logs", exist_ok=True)

print(f"[startup] Data directory: {data_dir}", flush=True)
print(f"[startup] Contents: {os.listdir(data_dir)}", flush=True)

# Initialize app and create tables
from app import create_app, db

app = create_app("production")

with app.app_context():
    db.create_all()
    print("[startup] Database tables created/verified", flush=True)

# Start gunicorn
port = os.environ.get("PORT", "8000")
print(f"[startup] Starting gunicorn on port {port}", flush=True)

os.execvp(
    "gunicorn",
    [
        "gunicorn",
        "-w",
        "2",
        "-b",
        f"0.0.0.0:{port}",
        "--timeout",
        "120",
        "--access-logfile",
        "-",
        "--error-logfile",
        "-",
        'app:create_app("production")',
    ],
)
