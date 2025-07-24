import asyncio
import requests
import sys
import logging
import json
import websockets
import time
from datetime import datetime
from os import getenv
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

TOKEN = getenv("BOT_TOKEN")

# Глобальные переменные для отслеживания цены и пользователей
price_data = {"price": None, "last_update": 0}
bot = None
last_message_update = 0

# Словарь для хранения активных пользователей и их сообщений
# Структура: {chat_id: {"message_id": int, "active": bool}}
active_users = {}

# Константы
USERS_DATA_FILE = "users_data.json"
RECONNECTION_DELAY = 5
UPDATE_FREQUENCY_LIMIT = 3  # секунды между обновлениями

def save_users_data():
    """Сохранение данных пользователей в файл"""
    try:
        with open(USERS_DATA_FILE, 'w', encoding='utf-8') as f:
            # Сохраняем только активных пользователей (без message_id для безопасности)
            data_to_save = {
                str(chat_id): {"active": user_data["active"]} 
                for chat_id, user_data in active_users.items() 
                if user_data["active"]
            }
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        logging.info(f"Saved {len(data_to_save)} active users to {USERS_DATA_FILE}")
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
                    "message_id": None,  # Сбрасываем message_id после перезапуска
                    "active": user_data.get("active", False)
                }
        logging.info(f"Loaded {len(saved_data)} users from {USERS_DATA_FILE}")
    except FileNotFoundError:
        logging.info("No saved users data found. Starting fresh.")
    except Exception as e:
        logging.error(f"Error loading users data: {e}")

dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    text = f"Привет, {html.bold(message.from_user.full_name)}! 👋\n\n"\
           f"🤖 <b>Crypto-check Bot</b> - твой помощник для отслеживания криптовалют!\n\n"\
           f"📋 <b>Доступные команды:</b>\n"\
           f"• /checkCrypto - получить текущую цену BTC\n"\
           f"• /start_updates - включить автообновления цены\n"\
           f"• /stop_updates - отключить автообновления\n"\
           f"• /status - статус ваших подписок\n\n"\
           f"🔔 <i>Автообновления показывают цену в реальном времени!</i>"
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command('checkCrypto'))
async def check_crypto_handler(message: Message) -> None:
    """Команда для получения актуальной цены BTC"""
    if price_data["price"] is not None:
        formatted_price = f"{price_data['price']:,.2f}"
        if price_data["last_update"]:
            update_time = datetime.fromtimestamp(price_data["last_update"]).strftime("%H:%M:%S")
            text = f"💰 <b>BTC/USDT</b>: ${formatted_price}\n📊 Данные получены через WebSocket Binance\n🔄 Последнее обновление: {update_time}"
        else:
            text = f"💰 <b>BTC/USDT</b>: ${formatted_price}\n📊 Данные получены через WebSocket Binance"
        await message.answer(text, parse_mode=ParseMode.HTML)
    else:
        await message.answer("⏳ Цена еще загружается, попробуйте через несколько секунд...")

@dp.message(Command('start_updates'))
async def start_updates_handler(message: Message) -> None:
    """Включить автообновления для пользователя"""
    chat_id = message.chat.id
    
    if chat_id in active_users and active_users[chat_id]["active"]:
        await message.answer("✅ Автообновления уже включены!\nИспользуйте /stop_updates для отключения.")
        return
    
    # Добавляем пользователя в активные
    active_users[chat_id] = {"message_id": None, "active": True}
    save_users_data()  # Сохраняем изменения
    
    await message.answer("🔔 <b>Автообновления включены!</b>\n"\
                        "Сообщение с ценой будет обновляться в реальном времени.\n"\
                        "Используйте /stop_updates для отключения.", 
                        parse_mode=ParseMode.HTML)
    
    # Отправляем первое сообщение с ценой
    await send_initial_price_message(chat_id)

@dp.message(Command('stop_updates'))
async def stop_updates_handler(message: Message) -> None:
    """Отключить автообновления для пользователя"""
    chat_id = message.chat.id
    
    if chat_id not in active_users or not active_users[chat_id]["active"]:
        await message.answer("❌ Автообновления не были включены.")
        return
    
    # Деактивируем пользователя
    active_users[chat_id]["active"] = False
    save_users_data()  # Сохраняем изменения
    
    await message.answer("🔕 <b>Автообновления отключены!</b>\n"\
                        "Используйте /start_updates для включения.", 
                        parse_mode=ParseMode.HTML)

@dp.message(Command('status'))
async def status_handler(message: Message) -> None:
    """Показать статус подписок пользователя"""
    chat_id = message.chat.id
    
    if chat_id in active_users and active_users[chat_id]["active"]:
        status = "🔔 <b>Включены</b>"
        message_info = f"Message ID: {active_users[chat_id]['message_id']}" if active_users[chat_id]['message_id'] else "Сообщение еще не создано"
    else:
        status = "🔕 <b>Отключены</b>"
        message_info = "Автообновления неактивны"
    
    total_users = len([u for u in active_users.values() if u["active"]])
    
    text = f"📊 <b>Статус автообновлений:</b>\n"\
           f"Ваш статус: {status}\n"\
           f"Детали: {message_info}\n\n"\
           f"👥 Всего активных пользователей: {total_users}\n"\
           f"💰 Цена BTC: ${price_data['price']:,.2f}" if price_data['price'] else "💰 Цена загружается..."
    
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command('admin_stats'))
async def admin_stats_handler(message: Message) -> None:
    """Административная команда для просмотра статистики (только для разработчика)"""
    # Базовая проверка - можно улучшить
    if message.from_user.id != int(getenv("ADMIN_ID", "0")):
        await message.answer("❌ Недостаточно прав доступа.")
        return
    
    total_users = len(active_users)
    active_count = len([u for u in active_users.values() if u["active"]])
    inactive_count = total_users - active_count
    
    # Статистика WebSocket
    connection_status = "🟢 Подключен" if price_data["price"] else "🔴 Отключен"
    last_update = datetime.fromtimestamp(price_data["last_update"]).strftime("%H:%M:%S") if price_data["last_update"] else "Нет данных"
    
    text = f"🔧 <b>Административная панель</b>\n\n"\
           f"👥 <b>Статистика пользователей:</b>\n"\
           f"• Всего зарегистрировано: {total_users}\n"\
           f"• Активных подписок: {active_count}\n"\
           f"• Неактивных: {inactive_count}\n\n"\
           f"📡 <b>WebSocket статус:</b>\n"\
           f"• Соединение: {connection_status}\n"\
           f"• Последнее обновление: {last_update}\n"\
           f"• Текущая цена: ${price_data['price']:,.2f}" if price_data['price'] else "• Цена: Загружается..."
    
    await message.answer(text, parse_mode=ParseMode.HTML)

