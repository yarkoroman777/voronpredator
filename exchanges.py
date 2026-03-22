import ccxt
import config

def create_binance_client():
    """Создаёт и возвращает клиент Binance с API-ключами."""
    client = ccxt.binance({
        'apiKey': config.BINANCE_API_KEY,
        'secret': config.BINANCE_SECRET,
        'enableRateLimit': True,       # автоматическое соблюдение лимитов
        'options': {
            'defaultType': 'spot',
        }
    })
    return client
