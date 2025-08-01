# handlers/portfolio_handlers.py
from aiogram import Router, html
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from config import SUPPORTED_CRYPTOS
from services.user_service import active_users, save_users_data, get_user
from services.crypto_service import price_data

router = Router()

@router.message(Command('portfolio_add'))
async def portfolio_add_handler(message: Message) -> None:
    """Добавить актив в портфель пользователя"""
    chat_id = message.chat.id
    try:
        args = message.text.split()
        if len(args) != 3:
            raise ValueError
        
        _, crypto, amount_str = args
        amount = float(amount_str)
        crypto = crypto.upper()

        if crypto not in SUPPORTED_CRYPTOS:
            await message.answer(f"❌ Криптовалюта {crypto} не поддерживается.")
            return

        user_data = get_user(chat_id)
        
        if "portfolio" not in user_data:
            user_data["portfolio"] = {}

        user_data["portfolio"][crypto] = user_data["portfolio"].get(crypto, 0) + amount
        save_users_data()
        
        await message.answer(f"✅ Добавлено {amount} {crypto} в ваш портфель.")
        await portfolio_handler(message)

    except (ValueError, IndexError):
        await message.answer("❌ Неверный формат. Используйте: /portfolio_add [КОД] [КОЛ-ВО]\n"
                             "Пример: /portfolio_add BTC 0.1")

@router.message(Command('portfolio_remove'))
async def portfolio_remove_handler(message: Message) -> None:
    """Удалить актив из портфеля пользователя"""
    chat_id = message.chat.id
    try:
        args = message.text.split()
        if len(args) != 2:
            raise ValueError

        _, crypto = args
        crypto = crypto.upper()

        user_data = get_user(chat_id)
        if crypto not in user_data.get("portfolio", {}):
            await message.answer(f"❌ Актив {crypto} не найден в вашем портфеле.")
            return

        del user_data["portfolio"][crypto]
        save_users_data()
        
        await message.answer(f"✅ Актив {crypto} удален из вашего портфеля.")
        await portfolio_handler(message)

    except (ValueError, IndexError):
        await message.answer("❌ Неверный формат. Используйте: /portfolio_remove [КОД]\n"
                             "Пример: /portfolio_remove BTC")

@router.message(Command('portfolio'))
async def portfolio_handler(message: Message) -> None:
    """Показать портфель пользователя"""
    chat_id = message.chat.id
    
    user_data = get_user(chat_id)
    if not user_data.get("portfolio"):
        await message.answer("📭 Ваш портфель пуст.\n\n"
                             "Используйте /portfolio_add [КОД] [КОЛ-ВО], чтобы добавить актив.")
        return

    portfolio = user_data["portfolio"]
    total_value = 0
    text = "💼 <b>Ваш криптовалютный портфель:</b>\n\n"

    for crypto, amount in portfolio.items():
        current_price = price_data[crypto].get("price")
        if current_price:
            value = amount * current_price
            total_value += value
            text += f"• <b>{crypto}</b>: {amount} ({SUPPORTED_CRYPTOS[crypto]['symbol']}) - <b>€{value:,.2f}</b>\n"
        else:
            text += f"• <b>{crypto}</b>: {amount} ({SUPPORTED_CRYPTOS[crypto]['symbol']}) - <i>Цена загружается...</i>\n"
    
    text += f"\n----------------------------------\n"
    text += f"💰 <b>Общая стоимость: €{total_value:,.2f}</b>"
    
    await message.answer(text, parse_mode=ParseMode.HTML)
