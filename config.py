import configparser
import json

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')

INVOKE_ARDUINO = config.get('general', 'invoke_arduino', fallback='false').lower() == 'true'
INVOKE_WEBHOOK = config.get('general', 'invoke_webhook', fallback='false').lower() == 'true'
ARDUINO_DIGITAL_PIN = config.getint('arduino', 'digital_pin', fallback=0)
MYLOCATION = config.get('personal', 'alerts_location', fallback=None)
MYTIMEFRAME = int(config.get('personal', 'seconds_window', fallback=300))
EMERGENCY_FEED = config.get('general', 'emergency_feed')
HAVE_WEBHOOK = bool(config.get('webhook', 'URL', fallback=False))
WEBHOOK_FIRST = config.get('webhook', 'webhook_first', fallback='false').lower() == 'true'
HISTORY_FILE = config.get('general', 'history_file', fallback='history.txt')
seconds_between_polls = int(config.get('general', 'seconds_between_polls', fallback=15))
