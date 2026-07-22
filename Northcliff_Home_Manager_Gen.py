#!/usr/bin/env python
#Northcliff Home Manager - 17.4 Gen (Fix Calendar bug in TRMNL). Public/sanitised release - replace all <Your ...> placeholders with your own values.
import paho.mqtt.client as mqtt
import time
from datetime import datetime, date, timedelta
import json
import requests
import base64
import asyncio
import aiohttp
from luftdaten import Luftdaten
from astral import LocationInfo
from astral.sun import sun
import caldav
import pytz
import vobject
import re
from requests.utils import requote_uri
import traceback

class NorthcliffHomeManagerClass(object):
    def __init__(self, key_state_log_file_name, watchdog_file_name, luftdaten_sensor_id):
        #print ('Instantiated Home Manager')
        self.key_state_log_file_name = key_state_log_file_name
        self.watchdog_file_name = watchdog_file_name
        self.multisensors_present = True # Enable Multisensor monitoring
        self.door_sensors_present = True # Enables door sensor monitoring
        self.flood_sensors_present = True # Enables flood sensor monitoring
        self.garage_door_present = True # Enables garage door control
        self.aquarium_monitor_present = True # Enables aquarium monitoring
        self.enviro_monitors_present = True  # Enables outdoor air quality monitoring
        self.shelly_power_monitor_present = True # Enables Shelly 3EM Totals to Domoticz
        self.trmnl_present = True # Enables sending of data to a TRMNL display
        self.window_blinds_present = True # Enables the full WindowBlindClass automation (PowerView). Mutually exclusive with the lux-hysteresis below
        # List the multisensor names
        self.multisensor_names = ['Living', 'Study', 'Kitchen', 'North', 'South', 'Main', 'Rear Balcony', 'North Balcony', 'South Balcony', 'Comms']
        # List the outdoor sensors
        self.outdoor_multisensor_names = ['Rear Balcony', 'North Balcony', 'South Balcony']
        # Group outdoor sensors as services under one homebridge accessory name for passing to the homebridge object
        self.outdoor_sensors_homebridge_name = 'Balconies'
        # Name each door sensor and identify the room that contains that door sensor
        self.door_sensor_names_locations = {'North Living Room': 'Living Room', 'South Living Room': 'Living Room', 'Entry': 'Entry'}
        # List the flood sensors
        self.flood_sensor_names = ['Kitchen', 'Aquarium', 'Laundry']
        # Set up other mqtt topics
        self.homebridge_incoming_mqtt_topic = 'homebridge/from/set'
        self.domoticz_incoming_mqtt_topic = 'domoticz/out'
        self.garage_door_incoming_mqtt_topic = 'GarageStatus'
        self.aquarium_monitor_incoming_mqtt_topic = 'AquaTempHB'
        self.shelly_power_0_incoming_mqtt_topic = 'shellies/shellyem3-485519D6A0A5/emeter/0/power'
        self.shelly_energy_0_incoming_mqtt_topic = 'shellies/shellyem3-485519D6A0A5/emeter/0/total'
        self.shelly_power_1_incoming_mqtt_topic = 'shellies/shellyem3-485519D6A0A5/emeter/1/power'
        self.shelly_energy_1_incoming_mqtt_topic = 'shellies/shellyem3-485519D6A0A5/emeter/1/total'
        self.shelly_power_2_incoming_mqtt_topic = 'shellies/shellyem3-485519D6A0A5/emeter/2/power'
        self.shelly_energy_2_incoming_mqtt_topic = 'shellies/shellyem3-485519D6A0A5/emeter/2/total'
        self.window_blind_light_sensor = 'South Balcony' # Set name of Light Sensor that controls blind. '' if unused.
        self.window_blind_threshold_1 = 12000
        self.window_blind_threshold_2 = 20000
        self.previous_window_blind_state = 0
        heartbeat_check_start_time = time.time()
        enviro_capture_time = heartbeat_check_start_time
        self.luftdaten_sensor_id = luftdaten_sensor_id
        self.enviro_config = {'Outdoor': {'mqtt Topic': 'Outdoor EM0', 'Capture Non AQI': True, 'Homebridge Display': True, 'Wind': 'East', 'Capture Time': enviro_capture_time, 'Luftdaten Sensor ID': self.luftdaten_sensor_id,
                                          'Device IDs': {'P1': 784, 'P2.5': 778, 'P10': 779, 'AQI': 780, 'NH3': 781, 'Oxi': 782, 'Red': 783,
                                                          'Temp': 819, 'Hum': 819, 'Dew': 1063, 'Bar': 819, 'Lux':821, 'Noise': 838, 'Wind': 912}},
                              'Indoor': {'mqtt Topic': 'Indoor EM1', 'Capture Non AQI': True, 'Homebridge Display': True,
                                          'Device IDs': {'P1': 789, 'P2.5': 790, 'P10': 791, 'AQI': 792, 'NH3': 795, 'Oxi': 793, 'Red': 794,
                                                          'Temp': 824, 'Hum': 824, 'Dew': 1062,'Bar': 824, 'Lux':820, 'CO2': 825, 'VOC': 826, 'Noise': 837}},
                              'Front Outdoor': {'mqtt Topic': 'Outdoor EM012', 'Capture Non AQI': True, 'Homebridge Display': False, 'Wind': 'West',
                                          'Device IDs': {'P1': 909, 'P2.5': 908, 'P10': 907, 'AQI': 906, 'NH3': 905, 'Oxi': 904, 'Red': 903,
                                                          'Temp': 899, 'Hum': 899, 'Dew': 1061, 'Bar': 899, 'Lux':901, 'Noise': 902, 'Wind': 912}}}
        self.enable_outdoor_enviro_monitor_luftdaten_backup = True # Enable Luftdaten readings if no PM readings from outdoor Enviro Monitor
        self.enviro_wind_config = {'Front Outdoor': {'Air Pressure': None, 'Direction': 'West', 'Offset': 0.0}, 'Outdoor': {'Air Pressure': None, 'Direction': 'East', 'Offset': -0.25}}
        self.enviro_wind_distance = 23 #The distance between enviro air pressure sources in metres
        self.previous_enviro_wind_source = None #To ensure that alternate enviro sources are used to measure wind speed
        self.latest_wind = None #Most recent locally-measured wind for the TRMNL display
        self.enviro_wind_results = [None for x in range(10)] # Set up historical wind_data
        self.watchdog_update_time = 0
        self.trmnl_update_time = 0
        # ---- Window blind automation (used when window_blinds_present is True) ----
        self.powerview_hub_ip = '<Your PowerView Gen 2 Hub IP Address>' # PowerView Gen 2 hub for blind scene control
        self.window_blind_config = {'Living Room Blinds': {'light sensor': 'South Balcony', 'temp sensor': 'North Balcony',
                                    'sunlight threshold 0': 100, 'sunlight threshold 1': 1000, 'sunlight threshold 2': 12000, 'sunlight threshold 3': 20000,
                                    'high_temp_threshold': 28, 'low_temp_threshold': 15, 'sunny_season_start': 10, 'sunny_season_finish': 3,
                                    'non_sunny_season_sunlight_level_3_4_persist_time': 1800, 'sunny_season_sunlight_level_3_4_persist_time': 600,
                                    'blind_doors': {'North Living Room': {'door_state': 'Open', 'door_state_changed': False},
                                                    'South Living Room': {'door_state': 'Open', 'door_state_changed': False}},
                                    'status': 'Open', # Whole-group blind position: 'Open', 'Venetian' or 'Closed'
                                    'scenes': {'Open': 'Living Open', 'Venetian': 'Living View', 'Closed': 'Living Close',
                                               'Windows Venetian': 'Living Windows View', 'Windows Closed': 'Living Windows Close'}}}
        self.blind_light_sensor_names = [self.window_blind_config[b]['light sensor'] for b in self.window_blind_config]
        self.call_room_sunlight_control = {'State': False, 'Blind': '', 'Light Level': 100}
        self.call_control_blinds = {'State': False, 'Blind': '', 'Blind_position': ''}
        self.auto_blind_override_changed = {'Changed': False, 'Blind': '', 'State': False}
        self.blind_control_door_changed = {'State': False, 'Blind': '', 'Changed': False}
                               
    def on_connect(self, client, userdata, flags, reason_code, properties):
        # Sets up the mqtt subscriptions. Subscribing in on_connect() means that if we lose the connection and reconnect then subscriptions will be renewed.
        if reason_code == 0:
            self.print_update('Northcliff Home Manager Connected to mqtt Broker')
            print('')
            time.sleep(1)
            client.subscribe(self.homebridge_incoming_mqtt_topic) #Subscribe to Homebridge status for interworking with Apple Home
            client.subscribe(self.domoticz_incoming_mqtt_topic) # Subscribe to Domoticz for access to its devices
            if self.garage_door_present:
                client.subscribe(self.garage_door_incoming_mqtt_topic) # Subscribe to the Garage Door Controller
            if self.aquarium_monitor_present:
                client.subscribe(self.aquarium_monitor_incoming_mqtt_topic) # Subscribe to the Aquarium Monitor Heatbeat
            if self.shelly_power_monitor_present: # Subscribe to relevant Shelly messages if enabled
                client.subscribe(self.shelly_power_0_incoming_mqtt_topic)
                client.subscribe(self.shelly_energy_0_incoming_mqtt_topic)
                client.subscribe(self.shelly_power_1_incoming_mqtt_topic)
                client.subscribe(self.shelly_energy_1_incoming_mqtt_topic)
                client.subscribe(self.shelly_power_2_incoming_mqtt_topic)
                client.subscribe(self.shelly_energy_2_incoming_mqtt_topic)
            if self.enviro_monitors_present:
                for enviro_name in self.enviro_config:
                    client.subscribe(self.enviro_config[enviro_name]['mqtt Topic']) # Subscribe to the Enviro Monitors
        else:
           self.print_update('Error: Not Connected to mqtt Broker. Reason: ' + str(reason_code)) 
                
    def on_message(self, client, userdata, msg):
        # Calls the relevant methods for the Home Manager, based on the mqtt publish messages received from the doorbell monitor, the homebridge buttons,
        # Domoticz, the aircon controller and the garage door controller
        decoded_payload = str(msg.payload.decode("utf-8"))
        #print (msg.topic)
        if 'shellies' not in msg.topic: # Shelly doesn't have a json payload
            parsed_json = json.loads(decoded_payload)
        #print(msg.topic, parsed_json)
        if msg.topic == self.homebridge_incoming_mqtt_topic: # If it's a homebridge status message
            homebridge.capture_homebridge_buttons(parsed_json) # Capture the homebridge button
        elif msg.topic == self.domoticz_incoming_mqtt_topic: # If coming from domoticz
            domoticz.process_device_data(parsed_json) # Process the domoticz device data
        elif msg.topic == self.garage_door_incoming_mqtt_topic: # If coming from the Garage Door Controller
            garage_door.capture_status(parsed_json) # Capture garage door status
        elif msg.topic == self.aquarium_monitor_incoming_mqtt_topic:
            aquarium.capture_aquarium_heartbeat(parsed_json)
        elif msg.topic == self.shelly_power_0_incoming_mqtt_topic or msg.topic == self.shelly_energy_0_incoming_mqtt_topic or msg.topic == self.shelly_power_1_incoming_mqtt_topic or msg.topic == self.shelly_energy_1_incoming_mqtt_topic or msg.topic == self.shelly_power_2_incoming_mqtt_topic or msg.topic == self.shelly_energy_2_incoming_mqtt_topic:
            #print ('Shelly Message Found', decoded_payload)
            shelly.process_reading(msg.topic, decoded_payload) # Process and send Shelly readings
        else: # Test for enviro
            identified_message = False
            for enviro_name in self.enviro_config:
                if msg.topic == self.enviro_config[enviro_name]['mqtt Topic']: # If coming from an Enviro Monitor
                    #self.print_update(enviro_name +  ' Northcliff Enviro Monitor Data:' + str(parsed_json) + ' on ')
                    if enviro_name == 'Outdoor':
                        self.enviro_config[enviro_name]['Capture Time'] = time.time()
                    identified_message = True
                    enviro_monitor[enviro_name].capture_readings('Enviro', parsed_json) # Capture enviro readings
            if not identified_message: # If the mqtt topic is unknown
                print ('Unknown mqtt message received', msg.topic)

    def print_update(self, print_message): # Prints with a date and time stamp
        today = datetime.now()
        print('')
        print(print_message + today.strftime('%A %d %B %Y @ %H:%M:%S'))

    def log_key_states(self, reason):
        # Log Door, Blind and Powerpoint States
        key_state_log = {}
        key_state_log["Reason"] = reason
        if self.door_sensors_present:
            key_state_log["Door State"] = {name: door_sensor[name].current_door_opened for name in self.door_sensor_names_locations}
        if self.enviro_monitors_present:
            for enviro_name in self.enviro_config:
                if enviro_name == 'Indoor' and 'CO2' in self.enviro_config[enviro_name]['Device IDs']:
                    key_state_log['Enviro Max CO2'] = enviro_monitor[enviro_name].max_CO2
                    #print('Wrote Enviro Max CO2 to Log', reason, enviro_name, enviro_monitor[enviro_name].max_CO2)
        if self.window_blind_light_sensor != '' and self.multisensors_present:
            key_state_log['Window Blind State'] = homebridge.previous_window_blind_state
            key_state_log['Window Blind Light Level'] = multisensor[self.window_blind_light_sensor].sensor_types_with_value['Light Level']
        if self.window_blinds_present:
            key_state_log['Blind Status'] = {b: window_blind[b].window_blind_config['status'] for b in self.window_blind_config}
            key_state_log['Blind High Temp'] = {b: window_blind[b].window_blind_config['high_temp_threshold'] for b in self.window_blind_config}
            key_state_log['Blind Low Temp'] = {b: window_blind[b].window_blind_config['low_temp_threshold'] for b in self.window_blind_config}
            key_state_log['Blind Auto Override'] = {b: window_blind[b].auto_override for b in self.window_blind_config}
        with open(self.key_state_log_file_name, 'w') as f:
            f.write(json.dumps(key_state_log))   

    def retrieve_key_states(self):
        with open(self.key_state_log_file_name, 'r') as f:
            parsed_key_states = json.loads(f.read())
        print('Retrieved Key States', parsed_key_states)
        print ('Previous logging reason was', parsed_key_states['Reason'])
        if self.door_sensors_present and 'Door State' in parsed_key_states:
            for name in parsed_key_states['Door State']:
                door_sensor[name].current_door_opened = parsed_key_states['Door State'][name]
                door_sensor[name].previous_door_opened = parsed_key_states['Door State'][name]
                homebridge.update_door_state(name, self.door_sensor_names_locations[name], parsed_key_states['Door State'][name], False)
        if self.enviro_monitors_present and 'Enviro Max CO2' in parsed_key_states:
            for enviro_name in self.enviro_config:
                if enviro_name == 'Indoor' and 'CO2' in self.enviro_config[enviro_name]['Device IDs']:
                    enviro_monitor[enviro_name].max_CO2 = parsed_key_states['Enviro Max CO2']
                    #print('Retrieved Enviro Max CO2 from Log', parsed_key_states['Reason'], enviro_name, enviro_monitor[enviro_name].max_CO2)
        if self.window_blind_light_sensor != '' and self.multisensors_present:
            if 'Window Blind State' in parsed_key_states:
                homebridge.previous_window_blind_state = parsed_key_states['Window Blind State']
            if 'Window Blind Light Level' in parsed_key_states:
                multisensor[self.window_blind_light_sensor].sensor_types_with_value['Light Level'] = parsed_key_states['Window Blind Light Level']
        if self.window_blinds_present and 'Blind Status' in parsed_key_states:
            for b in parsed_key_states['Blind Status']:
                window_blind[b].window_blind_config['status'] = parsed_key_states['Blind Status'][b]
                window_blind[b].hk_position, window_blind[b].hk_tilt = window_blind[b]._status_to_pos_tilt(parsed_key_states['Blind Status'][b])
                window_blind[b].window_blind_config['high_temp_threshold'] = parsed_key_states['Blind High Temp'][b]
                window_blind[b].window_blind_config['low_temp_threshold'] = parsed_key_states['Blind Low Temp'][b]
                window_blind[b].auto_override = parsed_key_states['Blind Auto Override'][b]
                homebridge.update_blind_status(b, window_blind[b].window_blind_config)
                homebridge.update_blind_target_temps(b, parsed_key_states['Blind High Temp'][b], parsed_key_states['Blind Low Temp'][b])
                homebridge.set_auto_blind_override_button(b, parsed_key_states['Blind Auto Override'][b])
        if self.enviro_monitors_present:
            homebridge.reset_enviro_wind()

    def shutdown(self, reason):
        self.log_key_states(reason)
        client.loop_stop() # Stop mqtt monitoring
        self.print_update('Home Manager Shut Down due to ' + reason + ' on ')
      
    def run(self): # The main Home Manager start-up, loop and shut-down code                          
        try:
            # Retrieve logged key states
            self.retrieve_key_states()
            if self.multisensors_present:
                # Initialise multisensor readings on homebridge to start-up settings
                for name in self.multisensor_names:    
                    homebridge.update_temperature(name, multisensor[name].sensor_types_with_value['Temperature'])
                    homebridge.update_humidity(name, multisensor[name].sensor_types_with_value['Humidity'])
                    homebridge.update_light_level(name, multisensor[name].sensor_types_with_value['Light Level'])
                    homebridge.update_motion(name, multisensor[name].sensor_types_with_value['Motion'])
            # Initialise Garage Door state
            if self.garage_door_present:
                homebridge.update_garage_door('Closing')
                homebridge.update_garage_door('Closed')
            previous_luftdaten_capture_time = 0 # Initialise luftdaten capture time
            while True: # The main Home Manager Loop
                if time.time() - self.watchdog_update_time >= 60: # Write to the watchdog log every minute
                    with open(self.watchdog_file_name, 'w') as f:
                        f.write('Home Manager Script Alive')
                    self.watchdog_update_time = time.time()
                if self.enviro_monitors_present and self.enable_outdoor_enviro_monitor_luftdaten_backup:
                    if time.time() - self.enviro_config['Outdoor']['Capture Time'] > 600: # Capture Luftdaten Air Quality if the Outdoor Enviro Monitor is unavailable
                        if time.time() - previous_luftdaten_capture_time > 900:
                            print('No message from Outdoor Northcliff Enviro Monitor, using Luftdaten from station', self.enviro_config['Outdoor']['Luftdaten Sensor ID'])
                            enviro_monitor['Outdoor'].capture_luftdaten_data(self.enviro_config['Outdoor']['Luftdaten Sensor ID'])
                            previous_luftdaten_capture_time = time.time()
                if self.trmnl_present:
                    now = datetime.now()
                    if now.minute in (1, 16, 31, 46) and time.time() - self.trmnl_update_time >= 120: # Pushes updates one minute past hour and half hour
                        trmnl.push()
                        self.trmnl_update_time = time.time()
                if self.window_blinds_present:
                    # Blind triggers are actioned here (not in on_message) so their network/sleep calls don't delay mqtt handling
                    if self.call_room_sunlight_control['State']: # New blind light-sensor reading
                        blind = self.call_room_sunlight_control['Blind']
                        window_blind[blind].room_sunlight_control(self.call_room_sunlight_control['Light Level'])
                        self.call_room_sunlight_control['State'] = False
                    if self.blind_control_door_changed['Changed']: # A blind-control door changed state
                        blind = self.blind_control_door_changed['Blind']
                        light_level = multisensor[self.window_blind_config[blind]['light sensor']].sensor_types_with_value['Light Level']
                        window_blind[blind].room_sunlight_control(light_level)
                        self.blind_control_door_changed['Changed'] = False
                    if self.auto_blind_override_changed['Changed']: # The auto-override switch changed
                        blind = self.auto_blind_override_changed['Blind']
                        light_level = multisensor[self.window_blind_config[blind]['light sensor']].sensor_types_with_value['Light Level']
                        window_blind[blind].room_sunlight_control(light_level)
                        self.auto_blind_override_changed['Changed'] = False
                    if self.call_control_blinds['State']: # A manual blind change was invoked
                        blind = self.call_control_blinds['Blind']
                        window_blind[blind].control_blinds(self.call_control_blinds['Blind_position'])
                        self.call_control_blinds['State'] = False
                time.sleep(1) 
        except KeyboardInterrupt:
            self.shutdown('Keyboard Interrupt')

