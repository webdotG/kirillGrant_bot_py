import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('trades.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS candles
                 (figi TEXT, time TEXT, open REAL, high REAL, low REAL, close REAL, volume INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (figi TEXT, direction TEXT, price REAL, quantity INTEGER, time TEXT)''')
    conn.commit()
    conn.close()

def save_candle(figi, candle):
    conn = sqlite3.connect('trades.db')
    c = conn.cursor()
    c.execute('INSERT INTO candles VALUES (?, ?, ?, ?, ?, ?, ?)',
              (figi, candle['time'], candle['open'], candle['high'], candle['low'], candle['close'], candle['volume']))
    conn.commit()
    conn.close()

def save_trade(figi, direction, price, quantity):
    conn = sqlite3.connect('trades.db')
    c = conn.cursor()
    c.execute('INSERT INTO trades VALUES (?, ?, ?, ?, ?)',
              (figi, direction, price, quantity, datetime.now().isoformat()))
    conn.commit()
    conn.close()