import os
from dotenv import load_dotenv

load_dotenv()

# Binance API
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET = os.getenv("BINANCE_SECRET")

# Telegram (опционально)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Настройки торговли
MIN_SPREAD_PERCENT = float(os.getenv("MIN_SPREAD_PERCENT", 0.35))
SLIPPAGE_TOLERANCE = float(os.getenv("SLIPPAGE_TOLERANCE", 0.1))

# Символы и треугольник
# Мы используем пары: USDT -> BTC -> ETH -> USDT
# Символы для ордеров: BTC/USDT, ETH/BTC, ETH/USDT
SYMBOL1 = "BTC/USDT"
SYMBOL2 = "ETH/BTC"
SYMBOL3 = "ETH/USDT"

# Комиссия Binance спот (в процентах)
TRADE_FEE = 0.001  # 0.1%

# Глубина стакана: минимальный объём на нужной цене (в процентах от суммы сделки)
MIN_DEPTH_RATIO = 1.5  # <-- изменено с 2.0 на 1.5

# Логирование
LOG_FILE = "arbitrage.log"
