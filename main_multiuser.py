import asyncio
import requests
import sys
import logging
import json
import websockets
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

dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    text = f"Привет, {html.bold(message.from_user.full_name)}! 👋\\n\\n"\
           f"🤖 <b>Crypto-check Bot</b> - твой помощник для отслеживания криптовалют!\\n\\n"\
           f"📋 <b>Доступные команды:</b>\\n"\
           f"• /checkCrypto - получить текущую цену BTC\\n"\
           f"• /start_updates - включить автообновления цены\\n"\
           f"• /stop_updates - отключить автообновления\\n"\
           f"• /status - статус ваших подписок\\n\\n"\
           f"🔔 <i>Автообновления показывают цену в реальном времени!</i>"
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command('checkCrypto'))
async def check_crypto_handler(message: Message) -> None:
    """Команда для получения актуальной цены BTC"""
    if price_data["price"] is not None:
        formatted_price = f"{price_data['price']:,.2f}"
        from datetime import datetime
        if price_data["last_update"]:
            update_time = datetime.fromtimestamp(price_data["last_update"]).strftime("%H:%M:%S")
            text = f"💰 <b>BTC/USDT</b>: ${formatted_price}\\n📊 Данные получены через WebSocket Binance\\n🔄 Последнее обновление: {update_time}"
        else:
            text = f"💰 <b>BTC/USDT</b>: ${formatted_price}\\n📊 Данные получены через WebSocket Binance"
        await message.answer(text, parse_mode=ParseMode.HTML)
    else:
        await message.answer("⏳ Цена еще загружается, попробуйте через несколько секунд...")

@dp.message(Command('start_updates'))
async def start_updates_handler(message: Message) -> None:
    """Включить автообновления для пользователя"""
    chat_id = message.chat.id
    
    if chat_id in active_users and active_users[chat_id]["active"]:
        await message.answer("✅ Автообновления уже включены!\\nИспользуйте /stop_updates для отключения.")
        return
    
    # Добавляем пользователя в активные
    active_users[chat_id] = {"message_id": None, "active": True}
    
    await message.answer("🔔 <b>Автообновления включены!</b>\\n"\
                        "Сообщение с ценой будет обновляться в реальном времени.\\n"\
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
    
    await message.answer("🔕 <b>Автообновления отключены!</b>\\n"\
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
    
    text = f"📊 <b>Статус автообновлений:</b>\\n"\
           f"Ваш статус: {status}\\n"\
           f"Детали: {message_info}\\n\\n"\
           f"👥 Всего активных пользователей: {total_users}\\n"\
           f"💰 Цена BTC: ${price_data['price']:,.2f}" if price_data['price'] else "💰 Цена загружается..."
    
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
                text="⏳ <b>Загрузка данных...</b>\\nЦена появится через несколько секунд.",
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
        from datetime import datetime
        formatted_price = f"{price_data['price']:,.2f}"
        update_time = datetime.fromtimestamp(price_data["last_update"]).strftime("%H:%M:%S")
        text = f"💰 <b>BTC/USDT</b>: ${formatted_price}\\n🔄 Обновлено: {update_time} (Реальное время)"
        
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
    import time
    global last_message_update
    
    current_time = time.time()
    
    # Ограничиваем частоту обновлений
    if current_time - last_message_update < 3:
        return
    
    if not bot or price_data["price"] is None:
        return
    
    # Обновляем сообщения для всех активных пользователей
    for chat_id, user_data in active_users.items():
        if user_data["active"]:
            await update_user_message(chat_id)
    
    last_message_update = current_time

async def get_price():
    """Получение цены BTC через WebSocket Binance"""
    import time
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
            logging.warning("WebSocket connection closed. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            logging.error(f"Error in WebSocket connection: {e}")
            await asyncio.sleep(10)

async def main():
    global bot
    
    if not TOKEN:
        logging.error("BOT_TOKEN not set in environment variables")
        return
        
    bot = Bot(token=TOKEN)
    
    # Создаем фоновую задачу для получения цены
    price_task = asyncio.create_task(get_price())
    
    try:
        # Запускаем polling в основном потоке
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Error in polling: {e}")
    finally:
        # Отменяем фоновые задачи при завершении
        price_task.cancel()
        await bot.session.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
