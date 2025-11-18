import os
import requests
import pandas as pd
import numpy as np
from nsepy import get_history
from datetime import date, timedelta
from nsetools import Nse
from dotenv import load_dotenv
import time
from collections import defaultdict

# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
LOOKBACK_DAYS = int(os.getenv("LOOKBACK_DAYS", 40))  # for trend line

# ----------------------------
# Telegram messaging
# ----------------------------
def send_telegram_message(message):
    """Send message in chunks if > 4000 chars"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    max_len = 4000
    for i in range(0, len(message), max_len):
        chunk = message[i:i+max_len]
        payload = {"chat_id": CHAT_ID, "text": chunk, "parse_mode": "HTML"}
        try:
            requests.post(url, data=payload)
        except Exception as e:
            print("Error sending Telegram message:", e)

# ----------------------------
# Patterns detection
# ----------------------------
def detect_patterns(df, stock_name):
    messages = []
    if df.empty or len(df) < 2:
        return []

    today = df.iloc[-1]
    yesterday = df.iloc[-2]

    # --- Bullish Engulfing
    if (
        today['Close'] > today['Open'] and
        today['Open'] < yesterday['Close'] and
        today['Close'] > yesterday['Open']
    ):
        messages.append("Bullish Engulfing ✅")

    # --- Piercing Line
    if (
        yesterday['Close'] < yesterday['Open'] and
        today['Close'] > today['Open'] and
        today['Open'] < yesterday['Low'] and
        today['Close'] > (yesterday['Open'] + yesterday['Close']) / 2
    ):
        messages.append("Piercing Line 🟢")

    # --- Hammer
    body = abs(today['Close'] - today['Open'])
    lower_shadow = (today['Open'] - today['Low'] if today['Close'] >= today['Open'] else today['Close'] - today['Low'])
    upper_shadow = today['High'] - max(today['Close'], today['Open'])
    if body <= (today['High'] - today['Low']) * 0.3 and lower_shadow > 2 * body and upper_shadow < body:
        messages.append("Hammer 🔨")

    # --- Spinning Top
    candle_range = today['High'] - today['Low']
    if candle_range > 0 and body / candle_range < 0.3:
        messages.append("Spinning Top 🔹")

    # --- Resistance Breakout (lookback highs)
    if len(df) >= 2:
        prior_high = df['High'][:-1].max()
        if today['Close'] > prior_high:
            messages.append("Resistance Breakout 📈")

    # --- Trend Line Breakout (lookback pivot highs)
    if len(df) >= LOOKBACK_DAYS:
        recent_df = df[-LOOKBACK_DAYS:]
        highs_idx = recent_df['High'].nlargest(3).index
        x = np.array([d.toordinal() for d in highs_idx])
        y = recent_df.loc[highs_idx, 'High'].values
        if len(x) >= 2:
            coeffs = np.polyfit(x, y, 1)  # linear regression
            m, c = coeffs
            trend_y = m * today.name.toordinal() + c
            if today['Close'] >= trend_y * 0.995:  # potential breakout margin
                messages.append("Trend Line Breakout ⬆️")

    # --- Cup & Handle (approx, last 30 days)
    if len(df) >= 30:
        cup_df = df[-30:]
        left_rim = cup_df['High'].max()
        bottom_idx = cup_df['Low'].idxmin()
        bottom_price = cup_df.loc[bottom_idx, 'Low']
        right_rim_df = cup_df.loc[bottom_idx:]
        right_rim_price = right_rim_df['High'].max()
        if abs(right_rim_price - left_rim) / left_rim < 0.05:
            cup_height = left_rim - bottom_price
            handle_df = df.loc[right_rim_df.index[-5]:]
            if handle_df['Low'].min() >= right_rim_price - cup_height / 3:
                messages.append("Cup & Handle ☕️")

    if messages:
        price_change = abs(today['Close'] - today['Open'])
        return [{"stock": stock_name, "message": ", ".join(messages), "change": price_change}]
    return []

# ----------------------------
# Get Nifty groups (example placeholders)
# ----------------------------
def get_nifty_groups():
    nse = Nse()
    # You can replace these lists with actual symbols
    nifty_50 = ["RELIANCE", "TCS", "HDFCBANK", "INFY"]  # placeholder
    nifty_next_50 = ["AUROPHARMA", "ADANIPORTS"]        # placeholder
    nifty_bank = ["ICICIBANK", "KOTAKBANK"]            # placeholder
    nifty_100 = ["BAJAJ-AUTO", "LT"]                   # placeholder
    return [
        ("Nifty 50", nifty_50),
        ("Nifty Next 50", nifty_next_50),
        ("Nifty Bank", nifty_bank),
        ("Nifty 100", nifty_100),
    ]

# ----------------------------
# Main scanning function
# ----------------------------
def scan_stocks(max_patterns=40):
    nse = Nse()
    all_stock_codes = nse.get_stock_codes()[1:]  # skip header
    summary_list = []
    group_lists = get_nifty_groups()
    scanned_stocks = set()

    for group_name, group_stocks in group_lists:
        for stock in group_stocks:
            if stock in scanned_stocks:
                continue
            try:
                df = get_history(symbol=stock, start=date.today()-timedelta(days=60), end=date.today())
                if df.empty:
                    continue
                patterns = detect_patterns(df, stock)
                if patterns:
                    for p in patterns:
                        p['group'] = group_name
                    summary_list.extend(patterns)
                scanned_stocks.add(stock)
                time.sleep(0.1)
            except Exception as e:
                print(f"Skipping {stock}: {e}")
                continue

    # Scan remaining NSE stocks not in priority groups
    for stock in all_stock_codes:
        if stock in scanned_stocks:
            continue
        try:
            df = get_history(symbol=stock, start=date.today()-timedelta(days=60), end=date.today())
            if df.empty:
                continue
            patterns = detect_patterns(df, stock)
            if patterns:
                for p in patterns:
                    p['group'] = "Other NSE"
                summary_list.extend(patterns)
            scanned_stocks.add(stock)
            time.sleep(0.1)
        except Exception as e:
            print(f"Skipping {stock}: {e}")
            continue

    # Sort globally by strength
    summary_list.sort(key=lambda x: x['change'], reverse=True)

    # Send Telegram messages in chunks of max_patterns
    for i in range(0, len(summary_list), max_patterns):
        chunk = summary_list[i:i+max_patterns]
        grouped = defaultdict(list)
        for item in chunk:
            grouped[item['group']].append(f"{item['stock']}: {item['message']}")
        msg_lines = ["📊 <b>NSE Daily Summary</b>:"]
        for group_name in ["Nifty 50", "Nifty Next 50", "Nifty Bank", "Nifty 100", "Other NSE"]:
            if group_name in grouped:
                msg_lines.append(f"\n<b>{group_name}:</b>")
                msg_lines.extend(grouped[group_name])
        send_telegram_message("\n".join(msg_lines))

    if not summary_list:
        send_telegram_message("📊 <b>NSE Daily Summary</b>: No patterns detected today.")

# ----------------------------
# Run scanner
# ----------------------------
if __name__ == "__main__":
    scan_stocks()
