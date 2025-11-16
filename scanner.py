import requests
import pandas as pd
from datetime import datetime, timedelta
import os

# Load secrets from GitHub
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Send message to Telegram
def notify(msg):
    if BOT_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# TEST message to confirm Telegram is working
notify("Test message from GitHub Actions!")
except:
    pass

# Fetch stock list (NSE)
def get_stock_list():
    url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        data = requests.get(url, headers=headers).json()
        return [item["symbol"] for item in data["data"]]
    except:
        return []

# Candlestick pattern detection
def is_bullish_engulfing(prev, cur):
    return cur['close'] > cur['open'] and prev['open'] > prev['close'] and cur['close'] > prev['open'] and cur['open'] < prev['close']

def is_bearish_engulfing(prev, cur):
    return cur['open'] > cur['close'] and prev['close'] > prev['open'] and cur['open'] > prev['close'] and cur['close'] < prev['open']

def is_spinning_top(candle):
    body = abs(candle['close'] - candle['open'])
    range_candle = candle['high'] - candle['low']
    return body < 0.25 * range_candle

# Send message to Telegram
def notify(msg):
    if BOT_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def fetch_candles(symbol):
    url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        data = requests.get(url, headers=headers).json()
        return data["priceInfo"]["lastPrice"]
    except:
        return None

def run_scan():
    stocks = get_stock_list()
    report = "📊 *Daily NSE Scan Results*\n\n"

    for symbol in stocks[:50]:  # scanning first 50 to reduce load
        price = fetch_candles(symbol)
        if price:
            report += f"{symbol}: ₹{price}\n"

    notify(report)

if __name__ == "__main__":
    run_scan()
