import yfinance as yf
import argparse
from datetime import datetime, timedelta

def is_bullish_engulfing(prev, curr):
    return (
        prev['Close'] < prev['Open'] and            # previous red
        curr['Close'] > curr['Open'] and            # current green
        curr['Open'] < prev['Close'] and            # green opens below prev close
        curr['Close'] > prev['Open']                # closes above prev open
    )

def is_bearish_engulfing(prev, curr):
    return (
        prev['Close'] > prev['Open'] and            # previous green
        curr['Close'] < curr['Open'] and            # current red
        curr['Open'] > prev['Close'] and            # red opens above prev close
        curr['Close'] < prev['Open']                # closes below prev open
    )

def is_spinning_top(candle):
    body = abs(candle['Close'] - candle['Open'])
    high_tail = candle['High'] - max(candle['Close'], candle['Open'])
    low_tail = min(candle['Close'], candle['Open']) - candle['Low']
    return body < (high_tail + low_tail) * 0.3

def fetch_daily_candle(symbol, date):
    """Fetch OHLC for 1 day before and 1 day after to get prev candle."""
    start = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=3)).strftime("%Y-%m-%d")
    end = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=3)).strftime("%Y-%m-%d")

    data = yf.download(symbol, start=start, end=end, progress=False)
    if data.empty:
        print("No data received from Yahoo Finance.")
        return None, None

    data.index = data.index.strftime("%Y-%m-%d")

    if date not in data.index:
        print(f"No candle found for {date}. Market holiday or data missing.")
        return None, None

    # Get current candle
    curr = data.loc[date]

    # Get previous candle by index position
    idx = list(data.index).index(date)
    if idx == 0:
        print("No previous candle available.")
        return None, None

    prev_date = list(data.index)[idx - 1]
    prev = data.loc[prev_date]

    return prev, curr

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

    # Pattern Detection
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

if __name__ == "__main__":
    main()
