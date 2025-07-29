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

# Поддерживаемые криптовалюты
SUPPORTED_CRYPTOS = {
    "BTC": {"name": "Bitcoin", "symbol": "₿", "pair": "btceur"},
    "ETH": {"name": "Ethereum", "symbol": "Ξ", "pair": "etheur"},
    "SOL": {"name": "Solana", "symbol": "◎", "pair": "soleur"},
    "XRP": {"name": "XRP", "symbol": "✕", "pair": "xrpeur"}
}

# Глобальные переменные для отслеживания цен и пользователей
# Структура: {"BTC": {"price": float, "last_update": timestamp}, ...}
price_data = {crypto: {"price": None, "last_update": 0} for crypto in SUPPORTED_CRYPTOS}
bot = None
last_message_update = 0

# Словарь для хранения активных пользователей и их сообщений
# Структура: {chat_id: {"crypto": str, "message_id": int, "active": bool}}
active_users = {}

# Константы
USERS_DATA_FILE = "users_data.json"
RECONNECTION_DELAY = 5
UPDATE_FREQUENCY_LIMIT = 1  # секунда между обновлениями - реальное время

def save_users_data():
    """Сохранение данных пользователей в файл"""
    try:
        with open(USERS_DATA_FILE, 'w', encoding='utf-8') as f:
            # Сохраняем всех пользователей (активных и неактивных) для сохранения их настроек
            data_to_save = {}
            for chat_id, user_data in active_users.items():
                data_to_save[str(chat_id)] = {
                    "active": user_data.get("active", False),
                    "crypto": user_data.get("crypto", "BTC")
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
                    "message_id": None,  # Сбрасываем message_id после перезапуска
                    "active": user_data.get("active", False),
                    "crypto": user_data.get("crypto", "BTC"),  # По умолчанию BTC
                    "last_price": None  # Добавляем поле для отслеживания последней цены
                }
        logging.info(f"Loaded {len(saved_data)} users from {USERS_DATA_FILE}")
    except FileNotFoundError:
        logging.info("No saved users data found. Starting fresh.")  
    except Exception as e:
        logging.error(f"Error loading users data: {e}")

dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    crypto_list = "\n".join([f"• {code} ({info['name']})" for code, info in SUPPORTED_CRYPTOS.items()])
    text = f"Привет, {html.bold(message.from_user.full_name)}! 👋\n\n"\
           f"🤖 <b>Crypto-check Bot</b> - твой помощник для отслеживания криптовалют!\n\n"\
           f"💰 <b>Поддерживаемые криптовалюты:</b>\n{crypto_list}\n\n"\
           f"📋 <b>Доступные команды:</b>\n"\
           f"• /select_crypto - выбрать криптовалюту для отслеживания\n"\
           f"• /checkCrypto - получить текущую цену выбранной криптовалюты\n"\
           f"• /start_updates - включить автообновления цены\n"\
           f"• /stop_updates - отключить автообновления\n"\
           f"• /status - статус ваших подписок\n\n"\
           f"🔔 <i>Автообновления показывают цену в реальном времени!</i>"
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command('select_crypto'))
async def select_crypto_handler(message: Message) -> None:
    """Команда для выбора криптовалюты"""
    chat_id = message.chat.id
    
    crypto_options = "\n".join([
        f"• /{code.lower()} - {info['name']} ({info['symbol']})" 
        for code, info in SUPPORTED_CRYPTOS.items()
    ])
    
    current_crypto = active_users.get(chat_id, {}).get("crypto", "BTC")
    current_info = SUPPORTED_CRYPTOS[current_crypto]
    
    text = f"🔍 <b>Выбор криптовалюты</b>\n\n"\
           f"📊 Текущий выбор: <b>{current_crypto}</b> ({current_info['name']})\n\n"\
           f"💰 <b>Доступные криптовалюты:</b>\n{crypto_options}\n\n"\
           f"💡 <i>Выберите криптовалюту, нажав на соответствующую команду</i>"
    
    await message.answer(text, parse_mode=ParseMode.HTML)