class HomebridgeClass(object):
    def __init__(self, outdoor_multisensor_names, outdoor_sensors_name, door_sensor_names_locations, enviro_config,
                 window_blind_threshold_1, window_blind_threshold_2, previous_window_blind_state):
        #print ('Instantiated Homebridge', self)
        self.outgoing_mqtt_topic = 'homebridge/to/set'
        self.outdoor_multisensor_names = outdoor_multisensor_names
        self.outdoor_sensors_name = outdoor_sensors_name
        self.door_sensor_names_locations = door_sensor_names_locations
        self.temperature_format = {'name': ' Temperature', 'service': 'TemperatureSensor', 'service_name': ' Temperature', 'characteristics_properties': {}}
        self.humidity_format = {'name': ' Humidity', 'service': 'HumiditySensor', 'service_name': ' Humidity', 'characteristics_properties': {}}
        self.light_level_format = {'name': ' Lux', 'service': 'LightSensor', 'service_name': ' Lux', 'characteristics_properties': {}}
        self.motion_format = {'name': ' Motion', 'service': 'MotionSensor', 'service_name': ' Motion', 'characteristics_properties': {}}
        self.door_format = {'name': ' Door', 'service': 'ContactSensor', 'service_name': ' Door', 'characteristics_properties':{'StatusLowBattery': {}}}
        self.door_state_map = {'door_opened':{False: 0, True: 1}, 'low_battery':{False: 0, True: 1}}
        self.dimmer_format = {'name': ' Light', 'service': 'Lightbulb', 'service_name': ' Light', 'characteristics_properties': {'Brightness': {}}}
        self.garage_door_format = {'name': 'Garage', 'service_name': 'Garage Door', 'service': 'GarageDoorOpener', 'characteristics_properties': {}}
        self.flood_state_format = {'name': ' Flood', 'service': 'LeakSensor', 'service_name': '', 'characteristics_properties': {'StatusLowBattery': {}}}
        self.window_blind_threshold_1 = window_blind_threshold_1
        self.window_blind_threshold_2 = window_blind_threshold_2
        self.previous_window_blind_state = previous_window_blind_state
        # Set up Enviro Monitors
        self.enviro_config = enviro_config
        self.enviro_aqi_format = {'name': ' AQI', 'service_name': ' AQI', 'service': 'AirQualitySensor',
                                   'characteristics_properties': {'PM10Density': {}, 'PM2_5Density': {}, 'NitrogenDioxideDensity': {}}}
        self.enviro_reducing_format = {'name': ' Reducing', 'service_name': ' Reducing', 'service': 'AirQualitySensor', 'characteristics_properties': {'NitrogenDioxideDensity': {}}}
        self.enviro_ammonia_format = {'name': ' Ammonia', 'service_name': ' Ammonia', 'service': 'AirQualitySensor', 'characteristics_properties': {'NitrogenDioxideDensity': {}}}
        self.enviro_PM2_5_alert_format = {'name': ' PM2.5 Alert', 'service_name': ' PM2.5 Alert', 'service' :'MotionSensor', 'characteristics_properties': {'MotionDetected':{}}}
        self.enviro_temp_format = {'name': ' Env Temp', 'service': 'TemperatureSensor', 'service_name': ' Env Temp', 'characteristics_properties': {}}
        self.enviro_hum_format = {'name': ' Env Hum', 'service': 'HumiditySensor', 'service_name': ' Env Hum', 'characteristics_properties': {}}
        self.enviro_dew_format = {'name': ' Env Dew', 'service': 'TemperatureSensor', 'service_name': ' Env Dew', 'characteristics_properties': {}}
        self.enviro_lux_format = {'name': ' Env Lux', 'service': 'LightSensor', 'service_name': ' Env Lux', 'characteristics_properties': {}}
        self.enviro_CO2_level_format = {'name': ' CO2', 'service_name': ' CO2', 'service' :'CarbonDioxideSensor', 'characteristics_properties': {'CarbonDioxideLevel': {}, 'CarbonDioxidePeakLevel': {}}}
        self.enviro_wind_format = {'name': 'Balcony Wind', 'service_name': 'Balcony Wind', 'service': 'Fan', 'characteristics_properties': {}}
        self.enviro_chill_format = {'name': 'Balcony Chill', 'service_name': 'Balcony Chill', 'service': 'TemperatureSensor',  'characteristics_properties': {'CurrentTemperature': {'minValue': 0, 'maxValue': 100, 'minStep': 0.1}}}
        self.enviro_wind_state = {'Active': False, 'Wind Speed': 0 , 'Direction': 0}
        # ---- Window blind HomeKit formats (used when window_blinds_present is True) ----
        self.blinds_temp_format = {'service': 'Thermostat', 'low_temp_service_name': 'Blind Low Temp', 'high_temp_service_name': 'Blind High Temp'}
        self.auto_blind_override_button_format = {'service_name': 'Auto Blind Override', 'service': 'Switch', 'characteristics_properties': {}}
        self.blind_incoming_position_map = {100: 'Open', 50: 'Venetian', 0: 'Closed'}
        self.blind_outgoing_position_map = {'Open': 100, 'Venetian': 50, 'Closed': 0}
        # Tilt-based representation: the position axis carries Open (raised) vs lowered, the horizontal tilt axis carries Venetian vs Closed
        self.blind_status_to_position = {'Open': 100, 'Venetian': 0, 'Closed': 0}
        self.blind_status_to_tilt = {'Open': 90, 'Venetian': 90, 'Closed': 0} # 90 deg = slats open (Venetian), 0 deg = slats shut (Closed)
        
    def capture_homebridge_buttons(self, parsed_json):
        if self.dimmer_format['name'] in parsed_json['name']:
            print("Homebridge", parsed_json['service_name'], "Dynalite Button Pressed")
        elif parsed_json['name'] == self.garage_door_format['name']:
            self.process_garage_door_button(parsed_json)
        elif mgr.window_blinds_present and parsed_json['name'] in mgr.window_blind_config:
            self.process_blind_button(parsed_json)
        elif 'Towels' in parsed_json['name'] or 'Floor' in parsed_json['name'] or 'Window' in parsed_json['name'] or 'Shutters' in parsed_json['name'] or 'Coffee' in parsed_json['name']:
            print(parsed_json['name'], "Button Pressed. Message ignored")
        elif parsed_json['name'] == self.enviro_wind_format['name']:
            print("Enviro Wind button pressed. Resetting to previous state")
            self.process_enviro_wind_button()
        else:
            print('Unknown homebridge button received', parsed_json['name'])
        
    def process_garage_door_button(self, parsed_json):
        #print('Homebridge: Process Garage Door Button', parsed_json)
        if parsed_json['value'] == 0: # Open garage door if it's an open door command
            garage_door.open_garage_door(parsed_json)
        else: # Ignore any other commands and set homebridge garage door button to closed state
            homebridge_json = {}
            homebridge_json['name'] = self.garage_door_format['name']
            homebridge_json['service_name'] = self.garage_door_format['service_name']
            homebridge_json['value'] = 1
            characteristics = ('CurrentDoorState', 'TargetDoorState')
            for characteristic in characteristics:
                homebridge_json['characteristic'] = characteristic
                client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json)) # Close Current and Target Homebridge GarageDoor
 
    def process_enviro_wind_button(self): #Reset to previous state
        time.sleep(0.5)
        homebridge_json = {}
        homebridge_json['name'] = self.enviro_wind_format['name']
        homebridge_json['characteristic'] = 'On'
        homebridge_json['value'] = self.enviro_wind_state['Active']
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'RotationSpeed'
        homebridge_json['value'] = self.enviro_wind_state['Wind Speed']
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))  
        homebridge_json['characteristic'] = 'RotationDirection'
        homebridge_json['value'] = self.enviro_wind_state['Direction']
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def process_blind_button(self, parsed_json):
        #print('Homebridge: Process Blind Button', parsed_json)
        blind_name = parsed_json['name'] # Capture the blind's name
        # Set blind override status if it's an auto blind control override switch
        if parsed_json['service_name'] == self.auto_blind_override_button_format['service_name']:
            auto_override = parsed_json['value']
            window_blind[blind_name].change_auto_override(auto_override)
            mgr.auto_blind_override_changed = {'Changed': True, 'Blind': blind_name, 'State': auto_override}
        # Set blind high temp threshold
        elif parsed_json['service_name'] == self.blinds_temp_format['high_temp_service_name'] and parsed_json['characteristic'] == 'TargetTemperature':
            window_blind[blind_name].set_high_temp(parsed_json['value'])
        # Set blind low temp threshold
        elif parsed_json['service_name'] == self.blinds_temp_format['low_temp_service_name'] and parsed_json['characteristic'] == 'TargetTemperature':
            window_blind[blind_name].set_low_temp(parsed_json['value'])
        # Force the temp thermostats back to 'Cool' (low) and 'Heat' (high) if an attempt is made to change their state
        elif (parsed_json['service_name'] == self.blinds_temp_format['high_temp_service_name'] or parsed_json['service_name'] == self.blinds_temp_format['low_temp_service_name']) and parsed_json['characteristic'] == 'TargetHeatingCoolingState':
            time.sleep(0.1)
            self.update_blind_temp_states(blind_name)
        # Whole-group blind control: position axis = Open vs lowered, horizontal tilt axis = Venetian vs Closed.
        # HomeKit sends these as separate messages, so each is combined with the last-known other axis.
        elif parsed_json['characteristic'] == 'TargetPosition':
            window_blind[blind_name].change_blind_from_homekit(position=parsed_json['value'])
        elif parsed_json['characteristic'] == 'TargetHorizontalTiltAngle':
            window_blind[blind_name].change_blind_from_homekit(tilt=parsed_json['value'])
        else: # Ignore other buttons
            pass

    def update_blind_status(self, blind_room, window_blind_config):
        # Reflect the whole-group blind state back to the HomeKit WindowCovering: the position axis (Open vs
        # lowered) and the horizontal tilt axis (Venetian vs Closed). Send each Current before its Target (so
        # HomeKit derives no motion) and PositionState 'Stopped' last, spaced so homebridge-mqtt doesn't
        # coalesce/drop the reconciling updates and leave the tile stuck showing 'Opening'/'Closing'.
        homebridge_json = {}
        homebridge_json['name'] = blind_room
        homebridge_json['service_name'] = blind_room
        status = window_blind_config['status']
        position = self.blind_status_to_position[status]
        tilt = self.blind_status_to_tilt[status]
        for characteristic, value in (('CurrentPosition', position), ('TargetPosition', position),
                                      ('CurrentHorizontalTiltAngle', tilt), ('TargetHorizontalTiltAngle', tilt),
                                      ('PositionState', 2)):
            homebridge_json['characteristic'] = characteristic
            homebridge_json['value'] = value
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            time.sleep(0.1)

    def set_auto_blind_override_button(self, blind_room, state):
        homebridge_json = {}
        homebridge_json['name'] = blind_room
        homebridge_json['service_name'] = self.auto_blind_override_button_format['service_name']
        homebridge_json['characteristic'] = 'On'
        homebridge_json['value'] = state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_blind_current_temps(self, blind_room, temp):
        homebridge_json = {}
        homebridge_json['name'] = blind_room
        homebridge_json['characteristic'] = 'CurrentTemperature'
        homebridge_json['value'] = temp
        homebridge_json['service_name'] = self.blinds_temp_format['high_temp_service_name']
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['service_name'] = self.blinds_temp_format['low_temp_service_name']
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        self.update_blind_temp_states(blind_room)

    def update_blind_target_temps(self, blind_room, high_temp, low_temp):
        homebridge_json = {}
        homebridge_json['name'] = blind_room
        homebridge_json['characteristic'] = 'TargetTemperature'
        homebridge_json['value'] = high_temp
        homebridge_json['service_name'] = self.blinds_temp_format['high_temp_service_name']
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['value'] = low_temp
        homebridge_json['service_name'] = self.blinds_temp_format['low_temp_service_name']
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        self.update_blind_temp_states(blind_room)

    def update_blind_temp_states(self, blind_room):
        # Sets the Low Temp thermostat to 'Cool' and the High Temp thermostat to 'Heat'
        homebridge_json = {}
        homebridge_json['name'] = blind_room
        homebridge_json['characteristic'] = 'TargetHeatingCoolingState'
        homebridge_json['service_name'] = self.blinds_temp_format['low_temp_service_name']
        homebridge_json['value'] = 2
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['service_name'] = self.blinds_temp_format['high_temp_service_name']
        homebridge_json['value'] = 1
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_temperature(self, name, temperature):
        homebridge_json = {}
        homebridge_json['characteristic'] = 'CurrentTemperature'
        if name in self.outdoor_multisensor_names: # Check to see if this is an outdoor sensor
            # The homebridge JSON name for outdoor sensors is different from the internal sensors
            homebridge_json['name'] = self.outdoor_sensors_name
        else:
            homebridge_json['name'] = name + self.temperature_format['name']
        homebridge_json['service_name'] = name + self.temperature_format['service_name'] # Add the name to the service name
        homebridge_json['value'] = temperature
        # Update homebridge with the current temperature
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        
    def update_humidity(self, name, humidity):
        homebridge_json = {}
        homebridge_json['characteristic'] = 'CurrentRelativeHumidity'
        if name in self.outdoor_multisensor_names: # Check to see if this is an outdoor sensor
            # The homebridge JSON name for outdoor sensors is different from the internal sensors
            homebridge_json['name'] = self.outdoor_sensors_name
        else:
            homebridge_json['name'] = name + self.humidity_format['name']
        homebridge_json['service_name'] = name + self.humidity_format['service_name'] # Add the humidity service name to the name
        homebridge_json['value'] = humidity
        # Update homebridge with the current hunidity
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json)) # Update homebridge with the current humidity

    def update_light_level(self, name, light_level):
        # Check if it's a blind light sensor and adjust
        if name == mgr.window_blind_light_sensor and not mgr.window_blinds_present:
            old_state = self.previous_window_blind_state
            if light_level > self.window_blind_threshold_2:
                adjusted_light_level = light_level # Blockout on rising light
                self.previous_window_blind_state = 2
            elif light_level > self.window_blind_threshold_1 and light_level <= self.window_blind_threshold_2:
                adjusted_light_level = 4000 # Shade when between thresholds
                self.previous_window_blind_state = 1
            elif (light_level > self.window_blind_threshold_1 - 6000) and light_level <= self.window_blind_threshold_1:
                if self.previous_window_blind_state >= 1:
                    adjusted_light_level = 4000 # Shade on falling light
                    self.previous_window_blind_state = 1
                else:
                    adjusted_light_level = 1500 # Remain open on rising light
            elif light_level > 1400 and (light_level <= self.window_blind_threshold_1 - 6000):
                adjusted_light_level = 1400 # Open on falling light and keep open on rising light
                self.previous_window_blind_state = 0
            else:
                adjusted_light_level = light_level # Don't adjust light level if it's below 1400
                self.previous_window_blind_state = 0
            print(name, "Light Level:", light_level, "Adjusted Light Level:", adjusted_light_level, "Blind State:", self.previous_window_blind_state)
            light_level = adjusted_light_level
            if self.previous_window_blind_state != old_state:   # only on a real transition
                mgr.log_key_states("Window Blind State Change")
        homebridge_json = {}
        homebridge_json['characteristic'] = 'CurrentAmbientLightLevel'
        if name in self.outdoor_multisensor_names: # Check to see if this is an outdoor sensor
            # The homebridge JSON name for outdoor sensors is different from the internal sensors
            homebridge_json['name'] = self.outdoor_sensors_name
        else:
            homebridge_json['name'] = name + self.light_level_format['name']
        homebridge_json['service_name'] = name + self.light_level_format['service_name']# Add the light level service name to the name
        if light_level < 0.0001:
            light_level = 0.0001 #HomeKit minValue is set to 0.0001 Lux
        homebridge_json['value'] = light_level
        # Update homebridge with the current light level
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_motion(self, name, motion_detected):
        homebridge_json = {}
        homebridge_json['characteristic'] = 'MotionDetected'
        if name in self.outdoor_multisensor_names: # Check to see if this is an outdoor sensor
            # The homebridge JSON name for outdoor sensors is different from the internal sensors
            homebridge_json['name'] = self.outdoor_sensors_name
        else:
            homebridge_json['name'] = name + self.motion_format['name'] 
        homebridge_json['service_name'] = name + self.motion_format['service_name'] # Add the motion service name to the name
        homebridge_json['value'] = motion_detected
        # Update homebridge with the current motion state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        
    def update_door_state(self, door, location, door_opened, low_battery):
        homebridge_json = {}
        homebridge_json['name'] = location
        homebridge_json['characteristic'] = 'ContactSensorState'
        homebridge_json['service_name'] = door + self.door_format['name']
        homebridge_json['value'] = self.door_state_map['door_opened'][door_opened]
        #print("Homebridge Door State Change", homebridge_json)
        # Update homebridge with the current door state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'StatusLowBattery'
        homebridge_json['value'] = self.door_state_map['low_battery'][low_battery]
        # Update homebridge with the current door battery state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_flood_state(self, name, flooding, low_battery):
        #print('Homebridge: Update Flood State', name, flooding, low_battery)
        homebridge_json = {}
        homebridge_json['name'] = name + self.flood_state_format['name']
        homebridge_json['characteristic'] = 'LeakDetected'
        homebridge_json['service_name'] = name
        homebridge_json['value'] = flooding
        # Update homebridge with the current flood state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'StatusLowBattery'
        homebridge_json['value'] = low_battery
        # Update homebridge with the current flood sensor battery state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        
    def update_garage_door(self, state):
        #print('Homebridge: Update Garage Door', state)
        homebridge_json = dict(self.garage_door_format)
        if state =='Opened':
            mgr.print_update("Garage Door Opened on ")
            homebridge_json['characteristic'] = 'CurrentDoorState'
            homebridge_json['value'] = 0
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json)) # Send Current Garage Door Open Message to Homebridge
        elif state == 'Closing':
            mgr.print_update("Garage Door Closing on ")
            homebridge_json['characteristic'] = 'TargetDoorState'
            homebridge_json['value'] = 1
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json)) # Send Target Garage Door Closing Message to Homebridge
        elif state == 'Closed':
            mgr.print_update("Garage Door Closed on ")
            homebridge_json['characteristic'] = 'CurrentDoorState'
            homebridge_json['value'] = 1
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json)) # Send Current Garage Door Closed Message to Homebridge
        else:
            print("Invalid Garage Door Status Message", state)
        
    def update_enviro_aqi(self, name, enviro_config, aqi, parsed_json, individual_aqi, PM2_5_alert_level, gas_readings, max_CO2, CO2_threshold):
        homebridge_json = {}
        homebridge_json['name'] = name + self.enviro_aqi_format['name']
        homebridge_json['service_name'] = name + self.enviro_aqi_format['service_name']
        homebridge_json['characteristic'] = 'AirQuality'
        homebridge_json['value'] = aqi
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'PM2_5Density' # Requires homebridge-mqtt >= 0.6.2
        homebridge_json['value'] = round(parsed_json['P2.5'], 0)
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'PM10Density'
        homebridge_json['value'] = round(parsed_json['P10'], 0)
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        if 'VOC' in enviro_config['Device IDs'] and 'VOC' in parsed_json:
            homebridge_json['characteristic'] = 'VOCDensity'
            if parsed_json['VOC'] > 1000: # HomeKit Max limit
                homebridge_json['value'] = 1000
            else:
                homebridge_json['value'] = round(parsed_json['VOC'], 0)
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        if gas_readings:
            homebridge_json['characteristic'] = 'NitrogenDioxideDensity'
            homebridge_json['value'] = parsed_json['Oxi']
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['name'] = name + self.enviro_reducing_format['name']
            homebridge_json['service_name'] = name + self.enviro_reducing_format['service_name']
            homebridge_json['characteristic'] = 'AirQuality'
            homebridge_json['value'] = individual_aqi['Red']
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['characteristic'] = 'NitrogenDioxideDensity'
            homebridge_json['value'] = parsed_json['Red']
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['name'] = name + self.enviro_ammonia_format['name']
            homebridge_json['service_name'] = name + self.enviro_ammonia_format['service_name']
            homebridge_json['characteristic'] = 'AirQuality'
            homebridge_json['value'] = individual_aqi['NH3']
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['characteristic'] = 'NitrogenDioxideDensity'
            homebridge_json['value'] = parsed_json['NH3']
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        if 'CO2' in enviro_config['Device IDs'] and 'CO2' in parsed_json:
            homebridge_json['name'] = name + self.enviro_CO2_level_format['name']
            homebridge_json['service_name'] = name + self.enviro_CO2_level_format['service_name']
            homebridge_json['characteristic'] = 'CarbonDioxideLevel'
            homebridge_json['value'] = round(parsed_json['CO2'], 0)
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['characteristic'] = 'CarbonDioxideDetected'
            if homebridge_json['value'] < CO2_threshold:
                homebridge_json['value'] = 0
            else:
                homebridge_json['value'] = 1
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['characteristic'] = 'CarbonDioxidePeakLevel'
            homebridge_json['value'] = max_CO2
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['name'] = name + self.enviro_PM2_5_alert_format['name']
        homebridge_json['service_name'] = name + self.enviro_PM2_5_alert_format['service_name']
        homebridge_json['characteristic'] = 'MotionDetected'
        if parsed_json['P2.5'] >= PM2_5_alert_level:
            homebridge_json['value'] = True
        else:
            homebridge_json['value'] = False
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        if enviro_config['Capture Non AQI']: # If there are Non AQI Readings
            homebridge_json['name'] = name + self.enviro_temp_format['name']
            homebridge_json['service_name'] = name + self.enviro_temp_format['service_name']
            homebridge_json['characteristic'] = 'CurrentTemperature'
            homebridge_json['value'] = parsed_json['Temp']
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['name'] = name + self.enviro_hum_format['name']
            homebridge_json['service_name'] = name + self.enviro_hum_format['service_name']
            homebridge_json['characteristic'] = 'CurrentRelativeHumidity'
            homebridge_json['value'] = parsed_json['Hum'][0]
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['name'] = name + self.enviro_dew_format['name']
            homebridge_json['service_name'] = name + self.enviro_dew_format['service_name']
            homebridge_json['characteristic'] = 'CurrentTemperature'
            homebridge_json['value'] = parsed_json['Dew']
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['name'] = name + self.enviro_lux_format['name']
            homebridge_json['service_name'] = name + self.enviro_lux_format['service_name']
            homebridge_json['characteristic'] = 'CurrentAmbientLightLevel'
            light_level = parsed_json['Lux']
            if light_level < 0.0001:
                light_level = 0.0001 #HomeKit minValue is set to 0.0001 Lux
            homebridge_json['value'] = light_level
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            
    def reset_enviro_wind(self):
        homebridge_json = {}
        homebridge_json['name'] = self.enviro_wind_format['name']
        homebridge_json['characteristic'] = 'On'
        homebridge_json['value'] = False
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        self.enviro_wind_state['Active'] = False
        homebridge_json['name'] = self.enviro_chill_format['name']
        homebridge_json['characteristic'] = 'CurrentTemperature'
        homebridge_json['value'] = 0
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            
    def update_enviro_wind(self, wind_data):
        homebridge_json = {}
        homebridge_json['name'] = self.enviro_wind_format['name']
        if not self.enviro_wind_state['Active']:
            homebridge_json['characteristic'] = 'On'
            homebridge_json['value'] = True
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            self.enviro_wind_state['Active'] = True
        self.enviro_wind_state['Wind Speed'] = round(wind_data['Gust km/h'])
        if self.enviro_wind_state['Wind Speed'] > 100:
            self.enviro_wind_state['Wind Speed'] = 100 #Limit wind speed to 100km/h
        if wind_data['Direction'] == 'S' or wind_data['Direction'] == 'E':
            self.enviro_wind_state['Direction'] = 1 #Anticlockwise
        else:
            self.enviro_wind_state['Direction'] = 0 #Clockwise
        homebridge_json['characteristic'] = 'RotationDirection'
        homebridge_json['value'] = self.enviro_wind_state['Direction']
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'RotationSpeed'
        homebridge_json['value'] = self.enviro_wind_state['Wind Speed']
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['name'] = self.enviro_chill_format['name']
        homebridge_json['characteristic'] = 'CurrentTemperature'
        homebridge_json['value'] = wind_data['Chill']
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        
class DomoticzClass(object): # Manages communications to and from the z-wave objects
    def __init__(self):
        self.outgoing_mqtt_topic = 'domoticz/in'
        # Set up Domoticz label formats so that incoming message names can be decoded
        self.temperature_humidity_label = ' Climate'
        self.light_level_label = ' Light Level'
        self.motion_label = ' Motion'
        self.door_label = ' Door'
        self.flood_label = ' Flooding'
        self.shelly_power_idx = 1121
        
    def process_device_data(self, parsed_json):
        # Selects the object and method for incoming multisensor, door sensor, flood sensor and light dimmer messages
        sensor_name = parsed_json['name'] # This is where Domoticz sends the sensor's name
        # Determine which sensor label is in the name, remove the sensor label (leaving the sensor object name)
        # and call the relevant sensor method for that object
        if self.temperature_humidity_label in sensor_name: # If it's a temp/humidity sensor
            multisensor[sensor_name[0:sensor_name.find(self.temperature_humidity_label)]].process_temperature_humidity(parsed_json)
        elif self.light_level_label in sensor_name: # If it's a light level sensor
            multisensor[sensor_name[0:sensor_name.find(self.light_level_label)]].process_light_level(parsed_json)
        elif self.motion_label in sensor_name: # If it's a motion sensor
            multisensor[sensor_name[0:sensor_name.find(self.motion_label)]].process_motion(parsed_json)
        elif self.door_label in sensor_name: # If it's a door sensor
            #print('Door Message', sensor_name, parsed_json)
            door_sensor[sensor_name[0:sensor_name.find(self.door_label)]].process_door_state_change(parsed_json)
        elif self.flood_label in sensor_name: # If it's a flood sensor
            #print('Flood Message', sensor_name, parsed_json)
            flood_sensor[sensor_name[0:sensor_name.find(self.flood_label)]].process_flood_state_change(parsed_json)


    def update_enviro_aqi(self, name, enviro_config, aqi, parsed_json):
        #print('Incoming Domoticz Enviro', parsed_json, enviro_config)
        domoticz_json = {}
        domoticz_json['nvalue'] = 0
        non_aqi_message = {}
        for measurement in enviro_config['Device IDs']:
            if (measurement == 'Temp' or measurement == 'Hum' or measurement == 'Bar') and measurement in parsed_json:
                non_aqi_message[measurement] = parsed_json[measurement]
            elif (measurement == 'VOC' or measurement == 'CO2') and measurement in parsed_json:
                domoticz_json['idx'] = enviro_config['Device IDs'][measurement]
                domoticz_json['nvalue'] = parsed_json[measurement]
                domoticz_json['svalue'] = ""
                #print('Domoticz', domoticz_json)
                client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))
            elif measurement != 'AQI' and measurement in parsed_json:
                domoticz_json['idx'] = enviro_config['Device IDs'][measurement]
                domoticz_json['nvalue'] = 0
                domoticz_json['svalue'] = str(parsed_json[measurement])
                #print('Domoticz', domoticz_json)
                client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))
        domoticz_json['idx'] = enviro_config['Device IDs']['AQI']
        domoticz_json['nvalue'] = 0
        domoticz_json['svalue'] = str(aqi)
        #print('Domoticz', domoticz_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))
        if non_aqi_message: # If there are some climate messages
            domoticz_json['idx'] = enviro_config['Device IDs']['Temp']
            domoticz_json['nvalue'] = 0
            domoticz_json['svalue'] = str(non_aqi_message['Temp']) + ';'+ str(non_aqi_message['Hum'][0]) + ';' + non_aqi_message['Hum'][1] + ';' + str(non_aqi_message['Bar'][0]) + ';' + non_aqi_message['Bar'][1]
            #print('Domoticz', domoticz_json)
            client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))                       
            if 'Wind' in parsed_json:
                if parsed_json['Wind'] != {}:
                    wind_data = parsed_json['Wind']
                    wind_speed = wind_data['m/s'] * 10 #Domoticz requires wind speed in m/sec * 10
                    wind_gust = wind_data['Gust m/s'] * 10 #Domoticz requires wind speed in m/sec * 10
                    wind_chill = wind_data['Chill']
                    domoticz_json = {}
                    domoticz_json['idx'] = enviro_config['Device IDs']['Wind']
                    domoticz_json['nvalue'] = 0
                    domoticz_json['svalue'] = wind_data['Bearing'] + ';' + wind_data['Direction'] + ';' + str(wind_speed) + ';' + str(wind_gust) + ';' + str(non_aqi_message['Temp']) + ';' + str(wind_chill)
                    #print('Wind Domoticz', domoticz_json)
                    client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))

    def update_electricity_data(self, total_power, total_energy):
        #print ('Update Domoticz Electricity', total_power, total_energy)
        send_power = round(total_power,1)
        send_energy = int(total_energy)
        domoticz_json = {}
        domoticz_json['idx'] = self.shelly_power_idx
        domoticz_json['nvalue'] = 0
        domoticz_json['svalue'] = str(send_power) + ';' + str(send_energy)
        #print('Electricity Domoticz', domoticz_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))    
                        
