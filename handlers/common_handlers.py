# handlers/common_handlers.py
from aiogram import Router, html
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from config import SUPPORTED_CRYPTOS

router = Router()

@router.message(CommandStart())
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
           f"💼 <b>Управление портфелем:</b>\n"\
           f"• /portfolio_add [КОД] [КОЛ-ВО] - добавить актив\n"\
           f"• /portfolio_remove [КОД] - удалить актив\n"\
           f"• /portfolio - посмотреть портфель\n\n"\
           f"🔔 <i>Автообновления показывают цену в реальном времени!</i>"
    await message.answer(text, parse_mode=ParseMode.HTML)
