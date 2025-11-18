name: Daily NSE Scanner

on:
  schedule:
    - cron: "0 11 * * 1-5"   # Runs at 4:30 PM IST Monday–Friday
  workflow_dispatch:         # Allows manual run

jobs:
  run-scan:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.10"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install nsepy nsetools pandas requests python-dotenv yfinance

      - name: Run scanner
        env:
          BOT_TOKEN: ${{ secrets.BOT_TOKEN }}
          CHAT_ID: ${{ secrets.CHAT_ID }}
        run: |
          python nse.py