# Обработчики для каждой криптовалюты
@dp.message(Command('btc'))
async def select_btc_handler(message: Message) -> None:
    await set_user_crypto(message, "BTC")

@dp.message(Command('eth'))
async def select_eth_handler(message: Message) -> None:
    await set_user_crypto(message, "ETH")

@dp.message(Command('sol'))
async def select_sol_handler(message: Message) -> None:
    await set_user_crypto(message, "SOL")

@dp.message(Command('xrp'))
async def select_xrp_handler(message: Message) -> None:
    await set_user_crypto(message, "XRP")

async def set_user_crypto(message: Message, crypto: str) -> None:
    """Установить выбранную криптовалюту для пользователя"""
    chat_id = message.chat.id
    crypto_info = SUPPORTED_CRYPTOS[crypto]
    
    # Инициализируем пользователя если его нет
    if chat_id not in active_users:
        active_users[chat_id] = {
            "message_id": None, 
            "active": False, 
            "crypto": crypto,
            "last_price": None
        }
    else:
        active_users[chat_id]["crypto"] = crypto
        # Сбрасываем last_price при смене криптовалюты
        active_users[chat_id]["last_price"] = None
        active_users[chat_id]["message_id"] = None  # Сбрасываем message_id тоже
    
    save_users_data()
    
    text = f"✅ <b>Выбрано:</b> {crypto} ({crypto_info['name']})\n"\
           f"🔗 Торговая пара: {crypto}/EUR\n\n"\
           f"💡 Теперь используйте:\n"\
           f"• /checkCrypto - для проверки цены\n"\
           f"• /start_updates - для автообновлений"
    
    await message.answer(text, parse_mode=ParseMode.HTML)

@dp.message(Command('checkCrypto'))
async def check_crypto_handler(message: Message) -> None:
    """Команда для получения актуальной цены выбранной криптовалюты"""
    chat_id = message.chat.id
    
    # Получаем выбранную пользователем криптовалюту
    user_crypto = active_users.get(chat_id, {}).get("crypto", "BTC")
    crypto_info = SUPPORTED_CRYPTOS[user_crypto]
    
    if price_data[user_crypto]["price"] is not None:
        formatted_price = f"{price_data[user_crypto]['price']:,.2f}"
        if price_data[user_crypto]["last_update"]:
            update_time = datetime.fromtimestamp(price_data[user_crypto]["last_update"]).strftime("%H:%M:%S")
            text = f"💰 <b>{user_crypto}/EUR</b>: €{formatted_price}\n"\
                   f"📊 Данные получены через WebSocket Binance\n"\
                   f"🔄 Последнее обновление: {update_time}"
        else:
            text = f"💰 <b>{user_crypto}/EUR</b>: €{formatted_price}\n"\
                   f"📊 Данные получены через WebSocket Binance"
        await message.answer(text, parse_mode=ParseMode.HTML)
    else:
        await message.answer(f"⏳ Цена {user_crypto} еще загружается, попробуйте через несколько секунд...")

