"""Add previous_close and day_change_pct columns to holdings table"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Add new columns using raw SQL
    try:
        db.session.execute(text("""
            ALTER TABLE holdings
            ADD COLUMN previous_close NUMERIC(15, 4)
        """))
        db.session.commit()
        print("Added previous_close column")
    except Exception as e:
        print(f"previous_close column may already exist: {e}")
        db.session.rollback()

    try:
        db.session.execute(text("""
            ALTER TABLE holdings
            ADD COLUMN day_change_pct NUMERIC(10, 4)
        """))
        db.session.commit()
        print("Added day_change_pct column")
    except Exception as e:
        print(f"day_change_pct column may already exist: {e}")
        db.session.rollback()

    print("Migration completed")