async def send_initial_price_message(chat_id):
    """Отправка первого сообщения с ценой для пользователя"""
    if price_data["price"] is None:
        # Ждем загрузки цены
        for _ in range(10):  # Максимум 10 секунд
            if price_data["price"] is not None:
                break
            await asyncio.sleep(1)
    
    if price_data["price"] is not None:
        await update_user_message(chat_id)
    else:
        # Отправляем сообщение о загрузке
        try:
            msg = await bot.send_message(
                chat_id=chat_id,
                text="⏳ <b>Загрузка данных...</b>\nЦена появится через несколько секунд.",
                parse_mode=ParseMode.HTML
            )
            active_users[chat_id]["message_id"] = msg.message_id
        except Exception as e:
            logging.error(f"Error sending initial message to {chat_id}: {e}")

async def update_user_message(chat_id):
    """Обновление сообщения для конкретного пользователя"""
    if chat_id not in active_users or not active_users[chat_id]["active"]:
        return
    
    if price_data["price"] is None:
        return
    
    try:
        formatted_price = f"{price_data['price']:,.2f}"
        update_time = datetime.fromtimestamp(price_data["last_update"]).strftime("%H:%M:%S")
        text = f"💰 <b>BTC/USDT</b>: ${formatted_price}\n🔄 Обновлено: {update_time} (Реальное время)"
        
        if active_users[chat_id]["message_id"] is None:
            # Отправляем новое сообщение
            msg = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML
            )
            active_users[chat_id]["message_id"] = msg.message_id
            logging.info(f"Sent initial price message to {chat_id}")
        else:
            # Обновляем существующее сообщение
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=active_users[chat_id]["message_id"],
                text=text,
                parse_mode=ParseMode.HTML
            )
            logging.debug(f"Updated price message for {chat_id}")
            
    except Exception as e:
        logging.error(f"Error updating message for {chat_id}: {e}")
        # Если сообщение не найдено, сбрасываем ID
        if "message to edit not found" in str(e).lower():
            active_users[chat_id]["message_id"] = None

async def update_all_users():
    """Обновление сообщений для всех активных пользователей"""
    global last_message_update
    
    current_time = time.time()
    
    # Ограничиваем частоту обновлений
    if current_time - last_message_update < UPDATE_FREQUENCY_LIMIT:
        return
    
    if not bot or price_data["price"] is None:
        return
    
    # Обновляем сообщения для всех активных пользователей
    active_count = 0
    for chat_id, user_data in active_users.items():
        if user_data["active"]:
            await update_user_message(chat_id)
            active_count += 1
    
    if active_count > 0:
        logging.debug(f"Updated messages for {active_count} active users")
    
    last_message_update = current_time

async def get_price():
    """Получение цены BTC через WebSocket Binance с автоматическим переподключением"""
    uri = "wss://stream.binance.com:9443/ws/btcusdt@ticker"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                logging.info("WebSocket connected to Binance")
                async for message in websocket:
                    data = json.loads(message)
                    new_price = float(data['c'])
                    current_time = time.time()
                    
                    # Обновляем данные о цене
                    price_data["price"] = new_price
                    price_data["last_update"] = current_time
                    
                    logging.debug(f"Updated price: {new_price}")
                    
                    # Обновляем сообщения для всех активных пользователей
                    await update_all_users()
                    
        except websockets.exceptions.ConnectionClosed:
            logging.warning(f"WebSocket connection closed. Reconnecting in {RECONNECTION_DELAY} seconds...")
            await asyncio.sleep(RECONNECTION_DELAY)
        except Exception as e:
            logging.error(f"Error in WebSocket connection: {e}")
            await asyncio.sleep(RECONNECTION_DELAY * 2)  # Двойная задержка при ошибке

async def main():
    """Главная функция приложения"""
    global bot
    
    if not TOKEN:
        logging.error("BOT_TOKEN not set in environment variables")
        return
    
    # Загружаем сохраненные данные пользователей    
    load_users_data()
    logging.info(f"Loaded {len([u for u in active_users.values() if u['active']])} active users")
        
    bot = Bot(token=TOKEN)
    
    # Создаем фоновую задачу для получения цены
    price_task = asyncio.create_task(get_price())
    
    try:
        logging.info("Starting bot polling...")
        # Запускаем polling в основном потоке
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Error in polling: {e}")
    finally:
        logging.info("Shutting down bot...")
        # Сохраняем данные пользователей перед завершением
        save_users_data()
        # Отменяем фоновые задачи при завершении
        price_task.cancel()
        try:
            await price_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()
        logging.info("Bot shutdown complete")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
