import config
import math

def calculate_spread(prices):
    """
    Рассчитывает спред для треугольника USDT -> BTC -> ETH -> USDT.
    prices: dict с ценами BTC/USDT, ETH/BTC, ETH/USDT
    Возвращает спред в процентах (положительный, если есть прибыль).
    """
    try:
        btc_usdt = prices['BTC/USDT']
        eth_btc = prices['ETH/BTC']
        eth_usdt = prices['ETH/USDT']
    except KeyError:
        return None

    # Исправленная формула: 1 USDT -> (1/btc_usdt) BTC -> (1/btc_usdt) * (1/eth_btc) ETH -> (1/btc_usdt)*(1/eth_btc)*eth_usdt USDT
    final_usdt = (1 / btc_usdt) * (1 / eth_btc) * eth_usdt
    spread = (final_usdt - 1) * 100
    return spread

def get_expected_profit(capital_usdt, spread_percent):
    """
    Возвращает ожидаемую прибыль в USDT с учётом комиссий.
    spread_percent: спред до вычета комиссий (в %).
    """
    net_spread = spread_percent - (config.TRADE_FEE * 3 * 100)
    if net_spread <= 0:
        return 0
    profit = capital_usdt * (net_spread / 100)
    return profit
