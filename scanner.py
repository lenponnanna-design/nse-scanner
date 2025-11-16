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
# Detect candlestick patterns
# ----------------------------
def detect_patterns(df, stock_name):
    messages = []
    if df.empty:
        return messages
    
    # Bullish Engulfing
    if len(df) >= 2:
        if df['Close'].iloc[-1] > df['Open'].iloc[-1] and df['Open'].iloc[-1] < df['Close'].iloc[-2] and df['Close'].iloc[-1] > df['Open'].iloc[-2]:
            messages.append(f"{stock_name}: Bullish Engulfing ✅")
    
    # Spinning Top
    last_candle = df.iloc[-1]
    body = abs(last_candle['Close'] - last_candle['Open'])
    candle_range = last_candle['High'] - last_candle['Low']
    if candle_range > 0 and body / candle_range < 0.3:
        messages.append(f"{stock_name}: Spinning Top 🔹")
    
    return messages

# ----------------------------
# Scan all NSE stocks
# ----------------------------
def scan_stocks(limit=20):
    nse = Nse()
    stock_codes = list(nse.get_stock_codes().keys())[1:]  # skip first 'SYMBOL'
    
    end_date = date.today()
    start_date = end_date - timedelta(days=5)
    
    summary_messages = []
    
    for stock in stock_codes:
        if len(summary_messages) >= limit:
            break
        try:
            df = get_history(symbol=stock, start=start_date, end=end_date)
            patterns = detect_patterns(df, stock)
            if patterns:
                summary_messages.append(patterns[0])  # take first pattern per stock
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
