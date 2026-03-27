import asyncio
import websockets
import json
import config

class BinanceWebSocket:
    """Класс для получения цен через WebSocket Binance."""
    def __init__(self):
        self.prices = {}  # {symbol: price}
        self.base_url = "wss://stream.binance.com:9443/ws"
        self.streams = [
            "btcusdt@ticker",
            "ethbtc@ticker",
            "ethusdt@ticker"
        ]
        self.websocket = None
        self.running = True

    async def connect(self):
        """Подключается к WebSocket и подписывается на потоки."""
        stream_names = "/".join(self.streams)
        url = f"{self.base_url}/{stream_names}"
        print(f"DEBUG: Connecting to {url}")
        self.websocket = await websockets.connect(url)
        print("DEBUG: Connected")
        asyncio.create_task(self._receive_messages())

    async def _receive_messages(self):
        """Принимает сообщения и обновляет цены."""
        while self.running:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                stream = data.get('stream')
                if stream:
                    symbol_raw = stream.split('@')[0].upper()
                    price = float(data['data']['c'])  # последняя цена
                    print(f"DEBUG: Received {symbol_raw} price {price}")
                    # Преобразуем в формат CCXT
                    if symbol_raw == 'BTCUSDT':
                        self.prices['BTC/USDT'] = price
                    elif symbol_raw == 'ETHBTC':
                        self.prices['ETH/BTC'] = price
                    elif symbol_raw == 'ETHUSDT':
                        self.prices['ETH/USDT'] = price
                    print(f"DEBUG: Prices now: {self.prices}")
            except websockets.ConnectionClosed:
                print("WebSocket connection closed. Reconnecting...")
                await self.reconnect()
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
                break

    async def reconnect(self):
        """Переподключение при разрыве."""
        await asyncio.sleep(5)
        if self.running:
            await self.connect()

    async def close(self):
        self.running = False
        if self.websocket:
            await self.websocket.close()
