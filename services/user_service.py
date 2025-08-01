# services/user_service.py
import json
import logging
from config import USERS_DATA_FILE

# Словарь для хранения активных пользователей и их сообщений
# Структура: {chat_id: {"crypto": str, "message_id": int, "active": bool, "portfolio": {}}}
active_users = {}

def save_users_data():
    """Сохранение данных пользователей в файл"""
    try:
        with open(USERS_DATA_FILE, 'w', encoding='utf-8') as f:
            data_to_save = {}
            for chat_id, user_data in active_users.items():
                data_to_save[str(chat_id)] = {
                    "active": user_data.get("active", False),
                    "crypto": user_data.get("crypto", "BTC"),
                    "portfolio": user_data.get("portfolio", {})
                }
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        
        active_count = len([u for u in active_users.values() if u.get("active", False)])
        logging.info(f"Saved {len(data_to_save)} users ({active_count} active) to {USERS_DATA_FILE}")
    except Exception as e:
        logging.error(f"Error saving users data: {e}")

def load_users_data():
    """Загрузка данных пользователей из файла"""
    try:
        with open(USERS_DATA_FILE, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            for chat_id_str, user_data in saved_data.items():
                chat_id = int(chat_id_str)
                active_users[chat_id] = {
                    "message_id": None,
                    "active": user_data.get("active", False),
                    "crypto": user_data.get("crypto", "BTC"),
                    "last_price": None,
                    "portfolio": user_data.get("portfolio", {})
                }
        logging.info(f"Loaded {len(saved_data)} users from {USERS_DATA_FILE}")
    except FileNotFoundError:
        logging.info("No saved users data found. Starting fresh.")
    except Exception as e:
        logging.error(f"Error loading users data: {e}")

def get_user(chat_id):
    """Получение данных пользователя или создание нового"""
    if chat_id not in active_users:
        active_users[chat_id] = {
            "message_id": None,
            "active": False,
            "crypto": "BTC",
            "last_price": None,
            "portfolio": {}
        }
    return active_users[chat_id]
