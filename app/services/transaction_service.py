from datetime import datetime
from decimal import Decimal
from app import db
from app.models.transaction import Transaction
from app.models.holding import Holding
from app.models.realized_pnl import RealizedPnl
from app.utils.logger import get_logger, log_database_operation

logger = get_logger('transaction_service')


class TransactionService:
    """取引データ管理サービス"""

    @staticmethod
    def save_transactions(transactions_data):
        """
        取引データを保存

        Args:
            transactions_data: 取引データのリスト

        Returns:
            dict: 保存結果 {'success': 件数, 'failed': 件数, 'errors': エラーリスト}
        """
        logger.info(f"取引データ保存開始: {len(transactions_data)}件")
        success_count = 0
        failed_count = 0
        errors = []

        # 日付順にソート（移動平均法の正確な計算のため）
        sorted_data = sorted(transactions_data, key=lambda x: x.get('transaction_date', ''))

        for data in sorted_data:
            try:
                # 重複チェック
                existing = Transaction.query.filter_by(
                    transaction_date=data['transaction_date'],
                    ticker_symbol=data['ticker_symbol'],
                    quantity=data['quantity'],
                    unit_price=data['unit_price']
                ).first()

                if existing:
                    logger.warning(f"重複取引をスキップ: {data.get('ticker_symbol')} {data.get('transaction_date')}")
                    errors.append({
                        'data': data,
                        'error': '重複する取引が既に存在します'
                    })
                    failed_count += 1
                    continue

                # トランザクション作成
                transaction = Transaction(**data)
                db.session.add(transaction)

                # 保有銘柄を更新
                TransactionService._update_holding(transaction)

                db.session.commit()
                log_database_operation(logger, 'INSERT', 'transactions', f"{data.get('ticker_symbol')} - {data.get('transaction_type')}")
                success_count += 1

            except Exception as e:
                db.session.rollback()
                logger.error(f"取引保存エラー ({data.get('ticker_symbol')}): {str(e)}")
                log_database_operation(logger, 'INSERT', 'transactions', error=str(e))
                errors.append({
                    'data': data,
                    'error': str(e)
                })
                failed_count += 1

        logger.info(f"取引データ保存完了: 成功={success_count}, 失敗={failed_count}")
        return {
            'success': success_count,
            'failed': failed_count,
            'errors': errors
        }

    @staticmethod
    def _update_holding(transaction):
        """保有銘柄を更新（移動平均法）"""
        holding = Holding.query.filter_by(
            ticker_symbol=transaction.ticker_symbol
        ).first()

        if transaction.transaction_type == 'BUY':
            # 買付処理
            # 受渡金額を使用（手数料込みの実際の支払額）
            transaction_cost = transaction.settlement_amount if transaction.settlement_amount else (transaction.quantity * transaction.unit_price + (transaction.commission or 0))

            if holding:
                # 既存保有銘柄の平均単価を更新（移動平均法）
                total_cost = holding.total_cost + transaction_cost
                total_quantity = holding.total_quantity + transaction.quantity
                holding.average_cost = total_cost / total_quantity
                holding.total_quantity = total_quantity
                holding.total_cost = total_cost
            else:
                # 新規保有銘柄
                holding = Holding(
                    ticker_symbol=transaction.ticker_symbol,
                    security_name=transaction.security_name,
                    total_quantity=transaction.quantity,
                    average_cost=transaction_cost / transaction.quantity,
                    currency=transaction.currency,
                    total_cost=transaction_cost
                )
                db.session.add(holding)

        elif transaction.transaction_type == 'SELL':
            # 売却処理
            if not holding:
                raise ValueError(f"保有していない銘柄を売却しようとしています: {transaction.ticker_symbol}")

            if holding.total_quantity < transaction.quantity:
                raise ValueError(f"保有数量が不足しています: {transaction.ticker_symbol}")

            # 確定損益を計算 (JPYベース)
            # transaction.settlement_amount は常に受渡金額 (JPY)
            sell_proceeds_jpy = Decimal(str(transaction.settlement_amount or 0))
            cost_basis_jpy = Decimal(str(holding.average_cost or 0)) * Decimal(str(transaction.quantity or 0))
            realized_pnl = sell_proceeds_jpy - cost_basis_jpy
            
            realized_pnl_pct = None
            if holding.average_cost > 0:
                cost_basis = holding.average_cost * transaction.quantity
                realized_pnl_pct = (realized_pnl / cost_basis) * 100

            # 確定損益を記録
            pnl_record = RealizedPnl(
                ticker_symbol=transaction.ticker_symbol,
                sell_date=transaction.transaction_date,
                quantity=transaction.quantity,
                average_cost=holding.average_cost,
                sell_price=transaction.unit_price,
                realized_pnl=realized_pnl,
                realized_pnl_pct=realized_pnl_pct,
                commission=transaction.commission,
                currency=transaction.currency
            )
            db.session.add(pnl_record)

            # 保有数量を減少
            holding.total_quantity -= transaction.quantity
            holding.total_cost = holding.total_quantity * holding.average_cost

            # 保有数量が0になった場合は削除
            if holding.total_quantity == 0:
                db.session.delete(holding)

    @staticmethod
    def check_duplicate(transaction_date, ticker_symbol, quantity, unit_price):
        """重複チェック"""
        return Transaction.query.filter_by(
            transaction_date=transaction_date,
            ticker_symbol=ticker_symbol,
            quantity=quantity,
            unit_price=unit_price
        ).first() is not None

    @staticmethod
    def recalculate_holding(ticker_symbol):
        """
        指定された銘柄の保有情報を取引履歴から再計算
        取引削除後などに使用
        """
        # 既存の保有情報を削除
        holding = Holding.query.filter_by(ticker_symbol=ticker_symbol).first()
        if holding:
            db.session.delete(holding)

        # 既存の確定損益を削除
        RealizedPnl.query.filter_by(ticker_symbol=ticker_symbol).delete()

        # 取引履歴を日付順に取得
        transactions = Transaction.query.filter_by(
            ticker_symbol=ticker_symbol
        ).order_by(Transaction.transaction_date).all()

        if not transactions:
            # 取引がない場合は終了
            db.session.commit()
            return

        # 取引を順番に処理して保有情報を再構築
        current_holding = None

        for transaction in transactions:
            if transaction.transaction_type == 'BUY':
                # 受渡金額を使用（手数料込みの実際の支払額）
                transaction_cost = transaction.settlement_amount if transaction.settlement_amount else (transaction.quantity * transaction.unit_price + (transaction.commission or 0))

                if current_holding:
                    # 平均単価を更新（移動平均法）
                    total_cost = current_holding['total_cost'] + transaction_cost
                    total_quantity = current_holding['total_quantity'] + transaction.quantity
                    current_holding['average_cost'] = total_cost / total_quantity
                    current_holding['total_quantity'] = total_quantity
                    current_holding['total_cost'] = total_cost
                else:
                    # 初回買付
                    current_holding = {
                        'ticker_symbol': transaction.ticker_symbol,
                        'security_name': transaction.security_name,
                        'total_quantity': transaction.quantity,
                        'average_cost': transaction_cost / transaction.quantity,
                        'currency': transaction.currency,
                        'total_cost': transaction_cost
                    }

            elif transaction.transaction_type == 'SELL':
                if not current_holding or current_holding['total_quantity'] < transaction.quantity:
                    # データ不整合の場合はスキップ
                    continue

                # 確定損益を計算 (JPYベース)
                # transaction.settlement_amount は常に受渡金額 (JPY)
                sell_proceeds_jpy = Decimal(str(transaction.settlement_amount or 0))
                cost_basis_jpy = Decimal(str(current_holding['average_cost'] or 0)) * Decimal(str(transaction.quantity or 0))
                realized_pnl = sell_proceeds_jpy - cost_basis_jpy

                realized_pnl_pct = None
                if current_holding['average_cost'] > 0:
                    cost_basis = current_holding['average_cost'] * transaction.quantity
                    realized_pnl_pct = (realized_pnl / cost_basis) * 100

                # 確定損益を記録
                pnl_record = RealizedPnl(
                    ticker_symbol=transaction.ticker_symbol,
                    sell_date=transaction.transaction_date,
                    quantity=transaction.quantity,
                    average_cost=current_holding['average_cost'],
                    sell_price=transaction.unit_price,
                    realized_pnl=realized_pnl,
                    realized_pnl_pct=realized_pnl_pct,
                    commission=transaction.commission,
                    currency=transaction.currency
                )
                db.session.add(pnl_record)

                # 保有数量を減少
                current_holding['total_quantity'] -= transaction.quantity
                current_holding['total_cost'] = current_holding['total_quantity'] * current_holding['average_cost']

                # 保有数量が0になった場合
                if current_holding['total_quantity'] == 0:
                    current_holding = None

        # 最終的な保有情報を保存
        if current_holding and current_holding['total_quantity'] > 0:
            new_holding = Holding(**current_holding)
            db.session.add(new_holding)

        db.session.commit()

    @staticmethod
    def recalculate_all_holdings():
        """全銘柄の保有情報を取引履歴から再計算"""
        from app.models.transaction import Transaction
        
        # 取引履歴にある全銘柄を抽出
        tickers = db.session.query(Transaction.ticker_symbol).distinct().all()
        ticker_list = [t[0] for t in tickers]
        
        print(f"Recalculating {len(ticker_list)} holdings...")
        for ticker in ticker_list:
            TransactionService.recalculate_holding(ticker)
        
        print("Recalculation complete.")
