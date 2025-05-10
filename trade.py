import logging
from api import get_portfolio, post_order, get_orders

def trade_loop(account_id):
    """Основной цикл торговли"""
    try:
        # 1. Проверяем текущий портфель
        portfolio = get_portfolio(account_id)
        logging.info(f"Current portfolio: {portfolio}")
        
        # 2. Получаем список активных ордеров
        active_orders = get_orders(account_id)
        logging.info(f"Active orders: {len(active_orders)}")
        
        # 3. Пример простой торговой логики:
        # Если у нас есть RUB и нет активов - покупаем
        # Если есть активы - продаем
        
        total_rub = float(portfolio['totalAmount'])
        positions = portfolio['positions']
        
        if total_rub > 1000 and not positions:
            # Пример: покупаем USD/RUB
            figi = "BBG0013HGFT4"  # FIGI для USD/RUB
            order_response = post_order(
                account_id=account_id,
                figi=figi,
                operation="Buy",
                lots=1  # 1 лот = 1 доллар
            )
            logging.info(f"Buy order placed: {order_response}")
            
        elif positions:
            # Продаем все позиции
            for position in positions:
                order_response = post_order(
                    account_id=account_id,
                    figi=position['figi'],
                    operation="Sell",
                    lots=position['quantity']
                )
                logging.info(f"Sell order placed: {order_response}")
        
        return True
    except Exception as e:
        logging.error(f"Trade error: {str(e)}")
        return False