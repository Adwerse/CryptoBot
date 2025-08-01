# handlers/admin_handlers.py
from aiogram import Router, html
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from config import SUPPORTED_CRYPTOS, ADMIN_ID
from services.user_service import active_users
from services.crypto_service import price_data
from datetime import datetime

router = Router()

@router.message(Command('admin_stats'))
async def admin_stats_handler(message: Message) -> None:
    """Административная команда для просмотра статистики"""
    if str(message.from_user.id) != ADMIN_ID:
        await message.answer("❌ Недостаточно прав доступа.")
        return
    
    total_users = len(active_users)
    active_count = len([u for u in active_users.values() if u["active"]])
    inactive_count = total_users - active_count
    
    crypto_stats = {}
    for user_data in active_users.values():
        if user_data["active"]:
            crypto = user_data.get("crypto", "BTC")
            crypto_stats[crypto] = crypto_stats.get(crypto, 0) + 1
    
    crypto_breakdown = "\n".join([f"• {crypto}: {count} пользователей" for crypto, count in crypto_stats.items()])
    
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
    
    for crypto, data in price_data.items():
        if data["price"]:
            last_update = datetime.fromtimestamp(data["last_update"]).strftime("%H:%M:%S")
            text += f"• {crypto}: €{data['price']:,.2f} ({last_update})\n"
        else:
            text += f"• {crypto}: Загружается...\n"
    
    await message.answer(text, parse_mode=ParseMode.HTML)

@router.message(Command('status'))
async def status_handler(message: Message) -> None:
    """Показать статус подписок пользователя"""
    chat_id = message.chat.id
    user_data = active_users.get(chat_id, {})
    
    if user_data.get("active"):
        status = "🔔 <b>Включены</b>"
        message_info = f"Message ID: {user_data['message_id']}" if user_data.get('message_id') else "Сообщение еще не создано"
        user_crypto = user_data.get("crypto", "BTC")
    else:
        status = "🔕 <b>Отключены</b>"
        message_info = "Автообновления неактивны"
        user_crypto = user_data.get("crypto", "BTC")
    
    crypto_info = SUPPORTED_CRYPTOS[user_crypto]
    total_active_users = len([u for u in active_users.values() if u.get("active")])
    
    price_info = f"💰 Цена {user_crypto}: €{price_data[user_crypto]['price']:,.2f}" if price_data[user_crypto].get('price') else f"💰 Цена {user_crypto}: Загружается..."
    
    text = f"📊 <b>Статус автообновлений:</b>\n"\
           f"Ваш статус: {status}\n"\
           f"Выбранная крипта: <b>{user_crypto}</b> ({crypto_info['name']})\n"\
           f"Детали: {message_info}\n\n"\
           f"👥 Всего активных пользователей: {total_active_users}\n"\
           f"{price_info}"
    
    await message.answer(text, parse_mode=ParseMode.HTML)
