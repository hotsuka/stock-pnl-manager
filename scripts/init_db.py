#!/usr/bin/env python
"""Database initialization script"""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app import create_app, db
from flask_migrate import init, migrate, upgrade

def init_database():
    """Initialize database with migrations"""
    print("Starting database initialization...")

    app = create_app('development')

    with app.app_context():
        # Check if versions directory exists
        versions_dir = project_root / 'migrations' / 'versions'

        if not versions_dir.exists():
            print(f"Creating versions directory: {versions_dir}")
            versions_dir.mkdir(parents=True, exist_ok=True)

        # Check if any migration files exist
        migration_files = list(versions_dir.glob('*.py'))

        if not migration_files:
            print("\nNo migration files found. Creating initial migration...")

            # Create initial migration
            try:
                from flask_migrate import Migrate
                migrate_obj = Migrate(app, db)

                # Import all models to ensure they're registered
                from app.models import (
                    Transaction, Holding, Dividend,
                    StockPrice, RealizedPnl, StockMetrics
                )

                print("All models imported successfully")
                print(f"  - Transaction: {Transaction.__tablename__}")
                print(f"  - Holding: {Holding.__tablename__}")
                print(f"  - Dividend: {Dividend.__tablename__}")
                print(f"  - StockPrice: {StockPrice.__tablename__}")
                print(f"  - RealizedPnl: {RealizedPnl.__tablename__}")
                print(f"  - StockMetrics: {StockMetrics.__tablename__}")

                # Run flask db migrate
                os.system('flask db migrate -m "Initial migration with all models"')

                print("\nMigration file created successfully!")

            except Exception as e:
                print(f"Error creating migration: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print(f"\nFound {len(migration_files)} existing migration file(s)")

        # Apply migrations
        print("\nApplying migrations to database...")
        try:
            os.system('flask db upgrade')
            print("Database migrations applied successfully!")
        except Exception as e:
            print(f"Error applying migrations: {e}")
            import traceback
            traceback.print_exc()
            return False

        # Verify tables were created
        print("\nVerifying database tables...")
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        print(f"Found {len(tables)} tables in database:")
        for table in tables:
            print(f"  - {table}")

        expected_tables = ['transactions', 'holdings', 'dividends',
                          'stock_prices', 'realized_pnl', 'stock_metrics']
        missing_tables = [t for t in expected_tables if t not in tables]

        if missing_tables:
            print(f"\nWARNING: Missing expected tables: {missing_tables}")
            return False
        else:
            print("\nAll expected tables exist!")
            return True

if __name__ == '__main__':
    success = init_database()

    if success:
        print("\n" + "="*60)
        print("Database initialization completed successfully!")
        print("="*60)
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("Database initialization failed!")
        print("="*60)
        sys.exit(1)
