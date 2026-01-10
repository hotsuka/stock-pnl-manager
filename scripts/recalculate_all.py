"""全銘柄の保有情報を移動平均法で再計算するスクリプト"""
from app import create_app, db
from app.models.holding import Holding
from app.services.transaction_service import TransactionService

app = create_app()
ctx = app.app_context()
ctx.push()

print('=' * 60)
print('全銘柄の保有情報を移動平均法で再計算します')
print('=' * 60)

# すべての保有銘柄を取得
holdings = Holding.query.all()

if not holdings:
    print('\n保有銘柄がありません')
else:
    print(f'\n対象銘柄数: {len(holdings)}件\n')

    success_count = 0
    error_count = 0

    for holding in holdings:
        ticker = holding.ticker_symbol
        name = holding.security_name or ticker

        print(f'再計算中: {ticker} ({name})... ', end='', flush=True)

        try:
            # 再計算実行
            TransactionService.recalculate_holding(ticker)
            print('OK')
            success_count += 1
        except Exception as e:
            print(f'ERROR: {str(e)}')
            error_count += 1

    print('\n' + '=' * 60)
    print('再計算完了')
    print('=' * 60)
    print(f'成功: {success_count}件')
    print(f'エラー: {error_count}件')
    print('\nブラウザをリフレッシュして、ダッシュボードを確認してください。')
