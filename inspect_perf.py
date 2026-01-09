import os
from app import create_app, db
from app.services.performance_service import PerformanceService

app = create_app(os.getenv('FLASK_ENV', 'development'))

def test_performance():
    with app.app_context():
        print("Testing PerformanceService.get_performance_history(days=30)...")
        try:
            results = PerformanceService.get_performance_history(days=30)
            print(f"Results count: {len(results)}")
            if results:
                print("All results:")
                for r in results:
                    print(f" Date: {r['date']}, Total: {r['total']}, HoldingPnL: {r['holding_pnl']}, Realized: {r['realized_pnl']}, Div: {r['dividend_income']}")
        except Exception as e:
            print(f"Error during calculation: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_performance()
