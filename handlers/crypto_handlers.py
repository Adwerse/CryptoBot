# handlers/crypto_handlers.py
from aiogram import Router, html
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from config import SUPPORTED_CRYPTOS
from services.user_service import active_users, save_users_data, get_user
from services.crypto_service import price_data
from datetime import datetime

router = Router()

@router.message(Command('select_crypto'))
async def select_crypto_handler(message: Message) -> None:
    """Команда для выбора криптовалюты"""
    chat_id = message.chat.id
    
    crypto_options = "\n".join([
        f"• /{code.lower()} - {info['name']} ({info['symbol']})" 
        for code, info in SUPPORTED_CRYPTOS.items()
    ])
    
    user_data = get_user(chat_id)
    current_crypto = user_data.get("crypto", "BTC")
    current_info = SUPPORTED_CRYPTOS[current_crypto]
    
    text = f"🔍 <b>Выбор криптовалюты</b>\n\n"\
           f"📊 Текущий выбор: <b>{current_crypto}</b> ({current_info['name']})\n\n"\
           f"💰 <b>Доступные криптовалюты:</b>\n{crypto_options}\n\n"\
           f"💡 <i>Выберите криптовалюту, нажав на соответствующую команду</i>"
    
    await message.answer(text, parse_mode=ParseMode.HTML)

# Обработчики для каждой криптовалюты
@router.message(Command('btc'))
async def select_btc_handler(message: Message) -> None:
    await set_user_crypto(message, "BTC")

@router.message(Command('eth'))
async def select_eth_handler(message: Message) -> None:
    await set_user_crypto(message, "ETH")

@router.message(Command('sol'))
async def select_sol_handler(message: Message) -> None:
    await set_user_crypto(message, "SOL")

@router.message(Command('xrp'))
async def select_xrp_handler(message: Message) -> None:
    await set_user_crypto(message, "XRP")

async def set_user_crypto(message: Message, crypto: str) -> None:
    """Установить выбранную криптовалюту для пользователя"""
    chat_id = message.chat.id
    crypto_info = SUPPORTED_CRYPTOS[crypto]
    
    user_data = get_user(chat_id)
    user_data["crypto"] = crypto
    user_data["last_price"] = None
    user_data["message_id"] = None
    
    save_users_data()
    
    text = f"✅ <b>Выбрано:</b> {crypto} ({crypto_info['name']})\n"\
           f"🔗 Торговая пара: {crypto}/EUR\n\n"\
           f"💡 Теперь используйте:\n"\
           f"• /checkCrypto - для проверки цены\n"\
           f"• /start_updates - для автообновлений"
    
    await message.answer(text, parse_mode=ParseMode.HTML)

@router.message(Command('checkCrypto'))
async def check_crypto_handler(message: Message) -> None:
    """Команда для получения актуальной цены выбранной криптовалюты"""
    chat_id = message.chat.id
    
    user_data = get_user(chat_id)
    user_crypto = user_data.get("crypto", "BTC")
    
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
