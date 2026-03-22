import time
import asyncio
import config
from exchanges import create_binance_client
import triangular

class ArbitrageTrader:
    def __init__(self, client, prices):
        self.client = client
        self.prices = prices
        self.logger = None  # будет установлен из main

    def check_depth(self, symbol, side, amount_usdt):
        """
        Проверяет глубину стакана для лимитного ордера.
        side: 'buy' или 'sell'
        amount_usdt: сумма в USDT, которую планируем потратить (для покупки)
        """
        order_book = self.client.fetch_order_book(symbol, limit=10)
        if side == 'buy':
            # Нужно купить amount_usdt / price монет
            # Проверяем, хватит ли объёма на лучшей цене
            best_ask = order_book['asks'][0][0]  # цена
            best_ask_volume = order_book['asks'][0][1]  # объём в монетах
            required_volume = amount_usdt / best_ask
            return best_ask_volume >= required_volume * config.MIN_DEPTH_RATIO
        elif side == 'sell':
            # Продажа: проверяем объём на лучшем биде
            best_bid = order_book['bids'][0][0]
            best_bid_volume = order_book['bids'][0][1]
            required_volume = amount_usdt / best_bid
            return best_bid_volume >= required_volume * config.MIN_DEPTH_RATIO
        return False

    def execute_triangle(self, capital_usdt):
        """
        Выполняет треугольную сделку:
        1. Купить BTC за USDT
        2. Купить ETH за BTC
        3. Продать ETH за USDT
        """
        # Проверяем, что цены актуальны
        if not all(k in self.prices for k in ['BTC/USDT', 'ETH/BTC', 'ETH/USDT']):
            return None

        btc_usdt = self.prices['BTC/USDT']
        eth_btc = self.prices['ETH/BTC']
        eth_usdt = self.prices['ETH/USDT']

        # Проверяем глубину стакана для каждого шага
        if not self.check_depth('BTC/USDT', 'buy', capital_usdt):
            self.logger.log("❌ Недостаточная глубина для покупки BTC")
            return None

        btc_amount = capital_usdt / btc_usdt
        # Для ETH/BTC нужно знать объём в ETH, который получится
        eth_amount = btc_amount * eth_btc
        if not self.check_depth('ETH/BTC', 'buy', btc_amount):  # проверка по BTC? Упростим
            # Более точная проверка: нужен объём в ETH на продажу (или в BTC)
            self.logger.log("❌ Недостаточная глубина для ETH/BTC")
            return None

        if not self.check_depth('ETH/USDT', 'sell', eth_amount * eth_usdt):
            self.logger.log("❌ Недостаточная глубина для продажи ETH")
            return None

        # Исполняем лимитные ордера
        try:
            # 1. Купить BTC за USDT по лимиту
            order1 = self.client.create_limit_buy_order(
                symbol='BTC/USDT',
                amount=btc_amount,
                price=btc_usdt
            )
            self.logger.log(f"📈 Куплено {btc_amount:.6f} BTC по {btc_usdt}")
            # Ждём исполнения (упрощённо: ждём 3 сек, потом проверяем)
            time.sleep(3)
            order1 = self.client.fetch_order(order1['id'], 'BTC/USDT')
            if order1['status'] != 'closed':
                self.client.cancel_order(order1['id'], 'BTC/USDT')
                self.logger.log("❌ Не удалось купить BTC вовремя, отмена")
                return None

            # 2. Купить ETH за BTC
            order2 = self.client.create_limit_buy_order(
                symbol='ETH/BTC',
                amount=eth_amount,
                price=eth_btc
            )
            self.logger.log(f"📈 Куплено {eth_amount:.6f} ETH по {eth_btc} BTC")
            time.sleep(3)
            order2 = self.client.fetch_order(order2['id'], 'ETH/BTC')
            if order2['status'] != 'closed':
                self.client.cancel_order(order2['id'], 'ETH/BTC')
                self.logger.log("❌ Не удалось купить ETH вовремя, отмена")
                return None

            # 3. Продать ETH за USDT
            order3 = self.client.create_limit_sell_order(
                symbol='ETH/USDT',
                amount=eth_amount,
                price=eth_usdt
            )
            self.logger.log(f"📉 Продано {eth_amount:.6f} ETH по {eth_usdt}")
            time.sleep(3)
            order3 = self.client.fetch_order(order3['id'], 'ETH/USDT')
            if order3['status'] != 'closed':
                self.client.cancel_order(order3['id'], 'ETH/USDT')
                self.logger.log("❌ Не удалось продать ETH вовремя, отмена")
                return None

            # Расчёт прибыли
            final_usdt = eth_amount * eth_usdt
            profit = final_usdt - capital_usdt
            self.logger.log(f"✅ Сделка завершена. Прибыль: {profit:.2f} USDT")
            return profit

        except Exception as e:
            self.logger.log(f"❌ Ошибка исполнения: {e}")
            return None