@dp.message(Command('start_updates'))
async def start_updates_handler(message: Message) -> None:
    """Включить автообновления для пользователя"""
    chat_id = message.chat.id
    
    if chat_id in active_users and active_users[chat_id]["active"]:
        await message.answer("✅ Автообновления уже включены!\nИспользуйте /stop_updates для отключения.")
        return
    
    # Добавляем пользователя в активные
    if chat_id not in active_users:
        active_users[chat_id] = {
            "message_id": None, 
            "active": True, 
            "crypto": "BTC",
            "last_price": None
        }
    else:
        active_users[chat_id]["active"] = True
        # Сбрасываем last_price при включении обновлений
        active_users[chat_id]["last_price"] = None
        active_users[chat_id]["message_id"] = None  # Сбрасываем message_id тоже
    
    save_users_data()  # Сохраняем изменения
    
    user_crypto = active_users[chat_id]["crypto"]
    crypto_info = SUPPORTED_CRYPTOS[user_crypto]
    
    await message.answer(f"🔔 <b>Автообновления включены!</b>\n"\
                        f"📊 Отслеживаем: {user_crypto} ({crypto_info['name']})\n"\
                        f"Сообщение с ценой будет обновляться в реальном времени.\n"\
                        f"Используйте /stop_updates для отключения.", 
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
        user_crypto = active_users[chat_id].get("crypto", "BTC")
    else:
        status = "🔕 <b>Отключены</b>"
        message_info = "Автообновления неактивны"
        user_crypto = active_users.get(chat_id, {}).get("crypto", "BTC")
    
    crypto_info = SUPPORTED_CRYPTOS[user_crypto]
    total_users = len([u for u in active_users.values() if u["active"]])
    
    text = f"📊 <b>Статус автообновлений:</b>\n"\
           f"Ваш статус: {status}\n"\
           f"Выбранная крипта: <b>{user_crypto}</b> ({crypto_info['name']})\n"\
           f"Детали: {message_info}\n\n"\
           f"👥 Всего активных пользователей: {total_users}\n"\
           f"💰 Цена {user_crypto}: €{price_data[user_crypto]['price']:,.2f}" if price_data[user_crypto]['price'] else f"💰 Цена {user_crypto}: Загружается..."
    
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
    
    # Статистика по криптовалютам
    crypto_stats = {}
    for user_data in active_users.values():
        if user_data["active"]:
            crypto = user_data.get("crypto", "BTC")
            crypto_stats[crypto] = crypto_stats.get(crypto, 0) + 1
    
    crypto_breakdown = "\n".join([f"• {crypto}: {count} пользователей" for crypto, count in crypto_stats.items()])
    
    # Статистика WebSocket
    all_connected = all(price_data[crypto]["price"] is not None for crypto in SUPPORTED_CRYPTOS)
    connection_status = "🟢 Все подключены" if all_connected else "🟡 Частично подключены"
    
    text = f"🔧 <b>Административная панель</b>\n\n"\
           f"👥 <b>Статистика пользователей:</b>\n"\
           f"• Всего зарегистрировано: {total_users}\n"\
           f"• Активных подписок: {active_count}\n"\
           f"• Неактивных: {inactive_count}\n\n"\
           f"📊 <b>По криптам:</b>\n{crypto_breakdown or '• Нет активных подписок'}\n\n"\
           f"📡 <b>WebSocket статус:</b>\n"\
           f"• Соединения: {connection_status}\n"
    
    # Добавляем цены всех криптовалют
    for crypto, data in price_data.items():
        if data["price"]:
            last_update = datetime.fromtimestamp(data["last_update"]).strftime("%H:%M:%S")
            text += f"• {crypto}: €{data['price']:,.2f} ({last_update})\n"
        else:
            text += f"• {crypto}: Загружается...\n"
    
    await message.answer(text, parse_mode=ParseMode.HTML)

async def send_initial_price_message(chat_id):
    """Отправка первого сообщения с ценой для пользователя"""
    user_crypto = active_users[chat_id].get("crypto", "BTC")
    
    if price_data[user_crypto]["price"] is None:
        # Ждем загрузки цены
        for _ in range(10):  # Максимум 10 секунд
            if price_data[user_crypto]["price"] is not None:
                break
            await asyncio.sleep(1)
    
    if price_data[user_crypto]["price"] is not None:
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
    
    user_crypto = active_users[chat_id].get("crypto", "BTC")
    
    if price_data[user_crypto]["price"] is None:
        return
    
    try:
        formatted_price = f"{price_data[user_crypto]['price']:,.2f}"
        update_time = datetime.fromtimestamp(price_data[user_crypto]["last_update"]).strftime("%H:%M:%S")
        crypto_info = SUPPORTED_CRYPTOS[user_crypto]
        new_text = f"💰 <b>{user_crypto}/EUR</b>: €{formatted_price}\n🔄 Обновлено: {update_time} (Реальное время)"
        
        # Проверяем, изменилась ли цена (а не время)
        last_price = active_users[chat_id].get("last_price", None)
        current_price = price_data[user_crypto]["price"]
        
        if active_users[chat_id]["message_id"] is None:
            # Отправляем новое сообщение
            msg = await bot.send_message(
                chat_id=chat_id,
                text=new_text,
                parse_mode=ParseMode.HTML
            )
            active_users[chat_id]["message_id"] = msg.message_id
            active_users[chat_id]["last_price"] = current_price
            logging.info(f"Sent initial price message to {chat_id}")
        else:
            # Обновляем только если цена изменилась значительно (более чем на 0.01€)
            if last_price is None or abs(current_price - last_price) >= 0.01:
                try:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=active_users[chat_id]["message_id"],
                        text=new_text,
                        parse_mode=ParseMode.HTML
                    )
                    active_users[chat_id]["last_price"] = current_price
                    logging.debug(f"Updated price message for {chat_id} (price change: {abs(current_price - (last_price or 0)):.4f}€)")
                except Exception as edit_error:
                    # Если не удалось отредактировать, отправляем новое сообщение
                    if "message to edit not found" in str(edit_error).lower():
                        msg = await bot.send_message(
                            chat_id=chat_id,
                            text=new_text,
                            parse_mode=ParseMode.HTML
                        )
                        active_users[chat_id]["message_id"] = msg.message_id
                        active_users[chat_id]["last_price"] = current_price
                        logging.info(f"Sent new price message to {chat_id} (old message not found)")
                    else:
                        # Игнорируем ошибку "message is not modified"
                        if "message is not modified" not in str(edit_error).lower():
                            logging.error(f"Error editing message for {chat_id}: {edit_error}")
            
    except Exception as e:
        logging.error(f"Error updating message for {chat_id}: {e}")
        # Если ошибка с отправкой, сбрасываем message_id
        active_users[chat_id]["message_id"] = None

