import asyncio
import requests
import sys
import logging
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

dp = Dispatcher()

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")

@dp.message(Command('checkCrypto'))
async def check_crypto_handler(message: Message) -> None:
    await message.answer("Функция проверки криптовалют еще не реализована!")

async def main():
    bot = Bot(token=TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)