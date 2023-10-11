## Israel SOS Emergency notifications to Arduino
### This is not a replacement for the official apps
[![App for iOS](media/apple-app.png)](http://bit.ly/Oref_App_iOS)
[![App for Android](media/android-app.png)](http://bit.ly/Oref_App_Android)

The IDF Home Security department has a feed that contains a live feed of events.

You may want to monitor the feed and take actions: move a robotic arm via arduino, control your digital home, send notifications to family abroad, or anything else that comes to mind. 

This is a template to do that. 

The python script monitors the IDF live feed, can invoke IFTTT / Zapier / Make.com webhooks, and can control custom appliances via Arduino.  

### Installation of the python script
The `check_events_activate_arduino.py` script has several prerequisites. 

Use pip to install them 

    # to install in the python environment
    pip install -r requirements.txt
    
    # to install in this directory
    pip install -r requirements.txt -t .

Copy `config-example.ini` to a new file `config.ini` and modify it according to your needs.
### Reset history
The tool keeps a record of processed events in a history file. Clear the history.txt file to reset. 
### Known limitations and problems
This script must run from an Israeli IP address. The IDF blocks non-Israeli traffic. 