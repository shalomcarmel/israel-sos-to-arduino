import pyfirmata
import time
import datetime
import requests
from json.decoder import JSONDecodeError
import json
import serial.tools.list_ports
import configparser
import re
import hashlib

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')

def save_global_hashed_events(location, data):
    hashed_events_string = "\n".join(data)
    with open(location, "w") as file:
        file.write(hashed_events_string)
    return

def load_global_hashed_events(location):
    try:
        with open(location, "r") as file:
            # Read lines into a list and remove any trailing newline characters
            hashed_events = [line.strip() for line in file.readlines()]
    except:
        hashed_events = []
    return hashed_events

def activate_webhook(event):
    # check if webhook is to be activated at all
    try:
        webhook = config["webhook"]
    except:
        print('No Webhook defined')
        return
    webhook_url = webhook.get('URL')
    if not webhook_url:
        print('No Webhook URL defined')
        return
    # retrieve webhook parameters
    webhook_method = webhook.get('method', 'POST')
    try:
        webhook_headers = config["webhook-headers"]
    except:
        webhook_headers = {'Content-Type': 'application/json'}
    try:
        webhook_parameters = config["webhook-parameters"]
    except:
        webhook_parameters = {}
    webhook_content_type = webhook_headers.get('Content-Type', 'application/json')
    json_pattern = '^application\/(vnd\.api\+)?json.*$'
    send_JSON = re.match(json_pattern, webhook_content_type)
    webhook_headers['Content-Type'] = webhook_content_type
    # start preparing the full request parameters
    request_parameters = {"headers" : dict(webhook_headers) }
    params = dict(webhook_parameters)
    if webhook_method.lower() in ['get', 'head', 'delete', 'options']:
        params.update(event)
    else:
        if send_JSON:
            request_parameters["json"]=event
        else:
            request_parameters["data"]=event
    request_parameters["params"] = params
    try:
        res = requests.request(webhook_method, webhook_url, **request_parameters)
        response = res.content
    except Exception as e:
        print("ERROR: invoking webhook")
        response = ''
    return response

def get_current_events():
    url = EMERGENCY_FEED
    # https://www.oref.org.il/WarningMessages/History/AlertsHistory.json
    try:
        response = requests.get(url)
    except Exception as e:
        print("ERROR: HTTP request failed")
        print("ERROR:",e)
        raise
    try:
        results = response.json()
        return results
    except JSONDecodeError:
        print("ERROR: response JSON decoding failure")
        print("ERROR: Response:\t", response.content.decode('utf-8'))
        raise

def filtered_events(full_events, location,seconds):
    response=[]
    now = datetime.datetime.now()
    for event in full_events:
        event_time = datetime.datetime.strptime(event['alertDate'], "%Y-%m-%d %H:%M:%S")
        diff = (now - event_time).seconds
        event_hash = calculate_event_hash(event)
        if  (location is None or location in event['data']) and diff<=seconds and event_hash not in GLOBAL_HASHED_EVENTS:
            response.append(event)
            GLOBAL_HASHED_EVENTS.append(event_hash)
    return response

def find_arduino_com_port():
    arduino_ports = [
        p.device
        for p in serial.tools.list_ports.comports()
        if 'Arduino' in p.description or 'CH340' in p.description or 'FTDI' in p.description
    ]
    if not arduino_ports:
        raise IOError("No Arduino found")
    if len(arduino_ports) > 1:
        print('Multiple Arduinos found - using the first one')
    return arduino_ports[0]

def calculate_event_hash(event):
    # The `sort_keys=True` ensures that the dictionary is serialized in a consistent order, so identical dictionaries produce identical strings.
    event_string = json.dumps(event, sort_keys=True)
    hash_object = hashlib.sha256()
    hash_object.update(event_string.encode())
    return hash_object.hexdigest()

def main():
    while True:
        try:
            events = get_current_events()
        except:
            print("Error: while fetching data.")
            events = []
        print(f"Found {len(events)} raw events in live feed")
        events_to_handle = filtered_events(events, MYLOCATION, MYTIMEFRAME)
        print(f"There are {len(events_to_handle)} messages to handle")
        save_global_hashed_events(HISTORY_FILE, GLOBAL_HASHED_EVENTS)
        if len(events_to_handle)>0: # have messages
            if HAVE_WEBHOOK and INVOKE_WEBHOOK:
                print(f"Sending {len(events_to_handle)} events to webhook")
                for event in events_to_handle:
                    activate_webhook(event)
            if INVOKE_ARDUINO:
                COMport = find_arduino_com_port()
                print(f"Arduino is connected on port: {COMport}")
                board = pyfirmata.Arduino(COMport, baudrate=57600)
                board.digital[ARDUINO_DIGITAL_PIN].mode = pyfirmata.PWM
                for i in range(3):
                    board.digital[ARDUINO_DIGITAL_PIN].write(100)
                    time.sleep(1)
                    board.digital[ARDUINO_DIGITAL_PIN].write(0)
                    time.sleep(1)
                board.exit()
        time.sleep(seconds_between_polls)

if __name__ == '__main__':
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
    GLOBAL_HASHED_EVENTS = load_global_hashed_events(HISTORY_FILE)
    main()
