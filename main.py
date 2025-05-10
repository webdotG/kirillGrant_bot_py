import asyncio
import os
import logging
import requests
from flask import Flask, render_template
from flask_socketio import SocketIO
from api import open_sandbox_account, sandbox_pay_in, get_portfolio, get_current_prices, get_candles, generate_chart_image
from trade import trade_loop
from tg_bot import send_message, bot, dp
from db import init_db
from dotenv import load_dotenv
from news import NewsReader, default_serializer
import json
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

# Настройки для песочницы
SANDBOX_API_URL = "https://sandbox-invest-public-api.tinkoff.ru/openapi"
TINKOFF_TOKEN = os.getenv('TINKOFF_SANDBOX_TOKEN')

# Инициализация модуля новостей
news_reader = NewsReader()

# Инициализация Flask и SocketIO
app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')

# Глобальные переменные
account_id = None
trading_active = False

async def init_sandbox():
    """Инициализация счёта песочницы"""
    global account_id
    try:
        logging.info("Initializing sandbox account...")
        account_id = open_sandbox_account()
        if account_id:
            logging.info(f"Sandbox account created or retrieved: {account_id}")
            sandbox_pay_in(account_id, 100000)
            await send_message(f"Sandbox account initialized: {account_id}")
        else:
            raise Exception("Failed to create or retrieve sandbox account")
    except Exception as e:
        logging.error(f"Sandbox init error: {str(e)}")
        await send_message(f"Failed to initialize sandbox: {str(e)}")
        raise

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    """Обработка подключения клиента"""
    logging.info("Client connected")
    socketio.emit('log', {'message': 'Client connected'})

@socketio.on('command')
def handle_command(data):
    """Обработка команд от клиента"""
    global trading_active
    action = data.get('action')
    
    if action == 'start_trading':
        if not trading_active:
            trading_active = True
            socketio.emit('command_response', {'message': 'Trading started'})
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(start_trading(), loop)
        else:
            socketio.emit('command_response', {'message': 'Trading already active'})
    
    elif action == 'stop_trading':
        if trading_active:
            trading_active = False
            socketio.emit('command_response', {'message': 'Trading stopped'})
        else:
            socketio.emit('command_response', {'message': 'Trading already stopped'})
    
    elif action == 'check_portfolio':
        try:
            if not account_id:
                raise Exception("Sandbox account not initialized")
            portfolio = get_portfolio(account_id)
            socketio.emit('portfolio', portfolio)
        except Exception as e:
            logging.error(f"Portfolio error: {str(e)}")
            socketio.emit('command_response', {'message': f'Portfolio error: {str(e)}'})
    
    elif action == 'refresh_prices':
        try:
            prices = get_current_prices()
            socketio.emit('prices', {'prices': prices})
        except Exception as e:
            logging.error(f"Price update error: {str(e)}")
            socketio.emit('log', {'message': f'Price update error: {str(e)}'})
    
    elif action == 'show_chart':
        try:
            interval = data.get('interval', '1h')
            figi = "BBG004S68CV8"  # ВСМПО-АВИСМА
            interval_map = {
                '1m': 'MINUTE',
                '5m': 'FIVE_MINUTE',
                '15m': 'QUARTER_HOUR',
                '1h': 'HOUR',
                '1d': 'DAY'
            }
            candles = get_candles(figi, interval_map.get(interval, 'HOUR'))
            if candles:
                chart_image = generate_chart_image(candles, interval)
                socketio.emit('chart', {'chartUrl': f'data:image/png;base64,{chart_image}'})
            else:
                socketio.emit('log', {'message': 'No candles data available'})
        except Exception as e:
            logging.error(f"Chart error: {str(e)}")
            socketio.emit('log', {'message': f'Chart error: {str(e)}'})
    
    elif action == 'get_news':
        try:
            source = data.get('source', 'all')
            news = news_reader.get_news(source)
            serialized_news = json.dumps({'news': news}, default=default_serializer)
            socketio.emit('news', serialized_news)
        except Exception as e:
            logging.error(f"News error: {str(e)}")
            socketio.emit('log', {'message': f'News error: {str(e)}'})

async def start_trading():
    """Запуск торгового цикла"""
    global trading_active
    try:
        if not account_id:
            await init_sandbox()
        
        while trading_active:
            await trade_loop(account_id)
            await asyncio.sleep(60)
    except Exception as e:
        logging.error(f"Trading error: {str(e)}")
        trading_active = False
        await send_message(f"Trading stopped due to error: {str(e)}")

async def run_bot():
    """Запуск Telegram-бота"""
    try:
        logging.info("Starting Telegram bot polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Bot polling error: {str(e)}")
        await send_message(f"Bot polling error: {str(e)}")
    finally:
        await bot.session.close()

def run_flask():
    """Запуск Flask-сервера"""
    try:
        socketio.run(app, host='0.0.0.0', port=3000)
    except Exception as e:
        logging.error(f"Flask server error: {str(e)}")

async def main():
    """Основная функция"""
    try:
        init_db()
        await init_sandbox()
        
        bot_task = asyncio.create_task(run_bot())
        flask_task = asyncio.create_task(asyncio.to_thread(run_flask))
        
        await send_message("Trading bot started!")
        
        await asyncio.gather(bot_task, flask_task)
    except Exception as e:
        logging.error(f"Main loop error: {str(e)}")
        await send_message(f"Bot stopped due to error: {str(e)}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Shutting down...")
    except Exception as e:
        logging.error(f"Startup error: {str(e)}")
    finally:
        asyncio.run(bot.session.close())