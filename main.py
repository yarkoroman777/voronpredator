import asyncio
import time
import config
from exchanges import create_binance_client
from websocket_streams import BinanceWebSocket
from triangular import calculate_spread, get_expected_profit
from trader import ArbitrageTrader
from logger import Logger

async def main():
    # Инициализация
    logger = Logger()
    logger.log("🚀 Бот треугольного арбитража запущен")
    logger.log(f"Минимальный спред: {config.MIN_SPREAD_PERCENT}%")
    logger.log(f"Допуск проскальзывания: {config.SLIPPAGE_TOLERANCE}%")

    # Клиент Binance
    client = create_binance_client()

    # Проверка баланса
    balance = client.fetch_balance()
    usdt_balance = balance['USDT']['free']
    logger.log(f"Баланс USDT: {usdt_balance}")

    if usdt_balance < 50:
        logger.log("⚠️ Баланс USDT очень низкий. Остановка.")
        return

    # WebSocket
    ws = BinanceWebSocket()
    await ws.connect()
    logger.log("✅ WebSocket подключён")

    trader = ArbitrageTrader(client, ws.prices)
    trader.logger = logger

    # Основной цикл проверки спреда
    while True:
        # Проверяем, есть ли цены
        missing = [k for k in ['BTC/USDT', 'ETH/BTC', 'ETH/USDT'] if k not in ws.prices]
        if missing:
            print(f"DEBUG: Missing prices: {missing}. Current keys: {list(ws.prices.keys())}")
            await asyncio.sleep(5)
            continue

        spread = calculate_spread(ws.prices)
        if spread is None:
            await asyncio.sleep(5)
            continue

        # ВСЕГДА выводим текущий спред (даже если он ниже порога)
        logger.log(f"📊 Текущий спред: {spread:.2f}%")

        # Фильтр по минимальному спреду
        if spread >= config.MIN_SPREAD_PERCENT:
            profit = get_expected_profit(usdt_balance, spread)
            if profit > 0:
                logger.log(f"🎯 Найден спред: {spread:.2f}%, ожидаемая прибыль: {profit:.2f} USDT")
                # Выполняем сделку
                result = trader.execute_triangle(usdt_balance)
                if result:
                    usdt_balance += result
                    logger.log(f"💰 Новый баланс: {usdt_balance:.2f} USDT")
                # Небольшая пауза после сделки, чтобы не зафлудить
                await asyncio.sleep(30)

        # Пауза между проверками спреда
        await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(main())
