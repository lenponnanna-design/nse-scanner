import os
import requests
import pandas as pd
from nsepy import get_history
from datetime import date, timedelta
from dotenv import load_dotenv
import time

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
        # Split into 4000-char chunks
        max_len = 4000
        for i in range(0, len(message), max_len):
            requests.post(url, data={"chat_id": CHAT_ID, "text": message[i:i+max_len], "parse_mode": "HTML"})
    except Exception as e:
        print("Error sending Telegram message:", e)

# ----------------------------
# Candlestick pattern detection
# ----------------------------
def detect_patterns(df, stock_name):
    messages = []
    if df.empty or len(df) < 2:
        return messages

    today = df.iloc[-1]
    yesterday = df.iloc[-2]

    # Bullish Engulfing
    if today['Close'] > today['Open'] and today['Open'] < yesterday['Close'] and today['Close'] > yesterday['Open']:
        messages.append("Bullish Engulfing ✅")

    # Piercing Line
    if today['Open'] < yesterday['Low'] and today['Close'] > yesterday['Close']*0.5 and today['Close'] < yesterday['Open']:
        messages.append("Piercing Line 💡")

    # Hammer
    body = abs(today['Close'] - today['Open'])
    lower_shadow = today['Open'] - today['Low'] if today['Close'] >= today['Open'] else today['Close'] - today['Low']
    upper_shadow = today['High'] - max(today['Close'], today['Open'])
    if body <= (today['High'] - today['Low']) * 0.3 and lower_shadow > 2 * body and upper_shadow < body:
        messages.append("Hammer 🔨")

    # Spinning Top
    candle_range = today['High'] - today['Low']
    if candle_range > 0 and body / candle_range < 0.3:
        messages.append("Spinning Top 🔹")

    # Resistance Breakout
    if today['Close'] > df['High'].max():
        messages.append("Resistance Breakout 📈")

    # Trendline Breakout (last 2 months ~ 60 days)
    if len(df) >= 10:
        # Simple trendline: connect lowest points in downtrend to rising price
        df_last = df[-60:] if len(df) > 60 else df
        lows = df_last['Low']
        min_idx = lows.idxmin()
        min_val = lows.min()
        if today['Close'] > min_val:
            messages.append("Trendline Breakout ⬆️")

    if messages:
        return [{
            "stock": stock_name,
            "message": ", ".join(messages)
        }]
    return []

# ----------------------------
# Nifty groups prioritization
# ----------------------------
def get_nifty_groups():
    # Hardcoded Nifty lists (can update manually if needed)
    nifty_50 = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "HDFC", "ICICIBANK"]
    nifty_next_50 = ["BAJFINANCE", "BHARTIARTL", "TECHM", "ADANITRANS"]
    nifty_bank = ["AXISBANK", "KOTAKBANK", "SBIN"]
    nifty_100 = ["LT", "ITC", "SUNPHARMA", "MARUTI"]
    return [nifty_50, nifty_next_50, nifty_bank, nifty_100]

# ----------------------------
# Scan NSE stocks
# ----------------------------
def scan_stocks():
    limit_per_msg = 40
    summary_list = []

    for group in get_nifty_groups():
        for stock in group:
            try:
                df = get_history(
                    symbol=stock,
                    start=date.today() - timedelta(days=10),
                    end=date.today()
                )
                if df.empty:
                    continue

                patterns = detect_patterns(df, stock)
                if patterns:
                    summary_list.extend(patterns)

                time.sleep(0.1)

                # Send batch every 40
                if len(summary_list) >= limit_per_msg:
                    msg_text = "📊 <b>NSE Daily Summary</b>:\n" + "\n".join(
                        [f"<b>{item['stock']}</b>: {item['message']}" for item in summary_list[:limit_per_msg]]
                    )
                    send_telegram_message(msg_text)
                    summary_list = summary_list[limit_per_msg:]

            except Exception as e:
                print(f"Skipping {stock}: {e}")
                continue

    # Send remaining
    if summary_list:
        msg_text = "📊 <b>NSE Daily Summary</b>:\n" + "\n".join(
            [f"<b>{item['stock']}</b>: {item['message']}" for item in summary_list]
        )
        send_telegram_message(msg_text)
    elif not summary_list:
        send_telegram_message("📊 <b>NSE Daily Summary</b>: No patterns detected today.")

# ----------------------------
# Run scanner
# ----------------------------
if __name__ == "__main__":
    scan_stocks()
