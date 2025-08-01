# services/crypto_service.py
import time
import logging
import json
import websockets
import asyncio
from config import SUPPORTED_CRYPTOS, RECONNECTION_DELAY

# Глобальные переменные для отслеживания цен
price_data = {crypto: {"price": None, "last_update": 0} for crypto in SUPPORTED_CRYPTOS}

async def get_crypto_price(crypto, update_callback):
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
                    
                    price_data[crypto]["price"] = new_price
                    price_data[crypto]["last_update"] = current_time
                    
                    logging.debug(f"Updated {crypto}/EUR price: {new_price}")
                    
                    await update_callback()
                    
        except websockets.exceptions.ConnectionClosed:
            logging.warning(f"WebSocket connection closed for {crypto}. Reconnecting in {RECONNECTION_DELAY} seconds...")
            await asyncio.sleep(RECONNECTION_DELAY)
        except Exception as e:
            logging.error(f"Error in WebSocket connection for {crypto}: {e}")
            await asyncio.sleep(RECONNECTION_DELAY * 2)
