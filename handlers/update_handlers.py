# handlers/update_handlers.py
import asyncio
import logging
import time
from aiogram import Bot
from aiogram.enums import ParseMode
from config import SUPPORTED_CRYPTOS, UPDATE_FREQUENCY_LIMIT
from services.user_service import active_users, get_user
from services.crypto_service import price_data
from datetime import datetime

bot: Bot
last_message_update = 0

def init_bot(b: Bot):
    global bot
    bot = b

async def start_updates_handler(message):
    """Включить автообновления для пользователя"""
    chat_id = message.chat.id
    user_data = get_user(chat_id)
    
    if user_data["active"]:
        await message.answer("✅ Автообновления уже включены!\nИспользуйте /stop_updates для отключения.")
        return
    
    user_data["active"] = True
    user_data["last_price"] = None
    user_data["message_id"] = None
    
    user_crypto = user_data["crypto"]
    crypto_info = SUPPORTED_CRYPTOS[user_crypto]
    
    await message.answer(f"🔔 <b>Автообновления включены!</b>\n"\
                        f"📊 Отслеживаем: {user_crypto} ({crypto_info['name']})\n"\
                        f"Сообщение с ценой будет обновляться в реальном времени.\n"\
                        f"Используйте /stop_updates для отключения.", 
                        parse_mode=ParseMode.HTML)
    
    await send_initial_price_message(chat_id)

async def stop_updates_handler(message):
    """Отключить автообновления для пользователя"""
    chat_id = message.chat.id
    user_data = get_user(chat_id)
    
    if not user_data["active"]:
        await message.answer("❌ Автообновления не были включены.")
        return
    
    user_data["active"] = False
    
    await message.answer("🔕 <b>Автообновления отключены!</b>\n"\
                        "Используйте /start_updates для включения.", 
                        parse_mode=ParseMode.HTML)

async def send_initial_price_message(chat_id):
    """Отправка первого сообщения с ценой для пользователя"""
    user_data = get_user(chat_id)
    user_crypto = user_data.get("crypto", "BTC")
    
    if price_data[user_crypto]["price"] is None:
        for _ in range(10):
            if price_data[user_crypto]["price"] is not None:
                break
            await asyncio.sleep(1)
    
    if price_data[user_crypto]["price"] is not None:
        await update_user_message(chat_id)
    else:
        try:
            msg = await bot.send_message(
                chat_id=chat_id,
                text="⏳ <b>Загрузка данных...</b>\nЦена появится через несколько секунд.",
                parse_mode=ParseMode.HTML
            )
            user_data["message_id"] = msg.message_id
        except Exception as e:
            logging.error(f"Error sending initial message to {chat_id}: {e}")

async def update_user_message(chat_id):
    """Обновление сообщения для конкретного пользователя"""
    user_data = get_user(chat_id)
    if not user_data["active"]:
        return
    
    user_crypto = user_data.get("crypto", "BTC")
    
    if price_data[user_crypto]["price"] is None:
        return
    
    try:
        formatted_price = f"{price_data[user_crypto]['price']:,.2f}"
        update_time = datetime.fromtimestamp(price_data[user_crypto]["last_update"]).strftime("%H:%M:%S")
        new_text = f"💰 <b>{user_crypto}/EUR</b>: €{formatted_price}\n🔄 Обновлено: {update_time} (Реальное время)"
        
        last_price = user_data.get("last_price", None)
        current_price = price_data[user_crypto]["price"]
        
        if user_data["message_id"] is None:
            msg = await bot.send_message(
                chat_id=chat_id,
                text=new_text,
                parse_mode=ParseMode.HTML
            )
            user_data["message_id"] = msg.message_id
            user_data["last_price"] = current_price
            logging.info(f"Sent initial price message to {chat_id}")
        else:
            if last_price is None or abs(current_price - last_price) >= 0.01:
                try:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=user_data["message_id"],
                        text=new_text,
                        parse_mode=ParseMode.HTML
                    )
                    user_data["last_price"] = current_price
                    logging.debug(f"Updated price message for {chat_id}")
                except Exception as edit_error:
                    if "message to edit not found" in str(edit_error).lower():
                        msg = await bot.send_message(
                            chat_id=chat_id,
                            text=new_text,
                            parse_mode=ParseMode.HTML
                        )
                        user_data["message_id"] = msg.message_id
                        user_data["last_price"] = current_price
                        logging.info(f"Sent new price message to {chat_id} (old message not found)")
                    elif "message is not modified" not in str(edit_error).lower():
                        logging.error(f"Error editing message for {chat_id}: {edit_error}")
            
    except Exception as e:
        logging.error(f"Error updating message for {chat_id}: {e}")
        user_data["message_id"] = None

async def update_all_users():
    """Обновление сообщений для всех активных пользователей"""
    global last_message_update
    
    current_time = time.time()
    
    if current_time - last_message_update < UPDATE_FREQUENCY_LIMIT:
        return
    
    if not bot:
        return
    
    active_user_list = [chat_id for chat_id, data in active_users.items() if data.get("active")]
    
    tasks = [update_user_message(chat_id) for chat_id in active_user_list]
    await asyncio.gather(*tasks)
    
    if active_user_list:
        logging.debug(f"Updated messages for {len(active_user_list)} active users")
    
    last_message_update = current_time
