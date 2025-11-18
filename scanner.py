import os
import requests
import pandas as pd
import numpy as np
from nsepy import get_history
from datetime import date, timedelta
from nsetools import Nse
from dotenv import load_dotenv
import time
import yfinance as yf
from scipy.signal import find_peaks
from collections import defaultdict

# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
LOOKBACK_DAYS = int(os.getenv("LOOKBACK_DAYS", 40))

# ----------------------------
# Telegram messaging
# ----------------------------
def send_telegram_message(message):
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
# Fetch historical data (nsepy with yfinance fallback)
# ----------------------------
def fetch_history(stock_symbol, start_date, end_date):
    try:
        df = get_history(symbol=stock_symbol, start=start_date, end=end_date)
        if df.empty:
            raise ValueError("Empty data from nsepy")
        return df
    except:
        try:
            df = yf.download(stock_symbol + ".NS", start=start_date, end=end_date, progress=False)
            if df.empty:
                return pd.DataFrame()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(0)
            df.index = pd.to_datetime(df.index)
            df.index.name = None
            df = df.rename(columns={"Close": "Close", "Open": "Open", "High": "High", "Low": "Low"})
            return df
        except Exception as e:
            print(f"Failed to fetch data for {stock_symbol}: {e}")
            return pd.DataFrame()

# ----------------------------
# Patterns detection
# ----------------------------
def detect_patterns(df, stock_name):
    patterns_list = []
    if df.empty or len(df) < 2:
        return []

    today = df.iloc[-1]
    yesterday = df.iloc[-2]
    messages = []

    # Bullish Engulfing
    if today['Close'] > today['Open'] and today['Open'] < yesterday['Close'] and today['Close'] > yesterday['Open']:
        messages.append("Bullish Engulfing ✅")

    # Piercing Line
    if yesterday['Close'] < yesterday['Open'] and today['Close'] > today['Open'] and today['Open'] < yesterday['Low'] and today['Close'] > (yesterday['Close'] + yesterday['Open'])/2:
        messages.append("Piercing Line 🟢")

    # Hammer
    body = abs(today['Close'] - today['Open'])
    lower_shadow = (today['Open'] - today['Low'] if today['Close'] >= today['Open'] else today['Close'] - today['Low'])
    upper_shadow = today['High'] - max(today['Close'], today['Open'])
    if body <= (today['High'] - today['Low']) * 0.3 and lower_shadow > 2*body and upper_shadow < body:
        messages.append("Hammer 🔨")

    # Spinning Top
    candle_range = today['High'] - today['Low']
    if candle_range > 0 and body / candle_range < 0.3:
        messages.append("Spinning Top 🔹")

    # Resistance Breakout
    if len(df) >= 2:
        prior_high = df['High'][:-1].max()
        if today['Close'] > prior_high:
            messages.append("Resistance Breakout 📈")

    # Trend Line Breakout using scipy peaks
    if len(df) >= LOOKBACK_DAYS:
        recent_df = df[-LOOKBACK_DAYS:]
        highs = recent_df['High'].values
        x_vals = np.arange(len(highs))
        peak_indices, _ = find_peaks(highs, distance=3)
        if len(peak_indices) >= 2:
            y = highs[peak_indices]
            x = x_vals[peak_indices]
            m, c = np.polyfit(x, y, 1)
            trend_y = m * (len(highs)-1) + c
            if today['Close'] >= trend_y * 0.995:
                messages.append("Trend Line Breakout ⬆️")

    # Cup & Handle detection (approx, 30 days)
    if len(df) >= 30:
        cup_df = df[-30:]
        left_rim = cup_df['High'].max()
        bottom_idx = cup_df['Low'].idxmin()
        bottom_price = cup_df.loc[bottom_idx, 'Low']
        right_rim_df = cup_df.loc[bottom_idx:]
        right_rim_price = right_rim_df['High'].max()
        if abs(right_rim_price - left_rim)/left_rim < 0.05:
            cup_height = left_rim - bottom_price
            handle_df = df.loc[right_rim_df.index[-5]:]
            if handle_df['Low'].min() >= right_rim_price - cup_height/3:
                messages.append("Cup & Handle ☕️")

    if messages:
        price_change = abs(today['Close'] - today['Open'])
        patterns_list.append({"stock": stock_name, "message": ", ".join(messages), "change": price_change})
    return patterns_list

# ----------------------------
# Static Nifty Lists
# ----------------------------
def get_nifty_groups():
    # Nifty 50 (top 50 large-cap stocks)
    nifty_50 = [
        "RELIANCE","TCS","HDFCBANK","INFY","HDFC","ICICIBANK","KOTAKBANK",
        "SBIN","LT","ITC","AXISBANK","HCLTECH","BHARTIARTL","ASIANPAINT",
        "BAJFINANCE","MARUTI","NESTLEIND","SUNPHARMA","HDFC LIFE","TECHM",
        # ... add all Nifty 50 symbols here
    ]

    # Nifty Next 50 (mid-cap)
    nifty_next_50 = [
        "ADANITRANS","BANDHANBNK","ALOKINDS","MUTHOOTFIN","ICICIPRULI",
        # ... add all Nifty Next 50 symbols here
    ]

    # Nifty Bank
    nifty_bank = ["HDFCBANK","ICICIBANK","KOTAKBANK","SBIN","AXISBANK"]

    # Nifty 100 (can be combination of above)
    nifty_100 = list(set(nifty_50 + nifty_next_50))

    return [
        ("Nifty 50", nifty_50),
        ("Nifty Next 50", nifty_next_50),
        ("Nifty Bank", nifty_bank),
        ("Nifty 100", nifty_100)
    ]

# ----------------------------
# Main Scanner
# ----------------------------
def scan_stocks(max_patterns=40):
    nse = Nse()
    all_stock_codes = nse.get_stock_codes()[1:]
    summary_list = []
    group_lists = get_nifty_groups()
    scanned_stocks = set()

    # Scan priority groups
    for group_name, group_stocks in group_lists:
        for stock in group_stocks:
            if stock in scanned_stocks:
                continue
            df = fetch_history(stock, date.today()-timedelta(days=60), date.today())
            if df.empty:
                continue
            patterns = detect_patterns(df, stock)
            for p in patterns:
                p['group'] = group_name
            summary_list.extend(patterns)
            scanned_stocks.add(stock)
            time.sleep(0.1)

    # Scan remaining NSE stocks
    for stock in all_stock_codes:
        if stock in scanned_stocks:
            continue
        df = fetch_history(stock, date.today()-timedelta(days=60), date.today())
        if df.empty:
            continue
        patterns = detect_patterns(df, stock)
        for p in patterns:
            p['group'] = "Other NSE"
        summary_list.extend(patterns)
        scanned_stocks.add(stock)
        time.sleep(0.1)

    # Sort globally by candle strength
    summary_list.sort(key=lambda x: x['change'], reverse=True)

    # Send messages in chunks of max_patterns
    for i in range(0, len(summary_list), max_patterns):
        chunk = summary_list[i:i+max_patterns]
        grouped = defaultdict(list)
        for item in chunk:
            grouped[item['group']].append(f"{item['stock']}: {item['message']}")
        msg_lines = ["📊 <b>NSE Daily Summary</b>:"]
        for group_name in ["Nifty 50","Nifty Next 50","Nifty Bank","Nifty 100","Other NSE"]:
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