class FloodSensorClass(object): 
    def __init__(self, name):        
        self.name = name
        #print ('Instantiated Flood Sensor', self, name)
        self.low_battery = False # Initial battery state is OK
        self.flood_state_map = {'Flood State':{0: 'No Flooding', 1: 'Flooding'},
                                       'Battery State':{0: 'normal', 1: 'low'}}

    def process_flood_state_change(self, parsed_json):
        #print(parsed_json)
        #flood_value =  int(parsed_json['svalue1'])
        self.flooding = parsed_json['nvalue'] # 1 for flooding and 0 for not flooding
        battery_value = int(parsed_json['Battery'])
        #if flood_value == 255:
            #self.flooding = 1 # Indicates that there is flooding
        #else:
            #self.flooding = 0 # Indicates that there is no flooding
        if battery_value < 20: # Check if the battery level is less than 20%
            self.low_battery = 1 # Battery low flag
        else:
            self.low_battery = 0 # Battery OK flag
        mgr.print_update("Updating Flood Detection for " + self.name + " Sensor to " + self.flood_state_map['Flood State'][self.flooding]
                         + ". Battery Level " + self.flood_state_map['Battery State'][self.low_battery] + " on ")
        # Update homebridge with the new flood state
        homebridge.update_flood_state(self.name, self.flooding, self.low_battery)

