import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from api import get_current_prices, get_candles, generate_chart_image, get_portfolio, post_order, get_sandbox_accounts
from news import NewsReader
from dotenv import load_dotenv
from io import BytesIO
import base64

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is not set in .env")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot=bot, storage=MemoryStorage())
news_reader = NewsReader()

async def send_message(text):
    if not TELEGRAM_CHAT_ID:
        logging.error("TELEGRAM_CHAT_ID is not set in .env")
        return
    logging.info(f"Sending message to chat {TELEGRAM_CHAT_ID}: {text[:50]}...")
    max_length = 4096
    for i in range(0, len(text), max_length):
        await bot.send_message(TELEGRAM_CHAT_ID, text[i:i + max_length], parse_mode='HTML')

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    logging.info(f"Received /start from chat {message.chat.id}")
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="📈 Current Prices", callback_data="prices"),
            types.InlineKeyboardButton(text="📰 News", callback_data="news")
        ],
        [
            types.InlineKeyboardButton(text="🕯️ 1H Chart", callback_data="chart_1h"),
            types.InlineKeyboardButton(text="📊 1D Chart", callback_data="chart_1d")
        ],
        [
            types.InlineKeyboardButton(text="💼 Portfolio", callback_data="portfolio"),
        ],
        [
            types.InlineKeyboardButton(text="💵 Buy USD/RUB", callback_data="buy_usd_rub"),
            types.InlineKeyboardButton(text="💸 Sell USD/RUB", callback_data="sell_usd_rub")
        ]
    ])
    await message.answer("📊 Trading Bot Menu:", reply_markup=keyboard, parse_mode='HTML')

async def cmd_chart(message: types.Message, interval: str = 'HOUR'):
    figi = "BBG004S68CV8"  # ВСМПО-АВИСМА
    logging.info(f"Fetching chart for figi={figi}, interval={interval}")
    candles = get_candles(figi, interval)
    if not candles:
        await message.answer("Failed to get chart data")
        return
    chart_image = generate_chart_image(candles, interval)
    if not chart_image:
        await message.answer("Failed to generate chart")
        return
    img_data = base64.b64decode(chart_image)
    await message.answer_photo(
        types.InputFile(BytesIO(img_data), filename="chart.png"),
        caption=f"Candlestick Chart ({interval})"
    )

@dp.callback_query()
async def process_button_click(callback_query: types.CallbackQuery):
    data = callback_query.data
    logging.info(f"Received callback query: {data}")
    await callback_query.answer()

    if data == "prices":
        prices = get_current_prices()
        if not prices:
            await callback_query.message.answer("Failed to fetch prices")
            return
        text = "📊 <b>Current Prices:</b>\n\n"
        for asset, price_info in prices.items():
            text += f"• {asset}: {price_info['price']} RUB\n"
        max_length = 4096
        for i in range(0, len(text), max_length):
            await callback_query.message.answer(text[i:i + max_length], parse_mode='HTML')

    elif data == "news":
        news_items = news_reader.get_news()
        if not news_items:
            await callback_query.message.answer("Failed to fetch news")
            return
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
        for i, item in enumerate(news_items[:10], 1):
            keyboard.inline_keyboard.append([
                types.InlineKeyboardButton(
                    text=f"{i}. {item['title'][:50]}...",
                    callback_data=f"news_{i-1}"
                )
            ])
        await callback_query.message.answer("📰 <b>Latest News:</b>", parse_mode='HTML', reply_markup=keyboard)

    elif data == "chart_1h":
        await cmd_chart(callback_query.message, 'HOUR')

    elif data == "chart_1d":
        await cmd_chart(callback_query.message, 'DAY')

    elif data == "portfolio":
        account_id = os.getenv('TINKOFF_ACCOUNT_ID')
        if not account_id:
            accounts = get_sandbox_accounts()
            if not accounts:
                await callback_query.message.answer("No sandbox account found. Please create one.")
                return
            account_id = accounts[0]
            with open('.env', 'a') as f:
                f.write(f"\nTINKOFF_ACCOUNT_ID={account_id}")
        portfolio = get_portfolio(account_id)
        if not portfolio['positions']:
            await callback_query.message.answer("Portfolio is empty")
            return
        text = f"💼 <b>Portfolio</b>\nTotal Amount: {portfolio['totalAmount']} RUB\n\n"
        for pos in portfolio['positions']:
            text += f"• {pos['figi']}: {pos['quantity']} units\n"
        max_length = 4096
        for i in range(0, len(text), max_length):
            await callback_query.message.answer(text[i:i + max_length], parse_mode='HTML')

    elif data in ["buy_usd_rub", "sell_usd_rub"]:
        account_id = os.getenv('TINKOFF_ACCOUNT_ID')
        if not account_id:
            accounts = get_sandbox_accounts()
            if not accounts:
                await callback_query.message.answer("No sandbox account found. Please create one.")
                return
            account_id = accounts[0]
            with open('.env', 'a') as f:
                f.write(f"\nTINKOFF_ACCOUNT_ID={account_id}")
        figi = "BBG004S68CV8"  # ВСМПО-АВИСМА
        lots = 1
        operation = "ORDER_DIRECTION_BUY" if data == "buy_usd_rub" else "ORDER_DIRECTION_SELL"
        result = post_order(account_id, figi, operation, lots)
        if result:
            await callback_query.message.answer(f"{operation} order placed: {result}")
        else:
            await callback_query.message.answer(f"Failed to place {operation} order")

@dp.callback_query(lambda c: c.data.startswith("news_"))
async def process_news_selection(callback_query: types.CallbackQuery):
    news_index = int(callback_query.data.split("_")[1])
    news_items = news_reader.get_news()
    if news_index < len(news_items):
        item = news_items[news_index]
        text = f"<b>{item['title']}</b>\nSource: {item['source']}\nDate: {item['date']}\nLink: {item['url']}"
        max_length = 4096
        for i in range(0, len(text), max_length):
            await callback_query.message.answer(text[i:i + max_length], parse_mode='HTML')
    else:
        await callback_query.message.answer("News item not found.")
    await callback_query.answer()