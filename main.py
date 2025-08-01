# main.py
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from config import TOKEN, SUPPORTED_CRYPTOS
from services.user_service import load_users_data, save_users_data
from services.crypto_service import get_crypto_price
from handlers import common_handlers, crypto_handlers, portfolio_handlers, update_handlers, admin_handlers
from handlers.update_handlers import update_all_users, init_bot as init_update_bot

async def main():
    """Главная функция приложения"""
    if not TOKEN:
        logging.error("BOT_TOKEN not set in environment variables")
        return
    
    logging.basicConfig(level=logging.INFO)
    
    load_users_data()
    logging.info(f"Loaded users data.")
        
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    # Инициализация бота в модуле обновлений
    init_update_bot(bot)

    # Регистрация роутеров
    dp.include_router(common_handlers.router)
    dp.include_router(crypto_handlers.router)
    dp.include_router(portfolio_handlers.router)
    dp.include_router(admin_handlers.router)
    
    # Регистрация хендлеров для start/stop updates
    dp.message.register(update_handlers.start_updates_handler, Command('start_updates'))
    dp.message.register(update_handlers.stop_updates_handler, Command('stop_updates'))

    # Создаем фоновую задачу для получения цен
    price_tasks = [asyncio.create_task(get_crypto_price(crypto, update_all_users)) for crypto in SUPPORTED_CRYPTOS]
    
    try:
        logging.info("Starting bot polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Error in polling: {e}")
    finally:
        logging.info("Shutting down bot...")
        save_users_data()
        for task in price_tasks:
            task.cancel()
        await asyncio.gather(*price_tasks, return_exceptions=True)
        await bot.session.close()
        logging.info("Bot shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