class DoorSensorClass(object):
    def __init__(self, door, location):
        self.door = door
        self.location = location
        self.previous_door_opened = True
        self.current_door_opened = True
        self.low_battery = False
        self.door_state_map = {'door_opened':{False: 'closed', True: 'open'},
                                'low_battery':{False: 'normal', True: 'low'}}
        # Check the blind config to see if this door controls a blind
        self.blind_door = {'Blind Control': False, 'Blind Name': ''}
        if mgr.window_blinds_present:
            for blind in mgr.window_blind_config:
                if self.door in mgr.window_blind_config[blind]['blind_doors']:
                    self.blind_door = {'Blind Control': True, 'Blind Name': blind}

    def process_door_state_change(self, parsed_json):
        door_opened_value = parsed_json['nvalue']
        battery_value = int(parsed_json['Battery'])
        if door_opened_value == 1:
            self.current_door_opened = True
        else:
            self.current_door_opened = False
        if battery_value < 20:
            self.low_battery = True
        else:
            self.low_battery = False
        if self.current_door_opened != self.previous_door_opened:
            homebridge.update_door_state(self.door, self.location, self.current_door_opened, self.low_battery)
            mgr.print_update("Updating Door Detection for " + self.door + " from " +
                              self.door_state_map['door_opened'][self.previous_door_opened] + " to " +
                              self.door_state_map['door_opened'][self.current_door_opened] +
                              ". Battery Level " + self.door_state_map['low_battery'][self.low_battery] + " on ")
            if mgr.window_blinds_present and self.blind_door['Blind Control']: # Flag the door change so the blind algorithm re-evaluates
                blind_name = self.blind_door['Blind Name']
                door_state = 'Open' if self.current_door_opened else 'Closed'
                window_blind[blind_name].window_blind_config['blind_doors'][self.door]['door_state'] = door_state
                window_blind[blind_name].window_blind_config['blind_doors'][self.door]['door_state_changed'] = True
                mgr.blind_control_door_changed = {'State': self.current_door_opened, 'Blind': blind_name, 'Changed': True}
            self.previous_door_opened = self.current_door_opened
            mgr.log_key_states("Door State Change")

