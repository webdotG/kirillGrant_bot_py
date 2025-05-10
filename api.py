import os
import requests
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from io import BytesIO
import base64
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

# Конфигурация
TINKOFF_TOKEN = os.getenv('TINKOFF_SANDBOX_TOKEN')
BASE_URL = 'https://sandbox-invest-public-api.tinkoff.ru/rest'

def get_sandbox_accounts():
    """Получить список счетов в песочнице"""
    try:
        response = requests.post(
            f"{BASE_URL}/tinkoff.public.invest.api.contract.v1.UsersService/GetAccounts",
            headers={
                "Authorization": f"Bearer {TINKOFF_TOKEN}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json={}
        )
        response.raise_for_status()
        data = response.json()
        accounts = data.get('accounts', [])
        logging.info(f"Found {len(accounts)} sandbox accounts")
        return [account['id'] for account in accounts]
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error in get_sandbox_accounts: {str(e)}, Response: {e.response.text}")
        return []
    except Exception as e:
        logging.error(f"Error in get_sandbox_accounts: {str(e)}")
        return []

def open_sandbox_account():
    """Создать или получить существующий счёт в песочнице"""
    try:
        # Проверяем существующие счета
        accounts = get_sandbox_accounts()
        if accounts:
            logging.info(f"Found existing sandbox account: {accounts[0]}")
            return accounts[0]
        
        # Создаём новый счёт
        response = requests.post(
            f"{BASE_URL}/tinkoff.public.invest.api.contract.v1.SandboxService/OpenSandboxAccount",
            headers={
                "Authorization": f"Bearer {TINKOFF_TOKEN}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json={}
        )
        response.raise_for_status()
        data = response.json()
        account_id = data['accountId']
        logging.info(f"Created new sandbox account: {account_id}")
        return account_id
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error in open_sandbox_account: {str(e)}, Response: {e.response.text}")
        return None
    except Exception as e:
        logging.error(f"Error in open_sandbox_account: {str(e)}")
        return None

def sandbox_pay_in(account_id, amount):
    """Пополнить счёт песочницы рублями"""
    try:
        response = requests.post(
            f"{BASE_URL}/tinkoff.public.invest.api.contract.v1.SandboxService/SandboxPayIn",
            headers={
                "Authorization": f"Bearer {TINKOFF_TOKEN}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json={
                "accountId": account_id,
                "amount": {
                    "units": str(amount),
                    "nano": 0,
                    "currency": "rub"
                }
            }
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error in sandbox_pay_in: {str(e)}, Response: {e.response.text}")
        return None
    except Exception as e:
        logging.error(f"Error in sandbox_pay_in: {str(e)}")
        return None

def get_portfolio(account_id):
    """Получить портфель"""
    try:
        response = requests.post(
            f"{BASE_URL}/tinkoff.public.invest.api.contract.v1.OperationsService/GetPortfolio",
            headers={
                "Authorization": f"Bearer {TINKOFF_TOKEN}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json={
                "accountId": account_id
            }
        )
        response.raise_for_status()
        data = response.json()
        positions = []
        for item in data.get('positions', []):
            positions.append({
                'figi': item['figi'],
                'quantity': float(item['quantity']['units']) + float(item['quantity']['nano']) / 1e9
            })
        return {
            'totalAmount': float(data.get('totalAmountPortfolio', {}).get('units', 0)),
            'positions': positions
        }
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error in get_portfolio: {str(e)}, Response: {e.response.text}")
        return {'totalAmount': 0, 'positions': []}
    except Exception as e:
        logging.error(f"Error in get_portfolio: {str(e)}")
        return {'totalAmount': 0, 'positions': []}

def get_current_prices():
    """Получить текущие цены валют"""
    try:
        response = requests.post(
            f"{BASE_URL}/tinkoff.public.invest.api.contract.v1.MarketDataService/GetLastPrices",
            headers={
                "Authorization": f"Bearer {TINKOFF_TOKEN}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json={}
        )
        response.raise_for_status()
        data = response.json()
        prices = {}
        for price in data.get('lastPrices', []):
            prices[price['figi']] = {
                'price': float(price['price']['units']) + float(price['price']['nano']) / 1e9,
                'time': price['time']
            }
        return prices
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error in get_current_prices: {str(e)}, Response: {e.response.text}")
        return {}
    except Exception as e:
        logging.error(f"Error in get_current_prices: {str(e)}")
        return {}

def get_available_instruments():
    """Получить список доступных инструментов"""
    try:
        response = requests.post(
            f"{BASE_URL}/tinkoff.public.invest.api.contract.v1.InstrumentsService/Shares",
            headers={
                "Authorization": f"Bearer {TINKOFF_TOKEN}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json={}
        )
        response.raise_for_status()
        data = response.json()
        instruments = []
        for instrument in data.get('instruments', []):
            instruments.append({
                'figi': instrument['figi'],
                'name': instrument['name'],
                'ticker': instrument['ticker']
            })
        return instruments
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error in get_available_instruments: {str(e)}, Response: {e.response.text}")
        return []
    except Exception as e:
        logging.error(f"Error in get_available_instruments: {str(e)}")
        return []

def get_candles(figi, interval='HOUR', days=7):
    """Получить свечи для инструмента"""
    try:
        valid_intervals = ['MINUTE', 'FIVE_MINUTE', 'QUARTER_HOUR', 'HOUR', 'DAY']
        if interval.upper() not in valid_intervals:
            raise ValueError(f"Invalid interval: {interval}. Must be one of {valid_intervals}")

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        logging.info(f"Calling GetCandles with figi={figi}, interval={interval}, from={start_time}, to={end_time}")
        
        response = requests.post(
            f"{BASE_URL}/tinkoff.public.invest.api.contract.v1.MarketDataService/GetCandles",
            headers={
                "Authorization": f"Bearer {TINKOFF_TOKEN}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json={
                "figi": figi,
                "from": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "to": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "interval": f"CANDLE_INTERVAL_{interval.upper()}"
            }
        )
        response.raise_for_status()
        data = response.json()
        candles = []
        for candle in data.get('candles', []):
            candles.append({
                'date': candle['time'],
                'open': float(candle['open']['units']) + float(candle['open']['nano']) / 1e9,
                'high': float(candle['high']['units']) + float(candle['high']['nano']) / 1e9,
                'low': float(candle['low']['units']) + float(candle['low']['nano']) / 1e9,
                'close': float(candle['close']['units']) + float(candle['close']['nano']) / 1e9,
                'volume': int(candle['volume'])
            })
        logging.info(f"Retrieved {len(candles)} candles for figi={figi}")
        return candles
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error in get_candles: {str(e)}, Response: {e.response.text}")
        return []
    except Exception as e:
        logging.error(f"Error in get_candles: {str(e)}")
        return []

def generate_chart_image(candles, title="Price Chart"):
    """Создать изображение графика свечей"""
    try:
        df = pd.DataFrame(candles)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        buffer = BytesIO()
        mpf.plot(df, type='candle', style='charles',
                 title=title,
                 ylabel='Price',
                 savefig=dict(fname=buffer, dpi=100, bbox_inches='tight'))
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')
    except Exception as e:
        logging.error(f"Error in generate_chart_image: {str(e)}")
        return None

def post_order(account_id, figi, operation, lots):
    """Размещение торгового поручения в песочнице"""
    try:
        response = requests.post(
            f"{BASE_URL}/tinkoff.public.invest.api.contract.v1.OrdersService/PostOrder",
            headers={
                "Authorization": f"Bearer {TINKOFF_TOKEN}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json={
                "figi": figi,
                "quantity": lots,
                "direction": operation.upper(),
                "accountId": account_id,
                "orderType": "ORDER_TYPE_MARKET",
                "orderId": str(datetime.now().timestamp())
            }
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error in post_order: {str(e)}, Response: {e.response.text}")
        return None
    except Exception as e:
        logging.error(f"Error in post_order: {str(e)}")
        return None

def get_order_state(account_id, order_id):
    """Получить состояние торгового поручения"""
    try:
        response = requests.post(
            f"{BASE_URL}/tinkoff.public.invest.api.contract.v1.OrdersService/GetOrderState",
            headers={
                "Authorization": f"Bearer {TINKOFF_TOKEN}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json={
                "accountId": account_id,
                "orderId": order_id
            }
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error in get_order_state: {str(e)}, Response: {e.response.text}")
        return None
    except Exception as e:
        logging.error(f"Error in get_order_state: {str(e)}")
        return None

def cancel_order(account_id, order_id):
    """Отменить торговое поручение"""
    try:
        response = requests.post(
            f"{BASE_URL}/tinkoff.public.invest.api.contract.v1.OrdersService/CancelOrder",
            headers={
                "Authorization": f"Bearer {TINKOFF_TOKEN}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json={
                "accountId": account_id,
                "orderId": order_id
            }
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error in cancel_order: {str(e)}, Response: {e.response.text}")
        return None
    except Exception as e:
        logging.error(f"Error in cancel_order: {str(e)}")
        return None

def get_orders(account_id):
    """Получить список активных торговых поручений"""
    try:
        response = requests.post(
            f"{BASE_URL}/tinkoff.public.invest.api.contract.v1.OrdersService/GetOrders",
            headers={
                "Authorization": f"Bearer {TINKOFF_TOKEN}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json={
                "accountId": account_id
            }
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error in get_orders: {str(e)}, Response: {e.response.text}")
        return []
    except Exception as e:
        logging.error(f"Error in get_orders: {str(e)}")
        return []

if __name__ == "__main__":
    instruments = get_available_instruments()
    for instrument in instruments:
        print(f"FIGI: {instrument['figi']}, Name: {instrument['name']}, Ticker: {instrument['ticker']}")