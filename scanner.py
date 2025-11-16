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

# Send test message
notify("Test message from GitHub Actions!")

# ---------------------------
# BELOW HERE IS YOUR SCANNER
# ---------------------------

# Fetch stock list (NSE)
def get_stock_list():
    try:
        url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
        headers = {"User-Agent": "Mozilla/5.0"}
        data = requests.get(url, headers=headers).json()
        return [item["symbol"] for item in data["data"]]
    except Exception as e:
        notify(f"Error fetching stock list: {e}")
        return []

# Candlestick pattern detection
def is_bullish_engulfing(prev, cur):
    return (
        cur['close'] > cur['open'] and
        prev['open'] > prev['close'] and
        cur['close'] > prev['open'] and
        cur['open'] < prev['close']
    )

def is_spinning_top(candle):
    body = abs(candle['close'] - candle['open'])
    range_candle = candle['high'] - candle['low']
    return body < 0.25 * range_candle

# Dummy fetcher for now (real one comes later)
def fetch_candles(symbol):
    return {"open": 1, "close": 1, "high": 1, "low": 1}

def run_scan():
    stocks = get_stock_list()
    if not stocks:
        notify("No stocks fetched.")
        return

    notify(f"Scan complete! {len(stocks)} stocks fetched.")

if __name__ == "__main__":
    run_scan()
