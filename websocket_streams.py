import asyncio
import websockets
import json

class BinanceWebSocket:
    def __init__(self):
        self.prices = {}
        self.base_url = "wss://stream.binance.com:9443/ws"
        self.streams = ["btcusdt@ticker", "ethbtc@ticker", "ethusdt@ticker"]
        self.websocket = None
        self.running = True

    async def connect(self):
        stream_names = "/".join(self.streams)
        url = f"{self.base_url}/{stream_names}"
        print(f"DEBUG: Connecting to {url}")
        self.websocket = await websockets.connect(url)
        print("DEBUG: Connected")
        asyncio.create_task(self._receive_messages())

    async def _receive_messages(self):
        try:
            while self.running:
                message = await self.websocket.recv()
                data = json.loads(message)
                symbol = data.get('s')
                price = float(data.get('c'))
                if symbol == "BTCUSDT":
                    self.prices['BTC/USDT'] = price
                elif symbol == "ETHBTC":
                    self.prices['ETH/BTC'] = price
                elif symbol == "ETHUSDT":
                    self.prices['ETH/USDT'] = price
        except Exception as e:
            print(f"EXCEPTION in _receive_messages: {e}")

    async def close(self):
        self.running = False
        if self.websocket:
            await self.websocket.close()