class MultisensorClass(object):
    def __init__(self, name):
        self.name = name
        self.sensor_types_with_value = {'Temperature': 1, 'Humidity': 1, 'Motion': False, 'Light Level': 1}
        # Check the blind config to see if this sensor's light reading controls a blind
        self.blind_sensor = {'Blind Control': False, 'Blind Name': ''}
        if mgr.window_blinds_present:
            for blind in mgr.window_blind_config:
                if self.name == mgr.window_blind_config[blind]['light sensor']:
                    self.blind_sensor = {'Blind Control': True, 'Blind Name': blind}

    def process_temperature_humidity(self, parsed_json):
        temperature = float(parsed_json['svalue1'])
        if temperature != self.sensor_types_with_value['Temperature']:
            self.sensor_types_with_value['Temperature'] = temperature
            homebridge.update_temperature(self.name, temperature)
        humidity = int(parsed_json['svalue2'])
        if abs(humidity - self.sensor_types_with_value['Humidity']) >= 2:
            self.sensor_types_with_value['Humidity'] = humidity
            homebridge.update_humidity(self.name, humidity)

    def process_light_level(self, parsed_json):
        light_level = int(parsed_json['svalue1'])
        if abs(light_level - self.sensor_types_with_value['Light Level']) >= 2:
            self.sensor_types_with_value['Light Level'] = light_level
            homebridge.update_light_level(self.name, light_level)
            if mgr.window_blinds_present and self.blind_sensor['Blind Control']: # Trigger the blind sunlight algorithm in the main loop
                mgr.call_room_sunlight_control = {'State': True, 'Blind': self.blind_sensor['Blind Name'], 'Light Level': light_level}

    def process_motion(self, parsed_json):
        motion_value = parsed_json['nvalue']
        if motion_value == 1:
            motion_detected = True
        else:
            motion_detected = False
        if motion_detected != self.sensor_types_with_value['Motion']:
            self.sensor_types_with_value['Motion'] = motion_detected
            homebridge.update_motion(self.name, motion_detected)

class GaragedoorClass(object):
    def __init__(self):
        #print ('Instantiated Garage Door', self)
        self.garage_door_mqtt_topic = 'GarageControl'  
        self.open_garage_service = 'OpenGarage'
        
    def open_garage_door(self, parsed_json):
        garage_json = {}
        garage_json['service'] = self.open_garage_service
        garage_json['value'] = parsed_json['value']
        mgr.print_update("Garage Door Open Command sent on ")
        client.publish(self.garage_door_mqtt_topic, json.dumps(garage_json)) # Send command to Garage Door          
    
    def capture_status(self, parsed_json):
        #mgr.print_update("Garage Door Message Acknowledged on ")
        #print(parsed_json)
        if parsed_json['service'] == 'Restart':
            mgr.print_update('Garage Door Opener Restarted on ')
        elif parsed_json['service'] == 'Heartbeat':
            mgr.print_update('Received Heartbeat from Garage Door Opener and sending Ack on ')
            client.publish(self.garage_door_mqtt_topic, '{"service": "Heartbeat Ack"}')
        else:
            homebridge.update_garage_door(parsed_json['service'])

class AquariumClass:
    def __init__(self):
        self.outgoing_mqtt_topic = 'AquariumHB'
    
    def capture_aquarium_heartbeat(self, parsed_json):
        if parsed_json['service'] == 'Heartbeat':
            mgr.print_update('Received Aquarium Heartbeat and sending Ack on ')
            client.publish(self.outgoing_mqtt_topic, '{"service": "Heartbeat Ack"}')
        elif parsed_json['service'] == 'Restart':
            mgr.print_update('Aquarium Heartbeat Lost. Restarting Monitor')
            
