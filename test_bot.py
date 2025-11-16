import os
import requests
from dotenv import load_dotenv

# Load GitHub secrets if using locally with .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Send test message
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {"chat_id": CHAT_ID, "text": "✅ Telegram bot is working!"}

response = requests.post(url, data=payload)
print(response.text)  # prints Telegram API response
