#!/usr/bin/env python
"""Apply database migration"""
import os
import sys
from pathlib import Path

# Set environment variables
os.environ['FLASK_APP'] = 'run.py'
os.environ['FLASK_ENV'] = 'development'

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app import create_app, db

def apply_migration():
    """Apply migration to database"""
    print("="*60)
    print("Applying Database Migration")
    print("="*60)

    app = create_app('development')

    with app.app_context():
        # Import all models
        from app.models import (
            Transaction, Holding, Dividend,
            StockPrice, RealizedPnl, StockMetrics
        )

        print("\nImported models:")
        print(f"  - Transaction: {Transaction.__tablename__}")
        print(f"  - Holding: {Holding.__tablename__}")
        print(f"  - Dividend: {Dividend.__tablename__}")
        print(f"  - StockPrice: {StockPrice.__tablename__}")
        print(f"  - RealizedPnl: {RealizedPnl.__tablename__}")
        print(f"  - StockMetrics: {StockMetrics.__tablename__}")

        # Check current database state
        print("\nCurrent database state:")
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        current_tables = inspector.get_table_names()
        print(f"  Tables: {current_tables}")

        # Apply migration using flask-migrate
        print("\nApplying migration...")
        from flask_migrate import upgrade

        try:
            upgrade()
            print("✓ Migration applied successfully!")
        except Exception as e:
            print(f"✗ Error applying migration: {e}")
            import traceback
            traceback.print_exc()
            return False

        # Verify tables were created
        print("\nVerifying database after migration:")
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        print(f"\nTables in database ({len(tables)}):")
        for table in sorted(tables):
            print(f"  ✓ {table}")

        # Check expected tables
        expected_tables = ['transactions', 'holdings', 'dividends',
                          'stock_prices', 'realized_pnl', 'stock_metrics']
        missing_tables = [t for t in expected_tables if t not in tables]

        if missing_tables:
            print(f"\n✗ WARNING: Missing expected tables: {missing_tables}")
            return False
        else:
            print(f"\n✓ All expected tables exist!")

        # Show alembic version
        try:
            result = db.session.execute(db.text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            print(f"\n✓ Migration version: {version}")
        except Exception as e:
            print(f"\n✗ Could not read migration version: {e}")

        return True

if __name__ == '__main__':
    try:
        success = apply_migration()

        if success:
            print("\n" + "="*60)
            print("✓ Database migration completed successfully!")
            print("="*60)
            print("\nYou can now start the application:")
            print("  python run.py")
            sys.exit(0)
        else:
            print("\n" + "="*60)
            print("✗ Database migration failed!")
            print("="*60)
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
