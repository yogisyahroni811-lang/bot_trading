import aiohttp
from core.config import ConfigManager
from core.logger import get_logger

logger = get_logger(__name__)

async def send_telegram_alert(message: str):
    """
    Sends a message to the configured Telegram chat.
    """
    config = ConfigManager.load_config()
    notif_conf = config.get('notifications', {})
    
    if not notif_conf.get('telegram_enabled', False):
        return

    bot_token = notif_conf.get('bot_token')
    chat_id = notif_conf.get('chat_id')

    if not bot_token or not chat_id:
        logger.warning("Telegram enabled but token/chat_id missing in config")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    logger.error(f"Telegram send failed: {await response.text()}", extra={"context": {"status": response.status}})
    except Exception as e:
        logger.error(f"Telegram connection error: {e}", extra={"context": {"error": str(e)}})
    except Exception as e:
        logger.error(f"Telegram connection error: {e}", extra={"context": {"error": str(e)}})

def send_telegram_alert_sync(message: str):
    """
    Synchronous version for crash handler.
    """
    try:
        import requests
        config = ConfigManager.load_config()
        notif_conf = config.get('notifications', {})
        
        if not notif_conf.get('telegram_enabled', False):
            return

        bot_token = notif_conf.get('bot_token')
        chat_id = notif_conf.get('chat_id')

        if not bot_token or not chat_id:
            return

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        # Don't log to logger as it might be crashed, just stderr
        print(f"Failed to send crash alert: {e}")
