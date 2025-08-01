# config.py
from os import getenv
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

TOKEN = getenv("BOT_TOKEN")
ADMIN_ID = getenv("ADMIN_ID", "0")

# Поддерживаемые криптовалюты
SUPPORTED_CRYPTOS = {
    "BTC": {"name": "Bitcoin", "symbol": "₿", "pair": "btceur"},
    "ETH": {"name": "Ethereum", "symbol": "Ξ", "pair": "etheur"},
    "SOL": {"name": "Solana", "symbol": "◎", "pair": "soleur"},
    "XRP": {"name": "XRP", "symbol": "✕", "pair": "xrpeur"}
}

# Константы
USERS_DATA_FILE = "data/users_data.json"
RECONNECTION_DELAY = 5
UPDATE_FREQUENCY_LIMIT = 1  # секунда между обновлениями