class EnviroClass(object):
    def __init__(self, name, enviro_config):
        #print ('Created Enviro Instance', name, enviro_config)
        self.name = name
        self.valid_enviro_aqi_readings = ['P1', 'P2.5', 'P10', 'Red', 'Oxi', 'NH3', 'CO2', 'VOC']
        self.valid_enviro_aqi_readings_no_gas = ['P1', 'P2.5', 'P10', 'CO2', 'VOC']
        self.valid_enviro_non_aqi_readings = ['Temp', 'Hum', 'Dew', 'Bar', 'Lux', 'Noise']
        self.valid_luftdaten_readings = ['P2.5', 'P10']
        self.air_reading_bands = {'P1':[0, 6, 17, 27, 35], 'P2.5':[0, 11, 35, 53, 70], 'P10': [0, 16, 50, 75, 100],
                                  'NH3': [0, 6, 2, 10, 15], 'Red': [0, 6, 10, 50, 75], 'Oxi': [0, 0.2, 0.4, 0.8, 1],
                                  'CO2': [0, 500, 1000, 1600, 2000], 'VOC': [0, 120, 220, 660, 2200]}
        self.PM2_5_alert_level = 35
        self.max_aqi = 1
        self.enviro_config = enviro_config
        self.max_CO2 = 0
        self.CO2_threshold = self.air_reading_bands['CO2'][2]
        self.latest = {}
        
    def capture_readings(self, source, parsed_json):
        #print('Capturing Enviro Readings', source, parsed_json)
        self.latest = parsed_json
        if source == 'Luftdaten':
            valid_source = True
            gas_readings = False
            valid_aqi_readings = self.valid_luftdaten_readings
        elif source == 'Enviro':
            valid_source = True
            if 'Gas Calibrated' in parsed_json: # Only capture gas readings if the sensors have been calibrated
                if parsed_json['Gas Calibrated']:
                    gas_readings = True
                    valid_aqi_readings = self.valid_enviro_aqi_readings
                else:
                    gas_readings = False
                    valid_aqi_readings = self.valid_enviro_aqi_readings_no_gas
            else:
                gas_readings = True # This is for backwards compatibility. Enviro Monitors prior to 3.55 didn't have a 'Gas Calibrated' key
                valid_aqi_readings = self.valid_enviro_aqi_readings
        else:
            valid_source = False
        if valid_source:
            individual_aqi = {}
            homebridge_data = {}
            domoticz_data = {}
            self.max_aqi = 0
            valid_source = False
            for reading in parsed_json: # Check each reading
                if reading in valid_aqi_readings: # Analyse AQI Readings
                    individual_aqi[reading] = 0
                    for boundary in range(4): # Check each reading against its AQI boundary
                        if parsed_json[reading] >= self.air_reading_bands[reading][boundary]: # Find the boundary that the reading has met or exceeded 
                            aqi = boundary + 1 # Convert the boundary to the AQI reading
                            individual_aqi[reading] = aqi
                            #print('Search Max AQI', aqi, reading, self.air_reading_bands[reading])
                            if aqi > self.max_aqi: # If this reading has the maximum AQI so far, make it the max AQI
                                self.max_aqi = aqi
                                max_reading = reading
                            #print('Air Quality Component:', reading, 'has an AQI Level of', aqi, 'with a reading of', round(parsed_json[reading],0))
                    if self.max_aqi > 0:
                        #print('AQI is at Level', self.max_aqi, 'due to', max_reading, 'with a reading of', round(parsed_json[max_reading],0))
                        pass
                    else:
                        #print('AQI is at Level 0')
                        pass
                    domoticz_data[reading] = parsed_json[reading]
                    # Convert ppm to ug/m3 for Enviro homebridge gases data (except for Red and NH3, which is in mg/m3)
                    if reading == 'Oxi':
                        homebridge_data[reading] = round(1000* parsed_json[reading] * 46/24.45, 0)
                        if homebridge_data[reading] > 1000: # Set max NO2 Level to 1000 ug/m3 (HAP Limit)
                            homebridge_data[reading] = 1000
                    elif reading == 'Red':
                        homebridge_data[reading] = round(parsed_json[reading] * 28/24.45, 2)
                        if homebridge_data[reading] > 1000: # Set max Red Level to 1000 mg/m3 (HAP Limit)
                            homebridge_data[reading] = 1000
                    elif reading == 'NH3':
                        homebridge_data[reading] = round(parsed_json[reading] * 17/24.45, 2)
                        if homebridge_data[reading] > 1000: # Set max NH3 Level to 1000 mg/m3 (HAP Limit)
                            homebridge_data[reading] = 1000
                    else:
                        homebridge_data[reading] = parsed_json[reading]
                    if reading == 'CO2':
                        if parsed_json[reading] > self.max_CO2:
                            print('Old Max CO2:', self.max_CO2)
                            self.max_CO2 = parsed_json[reading]
                            print('New Max CO2:', self.max_CO2)
                            mgr.log_key_states("Enviro Max CO2 Change")
                elif reading in self.valid_enviro_non_aqi_readings:
                    if self.enviro_config['Capture Non AQI']:
                        if reading != 'Noise': # Don't capture noise readings in homebridge
                            homebridge_data[reading] = parsed_json[reading]
                        domoticz_data[reading] = parsed_json[reading]
                else:
                    pass # Ignore other readings
            #print(self.name, 'Air Quality Update. Overall AQI:', self.max_aqi, 'Individual AQI:', individual_aqi)
            if self.name in mgr.enviro_wind_config:
                #print("Calculating Domoticz Wind for", self.name, "with a reading of", domoticz_data['Bar'][0], "hPa and an offset of", mgr.enviro_wind_config[self.name]['Offset'], "hPa")
                mgr.enviro_wind_config[self.name]['Air Pressure'] = domoticz_data['Bar'][0] + mgr.enviro_wind_config[self.name]['Offset']
                if mgr.previous_enviro_wind_source != self.name and mgr.previous_enviro_wind_source != None: #Ensure that there are readings from two sources
                    valid_wind_reading = True
                else:
                    valid_wind_reading = False
                    print("No valid wind reading received")
                mgr.previous_enviro_wind_source = self.name
                if valid_wind_reading:
                    wind_data = {'Gust km/h': 0, 'm/s': 0, 'Gust m/s': 0, 'Chill': 0, 'Direction': '', 'Bearing': 0}
                    current_air_pressure_delta = 0
                    valid_orientation = True
                    for enviro in mgr.enviro_wind_config:
                        if mgr.enviro_wind_config[enviro]['Direction'] == 'West':
                            enviro_orientation = 'East West'
                            current_air_pressure_delta = current_air_pressure_delta - mgr.enviro_wind_config[enviro]['Air Pressure']
                        elif mgr.enviro_wind_config[enviro]['Direction'] == 'East':
                            enviro_orientation = 'East West'
                            current_air_pressure_delta = current_air_pressure_delta + mgr.enviro_wind_config[enviro]['Air Pressure']
                        elif mgr.enviro_wind_config[enviro]['Direction'] == 'North':
                            enviro_orientation = 'North South'
                            current_air_pressure_delta = current_air_pressure_delta - mgr.enviro_wind_config[enviro]['Air Pressure']
                        elif mgr.enviro_wind_config[enviro]['Direction'] == 'South':
                            enviro_orientation = 'North South'
                            current_air_pressure_delta = current_air_pressure_delta + mgr.enviro_wind_config[enviro]['Air Pressure']
                        else:
                            valid_orientation = False
                    if valid_orientation:
                        if enviro_orientation == 'East West':
                            if current_air_pressure_delta >= 0:
                                wind_data['Direction'] = 'E'
                                wind_data['Bearing'] = '90'
                            else:
                                wind_data['Direction'] = 'W'
                                wind_data['Bearing'] = '270'
                        else:
                            if current_air_pressure_delta >= 0:
                                wind_data['Direction'] = 'N'
                                wind_data['Bearing'] = '0'
                            else:
                                wind_data['Direction'] = 'S'
                                wind_data['Bearing'] = '180'
                        current_air_pressure_delta = round(current_air_pressure_delta, 2)
                        #print("Current Delta", current_air_pressure_delta)
                if valid_wind_reading and valid_orientation:
                    # Calculate mean wind over ten measurements, calulate the mean and the highest reading for the gust level
                    for pointer in range(9, 0, -1): # Move previous temperatures one position in the list to prepare for new temperature to be recorded 
                        mgr.enviro_wind_results[pointer] = mgr.enviro_wind_results[pointer - 1]
                    mgr.enviro_wind_results[0] = abs(current_air_pressure_delta)
                    valid_reading_count = 0
                    for pointer in range(0, 10):
                        if mgr.enviro_wind_results[pointer] != None:
                            valid_reading_count += 1
                    #print("Valid Reading Count", valid_reading_count)
                    reading_sum = 0
                    for pointer in range(0, valid_reading_count):
                        reading_sum = reading_sum + mgr.enviro_wind_results[pointer]
                    air_pressure_delta = round(reading_sum/valid_reading_count, 3)
                    gust_air_pressure_delta = max(mgr.enviro_wind_results[0:valid_reading_count]) #Replace latest wind reading with maximum over the reporting period for the Gust reading
                    #print("Enviro Wind Results", mgr.enviro_wind_results)
                    wind_data['Gust km/h'] = round(gust_air_pressure_delta * 2070 / mgr.enviro_wind_distance, 1) #Convert air pressure delta to km/h
                    wind_data['m/s'] = round(air_pressure_delta * 575 / mgr.enviro_wind_distance, 1) #Convert air pressure delta to m/s
                    wind_data['Gust m/s'] = round(gust_air_pressure_delta * 575 / mgr.enviro_wind_distance, 1)
                    wind_data['Chill'] = round(13.12 + 0.6215 * parsed_json['Temp'] - 11.37 * pow(wind_data['Gust km/h'], 0.16) + 0.3965 * parsed_json['Temp'] * pow(wind_data['Gust km/h'], 0.16), 1)
                    #print("Wind Data", wind_data)
                    domoticz_data['Wind'] = wind_data
                    mgr.latest_wind = wind_data #Stash latest wind for the TRMNL display
                    homebridge.update_enviro_wind(wind_data)
            domoticz.update_enviro_aqi(self.name, self.enviro_config, self.max_aqi, domoticz_data)
            if self.enviro_config['Homebridge Display']: # Only update Homebridge if enabled
                #print(self.name, 'Homebridge Data:', homebridge_data)
                homebridge.update_enviro_aqi(self.name, self.enviro_config, self.max_aqi, homebridge_data, individual_aqi,
                                             self.PM2_5_alert_level, gas_readings, self.max_CO2, self.CO2_threshold)

    def capture_luftdaten_data(self, sensor_id): # Call this if there has been no sensor data for 15 minutes
        try:
            async def main():
                #try:
                async with aiohttp.ClientSession() as session:
                    data = Luftdaten(sensor_id, loop, session)
                    await data.get_data()
                    if not await data.validate_sensor():
                        print("Station is not available:", data.sensor_id)
                        return "Station is not available", {}
                    if data.values and data.meta:
                        # Print the sensor values
                        #print("Sensor values:", data.values)
                        # Print the coordinates for the sensor
                        #print("Location:", data.meta['latitude'], data.meta['longitude'])
                        captured_data = {"P2.5": data.values["P2"], "P10": data.values["P1"], "P1": 0}
                        print('Luftdaten Data Captured. PM2.5:', captured_data['P2.5'],'ug/m3, PM10:', captured_data['P10'], 'ug/m3')
                        return "Data Captured", captured_data
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                message, captured_data = loop.run_until_complete(main())
            finally:
                loop.close()
            if message == "Data Captured":
                self.capture_readings('Luftdaten', captured_data)
        except Exception as e:
            print('Luftdaten Error, No Outdoor Enviro Data Available:', e)
            
class ShellyReadingClass(object):
    def __init__(self):
        print("Started Shelly Class")
        # map each topic to its channel number (0/1/2)
        self.power_topics  = {mgr.shelly_power_0_incoming_mqtt_topic: 0,
                              mgr.shelly_power_1_incoming_mqtt_topic: 1,
                              mgr.shelly_power_2_incoming_mqtt_topic: 2}
        self.energy_topics = {mgr.shelly_energy_0_incoming_mqtt_topic: 0,
                              mgr.shelly_energy_1_incoming_mqtt_topic: 1,
                              mgr.shelly_energy_2_incoming_mqtt_topic: 2}
        self.power  = {}          # channel -> latest power (W)
        self.energy = {}          # channel -> latest energy (Wh)
        self.energy_seen = set()  # channels received in the current cycle
        self.total_power = 0
        self.total_energy = 0

    def process_reading(self, topic, payload):
        value = float(payload)
        if topic in self.power_topics:
            self.power[self.power_topics[topic]] = value
            self.total_power = sum(self.power.values())
        elif topic in self.energy_topics:
            channel = self.energy_topics[topic]
            self.energy[channel] = value
            self.energy_seen.add(channel)
            if self.energy_seen == {0, 1, 2}:          # one full set received, any order
                self.total_power  = sum(self.power.values())
                self.total_energy = sum(self.energy.values())
                domoticz.update_electricity_data(self.total_power, self.total_energy)
                self.energy_seen.clear()

