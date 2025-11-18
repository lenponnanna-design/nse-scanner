import yfinance as yf
import argparse
from datetime import datetime, timedelta
import pandas as pd

# -----------------------------
# Helper to safely extract float
# -----------------------------
def val(x):
    """Convert pandas Series / numpy values to float safely."""
    try:
        return float(x)
    except:
        return float(x.item())

# -----------------------------
# Candlestick Pattern Logic
# -----------------------------
def is_bullish_engulfing(prev, curr):
    pO, pC = val(prev['Open']), val(prev['Close'])
    cO, cC = val(curr['Open']), val(curr['Close'])

    return (
        pC < pO and        # previous red
        cC > cO and        # current green
        cO < pC and        # opens below previous close
        cC > pO            # closes above previous open
    )

def is_bearish_engulfing(prev, curr):
    pO, pC = val(prev['Open']), val(prev['Close'])
    cO, cC = val(curr['Open']), val(curr['Close'])

    return (
        pC > pO and        # previous green
        cC < cO and        # current red
        cO > pC and        # opens above previous close
        cC < pO            # closes below previous open
    )

def is_spinning_top(candle):
    O, C = val(candle['Open']), val(candle['Close'])
    H, L = val(candle['High']), val(candle['Low'])

    body = abs(C - O)
    upper_wick = H - max(O, C)
    lower_wick = min(O, C) - L

    return body < (upper_wick + lower_wick) * 0.3

# -----------------------------
# Fetch candle (previous + target day)
# -----------------------------
def fetch_daily_candle(symbol, date):
    start = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=4)).strftime("%Y-%m-%d")
    end = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=4)).strftime("%Y-%m-%d")

    data = yf.download(symbol, start=start, end=end, progress=False)

    if data.empty:
        print("No data received from Yahoo Finance.")
        return None, None

    # Fix index formatting
    data.index = data.index.strftime("%Y-%m-%d")

    if date not in data.index:
        print(f"No candle found for {date}. Market holiday or missing data.")
        return None, None

    # Current candle
    curr = data.loc[date]

    # Previous candle
    dates = list(data.index)
    idx = dates.index(date)
    if idx == 0:
        print("No previous candle available.")
        return None, None

    prev_date = dates[idx - 1]
    prev = data.loc[prev_date]

    return prev, curr

# -----------------------------
# Main
# -----------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stock", required=True, help="Stock symbol e.g. IOC.NS")
    parser.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    args = parser.parse_args()

    prev, curr = fetch_daily_candle(args.stock, args.date)
    if prev is None or curr is None:
        return

    print("\n--- Candle Data ---")
    print("Previous:", prev.to_dict())
    print("Current:", curr.to_dict())
    print("-------------------\n")

    # Pattern checks
    if is_bearish_engulfing(prev, curr):
        print(f"🔥 BEARISH ENGULFING detected in {args.stock} on {args.date}")
        return

    if is_bullish_engulfing(prev, curr):
        print(f"🔥 BULLISH ENGULFING detected in {args.stock} on {args.date}")
        return

    if is_spinning_top(curr):
        print(f"🌀 SPINNING TOP detected in {args.stock} on {args.date}")
        return

    print(f"No pattern detected for {args.stock} on {args.date}")

# -----------------------------
if __name__ == "__main__":
    main()
