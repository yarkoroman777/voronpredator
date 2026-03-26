import time
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
            best_ask = order_book['asks'][0][0]
            best_ask_volume = order_book['asks'][0][1]
            required_volume = amount_usdt / best_ask
            return best_ask_volume >= required_volume * config.MIN_DEPTH_RATIO
        elif side == 'sell':
            best_bid = order_book['bids'][0][0]
            best_bid_volume = order_book['bids'][0][1]
            required_volume = amount_usdt / best_bid
            return best_bid_volume >= required_volume * config.MIN_DEPTH_RATIO
        return False

    def execute_triangle(self, capital_usdt):
        """
        Выполняет треугольную сделку с промежуточными проверками спреда.
        Возвращает прибыль в USDT или None при отмене/ошибке.
        """
        # Проверяем, что цены актуальны
        if not all(k in self.prices for k in ['BTC/USDT', 'ETH/BTC', 'ETH/USDT']):
            self.logger.log("❌ Цены не актуальны, сделка отменена")
            return None

        btc_usdt = self.prices['BTC/USDT']
        eth_btc = self.prices['ETH/BTC']
        eth_usdt = self.prices['ETH/USDT']

        # Проверка глубины для покупки BTC
        if not self.check_depth('BTC/USDT', 'buy', capital_usdt):
            self.logger.log("❌ Недостаточная глубина для покупки BTC")
            return None

        # --- ШАГ 1: Покупка BTC ---
        btc_amount = capital_usdt / btc_usdt
        try:
            order1 = self.client.create_limit_buy_order(
                symbol='BTC/USDT',
                amount=btc_amount,
                price=btc_usdt
            )
            self.logger.log(f"📈 Покупка BTC/USDT на {capital_usdt:.2f} USDT по {btc_usdt:.2f}")
            time.sleep(3)
            order1 = self.client.fetch_order(order1['id'], 'BTC/USDT')
            if order1['status'] != 'closed':
                self.client.cancel_order(order1['id'], 'BTC/USDT')
                self.logger.log("❌ Не удалось купить BTC вовремя, отмена")
                return None
        except Exception as e:
            self.logger.log(f"❌ Ошибка при покупке BTC: {e}")
            return None

        # --- ПОСЛЕ ПОКУПКИ BTC: пересчитываем спред с текущими ценами ---
        # Обновляем цены через fetch_tickers (можно и через WebSocket, но для надёжности запросим свежие)
        tickers = self.client.fetch_tickers(['ETH/BTC', 'ETH/USDT'])
        eth_btc_new = tickers['ETH/BTC']['last']
        eth_usdt_new = tickers['ETH/USDT']['last']

        # Пересчитываем финальный USDT после обмена BTC->ETH->USDT
        final_usdt = btc_amount * eth_btc_new * eth_usdt_new
        new_spread = (final_usdt / capital_usdt - 1) * 100
        # Вычитаем комиссии (уже учтены в capital_usdt, но в new_spread их нет, поэтому проверяем чистое значение)
        # Нам нужно, чтобы после комиссий (0.3%) оставалось не менее MIN_SPREAD_PERCENT
        net_spread = new_spread - (config.TRADE_FEE * 3 * 100)
        if net_spread < config.MIN_SPREAD_PERCENT:
            self.logger.log(f"⚠️ Спред схлопнулся до {new_spread:.2f}% (чистый {net_spread:.2f}%), отмена сделки")
            # Откат: продаём BTC обратно в USDT
            try:
                self.client.create_market_sell_order('BTC/USDT', btc_amount)
                self.logger.log("🔄 BTC продан обратно в USDT, сделка отменена")
            except Exception as e:
                self.logger.log(f"❌ Ошибка при откате: {e}")
            return None

        # --- ШАГ 2: Покупка ETH за BTC ---
        eth_amount = btc_amount * eth_btc_new
        if not self.check_depth('ETH/BTC', 'buy', btc_amount * eth_btc_new):
            self.logger.log("❌ Недостаточная глубина для ETH/BTC")
            # Откат
            self.client.create_market_sell_order('BTC/USDT', btc_amount)
            return None

        try:
            order2 = self.client.create_limit_buy_order(
                symbol='ETH/BTC',
                amount=eth_amount,
                price=eth_btc_new
            )
            self.logger.log(f"📈 Покупка ETH/BTC на {btc_amount:.6f} BTC по {eth_btc_new:.6f}")
            time.sleep(3)
            order2 = self.client.fetch_order(order2['id'], 'ETH/BTC')
            if order2['status'] != 'closed':
                self.client.cancel_order(order2['id'], 'ETH/BTC')
                self.logger.log("❌ Не удалось купить ETH вовремя, отмена")
                self.client.create_market_sell_order('BTC/USDT', btc_amount)
                return None
        except Exception as e:
            self.logger.log(f"❌ Ошибка при покупке ETH: {e}")
            self.client.create_market_sell_order('BTC/USDT', btc_amount)
            return None

        # --- ПОСЛЕ ПОКУПКИ ETH: проверяем спред перед продажей ---
        tickers2 = self.client.fetch_tickers(['ETH/USDT'])
        eth_usdt_final = tickers2['ETH/USDT']['last']
        final_usdt2 = eth_amount * eth_usdt_final
        new_spread2 = (final_usdt2 / capital_usdt - 1) * 100
        net_spread2 = new_spread2 - (config.TRADE_FEE * 3 * 100)
        if net_spread2 < config.MIN_SPREAD_PERCENT:
            self.logger.log(f"⚠️ Спред схлопнулся перед продажей ETH ({new_spread2:.2f}%), отмена")
            # Откат: продаём ETH обратно в BTC, потом BTC в USDT (упрощённо продадим ETH за USDT, но цена может быть невыгодна)
            # Лучше просто продать ETH на рынке и закрыть позицию, пусть с небольшой потерей
            try:
                self.client.create_market_sell_order('ETH/USDT', eth_amount)
                self.logger.log("🔄 ETH продан в USDT, сделка отменена")
            except Exception as e:
                self.logger.log(f"❌ Ошибка при откате: {e}")
            return None

        # --- ШАГ 3: Продажа ETH за USDT ---
        try:
            order3 = self.client.create_limit_sell_order(
                symbol='ETH/USDT',
                amount=eth_amount,
                price=eth_usdt_final
            )
            self.logger.log(f"📉 Продажа ETH/USDT по {eth_usdt_final:.2f}")
            time.sleep(3)
            order3 = self.client.fetch_order(order3['id'], 'ETH/USDT')
            if order3['status'] != 'closed':
                self.client.cancel_order(order3['id'], 'ETH/USDT')
                self.logger.log("❌ Не удалось продать ETH вовремя, отмена")
                # В этой ситуации мы держим ETH, нужно принять решение: держать или продать по рынку
                self.client.create_market_sell_order('ETH/USDT', eth_amount)
                return None
        except Exception as e:
            self.logger.log(f"❌ Ошибка при продаже ETH: {e}")
            return None

        # --- ФИНАЛ ---
        final_usdt_actual = eth_amount * eth_usdt_final
        profit = final_usdt_actual - capital_usdt
        self.logger.log(f"✅ Сделка завершена. Прибыль: {profit:.2f} USDT")
        return profit