class TrmnlClass(object):
    
    def __init__(self, plugin_uuid, api_key, geohash, caldav_url, caldav_user, caldav_pass, caldav_calendar, caldav_timezone,
                 peak_hours, tariff_rates, location):
        print("Started TRMNL Class")
        self.plugin_uuid = plugin_uuid
        self.api_key = api_key
        self.geohash = geohash
        self.caldav_url = caldav_url
        self.caldav_user = caldav_user
        self.caldav_pass = caldav_pass
        self.caldav_calendar = caldav_calendar
        self.caldav_timezone = caldav_timezone
        self.peak_hours = peak_hours
        self.tariff_rates = tariff_rates
        self.location = location

    def _fetch_bom(self, endpoint):
        url = f"https://api.weather.bom.gov.au/v1/locations/{self.geohash}/{endpoint}"
        weather_headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                                              "Accept": "application/json", "Referer": "https://www.bom.gov.au/"}
        try:
            response = requests.get(url, headers=weather_headers, timeout=30)
            response.raise_for_status()
            return response.json().get("data", {} if endpoint == "observations" else [])
        except Exception as e:
            print("TRMNL: BOM fetch error:", e)
            return {} if endpoint == "observations" else []

    def _get_tariff(self):
        dt = datetime.now()
        hour = dt.hour
        is_weekend = dt.weekday() >= 5
        if hour < 7 or hour >= 22:
            name = "Off Peak"
        elif is_weekend:
            name = "Shoulder"
        else:
            peak = self.peak_hours.get(dt.month)
            name = "Peak" if peak and peak[0] <= hour < peak[1] else "Shoulder"
        return name, self.tariff_rates[name]

    def _get_sun_times(self):
        try:
            s = sun(self.location.observer, date=datetime.now().date(), tzinfo=self.location.timezone)
            return s["sunrise"].strftime("%-I:%M %p"), s["sunset"].strftime("%-I:%M %p")
        except Exception as e:
            print("TRMNL: Sun times error:", e)
            return "–", "–"
        
    def _sanitize_ics(self, raw):
        lines = raw.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        content_start = re.compile(r'^[A-Z][A-Z0-9-]*[;:]')
        fixed = []
        for line in lines:
            if line == '':
                continue
            if fixed and not line.startswith((' ', '\t')) and not content_start.match(line):
                fixed[-1] = fixed[-1] + '\\n' + line
            else:
                fixed.append(line)
        return '\r\n'.join(fixed)
        
    def _get_calendar_events(self):
        """Return up to 5 of today's events as [{'time': str, 'title': str}, ...]."""
        tz = pytz.timezone(self.caldav_timezone)
        try:
            client = caldav.DAVClient(url=self.caldav_url, username=self.caldav_user, password=self.caldav_pass)
            principal = client.principal()
            target_cal = None
            for cal in principal.calendars():
                if cal.get_display_name() == self.caldav_calendar:
                    target_cal = cal
                    break
            if target_cal is None:
                print(f'TRMNL: Calendar "{self.caldav_calendar}" not found')
                return []
            now_local   = datetime.now(tz)
            today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end   = today_start + timedelta(days=1)
            events = target_cal.search(start=today_start, end=today_end, event=True, expand=True)
            result = []
            for event in events:
                try:
                    try:
                        vevent = event.vobject_instance.vevent
                    except Exception:
                        # caldav parses eagerly and can't hand us clean text for this event (iCloud emitted an
                        # unescaped newline, e.g. a multi-line address). Re-fetch the raw ICS directly and repair it.
                        resp = requests.get(requote_uri(str(event.url)),
                                            auth=(self.caldav_user, self.caldav_pass), timeout=10)
                        vevent = vobject.readOne(self._sanitize_ics(resp.text)).vevent
                    summary = str(vevent.summary.value) if hasattr(vevent, 'summary') else ''
                    dtstart = vevent.dtstart.value
                    if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
                        time_str = 'All day'
                        sort_key = (0, datetime.min.replace(tzinfo=tz))
                    else:
                        if dtstart.tzinfo is None:
                            dtstart = tz.localize(dtstart)
                        dtstart  = dtstart.astimezone(tz)
                        time_str = dtstart.strftime('%-I:%M %p')
                        sort_key = (1, dtstart)
                    result.append({'time': time_str, 'title': summary, '_sk': sort_key})
                except Exception as ev_ex:
                    print(f'TRMNL: Skipping calendar event: {ev_ex}')
                    continue
            result.sort(key=lambda e: e['_sk'])
            return [{'time': e['time'], 'title': e['title']} for e in result[:5]]
        except Exception as ex:
            print(f'TRMNL: Calendar fetch error: {ex}')
            return []

    def _extract(self, payload, key):
        val = payload.get(key)
        if val is None:
            return "–"
        return val[0] if isinstance(val, list) else val
    
    def _describe(self, code):
        names = {
            "sunny": "Sunny", "clear": "Clear", "mostly_sunny": "Mostly Sunny",
            "partly_cloudy": "Partly Cloudy", "cloudy": "Cloudy", "hazy": "Hazy",
            "windy": "Windy", "fog": "Fog", "frost": "Frost", "dusty": "Dusty",
            "light_shower": "Light Showers", "shower": "Showers",
            "heavy_shower": "Heavy Showers", "light_rain": "Light Rain",
            "rain": "Rain", "storm": "Storms", "snow": "Snow",
            "tropical_cyclone": "Cyclone",
        }
        return names.get(code, code.replace("_", " ").title())
    
    def _round0(self, val):
        return f"{val:.0f}" if isinstance(val, (int, float)) else val
    
    def _local_wind(self):
        w = mgr.latest_wind
        if not w:
            return "?"
        speed_kmh = round(w.get('m/s', 0) * 3.6)
        direction = w.get('Direction', '')
        if speed_kmh == 0:
            return "Calm"
        return f"{speed_kmh} km/h {direction}".strip()

    def _format_hour(self, iso_time):
        try:
            dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00")).astimezone()
            hour = dt.hour
            return f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'}"
        except Exception:
            return iso_time

    def _build_payload(self, obs, forecast):
        hours = []
        for entry in forecast[:6]:
            chance = entry.get("rain", {}).get("chance", 0)
            amount_min = entry.get("rain", {}).get("amount", {}).get("min", 0) or 0
            amount_max = entry.get("rain", {}).get("amount", {}).get("max", 0) or 0
            hours.append({
                "label": self._format_hour(entry.get("time", "")),
                "chance": chance,
                "amount": f"{amount_min}–{amount_max}" if amount_max else "0",
                "temp": entry.get("temp", "–"),
            })
        while len(hours) < 6:
            hours.append({"label": "–", "chance": 0, "amount": "0", "temp": "–"})
        sunrise, sunset = self._get_sun_times()
        tariff_name, tariff_rate = self._get_tariff()
        front_balcony = enviro_monitor['Front Outdoor'].latest if mgr.enviro_monitors_present else {}
        rear_balcony  = enviro_monitor['Outdoor'].latest       if mgr.enviro_monitors_present else {}
        kitchen       = enviro_monitor['Indoor'].latest        if mgr.enviro_monitors_present else {}
        elec_kw = shelly.total_power / 1000 if mgr.shelly_power_monitor_present else None
        elec_cost_ph = elec_kw * tariff_rate if elec_kw is not None else None
        payload = {
            "station": obs.get("station", {}).get("name", "Sydney"),
            "current_temp": obs.get("temp", "–"),
            "feels_like": obs.get("temp_feels_like", "–"),
            "description": self._describe(forecast[0].get("icon_descriptor", "")) if forecast else "",
            "wind": f"{obs.get('wind', {}).get('speed_kilometre', '–')} km/h {obs.get('wind', {}).get('direction', '–')}",
            "humidity": obs.get("humidity", "–"),
            "rain_since_9am": obs.get("rain_since_9am", 0),
            "updated": datetime.now().strftime("%-I:%M %p, %-d %b"),
            "sunrise": sunrise,
            "sunset": sunset,
            "tariff_name": tariff_name,
            "tariff_rate": f"{tariff_rate * 100:.1f}c/kWh",
            "front_balcony_temp": self._extract(front_balcony, "Temp"),
            "front_balcony_humidity": self._round0(self._extract(front_balcony, "Hum")),
            "front_balcony_dewpoint": self._extract(front_balcony, "Dew"),
            "front_balcony_barometer": self._round0(self._extract(front_balcony, "Bar")),
            "front_balcony_pm25": self._extract(front_balcony, "P2.5"),
            "rear_balcony_temp": self._extract(rear_balcony, "Temp"),
            "rear_balcony_humidity": self._round0(self._extract(rear_balcony, "Hum")),
            "rear_balcony_dewpoint": self._extract(rear_balcony, "Dew"),
            "rear_balcony_wind": self._local_wind(),
            "rear_balcony_pm25": self._extract(rear_balcony, "P2.5"),
            "kitchen_temp": self._extract(kitchen, "Temp"),
            "kitchen_humidity": self._round0(self._extract(kitchen, "Hum")),
            "kitchen_dewpoint": self._extract(kitchen, "Dew"),
            "kitchen_pm25": self._extract(kitchen, "P2.5"),
            "electricity_kw": f"{elec_kw:.2f}" if elec_kw is not None else "–",
            "electricity_cost_ph": f"${elec_cost_ph:.2f}/hr" if elec_cost_ph is not None else "–",
        }
        for i, h in enumerate(hours):
            payload[f"h{i}_label"] = h["label"]
            payload[f"h{i}_chance"] = h["chance"]
            payload[f"h{i}_amount"] = h["amount"]
            payload[f"h{i}_temp"] = h["temp"]
        cal_events = self._get_calendar_events()
        while len(cal_events) < 5:
            cal_events.append({'time': '', 'title': ''})
        for idx, ev in enumerate(cal_events):
            payload[f'cal_{idx}_time']  = ev['time']
            payload[f'cal_{idx}_title'] = ev['title']
        return payload

    def push(self):
        obs = self._fetch_bom("observations")
        forecast = self._fetch_bom("forecasts/hourly")
        variables = self._build_payload(obs, forecast)
        variables = {k: v.replace('\u2013', ' -').replace('\u2014', ' -') if isinstance(v, str) else v
                     for k, v in variables.items()}
        url = f"https://trmnl.com/api/custom_plugins/{self.plugin_uuid}"
        try:
            response = requests.post(
                url,
                data=json.dumps({"merge_variables": variables}, ensure_ascii=True).encode('utf-8'),
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
                timeout=30
            )
            print(f"TRMNL: Pushed (HTTP {response.status_code})")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("TRMNL: Push error:", e)
                    
