import os
import requests
import pandas as pd
from nsepy import get_history
from datetime import date, timedelta
from nsetools import Nse
from dotenv import load_dotenv

# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ----------------------------
# Telegram messaging
# ----------------------------
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print("Failed to send message:", response.text)
    except Exception as e:
        print("Error sending Telegram message:", e)

# ----------------------------
# Candlestick patterns detection
# ----------------------------
def detect_patterns(df, stock_name):
    messages = []
    if df.empty:
        return messages

    today = df.iloc[-1]
    if len(df) >= 2:
        yesterday = df.iloc[-2]

        # Bullish Engulfing
        if today['Close'] > today['Open'] and today['Open'] < yesterday['Close'] and today['Close'] > yesterday['Open']:
            messages.append(f"{stock_name}: Bullish Engulfing ✅")

        # Hammer
        body = abs(today['Close'] - today['Open'])
        lower_shadow = today['Open'] - today['Low'] if today['Close'] >= today['Open'] else today['Close'] - today['Low']
        upper_shadow = today['High'] - max(today['Close'], today['Open'])
        if body <= (today['High'] - today['Low']) * 0.3 and lower_shadow > 2 * body and upper_shadow < body:
            messages.append(f"{stock_name}: Hammer 🔨")

        # Shooting Star
        if body <= (today['High'] - today['Low']) * 0.3 and upper_shadow > 2 * body and lower_shadow < body:
            messages.append(f"{stock_name}: Shooting Star 🌟")

    # Spinning Top
    body = abs(today['Close'] - today['Open'])
    candle_range = today['High'] - today['Low']
    if candle_range > 0 and body / candle_range < 0.3:
        messages.append(f"{stock_name}: Spinning Top 🔹")

    # Resistance breakout (today's close > yesterday's high)
    if len(df) >= 2 and today['Close'] > df['High'].max():
        messages.append(f"{stock_name}: Resistance Breakout 📈")

    # Trend line breakout (today's close > 5-day moving average)
    if len(df) >= 5:
        ma5 = df['Close'][-5:].mean()
        if today['Close'] > ma5:
            messages.append(f"{stock_name}: Trend Line Breakout ⬆️")

    return messages

# ----------------------------
# Scan all NSE stocks and send summary
# ----------------------------
def scan_stocks(limit=40):
    nse = Nse()
    stock_codes = nse.get_stock_codes()[1:]  # skip SYMBOL header

    summary_messages = []

    for stock in stock_codes:
        if len(summary_messages) >= limit:
            break
        try:
            df = get_history(symbol=stock, start=date.today(), end=date.today())
            patterns = detect_patterns(df, stock)
            if patterns:
                summary_messages.append(", ".join(patterns))  # combine multiple patterns per stock
        except Exception as e:
            print(f"Error scanning {stock}: {e}")

    if summary_messages:
        summary_text = "📊 NSE Daily Summary:\n" + "\n".join(summary_messages)
        send_telegram_message(summary_text)
    else:
        send_telegram_message("📊 NSE Daily Summary: No patterns detected today.")

# ----------------------------
# Run scanner
# ----------------------------
if __name__ == "__main__":
    scan_stocks()
