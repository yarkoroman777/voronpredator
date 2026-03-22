import logging
import config
import requests

class Logger:
    def __init__(self, log_file=config.LOG_FILE):
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.console = logging.getLogger()

    def log(self, message, send_telegram=True):
        """Логирует сообщение и отправляет в Telegram, если настроено."""
        print(message)
        logging.info(message)
        if send_telegram and config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
            self.send_telegram(message)

    def send_telegram(self, message):
        """Отправляет сообщение в Telegram."""
        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            requests.post(url, data=data, timeout=5)
        except Exception as e:
            print(f"Telegram error: {e}")