async def update_all_users():
    """Обновление сообщений для всех активных пользователей"""
    global last_message_update
    
    current_time = time.time()
    
    # Ограничиваем частоту обновлений
    if current_time - last_message_update < UPDATE_FREQUENCY_LIMIT:
        return
    
    if not bot:
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

async def get_crypto_price(crypto):
    """Получение цены конкретной криптовалюты через WebSocket Binance"""
    crypto_info = SUPPORTED_CRYPTOS[crypto]
    uri = f"wss://stream.binance.com:9443/ws/{crypto_info['pair']}@ticker"
    
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                logging.info(f"WebSocket connected to Binance ({crypto}/EUR)")
                async for message in websocket:
                    data = json.loads(message)
                    new_price = float(data['c'])
                    current_time = time.time()
                    
                    # Обновляем данные о цене для конкретной криптовалюты
                    price_data[crypto]["price"] = new_price
                    price_data[crypto]["last_update"] = current_time
                    
                    logging.debug(f"Updated {crypto}/EUR price: {new_price}")
                    
                    # Обновляем сообщения для всех активных пользователей
                    await update_all_users()
                    
        except websockets.exceptions.ConnectionClosed:
            logging.warning(f"WebSocket connection closed for {crypto}. Reconnecting in {RECONNECTION_DELAY} seconds...")
            await asyncio.sleep(RECONNECTION_DELAY)
        except Exception as e:
            logging.error(f"Error in WebSocket connection for {crypto}: {e}")
            await asyncio.sleep(RECONNECTION_DELAY * 2)  # Двойная задержка при ошибке

async def get_price():
    """Запуск WebSocket соединений для всех поддерживаемых криптовалют"""
    tasks = []
    for crypto in SUPPORTED_CRYPTOS:
        task = asyncio.create_task(get_crypto_price(crypto))
        tasks.append(task)
    
    # Ждем выполнения всех задач (они будут работать бесконечно)
    await asyncio.gather(*tasks)

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