class WindowBlindClass(object):
    # Reinstated from Home Manager 14.2. The per-blind Somfy choreography has been collapsed to whole-group
    # positions ('Open'/'Venetian'/'Closed') that are realised through PowerView Gen 2 scenes, while the
    # original sunlight-level, seasonal, outdoor-temperature and door-override behaviour is retained.
    def __init__(self, blind_room, window_blind_config):
        self.blind = blind_room
        #print('Instantiated Window Blind', self, blind_room)
        self.window_blind_config = window_blind_config
        self.current_high_sunlight = 0 # Set initial sunlight level to 0
        self.previous_high_sunlight = 0
        self.previous_blind_temp_threshold = False
        self.auto_override = False
        self.auto_override_changed = False
        self.previous_door_open = True
        self.non_sunny_season_sunlight_level_3_4_persist_time = window_blind_config['non_sunny_season_sunlight_level_3_4_persist_time']
        self.sunny_season_sunlight_level_3_4_persist_time = window_blind_config['sunny_season_sunlight_level_3_4_persist_time']
        self.sunlight_level_3_4_persist_time = self.non_sunny_season_sunlight_level_3_4_persist_time
        self.last_sunlight_level_3_4_recording_time = time.time()
        self.sunlight_level_3_4_persist_time_previously_exceeded = False
        self.powerview_scenes = {} # PowerView scene name -> id, lazy-loaded from the hub
        self._load_powerview_scenes()
        self.hk_position, self.hk_tilt = self._status_to_pos_tilt(window_blind_config['status']) # HomeKit position/tilt, tracked to combine partial commands

    def _load_powerview_scenes(self): # Fetch and cache the hub's scene name -> id map (Gen 2 encodes scene names in base64)
        try:
            response = requests.get('http://' + mgr.powerview_hub_ip + '/api/scenes', timeout=5)
            data = response.json()
            scenes = {}
            for scene in data.get('sceneData', []):
                try:
                    name = base64.b64decode(scene['name']).decode('utf-8')
                except Exception:
                    name = scene.get('name', '')
                scenes[name] = scene['id']
            self.powerview_scenes = scenes
            print('PowerView scenes loaded for', self.blind, ':', list(scenes.keys()))
        except Exception as e:
            print('PowerView scene load error for', self.blind, ':', e)

    def activate_scene(self, scene_name): # Resolve the scene name to an id and activate it on the hub
        self._load_powerview_scenes() # Refresh first so re-saved/recreated scenes always use their current id
        scene_id = self.powerview_scenes.get(scene_name)
        if scene_id is None:
            print('PowerView scene not found on hub:', scene_name)
            return
        try:
            requests.get('http://' + mgr.powerview_hub_ip + '/api/scenes', params={'sceneId': scene_id}, timeout=5)
            mgr.print_update("Activated PowerView scene '" + scene_name + "' (id " + str(scene_id) + ") for " + self.blind + " on ")
        except Exception as e:
            print('PowerView scene activation error:', scene_name, e)

    def set_blind(self, position, door_open): # Realise a whole-group position through a PowerView scene, applying the door override
        scenes = self.window_blind_config['scenes']
        if position == 'Open':
            scene_name = scenes['Open']
        elif position == 'Venetian':
            scene_name = scenes['Windows Venetian'] if door_open else scenes['Venetian'] # Lower only the windows if a door is open
        elif position == 'Closed':
            scene_name = scenes['Windows Closed'] if door_open else scenes['Closed'] # Close only the windows if a door is open
        else:
            return
        self.activate_scene(scene_name)
        self.window_blind_config['status'] = position
        self.hk_position, self.hk_tilt = self._status_to_pos_tilt(position) # Keep the tracked HomeKit position/tilt in step with the new state

    def any_door_open(self):
        for door in self.window_blind_config['blind_doors']:
            if self.window_blind_config['blind_doors'][door]['door_state'] == 'Open':
                return True
        return False

    def check_season(self, sunny_season_start, sunny_season_finish): # Determines whether or not the sunny season blind settings are invoked
        month = datetime.now().month
        if month >= sunny_season_start or month <= sunny_season_finish:
            return True
        return False

    def check_outdoor_temperature(self, current_temperature, previous_blind_temp_threshold, hysteresis_gap):
        homebridge.update_blind_current_temps(self.blind, current_temperature)
        if previous_blind_temp_threshold == False:
            if (current_temperature > self.window_blind_config['high_temp_threshold']
                or current_temperature < self.window_blind_config['low_temp_threshold']):
                temp_passed_threshold = True
                current_blind_temp_threshold = True
            else: # Temp is still inside the blind temp thresholds
                temp_passed_threshold = False
                current_blind_temp_threshold = False
        else: # If the temp was previously outside the blind temp threshold
            if (current_temperature <= (self.window_blind_config['high_temp_threshold'] - hysteresis_gap)
                and current_temperature >= (self.window_blind_config['low_temp_threshold'] + hysteresis_gap)):
                temp_passed_threshold = True
                current_blind_temp_threshold = False
            else: # Set that it hasn't jumped the thresholds
                temp_passed_threshold = False
                current_blind_temp_threshold = True
        return(temp_passed_threshold, current_blind_temp_threshold)

    def check_door_state(self, previous_door_open):
        all_doors_closed = True
        one_door_has_opened = False
        a_door_state_has_changed = False
        for door in self.window_blind_config['blind_doors']:
            if self.window_blind_config['blind_doors'][door]['door_state'] == 'Open':
                all_doors_closed = False
                if self.window_blind_config['blind_doors'][door]['door_state_changed']:
                    one_door_has_opened = True
            if self.window_blind_config['blind_doors'][door]['door_state_changed']:
                a_door_state_has_changed = True
        if one_door_has_opened == True and previous_door_open == False: # A door has been opened when all doors were previously closed
            door_state_changed = True
            door_open = True
        elif all_doors_closed == True and a_door_state_has_changed: # All doors are now closed
            door_state_changed = True
            door_open = False
        else:
            door_state_changed = False
            door_open = not all_doors_closed
        return(door_open, door_state_changed)

    def change_auto_override(self, auto_override):
        self.auto_override = auto_override
        if auto_override:
            mgr.log_key_states("Sunlight Blind Auto Override Enabled")
        self.auto_override_changed = True

    def set_high_temp(self, high_temp):
        self.window_blind_config['high_temp_threshold'] = high_temp
        mgr.log_key_states('Blind High Temp Threshold Changed')

    def set_low_temp(self, low_temp):
        self.window_blind_config['low_temp_threshold'] = low_temp
        mgr.log_key_states('Blind Low Temp Threshold Changed')

    def _status_to_pos_tilt(self, status): # Map a whole-group state to the (position, tilt) shown on the HomeKit tile
        if status == 'Open':
            return 100, 90
        if status == 'Venetian':
            return 0, 90
        return 0, 0 # Closed

    def _pos_tilt_to_status(self, position, tilt): # Combine a HomeKit position + tilt back into a whole-group state
        if position >= 50:
            return 'Open'
        if tilt >= 45:
            return 'Venetian'
        return 'Closed'

    def change_blind_from_homekit(self, position=None, tilt=None):
        # HomeKit sends the position and tilt axes as separate messages; update whichever arrived, keep the other,
        # and combine them into a whole-group state
        if position is not None:
            self.hk_position = position
        if tilt is not None:
            self.hk_tilt = tilt
            self.hk_position = 0 # Choosing a slat angle implies the blind is lowered
        self.change_blind_position(self._pos_tilt_to_status(self.hk_position, self.hk_tilt))

    def change_blind_position(self, blind_position):
        # Sets the flag that triggers a manual blind change in the main Home Manager loop
        mgr.call_control_blinds = {'State': True, 'Blind': self.blind, 'Blind_position': blind_position}

    def control_blinds(self, blind_position): # Manual whole-group blind control from HomeKit
        mgr.print_update('Invoked Manual Blind Control on ')
        if blind_position in ('Open', 'Venetian', 'Closed'):
            self.set_blind(blind_position, self.any_door_open())
            homebridge.update_blind_status(self.blind, self.window_blind_config)
            mgr.log_key_states("Manual Blind State Change")
        else: # Ignore any other setting and resync HomeKit to the current position
            homebridge.update_blind_status(self.blind, self.window_blind_config)

    def target_position(self, level, sunny_season, current_blind_temp_threshold, persist_exceeded):
        # Map a sunlight level to a whole-group blind position, taking season and outdoor temperature into account
        if level == 4: # Strong direct sun: black out in the sunny season, otherwise shade to keep heat out/in
            return 'Closed' if sunny_season else 'Venetian'
        if level == 3: # Medium direct sun: shade in the sunny season, otherwise leave open
            return 'Venetian' if sunny_season else 'Open'
        if level == 2: # Strong indirect sun
            if self.previous_high_sunlight < 2: # Rising from low light: shade only if the outdoor temp is outside the thresholds
                return 'Venetian' if current_blind_temp_threshold else 'Open'
            if persist_exceeded: # Falling from levels 3/4 and the sun has been gone long enough
                return 'Venetian' if sunny_season else 'Open'
            return self.window_blind_config['status'] # Otherwise hold the current position
        if level == 1: # Low indirect sun: shade only if the outdoor temp is outside the thresholds
            return 'Venetian' if current_blind_temp_threshold else 'Open'
        return self.window_blind_config['status'] # Level 0 (night): hold the current position so HomeKit Good Night/Good Morning scenes are not overridden

    def room_sunlight_control(self, light_level):
        # Called when there's a change in the blind's light sensor, doors or auto-override button
        current_temperature = multisensor[self.window_blind_config['temp sensor']].sensor_types_with_value['Temperature']
        sunny_season = self.check_season(self.window_blind_config['sunny_season_start'], self.window_blind_config['sunny_season_finish'])
        if sunny_season:
            self.sunlight_level_3_4_persist_time = self.sunny_season_sunlight_level_3_4_persist_time
        else:
            self.sunlight_level_3_4_persist_time = self.non_sunny_season_sunlight_level_3_4_persist_time
        if current_temperature == 1: # Wait for a valid temperature reading (1 is the start-up placeholder)
            return
        temp_passed_threshold, current_blind_temp_threshold = self.check_outdoor_temperature(current_temperature, self.previous_blind_temp_threshold, 1)
        self.previous_blind_temp_threshold = current_blind_temp_threshold
        door_open, door_state_changed = self.check_door_state(self.previous_door_open)
        self.previous_door_open = door_open
        cfg = self.window_blind_config
        if light_level >= cfg['sunlight threshold 3']: # Strong direct sunlight
            new_high_sunlight = 4
            self.last_sunlight_level_3_4_recording_time = time.time()
            self.sunlight_level_3_4_persist_time_previously_exceeded = False
        elif light_level >= cfg['sunlight threshold 2']: # Medium direct sunlight
            new_high_sunlight = 3
            self.last_sunlight_level_3_4_recording_time = time.time()
            self.sunlight_level_3_4_persist_time_previously_exceeded = False
        elif light_level >= cfg['sunlight threshold 1']: # Strong indirect sunlight
            new_high_sunlight = 2
        elif light_level > cfg['sunlight threshold 0']: # Low indirect sunlight
            new_high_sunlight = 1
        else: # Night time
            new_high_sunlight = 0
        sunlight_level_change = (new_high_sunlight != self.current_high_sunlight)
        if sunlight_level_change:
            self.previous_high_sunlight = self.current_high_sunlight
        auto_override_newly_disabled = (self.auto_override_changed == True and self.auto_override == False)
        persist_now_exceeded = ((time.time() - self.last_sunlight_level_3_4_recording_time) >= self.sunlight_level_3_4_persist_time)
        trigger_falling_sunlight_level_2 = (new_high_sunlight == 2 and self.previous_high_sunlight > 2 and
                                            self.sunlight_level_3_4_persist_time_previously_exceeded == False and persist_now_exceeded)
        if not (sunlight_level_change or door_state_changed or temp_passed_threshold or auto_override_newly_disabled or trigger_falling_sunlight_level_2):
            return # Nothing that affects blind state has changed
        mgr.print_update('Blind change algorithm triggered on ')
        print('Sunlight Level Change:', sunlight_level_change, 'Door State Changed:', door_state_changed, 'Temp Passed Threshold:', temp_passed_threshold,
              'Auto Override Newly Disabled:', auto_override_newly_disabled, 'Trigger Falling Sunlight Level 2:', trigger_falling_sunlight_level_2)
        if door_state_changed: # Reset all door state changed flags now that they have been actioned
            for door in cfg['blind_doors']:
                cfg['blind_doors'][door]['door_state_changed'] = False
        if trigger_falling_sunlight_level_2:
            self.sunlight_level_3_4_persist_time_previously_exceeded = True
        self.auto_override_changed = False
        self.current_high_sunlight = new_high_sunlight
        if self.auto_override: # Auto blind control is overridden - leave the blinds where they are, but resync the tile (main loop, no thread race)
            #print('No Blind Change. Auto Blind Control is overridden')
            homebridge.update_blind_status(self.blind, cfg)
            return
        new_position = self.target_position(new_high_sunlight, sunny_season, current_blind_temp_threshold, persist_now_exceeded)
        self.set_blind(new_position, door_open)
        homebridge.update_blind_status(self.blind, cfg)
        mgr.log_key_states("Sunlight Blind State Change")

if __name__ == '__main__': # This is where to overall code kicks off
    # Create a Home Manager instance
    mgr = NorthcliffHomeManagerClass(key_state_log_file_name='<Your Key State Log File Path and Name>', watchdog_file_name='<Your Watchdog File Path and Name>', luftdaten_sensor_id='<Your Luftdaten Sensor ID>')
    # Create a Homebridge instance
    homebridge = HomebridgeClass(mgr.outdoor_multisensor_names, mgr.outdoor_sensors_homebridge_name, mgr.door_sensor_names_locations, mgr.enviro_config,
                                 mgr.window_blind_threshold_1, mgr.window_blind_threshold_2, mgr.previous_window_blind_state)
    # Create a Domoticz instance
    domoticz = DomoticzClass()
    if mgr.multisensors_present:
        # Use a dictionary comprehension to create a multisensor instance for each multisensor
        multisensor = {name: MultisensorClass(name) for name in mgr.multisensor_names}
    if mgr.window_blinds_present:
        # Create a Window Blind instance for each configured blind (PowerView Gen 2 scene control)
        window_blind = {blind: WindowBlindClass(blind, mgr.window_blind_config[blind]) for blind in mgr.window_blind_config}
    if mgr.door_sensors_present:
        # Use a dictionary comprehension to create a door sensor instance for each door
        door_sensor = {name: DoorSensorClass(name, mgr.door_sensor_names_locations[name]) for name in mgr.door_sensor_names_locations}
    if mgr.flood_sensors_present:
        # Use a dictionary comprehension to create a flood sensor instance for each flood sensor
        flood_sensor = {name: FloodSensorClass(name) for name in mgr.flood_sensor_names}
    if mgr.garage_door_present:
        # Create a Garage Door Controller instance
        garage_door = GaragedoorClass()
    if mgr.aquarium_monitor_present:
        # Create a Aquarium Temp Sensor instance
        aquarium = AquariumClass()
    if mgr.enviro_monitors_present:
        # Create Enviro Monitor instance for each Enviro Name
        enviro_monitor = {name: EnviroClass(name, mgr.enviro_config[name]) for name in mgr.enviro_config}
    if mgr.shelly_power_monitor_present:
        # Create Shelly Power Monitor instance
        shelly = ShellyReadingClass()
    if mgr.trmnl_present:
        # Create TRMNL Weather Display instance
        trmnl = TrmnlClass(plugin_uuid="<Your TRMNL Plugin UUID>", api_key="<Your TRMNL API Key>", geohash="<Your BOM Geohash>", caldav_url='https://caldav.icloud.com/', caldav_user='<Your CalDAV User>',
                           caldav_pass='<Your CalDAV App-Specific Password>', caldav_calendar='<Your CalDAV Calendar Name>', caldav_timezone='<Your Timezone e.g. Australia/Sydney>',
                           peak_hours = {1: (14, 20), 2: (14, 20), 3: (14, 20), 4: None, 5: None, 6: (17, 21), 7: (17, 21), 8: (17, 21), 9: None,
                                         10: (14, 17), 11: (14, 20), 12: (17, 20)},
                           tariff_rates = {"Off Peak": 0.16588, "Shoulder": 0.28435, "Peak": 0.538516},
                           location = LocationInfo("<Your City>", "<Your Country>", "<Your Timezone e.g. Australia/Sydney>", "<Your Latitude>", "<Your Longitude>"))
    # Create and set up an mqtt instance                             
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, 'home_manager')
    client.on_connect = mgr.on_connect
    client.on_message = mgr.on_message
    client.connect("<Your mqtt Broker IP Address or Name>", 1883, 60)
    # Blocking call that processes network traffic, dispatches callbacks and handles reconnecting.
    client.loop_start()
    mgr.run()
