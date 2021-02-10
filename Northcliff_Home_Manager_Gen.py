#!/usr/bin/env python
#Northcliff Home Manager - 9.6 - Gen Add EV Charger Monitoring
# Requires minimum Doorbell V2.5, HM Display 3.8, Aircon V3.47, homebridge-mqtt v0.6.2
import paho.mqtt.client as mqtt
import struct
import time
from datetime import datetime
import string
import json
import socket
import requests
import os
import asyncio
import aiohttp
from luftdaten import Luftdaten

class NorthcliffHomeManagerClass(object):
    def __init__(self, log_aircon_cost_data, log_aircon_damper_data, log_aircon_temp_data, load_previous_aircon_effectiveness, perform_homebridge_config_check):
        #print ('Instantiated Home Manager')
        self.log_aircon_cost_data = log_aircon_cost_data # Flags if the aircon cost data is to be logged
        self.log_aircon_damper_data = log_aircon_damper_data # Flags if the aircon damper data is to be logged
        self.log_aircon_temp_data = log_aircon_temp_data # Flags if the aircon temperature data is to be logged
        self.load_previous_aircon_effectiveness = load_previous_aircon_effectiveness # Flags if the aircon data is to be loaded on startup
        self.perform_homebridge_config_check = perform_homebridge_config_check # Flags that a homebridge config check is to be performed on start-up
        self.home_manager_file_name = '<Your Home Manager File Path and Name>'
        self.key_state_log_file_name = '<Your Key State Log File Path and Name>'
        self.watchdog_file_name = '<Your Watchdog File Path and Name>'
        self.light_dimmers_present = True # Enables Light Dimmer control
        self.multisensors_present = True # Enable Multisensor monitoring
        self.doorbell_present = True # Enables doorbell control
        self.door_sensors_present = True # Enables door sensor monitoring
        self.powerpoints_present = True # Enables powerpoint control
        self.flood_sensors_present = True # Enables flood sensor monitoring
        self.window_blinds_present = True # Enables window blind control
        self.aircons_present = True # Enables aircon control
        self.air_purifiers_present = True # Enables air purifier control
        self.garage_door_present = True # Enables garage door control
        self.aquarium_monitor_present = True # Enables aquarium monitoring
        self.enviro_monitors_present = True  # Enables outdoor air quality monitoring
        self.enable_reboot = True # Enables remote reboot function
        self.ev_charger_present = True # Enables EV Charger function
        # List the multisensor names
        self.multisensor_names = ['Living', 'Study', 'Kitchen', 'North', 'South', 'Main', 'Rear Balcony', 'North Balcony', 'South Balcony']
        # List the outdoor sensors
        self.outdoor_multisensor_names = ['Rear Balcony', 'North Balcony', 'South Balcony']
        # Group outdoor sensors as services under one homebridge accessory name for passing to the homebridge object
        self.outdoor_sensors_homebridge_name = 'Balconies'
        # Name each door sensor and identify the room that contains that door sensor
        self.door_sensor_names_locations = {'North Living Room': 'Living Room', 'South Living Room': 'Living Room', 'Entry': 'Entry'}
        # Name each powerpoint and map to its device id
        self.powerpoint_names_device_id = {'Living': 646, 'South Balcony': 626, 'North Balcony': 647}
        # List the flood sensors
        self.flood_sensor_names = ['Kitchen', 'Aquarium']
        # Name each light dimmer and map to its device id
        self.light_dimmer_names_device_id = {'Lounge Light': 323, 'TV Light': 325, 'Dining Light': 324, 'Study Light': 648, 'Kitchen Light': 504, 'Hallway Light': 328, 'North Light': 463,
                                              'South Light': 475, 'Main Light': 451, 'North Balcony Light': 517, 'South Balcony Light': 518}
        self.colour_light_dimmer_names = [] # Dimmers in self.light_dimmer_names_device_id that require hue and saturation characteristics
        # Set up the config for each aircon, including their mqtt topics
        self.aircon_config = {'Aircon': {'mqtt Topics': {'Outgoing':'AirconControl', 'Incoming': 'AirconStatus'}, 'Day Zone': ['Living', 'Study', 'Kitchen'],
                                         'Night Zone': ['North', 'South', 'Main'], 'Master': 'Master', 'Outdoor Temp Sensor': 'North Balcony', 'Cost Log': '<Your Cost Log File Path and Name>',
                                         'Effectiveness Log': '<Your Effectiveness Log File Path and Name>', 'Spot Temperature History Log': '<Your Spot Temperature History Log File Path and Name>',
                                         'Damper Log': '<Your Damper Log File Path and Name>'}}
        # List the temperature sensors that control the aircons
        self.aircon_temp_sensor_names = []
        for aircon in self.aircon_config:
            self.aircon_temp_sensor_names = self.aircon_temp_sensor_names + self.aircon_config[aircon]['Day Zone'] + self.aircon_config[aircon]['Night Zone']
        # Map each sensor to its relevant aircon
        self.aircon_sensor_name_aircon_map = {}
        for sensor in self.aircon_temp_sensor_names:
            for aircon in self.aircon_config:
                if sensor in self.aircon_config[aircon]['Day Zone'] or sensor in self.aircon_config[aircon]['Night Zone'] or sensor in self.aircon_config[aircon]['Master']:
                    self.aircon_sensor_name_aircon_map[sensor] = aircon
        #print('Aircon sensor name aircon map', self.aircon_sensor_name_aircon_map)
        # Set up other mqtt topics
        self.homebridge_incoming_mqtt_topic = 'homebridge/from/set'
        self.homebridge_incoming_config_mqtt_topic = 'homebridge/from/response'
        self.domoticz_incoming_mqtt_topic = 'domoticz/out'
        self.doorbell_incoming_mqtt_topic = 'DoorbellStatus'
        self.garage_door_incoming_mqtt_topic = 'GarageStatus'
        self.enviro_monitor_incoming_mqtt_topics = ['Outdoor EM0', 'Indoor EM1']
        self.ev_charger_incoming_mqtt_topic = 'ttn/<Your TTN Application ID>/up/state'
        # Set up the config for each window blind
        self.window_blind_config = {'Living Room Blinds': {'blind host name': '<mylink host name>', 'blind port': 44100, 'light sensor': 'South Balcony',
                                                            'temp sensor': 'North Balcony', 'sunlight threshold 0': 100,'sunlight threshold 1': 1000,
                                                            'sunlight threshold 2': 12000, 'sunlight threshold 3': 20000, 'high_temp_threshold': 28,
                                                            'low_temp_threshold': 15, 'sunny_season_start': 10, 'sunny_season_finish': 3,
                                                            'non_sunny_season_sunlight_level_3_4_persist_time': 1800, 'sunny_season_sunlight_level_3_4_persist_time': 600, 
                                                            'blind_doors': {'North Living Room': {'door_state': 'Open','door_state_changed': False},
                                                                             'South Living Room': {'door_state': 'Open', 'door_state_changed': False}},
                                                            'status':{'Left Window': 'Open', 'Left Door': 'Open', 'Right Door': 'Open',
                                                                       'Right Window': 'Open', 'All Blinds': 'Open', 'All Doors': 'Open', 'All Windows': 'Open'},
                                                            'blind commands': {'up Left Window': b'{"method": "mylink.move.up","params":{"targetID":"<mylink targetID>.1","auth":"<mylink auth>"},"id":1}',
                                                                         'up Left Door': b'{"method": "mylink.move.up","params":{"targetID":"<mylink targetID>.2","auth":"<mylink auth>"},"id":1}',
                                                                         'up Right Door': b'{"method": "mylink.move.up","params":{"targetID":"<mylink targetID>.3","auth":"<mylink auth>"},"id":1}',
                                                                         'up Right Window': b'{"method": "mylink.move.up","params":{"targetID":"<mylink targetID>.4","auth":"<mylink auth>"},"id":1}',
                                                                         'up All Blinds': b'{"method": "mylink.move.up","params":{"targetID":"<mylink targetID>.5","auth":"<mylink auth>"},"id":1}',
                                                                         'up All Doors': b'{"method": "mylink.move.up","params":{"targetID":"<mylink targetID>.6","auth":"<mylink auth>"},"id":1}',
                                                                         'up All Windows': b'{"method": "mylink.move.up","params":{"targetID":"<mylink targetID>.7","auth":"<mylink auth>"},"id":1}',
                                                                         'down Left Window': b'{"method": "mylink.move.down","params":{"targetID":"<mylink targetID>.1","auth":"<mylink auth>"},"id":1}',
                                                                         'down Left Door': b'{"method": "mylink.move.down","params":{"targetID":"<mylink targetID>.2","auth":"<mylink auth>"},"id":1}',
                                                                         'down Right Door': b'{"method": "mylink.move.down","params":{"targetID":"<mylink targetID>.3","auth":"<mylink auth>"},"id":1}',
                                                                         'down Right Window': b'{"method": "mylink.move.down","params":{"targetID":"<mylink targetID>.4","auth":"<mylink auth>"},"id":1}',
                                                                         'down All Blinds': b'{"method": "mylink.move.down","params":{"targetID":"<mylink targetID>.5","auth":"<mylink auth>"},"id":1}',
                                                                         'down All Doors': b'{"method": "mylink.move.down","params":{"targetID":"<mylink targetID>.6","auth":"<mylink auth>"},"id":1}',
                                                                         'down All Windows': b'{"method": "mylink.move.down","params":{"targetID":"<mylink targetID>.7","auth":"<mylink auth>"},"id":1}',
                                                                         'stop Left Window': b'{"method": "mylink.move.stop","params":{"targetID":"<mylink targetID>.1","auth":"<mylink auth>"},"id":1}',
                                                                         'stop Left Door': b'{"method": "mylink.move.stop","params":{"targetID":"<mylink targetID>.2","auth":"<mylink auth>"},"id":1}',
                                                                         'stop Right Door': b'{"method": "mylink.move.stop","params":{"targetID":"<mylink targetID>.3","auth":"<mylink auth>"},"id":1}',
                                                                         'stop Right Window': b'{"method": "mylink.move.stop","params":{"targetID":"<mylink targetID>.4","auth":"<mylink auth>"},"id":1}',
                                                                         'stop All Blinds': b'{"method": "mylink.move.stop","params":{"targetID":"<mylink targetID>.5","auth":"<mylink auth>"},"id":1}',
                                                                         'stop All Doors': b'{"method": "mylink.move.stop","params":{"targetID":"<mylink targetID>.6","auth":"<mylink auth>"},"id":1}',
                                                                         'stop All Windows': b'{"method": "mylink.move.stop","params":{"targetID":"<mylink targetID>.7","auth":"<mylink auth>"},"id":1}'}}}
        # List the light sensors that control blinds
        self.blind_light_sensor_names = [self.window_blind_config[blind]['light sensor'] for blind in self.window_blind_config]
        # When True, flags that a blind change has been manually invoked, referencing the relevant blind, blind_id and position
        self.call_control_blinds = {'State': False, 'Blind': '', 'Blind_id': '', 'Blind_position': ''}
        self.auto_blind_override_changed = {'Changed': False, 'Blind': '', 'State': False}
        # When True, flags that a change in sunlight had occurred, referencing the relevant blind and light level
        self.call_room_sunlight_control = {'State': False, 'Blind': '', 'Light Level': 100}
        # When True, flags that a blind-impacting door has been opened, referencing the relevant blind
        self.blind_control_door_changed = {'State': False, 'Blind': '', 'Changed': False}
        # Identify the door that controls the doorbell "Auto Possible" mode
        self.doorbell_door = 'Entry'
        # Set up air purifier dictionary with names, foobot device numbers and auto/manual flag.
        self.air_purifier_names = {'Living': {'Foobot Device': 1, 'Auto': True}, 'Main': {'Foobot Device': 0, 'Auto': False}}
        self.auto_air_purifier_names = []
        for name in self.air_purifier_names:
            if self.air_purifier_names[name]['Auto']:
                self.auto_air_purifier_names.append(name)
        self.universal_air_purifier_fan_speed = 1
        self.air_purifier_linking_times = {'Start': 9, 'Stop': 20}
        enviro_capture_time = time.time()
        self.enviro_config = {'Outdoor': {'mqtt Topic': 'Outdoor EM0', 'Capture Temp/Hum/Bar/Lux': True, 'Capture Time': enviro_capture_time, 'Luftdaten Sensor ID': 99999,
                                          'Device IDs': {'P1': 784, 'P2.5': 778, 'P10': 779, 'AQI': 780, 'NH3': 781, 'Oxi': 782, 'Red': 783,
                                                          'Temp': 819, 'Hum': 819, 'Bar': 819, 'Lux':821}},
                              'Indoor': {'mqtt Topic': 'Indoor EM1', 'Capture Temp/Hum/Bar/Lux': True,
                                          'Device IDs': {'P1': 789, 'P2.5': 790, 'P10': 791, 'AQI': 792, 'NH3': 795, 'Oxi': 793, 'Red': 794,
                                                          'Temp': 824, 'Hum': 824, 'Bar': 824, 'Lux':820, 'CO2': 825, 'VOC': 826}}}
        self.enable_outdoor_enviro_monitor_luftdaten_backup = True # Enable Luftdaten readings if no PM readings from outdoor Enviro Monitor
        self.watchdog_update_time = 0
                               
    def on_connect(self, client, userdata, flags, rc):
        # Sets up the mqtt subscriptions. Subscribing in on_connect() means that if we lose the connection and reconnect then subscriptions will be renewed.
        self.print_update('Northcliff Home Manager Connected with result code '+str(rc)+' on ')
        print('')
        time.sleep(1)
        client.subscribe(self.homebridge_incoming_mqtt_topic) #Subscribe to Homebridge status for interworking with Apple Home
        client.subscribe(self.homebridge_incoming_config_mqtt_topic) #Subscribe to Homebridge config for interworking with Apple Home
        client.subscribe(self.domoticz_incoming_mqtt_topic) # Subscribe to Domoticz for access to its devices
        client.subscribe(self.doorbell_incoming_mqtt_topic) # Subscribe to the Doorbell Monitor
        client.subscribe(self.garage_door_incoming_mqtt_topic) # Subscribe to the Garage Door Controller
        client.subscribe(self.ev_charger_incoming_mqtt_topic) # Subscribe to the EV Charger Controller
        for enviro_name in self.enviro_config:
            client.subscribe(self.enviro_config[enviro_name]['mqtt Topic']) # Subscribe to the Enviro Monitors
        for aircon_name in self.aircon_config: # Subscribe to the Aircon Controllers
            client.subscribe(self.aircon_config[aircon_name]['mqtt Topics']['Incoming'])
    
    def on_message(self, client, userdata, msg):
        # Calls the relevant methods for the Home Manager, based on the mqtt publish messages received from the doorbell monitor, the homebridge buttons,
        # Domoticz, the aircon controller and the garage door controller
        decoded_payload = str(msg.payload.decode("utf-8"))
        parsed_json = json.loads(decoded_payload)
        #print(msg.topic, parsed_json)
        if msg.topic == self.homebridge_incoming_mqtt_topic: # If it's a homebridge status message
            homebridge.capture_homebridge_buttons(parsed_json) # Capture the homebridge button
        elif msg.topic == self.homebridge_incoming_config_mqtt_topic: # If it's a homebridge config message
            homebridge.config_response(parsed_json) # Handle homebridge config responses
        elif msg.topic == self.domoticz_incoming_mqtt_topic: # If coming from domoticz
            domoticz.process_device_data(parsed_json) # Process the domoticz device data
        elif msg.topic == self.garage_door_incoming_mqtt_topic: # If coming from the Garage Door Controller
            garage_door.capture_status(parsed_json) # Capture garage door status
        elif msg.topic == self.doorbell_incoming_mqtt_topic: # If coming from the Doorbell Monitor
            doorbell.capture_doorbell_status(parsed_json) # Capture doorbell status
        elif msg.topic == self.ev_charger_incoming_mqtt_topic:
            print('EV Charger Message', parsed_json)
            ev_charger.capture_ev_charger_state(parsed_json)
        else: # Test for enviro or aircon messages
            identified_message = False
            for enviro_name in self.enviro_config:
                if msg.topic == self.enviro_config[enviro_name]['mqtt Topic']: # If coming from an Enviro Monitor
                    #self.print_update(enviro_name +  ' Northcliff Enviro Monitor Data:' + str(parsed_json) + ' on ')
                    if enviro_name == 'Outdoor':
                        self.enviro_config[enviro_name]['Capture Time'] = time.time()
                    identified_message = True
                    enviro_monitor[enviro_name].capture_readings('Enviro', parsed_json) # Capture enviro readings
            for aircon_name in self.aircon_config:
                if msg.topic == self.aircon_config[aircon_name]['mqtt Topics']['Incoming']: # If coming from an aircon
                    identified_message = True
                    aircon[aircon_name].capture_status(parsed_json) # Capture aircon status
            if identified_message == False: # If the mqtt topic is unknown
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
        if self.powerpoints_present:
            key_state_log['Powerpoint State'] = {name: powerpoint[name].powerpoint_state for name in self.powerpoint_names_device_id}
        if self.window_blinds_present:
            key_state_log['Blind Status'] = {blind: window_blind[blind].window_blind_config['status'] for blind in self.window_blind_config}
            key_state_log['Blind Door State'] = {blind: window_blind[blind].window_blind_config['blind_doors'] for blind in self.window_blind_config}
            key_state_log['Blind High Temp'] = {blind: window_blind[blind].window_blind_config['high_temp_threshold'] for blind in self.window_blind_config}
            key_state_log['Blind Low Temp'] = {blind: window_blind[blind].window_blind_config['low_temp_threshold'] for blind in self.window_blind_config}
            key_state_log['Blind Auto Override'] = {blind: window_blind[blind].auto_override for blind in self.window_blind_config}
        if self.aircons_present:
            key_state_log['Aircon Thermostat Status'] = {aircon_name: {thermostat: aircon[aircon_name].thermostat_status[thermostat]
                                                         for thermostat in (self.aircon_config[aircon_name]['Day Zone'] +
                                                                            self.aircon_config[aircon_name]['Night Zone'])} for aircon_name in self.aircon_config}
            key_state_log['Aircon Thermo Mode'] = {aircon_name: aircon[aircon_name].settings['indoor_thermo_mode'] for aircon_name in self.aircon_config}
            key_state_log['Aircon Thermo Active'] = {aircon_name: aircon[aircon_name].settings['indoor_zone_sensor_active'] for aircon_name in self.aircon_config}
        if self.air_purifiers_present:
            key_state_log['Air Purifier Max Co2'] = {air_purifier_name: air_purifier[air_purifier_name].max_co2 for air_purifier_name in self.auto_air_purifier_names}
        if self.enviro_monitors_present:
            for enviro_name in self.enviro_config:
                if enviro_name == 'Indoor' and 'CO2' in self.enviro_config[enviro_name]['Device IDs']:
                    key_state_log['Enviro Max CO2'] = enviro_monitor[enviro_name].max_CO2
        if self.ev_charger_present:
            key_state_log['EV Charger State'] = ev_charger.state
            key_state_log['EV Charger Locked State'] = ev_charger.locked_state
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
                if door_sensor[name].doorbell_door:
                    doorbell.update_doorbell_door_state(self.doorbell_door, parsed_key_states['Door State'][name])
        if self.window_blinds_present and 'Blind Status' in parsed_key_states:
            for blind in parsed_key_states['Blind Status']:
                window_blind[blind].window_blind_config['status'] = parsed_key_states['Blind Status'][blind]
                homebridge.update_blind_status(blind, window_blind[blind].window_blind_config)
                window_blind[blind].window_blind_config['blind_doors'] = parsed_key_states['Blind Door State'][blind]
                window_blind[blind].window_blind_config['high_temp_threshold'] = parsed_key_states['Blind High Temp'][blind]
                window_blind[blind].window_blind_config['low_temp_threshold'] = parsed_key_states['Blind Low Temp'][blind]
                homebridge.update_blind_target_temps(blind, parsed_key_states['Blind High Temp'][blind], parsed_key_states['Blind Low Temp'][blind])
                window_blind[blind].auto_override = parsed_key_states['Blind Auto Override'][blind]
                homebridge.set_auto_blind_override_button(blind, parsed_key_states['Blind Auto Override'][blind])
        if self.powerpoints_present and 'Powerpoint State' in parsed_key_states:
            for name in parsed_key_states['Powerpoint State']:
                powerpoint[name].on_off(parsed_key_states['Powerpoint State'][name])
                homebridge.update_powerpoint_state(name, parsed_key_states['Powerpoint State'][name])
        if self.aircons_present and 'Aircon Thermostat Status' in parsed_key_states:
            for aircon_name in self.aircon_config:
                for thermostat in parsed_key_states['Aircon Thermostat Status'][aircon_name]:
                    aircon[aircon_name].thermostat_status[thermostat]['Target Temperature'] = parsed_key_states['Aircon Thermostat Status'][aircon_name][thermostat]['Target Temperature']
                    homebridge.update_thermostat_target_temp(aircon_name, thermostat, parsed_key_states['Aircon Thermostat Status'][aircon_name][thermostat]['Target Temperature'])
                    aircon[aircon_name].thermostat_status[thermostat]['Mode'] = parsed_key_states['Aircon Thermostat Status'][aircon_name][thermostat]['Mode']
                    homebridge.update_aircon_thermostat(aircon_name, thermostat, parsed_key_states['Aircon Thermostat Status'][aircon_name][thermostat]['Mode'])
                    aircon[aircon_name].thermostat_status[thermostat]['Active'] = parsed_key_states['Aircon Thermostat Status'][aircon_name][thermostat]['Active']
                aircon[aircon_name].settings['indoor_thermo_mode'] = parsed_key_states['Aircon Thermo Mode'][aircon_name]
                aircon[aircon_name].settings['indoor_zone_sensor_active'] = parsed_key_states['Aircon Thermo Active'][aircon_name]
                aircon[aircon_name].update_zone_temps()
        if self.air_purifiers_present and 'Air Purifier Max Co2' in parsed_key_states:
            for air_purifier_name in parsed_key_states['Air Purifier Max Co2']:
                air_purifier[air_purifier_name].max_co2 = parsed_key_states['Air Purifier Max Co2'][air_purifier_name]
        if self.enviro_monitors_present and 'Enviro Max CO2' in parsed_key_states:
            for enviro_name in self.enviro_config:
                if enviro_name == 'Indoor' and 'CO2' in self.enviro_config[enviro_name]['Device IDs']:
                    enviro_monitor[enviro_name].max_CO2 = parsed_key_states['Enviro Max CO2']
        if self.ev_charger_present and 'EV Charger State' in parsed_key_states:
            ev_charger.state = parsed_key_states['EV Charger State']
            ev_charger.locked_state = parsed_key_states['EV Charger Locked State']
            homebridge.process_ev_charger_acks('Clear ACKs') # Clear ACK indicators

    def air_purifier_linking_hour(self):
        today = datetime.now()
        hour = int(today.strftime('%H'))
        if hour >= self.air_purifier_linking_times['Start'] and hour < self.air_purifier_linking_times['Stop']:
            return True
        else:
            return False

    def update_manual_air_purifier_fan_speeds(self, control_purifier, fan_speed):
        for name in self.air_purifier_names:
            if not self.air_purifier_names[name]['Auto']:
                print('Setting', name, 'Fan Speed to', fan_speed, 'due to change in', control_purifier, 'auto air purifier fan change')
                air_purifier[name].set_fan_speed(str(fan_speed))
                
    def shutdown(self, reason):
        #self.log_key_states(reason)
        # Shut down Aircons
        for aircon_name in self.aircon_config:
            aircon[aircon_name].shut_down()
        client.loop_stop() # Stop mqtt monitoring
        self.print_update('Home Manager Shut Down due to ' + reason + ' on ')
      
    def run(self): # The main Home Manager start-up, loop and shut-down code                          
        try:
            if self.perform_homebridge_config_check:
                homebridge.check_and_fix_config() 
            # Retrieve logged key states
            self.retrieve_key_states()
            if self.enable_reboot:
                homebridge.reset_reboot_button()
            if self.air_purifiers_present:
                # Capture Air Purifier readings and settings on startup and update homebridge
                for name in self.air_purifier_names:
                    if self.air_purifier_names[name]['Auto']: # Readings only come from auto units
                        self.purifier_readings_update_time, part_2_5, co2, voc, max_aqi, max_co2, co2_threshold, part_2_5_threshold = air_purifier[name].capture_readings()
                        homebridge.update_blueair_aqi(name, part_2_5, co2, voc, max_aqi, max_co2, co2_threshold, part_2_5_threshold)
                        domoticz.update_blueair_aqi(name, part_2_5, co2, voc, max_aqi)
                    settings_changed, self.purifier_settings_update_time, mode, fan_speed, child_lock, led_brightness,filter_status = air_purifier[name].capture_settings()
                    homebridge.set_air_purifier_state(name, mode, fan_speed, child_lock, led_brightness, filter_status)    
            if self.aircons_present:
                # Start up Aircons
                for aircon_name in mgr.aircon_config:
                    aircon[aircon_name].start_up(self.load_previous_aircon_effectiveness)
                if self.doorbell_present:
                    doorbell.update_doorbell_status() # Get doorbell status on startup
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
            # Initialise EV Charger State
            if self.ev_charger_present:
                homebridge.update_ev_charger_state(ev_charger.state, ev_charger.locked_state)
            previous_aquarium_capture_time = 0 # Initialise aquarium sensor capture time
            previous_aquarium_reading_time = 0 # Initialise aquarium sensor reading time
            previous_luftdaten_capture_time = 0 # Initialise luftdaten capture time
            while True: # The main Home Manager Loop
                if time.time() - self.watchdog_update_time >= 60: # Write to the watchdog log every minute
                    with open(self.watchdog_file_name, 'w') as f:
                        f.write('Home Manager Script Alive')
                    self.watchdog_update_time = time.time()
                if self.aircons_present:
                    for aircon_name in mgr.aircon_config:
                        aircon[aircon_name].control_aircon() # For each aircon, call the method that controls the aircon.
                if self.window_blinds_present:
                    # The following tests and method calls are here in the main code loop, rather than the on_message method to avoid time.sleep calls in the window blind object delaying incoming mqtt message handling
                    if self.call_room_sunlight_control['State']: # If there's a new reading from the blind control light sensor
                        blind = self.call_room_sunlight_control['Blind'] # Identify the blind
                        light_level = self.call_room_sunlight_control['Light Level'] # Capture the light level
                        window_blind[blind].room_sunlight_control(light_level) # Call the blind's sunlight control method, passing the light level
                        self.call_room_sunlight_control['State'] = False # Reset this flag because any light level update has now been actioned
                    if self.blind_control_door_changed['Changed']: # If a blind control door has changed state
                        blind = self.blind_control_door_changed['Blind'] # Identify the blind that is controlled by the door
                        light_level = self.call_room_sunlight_control['Light Level'] # Capture the light level
                        window_blind[blind].room_sunlight_control(light_level) # Call the blind's sunlight control method, passing the light level
                        self.blind_control_door_changed['Changed'] = False # Reset Door Changed Flag because any change of door state has now been actioned
                    if self.auto_blind_override_changed['Changed']: # If a blind auto override button has changed state
                        blind = self.auto_blind_override_changed['Blind'] # Identify the blind that is controlled by the button
                        light_level = self.call_room_sunlight_control['Light Level'] # Capture the light level
                        window_blind[blind].room_sunlight_control(light_level) # Call the blind's sunlight control method, passing the light level
                        self.auto_blind_override_changed['Changed'] = False # Reset Auto Override Flag because any change of override state has now been actioned
                    if self.call_control_blinds['State']: # If a manual blind change has been invoked
                        blind = self.call_control_blinds['Blind'] # Identify the blind that has been changed
                        window_blind[blind].control_blinds(blind, self.call_control_blinds) # Call the blind's manual control method
                        self.call_control_blinds['State'] = False # Reset Control Blinds Flag because any control blind request has now been actioned
                if self.air_purifiers_present:
                    purifier_readings_check_time = time.time()
                    if (purifier_readings_check_time - self.purifier_readings_update_time) >= 300: # Update air purifier readings if last update was >= 5 minutes ago
                        for name in self.air_purifier_names:
                            if self.air_purifier_names[name]['Auto']:# Readings only come from auto units
                                self.purifier_readings_update_time, part_2_5, co2, voc, max_aqi, max_co2, co2_threshold, part_2_5_threshold = air_purifier[name].capture_readings()
                                homebridge.update_blueair_aqi(name, part_2_5, co2, voc, max_aqi, max_co2, co2_threshold, part_2_5_threshold)
                                domoticz.update_blueair_aqi(name, part_2_5, co2, voc, max_aqi)
                    purifier_settings_check_time = time.time()
                    if (purifier_settings_check_time - self.purifier_settings_update_time) >= 5: # Update air purifier settings if last update was >= 5 seconds ago
                        for name in self.air_purifier_names:
                            settings_changed, self.purifier_settings_update_time, mode, fan_speed, child_lock, led_brightness, filter_status = air_purifier[name].capture_settings()
                            if settings_changed: # Only update Homebridge if a setting has changed (To minimise mqtt traffic)
                                homebridge.set_air_purifier_state(name, mode, fan_speed, child_lock, led_brightness, filter_status)
                                if self.air_purifier_names[name]['Auto']: # Change manual air purifier fan speeds if there's a change in the auto air purifier fan speed during linking hours
                                    if self.universal_air_purifier_fan_speed != fan_speed:
                                        self.universal_air_purifier_fan_speed = fan_speed
                                        if self.air_purifier_linking_hour():
                                            self.update_manual_air_purifier_fan_speeds(name, fan_speed)
                if self.aquarium_monitor_present:
                    if time.time() - previous_aquarium_capture_time > 600: # Capture aquarium reading every 10 minutes
                        print('Aquarium Capture Time:', datetime.fromtimestamp(time.time()).strftime('%A %d %B %Y @ %H:%M:%S'))
                        valid_aquarium_reading, message, ph, temp, nh3, reading_time =  aquarium_sensor.latest() # Capture Seneye device readings
                        if message == 'Seneye Comms Good': #If there were no Seneye comms errors
                            if reading_time > previous_aquarium_reading_time: # Only update Domoticz if there is a new reading
                                print('Aquarium Reading Time:', datetime.fromtimestamp(reading_time).strftime('%A %d %B %Y @ %H:%M:%S'), 'ph:', ph, 'nh3:', nh3, 'Temp:', temp)
                                if valid_aquarium_reading:
                                    domoticz.update_aquarium(ph, temp, nh3)
                                previous_aquarium_reading_time = reading_time
                        else:
                            print('Seneye Message Ignored: Comms Error') # Ignore bad Seneye comms messages
                        previous_aquarium_capture_time = time.time()
                if self.enviro_monitors_present and self.enable_outdoor_enviro_monitor_luftdaten_backup:
                    if time.time() - self.enviro_config['Outdoor']['Capture Time'] > 600: # Capture Luftdaten Air Quality if the Outdoor Enviro Monitor is unavailable
                        if time.time() - previous_luftdaten_capture_time > 900:
                            print('No message from Outdoor Northcliff Enviro Monitor, using Luftdaten from station', self.enviro_config['Outdoor']['Luftdaten Sensor ID'])
                            enviro_monitor['Outdoor'].capture_luftdaten_data(self.enviro_config['Outdoor']['Luftdaten Sensor ID'])
                            previous_luftdaten_capture_time = time.time()
                        
        except KeyboardInterrupt:
            self.shutdown('Keyboard Interrupt')

class HomebridgeClass(object):
    def __init__(self, outdoor_multisensor_names, outdoor_sensors_name, aircon_config, auto_air_purifier_names, window_blind_config, door_sensor_names_locations,
                  light_dimmer_names_device_id, colour_light_dimmer_names, air_purifier_names, multisensor_names, powerpoint_names_device_id, flood_sensor_names, enviro_config):
        #print ('Instantiated Homebridge', self)
        self.outgoing_mqtt_topic = 'homebridge/to/set'
        self.outgoing_config_mqtt_topic = 'homebridge/to/get'
        self.outgoing_add_accessory_mqtt_topic = 'homebridge/to/add'
        self.outgoing_add_service_mqtt_topic = 'homebridge/to/add/service'
        self.outgoing_remove_accessory_mqtt_topic = 'homebridge/to/remove'
        self.outgoing_remove_service_mqtt_topic = 'homebridge/to/remove/service'
        self.all_configs = {'name': '*'}
        self.all_configs_props = {'name': '*_props'}
        self.outdoor_multisensor_names = outdoor_multisensor_names
        self.outdoor_sensors_name = outdoor_sensors_name
        self.aircon_config = aircon_config
        self.auto_air_purifier_names = auto_air_purifier_names
        self.window_blind_config = window_blind_config
        self.door_sensor_names_locations = door_sensor_names_locations
        self.light_dimmer_names_device_id = light_dimmer_names_device_id
        self.colour_light_dimmer_names = colour_light_dimmer_names
        self.air_purifier_names = air_purifier_names
        self.multisensor_names = multisensor_names
        self.powerpoint_names_device_id = powerpoint_names_device_id
        self.flood_sensor_names = flood_sensor_names
        self.temperature_format = {'name': ' Temperature', 'service': 'TemperatureSensor', 'service_name': ' Temperature', 'characteristics_properties': {}}
        self.humidity_format = {'name': ' Humidity', 'service': 'HumiditySensor', 'service_name': ' Humidity', 'characteristics_properties': {}}
        self.light_level_format = {'name': ' Lux', 'service': 'LightSensor', 'service_name': ' Lux', 'characteristics_properties': {}}
        self.motion_format = {'name': ' Motion', 'service': 'MotionSensor', 'service_name': ' Motion', 'characteristics_properties': {}}
        self.door_format = {'name': ' Door', 'service': 'ContactSensor', 'service_name': ' Door', 'characteristics_properties':{'StatusLowBattery': {}}}
        self.door_state_map = {'door_opened':{False: 0, True: 1}, 'low_battery':{False: 0, True: 1}}
        self.dimmer_format = {'name': ' Light', 'service': 'Lightbulb', 'service_name': ' Light', 'characteristics_properties': {'Brightness': {}}}
        self.colour_light_dimmer_characteristics_properties = {'Brightness': {}, 'Hue': {}, 'Saturation': {}}
        self.dimmer_state_map = {0: False, 1: True}
        self.blinds_format = {'name': ' Blinds', 'service': 'WindowCovering', 'characteristics_properties': {'TargetPosition': {'minStep':50}}}
        self.blinds_temp_format = {'service': 'Thermostat', 'target_characteristic': 'TargetTemperature', 'low_temp_service_name': 'Blind Low Temp', 'high_temp_service_name': 'Blind High Temp',
                                    'high_temperature_characteristics_properties': {'TargetTemperature': {'minValue': 25, 'maxValue': 37, 'minStep': 1}, 'CurrentTemperature': {'minValue': -5, 'maxValue': 60, 'minStep': 0.1},
                                    'TargetHeatingCoolingState': {'minValue': 0, 'maxValue': 2}, 'CurrentHeatingCoolingState': {'minValue': 0, 'maxValue': 2}},
                                    'low_temperature_characteristics_properties': {'TargetTemperature':{'minValue': 5, 'maxValue': 16, 'minStep': 1},  'CurrentTemperature': {'minValue': -5, 'maxValue': 60, 'minStep': 0.1},
                                    'TargetHeatingCoolingState': {'minValue': 0, 'maxValue': 2}, 'CurrentHeatingCoolingState': {'minValue': 0, 'maxValue': 2}}}
        self.auto_blind_override_button_format = {'service_name': 'Auto Blind Override', 'service': 'Switch', 'characteristics_properties': {}}
        self.blind_incoming_position_map = {100: 'Open', 50: 'Venetian', 0: 'Closed'}
        self.blind_outgoing_position_map = {'Open': 100, 'Venetian': 50, 'Closed': 0}
        self.doorbell_name_identifier = 'Doorbell'
        self.doorbell_homebridge_json_name_map = {'Idle': 'Doorbell Idle', 'Automatic': 'Doorbell Automatic', 'Auto Possible': 'Doorbell Status', 'Manual': 'Doorbell Manual',
                                  'Triggered': 'Doorbell Status', 'Terminated': 'Doorbell Status', 'Ringing': 'Doorbell Status', 'Open Door': 'Doorbell Open Door'}
        self.doorbell_characteristics_properties = {'Ringing': {'MotionSensor': {'MotionDetected': {}}}, 'Others': {'Switch': {}}}
        # Set up homebridge switch types for doorbell (Indicator, Switch or TimedMomentary)
        self.doorbell_button_type = {'Terminated': 'Indicator', 'Auto Possible': 'Indicator', 'Triggered': 'Indicator',
                                     'Open Door': 'Momentary', 'Idle': 'Indicator', 'Automatic': 'Switch', 'Manual': 'Switch', 'Ringing': 'Motion'}
        self.powerpoint_format = {'name': ' Powerpoint', 'service': 'Outlet', 'service_name': '', 'characteristics_properties': {}}
        self.garage_door_format = {'name': 'Garage', 'service_name': 'Garage Door', 'service': 'GarageDoorOpener', 'characteristics_properties': {}}
        self.flood_state_format = {'name': ' Flood', 'service': 'LeakSensor', 'service_name': '', 'characteristics_properties': {'StatusLowBattery': {}}}
        self.aircon_thermostat_mode_map = {0: 'Off', 1: 'Heat', 2: 'Cool'}
        self.aircon_thermostat_incoming_mode_map = {'Off': 0, 'Heat': 1, 'Cool': 2}
        # Set up aircon homebridge button types (Indicator, Position Indicator or Thermostat Control)
        self.aircon_button_type = {'Remote Operation': 'Indicator', 'Heat': 'Indicator', 'Cool': 'Indicator', 'Fan': 'Indicator', 'Fan Hi': 'Indicator',
                                   'Fan Lo': 'Indicator', 'Heating': 'Indicator', 'Compressor': 'Indicator', 'Terminated': 'Indicator', 'Damper': 'Position Indicator',
                                   'Filter': 'Indicator', 'Malfunction': 'Indicator', 'Ventilation': 'Switch', 'Reset Effectiveness Log': 'Switch'}
        self.aircon_damper_position_state_map = {'Closing': 0, 'Opening': 1, 'Stopped': 2}
        self.aircon_thermostat_format = {}
        self.aircon_ventilation_button_format = {}
        self.aircon_filter_indicator_format = {}
        self.aircon_reset_effectiveness_log_button_format = {}
        self.aircon_control_thermostat_name = {}
        self.aircon_thermostat_names = {}
        self.aircon_damper_format = {}
        self.aircon_status_format = {}
        self.aircon_remote_operation_format = {}
        self.aircon_heat_format = {}
        self.aircon_cool_format = {}
        self.aircon_fan_format = {}
        self.aircon_fan_hi_format = {}
        self.aircon_fan_lo_format = {}
        self.aircon_compressor_format = {}
        self.aircon_heating_format = {}
        self.aircon_malfunction_format = {}
        self.aircon_names = []
        for aircon_name in self.aircon_config:
            self.aircon_thermostat_format[aircon_name] = {'service': 'Thermostat', 'characteristics_properties': {'TargetTemperature': {'minValue': 18, 'maxValue': 28, 'minStep': 0.5},
                                                                                                                  'CurrentTemperature': {'minValue': -5, 'maxValue': 60, 'minStep': 0.1},
                                                                                                                  'TargetHeatingCoolingState': {'minValue': 0, 'maxValue': 2},
                                                                                                                  'CurrentHeatingCoolingState': {'minValue': 0, 'maxValue': 2}}}
            self.aircon_ventilation_button_format[aircon_name] = {'name': aircon_name + ' Ventilation', 'service_name': 'Ventilation', 'service': 'Switch', 'characteristics_properties': {}}
            self.aircon_filter_indicator_format[aircon_name] = {'name': aircon_name + ' Filter', 'service_name': 'Filter', 'service': 'Switch', 'characteristics_properties': {}}
            self.aircon_reset_effectiveness_log_button_format[aircon_name] = {'name': aircon_name + ' Reset Effectiveness Log', 'service_name': 'Reset Effectiveness Log', 'service': 'Switch', 'characteristics_properties': {}}
            self.aircon_control_thermostat_name[aircon_name] = self.aircon_config[aircon_name]['Master']                                                                 
            self.aircon_thermostat_names[aircon_name] = self.aircon_config[aircon_name]['Day Zone'] + self.aircon_config[aircon_name]['Night Zone']
            self.aircon_thermostat_names[aircon_name].append(self.aircon_config[aircon_name]['Master'])
            self.aircon_status_format[aircon_name] = {'name': aircon_name + ' Status'}
            self.aircon_remote_operation_format[aircon_name] = {'name': aircon_name + ' Status', 'service_name': 'Remote Operation', 'service': 'Switch', 'characteristics_properties': {}}
            self.aircon_damper_format[aircon_name] = {'name': aircon_name + ' Status', 'service_name': 'Damper', 'service': 'Door', 'characteristics_properties': {'CurrentPosition':{'minValue': 0, 'maxValue': 100, 'minStep': 10}}}
            self.aircon_heat_format[aircon_name] = {'name': aircon_name + ' Status', 'service_name': 'Heat', 'service': 'Switch', 'characteristics_properties': {}}
            self.aircon_cool_format[aircon_name] = {'name': aircon_name + ' Status', 'service_name': 'Cool', 'service': 'Switch', 'characteristics_properties': {}}
            self.aircon_fan_format[aircon_name] = {'name': aircon_name + ' Status', 'service_name': 'Fan', 'service': 'Switch', 'characteristics_properties': {}}
            self.aircon_fan_hi_format[aircon_name] = {'name': aircon_name + ' Status', 'service_name': 'Fan Hi', 'service': 'Switch', 'characteristics_properties': {}}
            self.aircon_fan_lo_format[aircon_name] = {'name': aircon_name + ' Status', 'service_name': 'Fan Lo', 'service': 'Switch', 'characteristics_properties': {}}
            self.aircon_compressor_format[aircon_name] = {'name': aircon_name + ' Status', 'service_name': 'Compressor', 'service': 'Switch', 'characteristics_properties': {}}
            self.aircon_heating_format[aircon_name] = {'name': aircon_name + ' Status', 'service_name': 'Heating', 'service': 'Switch', 'characteristics_properties': {}}
            self.aircon_malfunction_format[aircon_name] = {'name': aircon_name + ' Status', 'service_name': 'Malfunction', 'service': 'Switch', 'characteristics_properties': {}}  
            for thermostat_name in self.aircon_thermostat_names[aircon_name]:
                self.aircon_button_type[aircon_name + ' ' + thermostat_name] = 'Thermostat Control'
            self.aircon_names.append(aircon_name)
        # Set up Air Purifiers
        self.air_purifier_format = {'name': ' Air Purifier', 'service' :'AirPurifier', 'service_name': '', 'characteristics_properties': {'RotationSpeed': {'minValue': 0, 'maxValue': 100, 'minStep': 25}, 'LockPhysicalControls': {}}}
        self.air_purifier_LED_format = {'name': ' Air Purifier', 'service_name': ' LED', 'service' :'Lightbulb', 'characteristics_properties': {'Brightness': {}}}
        self.air_purifier_filter_format = {'name': ' Air Purifier', 'service_name': ' Filter', 'service' :'FilterMaintenance', 'characteristics_properties': {}}
        self.air_quality_format = {'name': ' Air Quality', 'service_name': ' Air Quality', 'service': 'AirQualitySensor', 'characteristics_properties': {'PM2_5Density': {}, 'VOCDensity': {}}}
        self.CO2_level_format = {'name': ' CO2', 'service_name': ' CO2', 'service' :'CarbonDioxideSensor', 'characteristics_properties': {'CarbonDioxideLevel': {}, 'CarbonDioxidePeakLevel': {}}}
        self.PM2_5_alert_format = {'name': ' PM2.5 Alert', 'service_name': ' PM2.5 Alert', 'service' :'MotionSensor', 'characteristics_properties': {'MotionDetected':{}}}
        #self.air_quality_service_name_map = {name: name + self.air_quality_format['name'] for name in self.auto_air_purifier_names}
        #self.CO2_service_name_map = {name: name + self.CO2_level_format['name'] for name in self.auto_air_purifier_names}
        #self.PM2_5_service_name_map = {name: name + self.PM2_5_alert_format['name'] for name in self.auto_air_purifier_names}
        # Set up reboot
        self.reboot_format = {'name': 'Reboot'}
        self.reboot_arm_format = {'service_name': 'Reboot Arm', 'service': 'Switch', 'characteristics_properties': {}}
        self.reboot_trigger_format = {'service_name': 'Reboot Trigger', 'service': 'Switch', 'characteristics_properties': {}}
        self.restart_trigger_format = {'service_name': 'Restart Trigger', 'service': 'Switch', 'characteristics_properties': {}}
        self.reboot_armed = False
        # Set up Enviro Monitors
        self.enviro_config = enviro_config
        self.enviro_aqi_format = {'name': ' AQI', 'service_name': ' AQI', 'service': 'AirQualitySensor',
                                   'characteristics_properties': {'PM10Density': {}, 'PM2_5Density': {}, 'NitrogenDioxideDensity': {}}}
        self.enviro_aqi_voc_format = {'name': ' AQI', 'service_name': ' AQI', 'service': 'AirQualitySensor',
                                   'characteristics_properties': {'PM10Density': {}, 'PM2_5Density': {}, 'NitrogenDioxideDensity': {}, 'VOCDensity': {}}}   
        self.enviro_reducing_format = {'name': ' Reducing', 'service_name': ' Reducing', 'service': 'AirQualitySensor', 'characteristics_properties': {'NitrogenDioxideDensity': {}}}
        self.enviro_ammonia_format = {'name': ' Ammonia', 'service_name': ' Ammonia', 'service': 'AirQualitySensor', 'characteristics_properties': {'NitrogenDioxideDensity': {}}}
        self.enviro_PM2_5_alert_format = {'name': ' PM2.5 Alert', 'service_name': ' PM2.5 Alert', 'service' :'MotionSensor', 'characteristics_properties': {'MotionDetected':{}}}
        self.enviro_temp_format = {'name': ' Env Temp', 'service': 'TemperatureSensor', 'service_name': ' Env Temp', 'characteristics_properties': {}}
        self.enviro_hum_format = {'name': ' Env Hum', 'service': 'HumiditySensor', 'service_name': ' Env Hum', 'characteristics_properties': {}}
        self.enviro_lux_format = {'name': ' Env Lux', 'service': 'LightSensor', 'service_name': ' Env Lux', 'characteristics_properties': {}}
        self.enviro_CO2_level_format = {'name': ' CO2', 'service_name': ' CO2', 'service' :'CarbonDioxideSensor', 'characteristics_properties': {'CarbonDioxideLevel': {}, 'CarbonDioxidePeakLevel': {}}}
        # Set up EV Charger
        self.ev_charger_name_identifier = 'Charger'
        self.ev_charger_state_format = {'name': 'Charger State'}
        self.ev_charger_not_connected_format = {'service_name': 'Not Connected', 'service': 'Switch', 'characteristics_properties': {}}
        self.ev_charger_connected_locked_format = {'service_name': 'Connected and Locked', 'service': 'Switch', 'characteristics_properties': {}}
        self.ev_charger_charging_format = {'service_name': 'Charging', 'service': 'Switch', 'characteristics_properties': {}}
        self.ev_charger_charged_format = {'service_name': 'Charged', 'service': 'Switch', 'characteristics_properties': {}}
        self.ev_charger_control_format = {'name': 'Charger Control'}
        self.ev_charger_unlock_format = {'service_name': 'Unlock Charger', 'service': 'Switch', 'characteristics_properties': {}}
        self.ev_charger_lock_format = {'service_name': 'Lock Charger', 'service': 'Switch', 'characteristics_properties': {}}
        self.ev_charger_reset_format = {'name': 'Reset Charger', 'service_name': 'Reset Charger', 'service': 'Switch', 'characteristics_properties': {}}
        self.ev_charger_ack_format = {'name': 'Charger ACK'}
        self.ev_charger_unlock_ack_format = {'service_name': 'Unlock', 'service': 'Switch', 'characteristics_properties': {}}
        self.ev_charger_lock_ack_format = {'service_name': 'Lock', 'service': 'Switch', 'characteristics_properties': {}}
        self.ev_charger_reset_ack_format = {'name': 'Reset', 'service_name': 'Reset Charger', 'service': 'Switch', 'characteristics_properties': {}}
        # Set up config
        self.current_config = {}
        self.ack_cache = {}
        
    def check_and_fix_config(self): # Check and fix Homebridge Cached Accessories config against required config 
        print('Homebridge config check started. Please wait.')
        homebridge_restart_required = False
        time.sleep(5)
        client.publish(self.outgoing_config_mqtt_topic, json.dumps(self.all_configs_props)) # Request config check
        time.sleep(2)
        current_homebridge_config = self.current_config
        #current_homebridge_config['Dummy Accessory'] = {'Dummy Service Name': {'DummyService':{'DummyCharacteristic':{'DummyProperty':0}}}}
        required_homebridge_config = self.indentify_required_homebridge_config()
        missing_accessories, missing_accessories_services, additional_accessories_services, incorrect_accessories_services = self.find_incorrect_accessories(required_homebridge_config, current_homebridge_config)
        excess_accessories = self.find_excess_accessories(required_homebridge_config, current_homebridge_config)
        print('Missing Accessories:', missing_accessories)
        print('Excess Accessories:', excess_accessories)
        print('Missing Services within Accessories:', missing_accessories_services)
        print('Unrequired Services within Accessories', additional_accessories_services)
        print('Incorrect Services within Accessories:', incorrect_accessories_services)
        # Handle missing Accessories
        if missing_accessories == []: 
            print('No missing accessories')
        else:
            for accessory in missing_accessories:
                print(accessory, 'accessory is missing, along with the following config:-')
                for service_name in required_homebridge_config[accessory]:
                    print('Service Name:', service_name, 'Service:', required_homebridge_config[accessory][service_name])
            add_missing_accessories = input("Do you want to add the missing accessories? (y/n): ")
            if add_missing_accessories == 'y':
                homebridge_restart_required = True
                self.add_missing_accessories(missing_accessories, required_homebridge_config)     
        # Handle excess Accessories
        if excess_accessories == []: 
            print('No excess accessories')
        else:
            for accessory in excess_accessories:
                print(accessory, 'accessory is not required')
            remove_excess_accessories = input("Do you want to remove excess accessories? (y/n): ")
            if remove_excess_accessories == 'y':
                homebridge_restart_required = True
                self.remove_excess_accessories(excess_accessories)
        # Handle missing Services within Accessories
        if missing_accessories_services == []:
            print('No missing accessories services')
        else:
            for accessory in missing_accessories_services:
                for key in accessory:
                    for service_name in accessory[key]:
                        print(key, "accessory's service name", service_name, "is missing, along with the config:", required_homebridge_config[key][service_name])
            add_missing_accessories_services = input("Do you want to add the missing accessories' services? (y/n): ")
            if add_missing_accessories_services == 'y':
                homebridge_restart_required = True
                self.add_missing_accessories_services(missing_accessories_services, required_homebridge_config)
        # Handle unrequired Services within Accessories
        if additional_accessories_services == []:
            print('No additional accessories services')
        else:
            for accessory in additional_accessories_services:
                for key in accessory:
                    for service_name in accessory[key]:
                        print('')
                        print(key, "accessory's service name", service_name, "is not required")
            remove_additional_accessories_services = input("Do you want to delete the excess accessories' services? (y/n): ")
            if remove_additional_accessories_services == 'y':
                homebridge_restart_required = True
                self.remove_additional_accessories_services(additional_accessories_services)
        # Handle Services that are within Accessories but have a config error
        if incorrect_accessories_services == []:
            print('No incorrect accessories services')
        else:
            for accessory in incorrect_accessories_services:
                for key in accessory:
                    print('')
                    print(key, 'accessory is incorrect')
                    for service_name in accessory[key]:
                        if service_name in current_homebridge_config[key]:
                            print('Service Name:', service_name, 'is incorrect')
                        else:
                            print('Service Name:', service_name, 'is missing')
            fix_incorrect_accessories = input("Do you want to fix the incorrect accessories? (y/n): ")
            if fix_incorrect_accessories == 'y':
                homebridge_restart_required = True
                self.fix_incorrect_accessories(incorrect_accessories_services, required_homebridge_config)
        if homebridge_restart_required:
            print('Waiting for config acknowledgements')
            time.sleep(10)
            self.check_ack_cache()
            print('Please restart homebridge now to update the homebridge config cache')
            homebridge_restarted = input("Please enter 'y' when you have restarted homebridge")
            if homebridge_restarted == 'y':
                print('Updated homebridge config now captured in the homebridge cache')
            else:
                print('Updated homebridge config has not been captured in the homebridge cache. THE CACHE STILL CONTAINS THE OLD CONFIG UNTIL HOMEBRIDGE IS RESTARTED')
        print('Homebridge config check completed')

    def indentify_required_homebridge_config(self):
        # Blinds
        if mgr.window_blinds_present:
            blinds_homebridge_config = {blinds: {**{blind: {self.blinds_format['service']: self.blinds_format['characteristics_properties']} for blind in self.window_blind_config[blinds]['status']},
                                             **{self.blinds_temp_format['high_temp_service_name']: {self.blinds_temp_format['service']: self.blinds_temp_format['high_temperature_characteristics_properties']},
                                              self.blinds_temp_format['low_temp_service_name']: {self.blinds_temp_format['service']: self.blinds_temp_format['low_temperature_characteristics_properties']},
                                              self.auto_blind_override_button_format['service_name']: {self.auto_blind_override_button_format['service']: self.auto_blind_override_button_format['characteristics_properties']}}}
                                    for blinds in self.window_blind_config}
        else:
            blinds_homebridge_config = {}
        # Doors
        if mgr.door_sensors_present:
            door_sensor_rooms = []
            for door in self.door_sensor_names_locations:
                if self.door_sensor_names_locations[door] not in door_sensor_rooms:
                    door_sensor_rooms.append(self.door_sensor_names_locations[door]) # Create a list of rooms with door sensors to create accessory names
            door_sensors_homebridge_config = {room: {} for room in door_sensor_rooms} # Make an accessory name key for each door sensor room
            for room in door_sensor_rooms: # Iterate through the list of rooms with door sensors
                for door in self.door_sensor_names_locations:
                    if self.door_sensor_names_locations[door] == room: # Add the door sensor to the relevant room
                        door_sensors_homebridge_config[room][door + self.door_format['service_name']] = {self.door_format['service']: self.door_format['characteristics_properties']}
        else:
            door_sensors_homebridge_config = {}
        # Garage
        if mgr.garage_door_present == True:
            garage_door_homebridge_config = {self.garage_door_format['name']: {self.garage_door_format['service_name']: {self.garage_door_format['service']: self.garage_door_format['characteristics_properties']}}}
        else:
            garage_door_homebridge_config = {}    
        # Reboot
        if mgr.enable_reboot:
            reboot_homebridge_config = {self.reboot_format['name']: {self.reboot_arm_format['service_name']: {self.reboot_arm_format['service']: self.reboot_arm_format['characteristics_properties']},
                                                                        self.reboot_trigger_format['service_name']: {self.reboot_trigger_format['service']: self.reboot_trigger_format['characteristics_properties']},
                                                                        self.restart_trigger_format['service_name']: {self.restart_trigger_format['service']: self.restart_trigger_format['characteristics_properties']}}}
        else:
            reboot_homebridge_config = {}
        # Light Dimmers
        if mgr.light_dimmers_present:
            light_dimmers_homebridge_config = {light: {light: {self.dimmer_format['service']: self.dimmer_format['characteristics_properties']}} for light in self.light_dimmer_names_device_id}
            for light in self.colour_light_dimmer_names:
                light_dimmers_homebridge_config[light][light][self.dimmer_format['service']] = self.colour_light_dimmer_characteristics_properties # Add hue and saturation characteristics to colour dimmer
        else:
            light_dimmers_homebridge_config = {}
        # Aircon
        if mgr.aircons_present:
            aircon_homebridge_config = {}
            for aircon_name in self.aircon_config:
                aircon_homebridge_config[self.aircon_ventilation_button_format[aircon_name]['name']] = {self.aircon_ventilation_button_format[aircon_name]['service_name']:
                                                                                                        {self.aircon_ventilation_button_format[aircon_name]['service']:
                                                                                                         self.aircon_ventilation_button_format[aircon_name]['characteristics_properties']}}
                aircon_homebridge_config[self.aircon_filter_indicator_format[aircon_name]['name']] = {self.aircon_filter_indicator_format[aircon_name]['service_name']: {self.aircon_filter_indicator_format[aircon_name]['service']:
                                                                                                                                                                        self.aircon_filter_indicator_format[aircon_name]['characteristics_properties']}}
                aircon_homebridge_config[self.aircon_reset_effectiveness_log_button_format[aircon_name]['name']] = {self.aircon_reset_effectiveness_log_button_format[aircon_name]['service_name']:
                                                                                                                    {self.aircon_reset_effectiveness_log_button_format[aircon_name]['service']:
                                                                                                                      self.aircon_reset_effectiveness_log_button_format[aircon_name]['characteristics_properties']}}
                aircon_homebridge_config[self.aircon_status_format[aircon_name]['name']] = {self.aircon_remote_operation_format[aircon_name]['service_name']:
                                                                                            {self.aircon_remote_operation_format[aircon_name]['service']:
                                                                                             self.aircon_remote_operation_format[aircon_name]['characteristics_properties']},
                                                                                            self.aircon_damper_format[aircon_name]['service_name']:
                                                                                            {self.aircon_damper_format[aircon_name]['service']:
                                                                                             self.aircon_damper_format[aircon_name]['characteristics_properties']},
                                                                                            self.aircon_heat_format[aircon_name]['service_name']:
                                                                                            {self.aircon_heat_format[aircon_name]['service']:
                                                                                             self.aircon_heat_format[aircon_name]['characteristics_properties']},
                                                                                            self.aircon_cool_format[aircon_name]['service_name']:
                                                                                            {self.aircon_cool_format[aircon_name]['service']:
                                                                                             self.aircon_cool_format[aircon_name]['characteristics_properties']},
                                                                                            self.aircon_fan_format[aircon_name]['service_name']:
                                                                                            {self.aircon_fan_format[aircon_name]['service']:
                                                                                             self.aircon_fan_format[aircon_name]['characteristics_properties']},
                                                                                            self.aircon_fan_hi_format[aircon_name]['service_name']:
                                                                                            {self.aircon_fan_hi_format[aircon_name]['service']:
                                                                                             self.aircon_fan_hi_format[aircon_name]['characteristics_properties']},
                                                                                            self.aircon_fan_lo_format[aircon_name]['service_name']:
                                                                                            {self.aircon_fan_lo_format[aircon_name]['service']:
                                                                                             self.aircon_fan_lo_format[aircon_name]['characteristics_properties']},
                                                                                            self.aircon_compressor_format[aircon_name]['service_name']:
                                                                                            {self.aircon_compressor_format[aircon_name]['service']:
                                                                                             self.aircon_compressor_format[aircon_name]['characteristics_properties']},
                                                                                            self.aircon_heating_format[aircon_name]['service_name']:
                                                                                            {self.aircon_heating_format[aircon_name]['service']:
                                                                                             self.aircon_heating_format[aircon_name]['characteristics_properties']},
                                                                                            self.aircon_malfunction_format[aircon_name]['service_name']:
                                                                                            {self.aircon_malfunction_format[aircon_name]['service']:
                                                                                             self.aircon_malfunction_format[aircon_name]['characteristics_properties']}}
                aircon_thermostat_names = self.aircon_config[aircon_name]['Day Zone'] + self.aircon_config[aircon_name]['Night Zone'] + [self.aircon_config[aircon_name]['Master']]
                for thermostat in aircon_thermostat_names:
                    aircon_homebridge_config[aircon_name + ' ' + thermostat] = {aircon_name + ' ' + thermostat: {self.aircon_thermostat_format[aircon_name]['service']:
                                                                                                                 self.aircon_thermostat_format[aircon_name]['characteristics_properties']}}
        else:
            aircon_homebridge_config = {}
        # Doorbell
        if mgr.doorbell_present:
            doorbell_homebridge_config = {'Doorbell Status': {}} # Make a Doorbell Status Key
            for button in self.doorbell_homebridge_json_name_map:
                if self.doorbell_homebridge_json_name_map[button] != 'Doorbell Status':
                    doorbell_homebridge_config[self.doorbell_homebridge_json_name_map[button]] = {button: self.doorbell_characteristics_properties['Others']}
                else:
                    if button == 'Ringing':
                        doorbell_homebridge_config['Doorbell Status'][button] = self.doorbell_characteristics_properties['Ringing']
                    else:
                        doorbell_homebridge_config['Doorbell Status'][button] = self.doorbell_characteristics_properties['Others']
        else:
            doorbell_homebridge_config = {}                       
        # Air Purifiers
        if mgr.air_purifiers_present:
            air_purifiers_homebridge_config = {}
            for air_purifier in self.air_purifier_names:
                air_purifiers_homebridge_config[air_purifier + self.air_purifier_format['name']] = {air_purifier + self.air_purifier_format['service_name']: {self.air_purifier_format['service']: self.air_purifier_format['characteristics_properties']},
                                                                                                air_purifier + self.air_purifier_LED_format['service_name']: {self.air_purifier_LED_format['service']:
                                                                                                                                                                  self.air_purifier_LED_format['characteristics_properties']},
                                                                                                    air_purifier + self.air_purifier_filter_format['service_name']: {self.air_purifier_filter_format['service']:
                                                                                                                                                                     self.air_purifier_filter_format['characteristics_properties']}}
            for air_purifier in self.auto_air_purifier_names:
                air_purifiers_homebridge_config[air_purifier + self.air_quality_format['name']] = {air_purifier + self.air_quality_format['service_name']: {self.air_quality_format['service']:
                                                                                                                                                                     self.air_quality_format['characteristics_properties']}}
                air_purifiers_homebridge_config[air_purifier + self.CO2_level_format['name']] = {air_purifier + self.CO2_level_format['service_name']: {self.CO2_level_format['service']:
                                                                                                                                                                     self.CO2_level_format['characteristics_properties']}}
                air_purifiers_homebridge_config[air_purifier + self.PM2_5_alert_format['name']] = {air_purifier + self.PM2_5_alert_format['service_name']: {self.PM2_5_alert_format['service']:
                                                                                                                                                                     self.PM2_5_alert_format['characteristics_properties']}} 
        else:
            air_purifiers_homebridge_config = {}
        # Multisensors
        if mgr.multisensors_present:
            multisensors_homebridge_config = {self.outdoor_sensors_name: {}} # Make a key for the outdoor sensors' accessory name
            for multisensor in self.multisensor_names:
                if multisensor in self.outdoor_multisensor_names: # Outdoor sensors are grouped as services under one accessory
                    multisensors_homebridge_config[self.outdoor_sensors_name][multisensor + self.temperature_format['service_name']] = {self.temperature_format['service']: self.temperature_format['characteristics_properties']}
                    multisensors_homebridge_config[self.outdoor_sensors_name][multisensor + self.humidity_format['service_name']] = {self.humidity_format['service']: self.humidity_format['characteristics_properties']}
                    multisensors_homebridge_config[self.outdoor_sensors_name][multisensor + self.light_level_format['service_name']] = {self.light_level_format['service']: self.light_level_format['characteristics_properties']}
                    multisensors_homebridge_config[self.outdoor_sensors_name][multisensor + self.motion_format['service_name']] = {self.motion_format['service']: self.motion_format['characteristics_properties']}
                else: # Indoor Sensors are separate accessories
                    multisensors_homebridge_config[multisensor + self.temperature_format['name']] = {multisensor + self.temperature_format['service_name']: {self.temperature_format['service']:
                                                                                                                                                                     self.temperature_format['characteristics_properties']}}
                    multisensors_homebridge_config[multisensor + self.humidity_format['name']] = {multisensor + self.humidity_format['service_name']: {self.humidity_format['service']:
                                                                                                                                                       self.humidity_format['characteristics_properties']}}
                    multisensors_homebridge_config[multisensor + self.light_level_format['name']] = {multisensor + self.light_level_format['service_name']: {self.light_level_format['service']:
                                                                                                                                                             self.light_level_format['characteristics_properties']}}
                    multisensors_homebridge_config[multisensor + self.motion_format['name']] = {multisensor + self.motion_format['service_name']: {self.motion_format['service']:
                                                                                                                                                   self.motion_format['characteristics_properties']}}
        else:
            multisensors_homebridge_config = {}
            # Powerpoints
        if mgr.powerpoints_present:
            powerpoints_homebridge_config = {powerpoint + self.powerpoint_format['name']: {powerpoint + self.powerpoint_format['service_name']: {self.powerpoint_format['service']: self.powerpoint_format['characteristics_properties']}}
                                         for powerpoint in self.powerpoint_names_device_id}
        else:
            powerpoints_homebridge_config = {}
        # Flood Sensors
        if mgr.flood_sensors_present:
            flood_sensors_homebridge_config = {flood_sensor + self.flood_state_format['name']: {flood_sensor + self.flood_state_format['service_name']: {self.flood_state_format['service']:
                                                                                                                                                     self.flood_state_format['characteristics_properties']}}
                                           for flood_sensor in self.flood_sensor_names}
        else:
            flood_sensors_homebridge_config = {}
        # Enviro Monitors
        if mgr.enviro_monitors_present == True:
            enviro_monitors_homebridge_config = {}
            for enviro_monitor in self.enviro_config:
                if 'VOC' in self.enviro_config[enviro_monitor]['Device IDs']: # Add VOC if it's an Indoor Plus Enviro Monitor
                    enviro_monitors_homebridge_config[enviro_monitor + self.enviro_aqi_format['name']] = {enviro_monitor + self.enviro_aqi_voc_format['service_name']:
                                                                                      {self.enviro_aqi_voc_format['service']:
                                                                                       self.enviro_aqi_voc_format['characteristics_properties']}}
                else:
                    enviro_monitors_homebridge_config[enviro_monitor + self.enviro_aqi_format['name']] = {enviro_monitor + self.enviro_aqi_format['service_name']:
                                                                                          {self.enviro_aqi_format['service']:
                                                                                           self.enviro_aqi_format['characteristics_properties']}}
                enviro_monitors_homebridge_config[enviro_monitor + self.enviro_reducing_format['name']] = {enviro_monitor + self.enviro_reducing_format['service_name']:
                                                                                     {self.enviro_reducing_format['service']:
                                                                                      self.enviro_reducing_format['characteristics_properties']}}
                enviro_monitors_homebridge_config[enviro_monitor + self.enviro_ammonia_format['name']] = {enviro_monitor + self.enviro_ammonia_format['service_name']:
                                                                                      {self.enviro_ammonia_format['service']:
                                                                                        self.enviro_ammonia_format['characteristics_properties']}}
                enviro_monitors_homebridge_config[enviro_monitor + self.enviro_PM2_5_alert_format['name']] = {enviro_monitor +
                                                                                                               self.enviro_PM2_5_alert_format['service_name']:
                                                                                                               {self.enviro_PM2_5_alert_format['service']:
                                                                                                                self.enviro_PM2_5_alert_format['characteristics_properties']}}
                if self.enviro_config[enviro_monitor]['Capture Temp/Hum/Bar/Lux']: # Set up Temp/Hum/Bar/Lux if enabled
                    enviro_monitors_homebridge_config[enviro_monitor + self.enviro_temp_format['name']] = {enviro_monitor + self.enviro_temp_format['service_name']:
                                                                                                           {self.enviro_temp_format['service']:
                                                                                                            self.enviro_temp_format['characteristics_properties']}}
                    enviro_monitors_homebridge_config[enviro_monitor + self.enviro_hum_format['name']] = {enviro_monitor + self.enviro_hum_format['service_name']:
                                                                                                          {self.enviro_hum_format['service']:
                                                                                                           self.enviro_hum_format['characteristics_properties']}}
                    enviro_monitors_homebridge_config[enviro_monitor + self.enviro_lux_format['name']] = {enviro_monitor + self.enviro_lux_format['service_name']:
                                                                                                          {self.enviro_lux_format['service']:
                                                                                                           self.enviro_lux_format['characteristics_properties']}}
                if 'CO2' in self.enviro_config[enviro_monitor]['Device IDs']: # Add CO2 if it's an Indoor Plus Enviro Monitor
                    enviro_monitors_homebridge_config[enviro_monitor + self.enviro_CO2_level_format['name']] = {enviro_monitor + self.enviro_CO2_level_format['service_name']:
                                                                                      {self.enviro_CO2_level_format['service']: self.enviro_CO2_level_format['characteristics_properties']}}                
        else:
            enviro_monitors_homebridge_config = {}        
        # EV Charger
        if mgr.ev_charger_present:
            ev_charger_homebridge_config = {}
            ev_charger_homebridge_config[self.ev_charger_state_format['name']] = {self.ev_charger_not_connected_format['service_name']:
                                                                                    {self.ev_charger_not_connected_format['service']:
                                                                                     self.ev_charger_not_connected_format['characteristics_properties']},
                                                                                    self.ev_charger_connected_locked_format['service_name']:
                                                                                    {self.ev_charger_connected_locked_format['service']:
                                                                                     self.ev_charger_connected_locked_format['characteristics_properties']},
                                                                                    self.ev_charger_charging_format['service_name']:
                                                                                    {self.ev_charger_charging_format['service']:
                                                                                     self.ev_charger_charging_format['characteristics_properties']},
                                                                                    self.ev_charger_charged_format['service_name']:
                                                                                    {self.ev_charger_charged_format['service']:
                                                                                     self.ev_charger_charged_format['characteristics_properties']}}
            ev_charger_homebridge_config[self.ev_charger_control_format['name']] = {self.ev_charger_unlock_format['service_name']:
                                                                               {self.ev_charger_unlock_format['service']:
                                                                                self.ev_charger_unlock_format['characteristics_properties']},
                                                                               self.ev_charger_lock_format['service_name']:
                                                                               {self.ev_charger_lock_format['service']:
                                                                                self.ev_charger_lock_format['characteristics_properties']}}
            ev_charger_homebridge_config[self.ev_charger_reset_format['name']] = {self.ev_charger_reset_format['service_name']:
                                                                                    {self.ev_charger_reset_format['service']:
                                                                                     self.ev_charger_reset_format['characteristics_properties']}}
            ev_charger_homebridge_config[self.ev_charger_ack_format['name']] = {self.ev_charger_unlock_ack_format['service_name']:
                                                                                    {self.ev_charger_unlock_ack_format['service']:
                                                                                     self.ev_charger_unlock_ack_format['characteristics_properties']},
                                                                                self.ev_charger_lock_ack_format['service_name']:
                                                                                    {self.ev_charger_lock_ack_format['service']:
                                                                                     self.ev_charger_lock_ack_format['characteristics_properties']},
                                                                                self.ev_charger_reset_ack_format['service_name']:
                                                                                    {self.ev_charger_reset_ack_format['service']:
                                                                                     self.ev_charger_reset_ack_format['characteristics_properties']}}
        else:
            ev_charger_homebridge_config = {}
            
        # Build entire required_homebridge_config
        required_homebridge_config = {**blinds_homebridge_config, **door_sensors_homebridge_config, **garage_door_homebridge_config, **reboot_homebridge_config, **light_dimmers_homebridge_config,
                                      **aircon_homebridge_config, **doorbell_homebridge_config, **air_purifiers_homebridge_config, **multisensors_homebridge_config, **powerpoints_homebridge_config,
                                      **flood_sensors_homebridge_config, **enviro_monitors_homebridge_config, **ev_charger_homebridge_config}
        return required_homebridge_config
                    
    def find_incorrect_accessories(self, required_homebridge_config, current_homebridge_config):
        missing_accessories = []
        incorrect_accessories_services = []
        missing_accessories_services = []
        additional_accessories_services = []
        for required_accessory in required_homebridge_config:
            if required_accessory in current_homebridge_config: # Is the required accessory in the current config?
                missing_services = []
                additional_services = []
                incorrect_services = []
                for service_name in required_homebridge_config[required_accessory]:
                    if service_name in current_homebridge_config[required_accessory]: # Is the required service_name in the current config?
                        for service in required_homebridge_config[required_accessory][service_name]:
                            characteristics_OK = True
                            properties_OK = True
                            if service in current_homebridge_config[required_accessory][service_name]: # Does the service in the current config match the required service?
                                service_OK = True
                                for characteristic in required_homebridge_config[required_accessory][service_name][service]: # Do the characteristics in the current config match the required characteristics?
                                    if characteristic in current_homebridge_config[required_accessory][service_name][service]:
                                        for prop in required_homebridge_config[required_accessory][service_name][service][characteristic]:  # Do the properties in the current config match the required properties?
                                            if required_homebridge_config[required_accessory][service_name][service][characteristic][prop] != {}:
                                                if current_homebridge_config[required_accessory][service_name][service][characteristic][prop] != required_homebridge_config[required_accessory][service_name][service][characteristic][prop]:
                                                    properties_OK = False
                                    else:
                                        characteristics_OK = False
                            else:
                                service_OK = False
                        if not service_OK or not characteristics_OK or not properties_OK: # Is the service_name correct but there are errors in the service, characteristics or properties?
                            incorrect_services.append(service_name) # Capture incorrect services
                            print('Incorrect Service:', service_name)
                            print('service:', service_OK, 'characteristics:', characteristics_OK, 'properties:', properties_OK)
                    else: # The required service_name is missing from the current config
                        missing_services.append(service_name) # Capture missing services
                        print(service_name, 'is required in', required_accessory, 'accessory, but is missing')
                        for current_service_name in current_homebridge_config[required_accessory]:
                            if current_service_name not in required_homebridge_config[required_accessory]: # Is the current config service_name required?
                                additional_services.append(current_service_name) # Capture current config service_names that are not required 
                                print(current_service_name, 'is not required in', required_accessory, ' but is currently configured')
                if incorrect_services != []: # Record all incorrect services for the required accessory
                    incorrect_accessories_services.append({required_accessory: incorrect_services})
                if additional_services != []: # Record services that are in excess of the required accessory
                    additional_accessories_services.append({required_accessory: additional_services})
                if missing_services != []: # Record all missing services for the required accessory
                    missing_accessories_services.append({required_accessory: missing_services})
            else: # The required accessory is missing from the current config
                missing_accessories.append(required_accessory) # Record that the required accessory is missing    
        return missing_accessories, missing_accessories_services, additional_accessories_services, incorrect_accessories_services
    
    def find_excess_accessories(self, required_homebridge_config, current_homebridge_config):
        excess_accessories = []
        for current_accessory in current_homebridge_config:
           if current_accessory not in required_homebridge_config:
               excess_accessories.append(current_accessory)
        return excess_accessories
    
    def add_missing_accessories(self, missing_accessories, required_homebridge_config):
        print('Adding Missing Accessories')
        for accessory in missing_accessories:
            first_service = True
            homebridge_json = {}
            homebridge_json['name'] = accessory
            for service_name in required_homebridge_config[accessory]:
                homebridge_json['service_name'] = service_name
                for service in required_homebridge_config[accessory][service_name]:
                    homebridge_json['service'] = service
                    for characteristic in required_homebridge_config[accessory][service_name][service]:
                        if required_homebridge_config[accessory][service_name][service][characteristic] != {}:
                            properties = {}
                            for prop in required_homebridge_config[accessory][service_name][service][characteristic]:
                                if required_homebridge_config[accessory][service_name][service][characteristic][prop] != {}:
                                    properties[prop] = required_homebridge_config[accessory][service_name][service][characteristic][prop]
                                else:
                                    properties[prop] = 'default'
                            homebridge_json[characteristic] = properties
                        else:
                            homebridge_json[characteristic] = 'default'
                if first_service:
                    config_command = 'Adding ' + accessory
                    print('Adding', accessory, self.outgoing_add_accessory_mqtt_topic, homebridge_json)
                    ack_payload = {"ack": True, "message": "accessory '" + homebridge_json["name"] + "', service_name '" + homebridge_json['service_name'] + "' is added."}
                    #print(ack_payload)
                    self.push_ack_cache({config_command: ack_payload})
                    client.publish(self.outgoing_add_accessory_mqtt_topic, json.dumps(homebridge_json))
                    first_service = False
                    homebridge_json = {}
                    homebridge_json['name'] = accessory
                else:
                    config_command = 'Adding '+ service_name + ' service to ' + accessory
                    print('Adding', service_name, 'service to', accessory, self.outgoing_add_service_mqtt_topic, homebridge_json)
                    ack_payload = {"ack": True, "message": "service_name '" + homebridge_json['service_name'] + "', service '" +  homebridge_json['service'] + "' is added."}
                    #print(ack_payload)
                    self.push_ack_cache({config_command: ack_payload})
                    client.publish(self.outgoing_add_service_mqtt_topic, json.dumps(homebridge_json))
                    homebridge_json = {}
                    homebridge_json['name'] = accessory
                        
    def add_missing_accessories_services(self, missing_accessories_services, required_homebridge_config):
        print('Adding Missing Services')
        for accessory in missing_accessories_services:
            for key in accessory:
                for service_name in accessory[key]:
                    homebridge_json = {}
                    homebridge_json['name'] = key
                    homebridge_json['service_name'] = service_name
                    for service in required_homebridge_config[key][service_name]:
                        homebridge_json['service'] = service
                        for characteristic_properties in required_homebridge_config[key][service_name][service]:
                            if required_homebridge_config[key][service_name][service][characteristic_properties] != {}:
                                homebridge_json[characteristic_properties] = required_homebridge_config[key][service_name][service][characteristic_properties]
                            else:
                                homebridge_json[characteristic_properties] = 'default'
                    config_command = 'Adding '+ service_name + ' service to ' + key
                    print('Adding', service_name, 'service to', key, self.outgoing_add_service_mqtt_topic, homebridge_json)
                    ack_payload = {"ack": True, "message": "service_name '," + homebridge_json['service_name'] + "', service '" +  homebridge_json['service'] + "' is added."}
                    #print(ack_payload)
                    self.push_ack_cache({config_command: ack_payload})
                    client.publish(self.outgoing_add_service_mqtt_topic, json.dumps(homebridge_json))
                    homebridge_json = {}
                    homebridge_json['name'] = key
        
    def remove_additional_accessories_services(self, additional_accessories_services):
        print('Removing Additional Services')
        for accessory in additional_accessories_services:
            for key in accessory:
                for service_name in accessory[key]:
                    homebridge_json = {}
                    homebridge_json['name'] = key
                    homebridge_json['service_name'] = service_name
                    config_command = 'Removing '+ service_name + ' from ' + key
                    print('Removing', service_name, 'from', key, self.outgoing_remove_service_mqtt_topic, homebridge_json)
                    ack_payload = {"ack": True, "message": "accessory '" + homebridge_json["name"] + "', service_name '" + homebridge_json['service_name'] + "' is removed."}
                    #print(ack_payload)
                    self.push_ack_cache({config_command: ack_payload})
                    client.publish(self.outgoing_remove_service_mqtt_topic, json.dumps(homebridge_json))
        
    def fix_incorrect_accessories(self, incorrect_accessories_services, required_homebridge_config): ### Add ACK ###
        print('Fixing Incorrect Accessories')
        for accessory in incorrect_accessories_services:
            for key in accessory:
                for service_name in accessory[key]:
                    homebridge_json = {}
                    homebridge_json['name'] = key
                    homebridge_json['service_name'] = service_name
                    config_command = 'Removing '+ service_name + ' from ' + key
                    print('Removing', service_name, 'from', key, self.outgoing_remove_service_mqtt_topic, homebridge_json)
                    ack_payload = {"ack": True, "message": "accessory '" + homebridge_json["name"] + "', service_name '" + homebridge_json['service_name'] + "' is removed."}
                    #print(ack_payload)
                    self.push_ack_cache({config_command: ack_payload})
                    client.publish(self.outgoing_remove_service_mqtt_topic, json.dumps(homebridge_json))
                    time.sleep(0.5)
                    for service in required_homebridge_config[key][service_name]:
                        homebridge_json['service'] = service
                        for characteristic_properties in required_homebridge_config[key][service_name][service]:
                            if required_homebridge_config[key][service_name][service][characteristic_properties] != {}:
                                homebridge_json[characteristic_properties] = required_homebridge_config[key][service_name][service][characteristic_properties]
                            else:
                                homebridge_json[characteristic_properties] = 'default'
                    config_command = 'Adding '+ service_name + ' service to ' + key
                    print('Adding', service_name, 'service to', key, self.outgoing_add_service_mqtt_topic, homebridge_json)
                    ack_payload = {"ack": True, "message": "service_name '" + homebridge_json['service_name'] + "', service '" +  homebridge_json['service'] + "' is added."}
                    #print(ack_payload)
                    self.push_ack_cache({config_command: ack_payload})
                    client.publish(self.outgoing_add_service_mqtt_topic, json.dumps(homebridge_json))
                    homebridge_json = {}
                    homebridge_json['name'] = key
               
    def remove_excess_accessories(self, excess_accessories):
        print('Removing Excess Accessories')
        for accessory in excess_accessories:
            homebridge_json = {}
            homebridge_json['name'] = accessory
            config_command = 'Removing '+ accessory
            print('Removing', accessory, 'Accessory', self.outgoing_remove_accessory_mqtt_topic, homebridge_json)
            ack_payload = {"ack": True, "message": "accessory '" + homebridge_json["name"] + "' is removed."}
            #print(ack_payload)
            self.push_ack_cache({config_command: ack_payload})
            client.publish(self.outgoing_remove_accessory_mqtt_topic, json.dumps(homebridge_json))
        
    def capture_homebridge_buttons(self, parsed_json):
        #print('Homebridge Button', parsed_json)
        if self.dimmer_format['name'] in parsed_json['name']: # If it's a light dimmer button
            self.adjust_light_dimmer(parsed_json)
        elif self.blinds_format['name'] in parsed_json['name']: # If it's a blind button
            self.process_blind_button(parsed_json)
        elif self.doorbell_name_identifier in parsed_json['name']: # If it's a doorbell button
            self.process_doorbell_button(parsed_json)
        elif self.powerpoint_format['name'] in parsed_json['name']: # If it's a powerpoint button
            self.switch_powerpoint(parsed_json)
        elif parsed_json['name'] == self.garage_door_format['name']: # If it's a garage door button
            self.process_garage_door_button(parsed_json)
        elif self.air_purifier_format['name'] in parsed_json['name']: # If it's an air purifier button.
            self.process_air_purifier_button(parsed_json)
        elif parsed_json['name'] == self.reboot_format['name']: # If it's a reboot button.
            self.process_reboot_button(parsed_json)
        elif self.ev_charger_name_identifier in parsed_json['name']: # If it's a EV charger button.
            #print("Charger Button", parsed_json)
            self.process_ev_charger_button(parsed_json)
        else: # Test for aircon buttons and process if true
            identified_button = False
            for aircon_name in self.aircon_names:
                if aircon_name in parsed_json['name']: # If coming from an aircon
                    identified_button = True
                    self.process_aircon_button(parsed_json, aircon_name)
            if identified_button == False: # If parsed_json['name'] is unknown
                print ('Unknown homebridge button received', parsed_json['name'])
                
    def config_response(self, parsed_json):
        if "ack" in parsed_json:
            print("Ack Found")
            self.handle_acks(parsed_json)
        else:
            self.capture_config(parsed_json)
        
    def handle_acks(self, parsed_json):
        print('Homebridge Ack Received', parsed_json)
        command_found = False
        for ack in self.ack_cache:
            if self.ack_cache[ack] == parsed_json:
                print ('Command', ack, 'acknowledged')
                command_found = True
        if command_found:
            del self.ack_cache[ack]
        else:
            print("No command matches received ack", parsed_json)

    def push_ack_cache(self, command_ack):
        for key in command_ack:
            self.ack_cache[key] = command_ack[key]
        print(command_ack, 'added to ack_cache', self.ack_cache)
        
    def check_ack_cache(self):
        if self.ack_cache == {}:
            print('All config changes successful')
        else:
            for ack in self.ack_cache:
                print(ack, 'command unsuccessful')           
        
    def capture_config(self, parsed_json):
        #print("Capture Config", parsed_json)
        del parsed_json['request_id'] # Delete the Request ID
        current_config = {accessory: {service_name: {parsed_json[accessory]['services'][service_name]:
                                                     parsed_json[accessory]['properties'][service_name]}
                                      for service_name in parsed_json[accessory]['services']} for accessory in parsed_json}
        #print("Current Config", current_config)
        self.current_config = current_config

    def adjust_light_dimmer(self, parsed_json):
        # Determine which dimmer needs to be adjusted and call the relevant dimmer object method
        # that then calls the Domoticz method to adjust the dimmer brightness or state
        dimmer_name = parsed_json['name']
        if parsed_json['characteristic'] == 'Brightness':
            #print('Adjust Dimmer Brightness')
            brightness = int(parsed_json['value'])
            light_dimmer[dimmer_name].adjust_brightness(brightness)
        # Adjust dimmer state if a switch light state command has come from homebridge
        elif parsed_json['characteristic'] == 'On':
            light_state = parsed_json['value']
            light_dimmer[dimmer_name].on_off(light_state)
        # Adjust dimmer hue if a switch hue command has come from homebridge
        elif parsed_json['characteristic'] == 'Hue':
            hue_value = parsed_json['value']
            light_dimmer[dimmer_name].adjust_hue(hue_value)
        # Adjust dimmer saturation if a saturation command has come from homebridge
        elif parsed_json['characteristic'] == 'Saturation':
            saturation_value = parsed_json['value']
            light_dimmer[dimmer_name].adjust_saturation(saturation_value)
        else:
            # Print an error message if the homebridge dimmer message has an unknown characteristic
            print('Unknown dimmer characteristic received from ' + dimmer_name + ': ' + parsed_json['characteristic'] + ' Value: ', parsed_json['value'])
            pass

    def process_blind_button(self, parsed_json):
        #print('Homebridge: Process Blind Button', parsed_json)
        blind_name = parsed_json['name'] # Capture the blind's name
        # Set blind override status if it's a auto blind control override switch
        if parsed_json['service_name'] == 'Auto Blind Override':
            auto_override = parsed_json['value']
            window_blind[blind_name].change_auto_override(auto_override)
            mgr.auto_blind_override_changed = {'Changed': True, 'Blind': blind_name, 'State': auto_override}
        # Set blind high temp
        elif parsed_json['service_name'] == 'Blind High Temp' and parsed_json['characteristic'] == 'TargetTemperature':
            window_blind[blind_name].set_high_temp(parsed_json['value'])
        # Set blind low temp
        elif parsed_json['service_name'] == 'Blind Low Temp' and parsed_json['characteristic'] == 'TargetTemperature':
            window_blind[blind_name].set_low_temp(parsed_json['value'])
        # Set State to 'Cool' for Low Temp Button and 'Heat' for High Temp Button if an attempt is made to change the state through a button press
        elif (parsed_json['service_name'] == 'Blind High Temp' or parsed_json['service_name'] == 'Blind Low Temp') and parsed_json['characteristic'] == 'TargetHeatingCoolingState':
            time.sleep(0.1)
            self.update_blind_temp_states(blind_name)
        # Set blind position
        elif parsed_json['characteristic'] == 'TargetPosition':
            blind_id = parsed_json['service_name']
            # Convert blind position from a value to a string: 100 Open, 0 Closed, 50 Venetian
            blind_position = self.blind_incoming_position_map[parsed_json['value']]
            window_blind[blind_name].change_blind_position(blind_id, blind_position)
    # Ignore other buttons
        else:
            pass
            
    def process_doorbell_button(self, parsed_json):
        homebridge_json = {}
        #print('Homebridge: Process Doorbell Button', parsed_json)
        # Ignore the button press if it's only an indicator and reset to its pre-pressed state
        if self.doorbell_button_type[parsed_json['service_name']] == 'Indicator':
            #print('Indicator')
            time.sleep(1)
            homebridge_json['name'] = parsed_json['name']
            homebridge_json['characteristic'] = 'On'
            homebridge_json['service_name'] = parsed_json['service_name']
            homebridge_json['value'] = doorbell.status[parsed_json['service_name']]
            #print(self.outgoing_mqtt_topic, homebridge_json)
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))       
        # Send the doorbell button message to the doorbell if the button is a switch
        elif self.doorbell_button_type[parsed_json['service_name']] == 'Switch':
            doorbell.process_button(parsed_json['service_name'])
        # Send the doorbell button message to the doorbell and reset to the off position if the button is a momentary switch
        elif self.doorbell_button_type[parsed_json['service_name']] == 'Momentary':
            #print('Momentary')
            doorbell.process_button(parsed_json['service_name'])
            time.sleep(2)
            homebridge_json['name'] = parsed_json['name']
            homebridge_json['service_name'] = parsed_json['service_name']
            homebridge_json['characteristic'] = parsed_json['characteristic']
            homebridge_json['value'] = False # Prepare to return switch state to off
            # Publish homebridge payload with pre-pressed switch state
            #print(homebridge_json)
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        elif self.doorbell_button_type[parsed_json['service_name']] == 'Motion':
            #print ('Ringing')
            pass
        else:
            print('Unrecognised Doorbell Button Type')
            pass
        
    def process_ev_charger_button(self, parsed_json):
        homebridge_json = {}
        #print('Homebridge: Process EV Charger Button', parsed_json)
        # Ignore the button press if it's only an indicator and reset to its pre-pressed state
        if parsed_json['name'] == 'Charger State':
            #print('Charger State')
            time.sleep(1)
            homebridge_json['name'] = parsed_json['name']
            homebridge_json['characteristic'] = 'On'
            homebridge_json['service_name'] = parsed_json['service_name']
            homebridge_json['value'] = ev_charger.state[parsed_json['service_name']]
            #print(self.outgoing_mqtt_topic, homebridge_json)
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))       
        # Send the Reset Charger button message to the EV Charger and return the button to its pre-pressed state
        elif parsed_json['name'] == 'Reset Charger':
            #print('Reset Charger')
            ev_charger.process_ev_button(parsed_json['service_name'])
            time.sleep(2)
            homebridge_json['name'] = parsed_json['name']
            homebridge_json['service_name'] = parsed_json['service_name']
            homebridge_json['characteristic'] = parsed_json['characteristic']
            homebridge_json['value'] = False # Prepare to return switch state to off
            # Publish homebridge payload with pre-pressed switch state
            #print(homebridge_json)
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        elif parsed_json['name'] == 'Charger Control':
            #print('Lock/Unlock Charger')
            ev_charger.process_ev_button(parsed_json['service_name'])
        elif parsed_json['name'] == 'Charger ACK': #Indicator Only
            new_state = parsed_json['value']
            #print('Charger ACK')
            time.sleep(1)
            homebridge_json['name'] = parsed_json['name']
            homebridge_json['characteristic'] = 'On'
            homebridge_json['service_name'] = parsed_json['service_name']
            homebridge_json['value'] = not new_state
            #print(self.outgoing_mqtt_topic, homebridge_json)
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))     
        else:
            print('Unrecognised EV Charger Button Type')
            pass

    def process_garage_door_button(self, parsed_json):
        #print('Homebridge: Process Garage Door Button', parsed_json)
        if parsed_json['value'] == 0: # Open garage door if it's an open door command
            garage_door.open_garage_door(parsed_json)
        else: # Ignore any other commands and set homebridge garage door button to closed state
            homebridge_json = {}
            homebridge_json['value'] = 1
            characteristics = ('CurrentDoorState', 'TargetDoorState')
            for characteristic in characteristics:
                homebridge_json['characteristic'] = characteristic
                client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json)) # Close Current and Target Homebridge GarageDoor
 
    def process_aircon_button(self, parsed_json, aircon_name):
        #print('Homebridge: Process Aircon Button', parsed_json)
        # Ignore the button press if it's only an indicator and reset to its pre-pressed state
        if self.aircon_button_type[parsed_json['service_name']] == 'Indicator':
            time.sleep(0.5)
            homebridge_json = parsed_json
            homebridge_json['value'] = not parsed_json['value']
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        elif self.aircon_button_type[parsed_json['service_name']] == 'Thermostat Control':
            if parsed_json['characteristic'] == 'TargetHeatingCoolingState':
                control = 'Mode'
                # Set Thermostat mode if it's a mode message
                setting = self.aircon_thermostat_mode_map[parsed_json['value']]
            elif parsed_json['characteristic'] == 'TargetTemperature':
                control = 'Target Temperature'
                # Set the thermostat target temperature
                setting = parsed_json['value']
            else:
                control = 'Undefined Characteristic'
            if control != 'Undefined Characteristic':
                # Send thermostat control and setting to the aircon object
                thermostat_name = parsed_json['service_name'][len(aircon_name)+1:len(parsed_json['service_name'])]
                aircon[aircon_name].set_thermostat(thermostat_name, control, setting)
            else:
                print('Undefined aircon thermostat characteristic')
        elif self.aircon_button_type[parsed_json['service_name']] == 'Position Indicator':
            # If the damper position indicator has been pressed, reset it to the target position
            mgr.print_update('Trying to vary damper position on ')
            if parsed_json['characteristic'] == 'TargetPosition': # Don't let the Damper be varied manually
                time.sleep(0.1)
                homebridge_json = self.aircon_damper_format[aircon_name] 
                homebridge_json['characteristic'] = parsed_json['characteristic']
                homebridge_json['value'] = aircon[aircon_name].settings['target_day_zone']
                client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            else:
                pass
        elif self.aircon_button_type[parsed_json['service_name']] == 'Switch':
            if parsed_json['service_name'] == 'Ventilation':
                ventilation = parsed_json['value']
                #print('Ventilation Button Pressed')
                aircon[aircon_name].process_ventilation_button(ventilation)
            elif parsed_json['service_name'] == 'Reset Effectiveness Log':
                print('Reset', aircon_name, 'Effectiveness Log Pressed')
                aircon[aircon_name].reset_effectiveness_log()
                time.sleep(0.5)
                homebridge_json = parsed_json
                homebridge_json['value'] = False
                client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            else:
                print('Unknown Aircon Button Pressed', str(parsed_json))
        else:
            print("Unknown Aircon Homebridge Message", str(parsed_json))
            time.sleep(0.1)

    def process_air_purifier_button(self, parsed_json):
        #print('Air Purifier Button', parsed_json)
        purifier_name = parsed_json['service_name']
        characteristic = parsed_json['characteristic']
        value = parsed_json['value']
        if characteristic == 'Active':
            if value == 0:
                air_purifier[purifier_name].inactive()
        elif characteristic == 'TargetAirPurifierState':
            if value == 0:
                air_purifier[purifier_name].manual_mode()
            else:
                air_purifier[purifier_name].auto_mode()
        elif characteristic == 'RotationSpeed':
            if value == 0:
                air_purifier[purifier_name].set_fan_speed("0")
            elif value > 0 and value < 50:
                air_purifier[purifier_name].set_fan_speed("1")
            elif value >= 50 and value < 100:
                air_purifier[purifier_name].set_fan_speed("2")
            else:
                air_purifier[purifier_name].set_fan_speed("3")
        elif characteristic == 'LockPhysicalControls':
            if value == 0:
                lock = '0'
            else:
                lock = '1'
            air_purifier[purifier_name].set_child_lock(lock)
        elif characteristic == 'Brightness':
            if parsed_json['service_name'] == 'Living LED':
                purifier_name = 'Living'
            else:
                purifier_name = 'Main'
            if value == 0:
                air_purifier[purifier_name].set_led_brightness("0")
            elif value > 0 and value < 40:
                air_purifier[purifier_name].set_led_brightness("1")
            elif value >= 40 and value < 60:
                air_purifier[purifier_name].set_led_brightness("2")
            elif value >= 60 and value < 80:
                air_purifier[purifier_name].set_led_brightness("3")
            else:
                air_purifier[purifier_name].set_led_brightness("4")
        elif characteristic == 'On':
            if parsed_json['service_name'] == 'Living LED':
                purifier_name = 'Living'
            else:
                purifier_name = 'Main'
            if value == False:
                air_purifier[purifier_name].set_led_brightness("0")
            else:
                air_purifier[purifier_name].set_led_brightness("4")
        else:
            print('Unknown Air Purifier Button', characteristic)
        
    def process_reboot_button(self, parsed_json):
        if parsed_json['service_name'] == self.reboot_arm_format['service_name']:
            self.reboot_armed = parsed_json['value']
            if self.reboot_armed:
                mgr.print_update('Reboot Armed on ')
            else:
                mgr.print_update('Reboot Disarmed on ')
        if parsed_json['service_name'] == self.reboot_trigger_format['service_name']:
            if self.reboot_armed:
                mgr.print_update('Reboot Armed and Triggered on ')
                time.sleep(1)
                self.reset_reboot_button()
                time.sleep(1)
                mgr.shutdown('Reboot Button')
                time.sleep(2)
                os.system('sudo reboot')
            else:
                mgr.print_update('Reboot Trigger Command without arming received on ')
                time.sleep(1)
                self.reset_reboot_button()
                time.sleep(1)
        if parsed_json['service_name'] == self.restart_trigger_format['service_name']:
            if self.reboot_armed:
                mgr.print_update('Restart Armed and Triggered on ')
                time.sleep(1)
                self.reset_restart_button()
                time.sleep(1)
                mgr.shutdown('Restart Button')
                time.sleep(1)
                os.execv(mgr.home_manager_file_name, [''])
            else:
                mgr.print_update('Restart Trigger Command without arming received on ')
                time.sleep(1)
                self.reset_restart_button()
                time.sleep(1)

    def switch_powerpoint(self, parsed_json):
        powerpoint_name = parsed_json['service_name']
        switch_state = parsed_json['value']
        # Call the on_off method for the relevant powerpoint object
        powerpoint[powerpoint_name].on_off(switch_state)

    def update_temperature(self, name, temperature):
        homebridge_json = {}
        homebridge_json['service'] = self.temperature_format['service']
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
        
    def update_thermostat_current_temperature(self, name, temperature):
        found_thermostat = False
        homebridge_json = {}
        for aircon_name in self.aircon_config:
            if name in self.aircon_thermostat_names[aircon_name]:
                found_thermostat = True
                homebridge_json['name'] = aircon_name + ' ' + name
                homebridge_json['service'] = 'Thermostat'
        if found_thermostat:
            homebridge_json['characteristic'] = 'CurrentTemperature'
            # Set the service name to the thermostat name
            homebridge_json['service_name'] = aircon_name + ' ' + name
            homebridge_json['value'] = temperature
            # Update homebridge with the thermostat current temperature
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        else:
            print('Thermostat name not found', name)

    def update_humidity(self, name, humidity):
        homebridge_json = {}
        homebridge_json['service'] = self.humidity_format['service']
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
        homebridge_json = {}
        homebridge_json['service'] = self.light_level_format['service']
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
        homebridge_json['service'] = self.motion_format['service']
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
        homebridge_json['service'] = self.door_format['service']
        homebridge_json['characteristic'] = 'ContactSensorState'
        homebridge_json['service_name'] = door + self.door_format['name']
        homebridge_json['value'] = self.door_state_map['door_opened'][door_opened]
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
        homebridge_json['service'] = name + self.flood_state_format['service']
        homebridge_json['characteristic'] = 'LeakDetected'
        homebridge_json['service_name'] = name
        homebridge_json['value'] = flooding
        # Update homebridge with the current flood state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'StatusLowBattery'
        homebridge_json['value'] = low_battery
        # Update homebridge with the current flood sensor battery state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        
    def update_doorbell_status(self, parsed_json, status_item):
        homebridge_json = {}
        homebridge_json['name'] = self.doorbell_homebridge_json_name_map[status_item] # Map the homebridge_json['name'] to the service
        homebridge_json['service_name'] = status_item # Match homebridge service name with status item
        homebridge_json['value'] = parsed_json[status_item]
        if status_item != 'Ringing':
            homebridge_json['characteristic'] = 'On'    
            # Convert status bool states to strings for sending to homebridge
        else:
            homebridge_json['characteristic'] = 'MotionDetected' # Ringing uses a motion sensor on homebridge
        # Publish homebridge payload with updated doorbell status
        #print('Update Doorbell Status', homebridge_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_dimmer_state(self, name, dimmer_state):
        homebridge_json = {}
        homebridge_json['characteristic'] = 'On'
        homebridge_json['name'] = name
        homebridge_json['service_name'] = name
        homebridge_json['value'] = self.dimmer_state_map[dimmer_state]
        # Publish homebridge payload with updated dimmer state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_powerpoint_state(self, name, powerpoint_state):
        homebridge_json = {}
        homebridge_json['name'] = name + self.powerpoint_format['name']
        homebridge_json['service'] = self.powerpoint_format['service']
        homebridge_json['characteristic'] = 'On'
        homebridge_json['service_name'] = name
        homebridge_json['value'] = powerpoint_state
        # Publish homebridge payload with updated powerpoint state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_garage_door(self, state):
        #print('Homebridge: Update Garage Door', state)
        homebridge_json = self.garage_door_format
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
            print("Invalid Garage Door Status Message", service)
               
    def set_auto_blind_override_button(self, blind_room, state):
        #print('Homebridge: Reset Auto Blind Override Button', blind_room)
        homebridge_json = {}
        homebridge_json['name'] = blind_room
        homebridge_json['service'] = self.auto_blind_override_button_format['service']
        homebridge_json['service_name'] = self.auto_blind_override_button_format['service_name']
        homebridge_json['characteristic'] = 'On'                
        homebridge_json['value'] = state
        # Publish homebridge payload with button state off
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
                
    def update_blind_current_temps(self, blind_room, temp):
        homebridge_json = {}
        homebridge_json['name'] = blind_room
        homebridge_json['service'] = self.blinds_temp_format['service']
        # Set Current Temperature Levels on both High and Low Buttons
        homebridge_json['characteristic'] = 'CurrentTemperature'
        homebridge_json['value'] = temp
        homebridge_json['service_name'] = self.blinds_temp_format['high_temp_service_name']
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['service_name'] = self.blinds_temp_format['low_temp_service_name']
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        self.update_blind_temp_states(blind_room) # Set Thermostat to 'Cool' for Low Temp Button and 'Heat' for High Temp Button
        
    def update_blind_target_temps(self, blind_room, high_temp, low_temp):
        homebridge_json = {}
        homebridge_json['name'] = blind_room
        homebridge_json['service'] = self.blinds_temp_format['service']
        homebridge_json['characteristic'] = 'TargetTemperature'
        homebridge_json['value'] = high_temp
        homebridge_json['service_name'] = self.blinds_temp_format['high_temp_service_name']
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['value'] = low_temp
        homebridge_json['service_name'] = self.blinds_temp_format['low_temp_service_name']
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        self.update_blind_temp_states(blind_room) # Set Thermostat to 'Cool' for Low Temp Button and 'Heat' for High Temp Button
            
    def update_blind_temp_states(self, blind_room):
        # Sets Thermostat to 'Cool' for Low Temp Button and 'Heat' for High Temp Button
        homebridge_json = {}
        homebridge_json['name'] = blind_room
        homebridge_json['service'] = self.blinds_temp_format['service']
        homebridge_json['characteristic'] = 'TargetHeatingCoolingState'
        homebridge_json['service_name'] = self.blinds_temp_format['low_temp_service_name']
        homebridge_json['value'] = 2
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['service_name'] = self.blinds_temp_format['high_temp_service_name']
        homebridge_json['value'] = 1
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            
    def update_blind_status(self, blind_room, window_blind_config):
        homebridge_json = {}
        homebridge_json['name'] = blind_room
        homebridge_json['characteristic'] = 'TargetPosition'
        for blind in window_blind_config['status']:
            homebridge_json['service_name'] = blind
            homebridge_json['value'] = self.blind_outgoing_position_map[window_blind_config['status'][blind]]
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'CurrentPosition'
        for blind in window_blind_config['status']:
            homebridge_json['service_name'] = blind
            homebridge_json['value'] = self.blind_outgoing_position_map[window_blind_config['status'][blind]]
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'PositionState'
        for blind in window_blind_config['status']:
            homebridge_json['service_name'] = blind
            homebridge_json['value'] = 2
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_blind_position_state(self, blind_room, blind_id, command):
        homebridge_json = {}
        homebridge_json['name'] = blind_room
        homebridge_json['characteristic'] = 'PositionState'
        if command == 'stop':
            homebridge_json['value'] = 0
        elif command == 'up':
            homebridge_json['value'] = 1
        elif command == 'down':
            homebridge_json['value'] = 2
        else:
            homebridge_json['value'] = 0
        homebridge_json['service_name'] = blind_id
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            
    def reset_aircon_thermostats(self, aircon_name, thermostat_status): # Called on start-up to set all Homebridge sensors to same state as the aircon's thermostat statuses and Ventilation Button to 'Off'
        # Initialise Thermostat functions
        homebridge_json = {}
        for name in self.aircon_thermostat_names[aircon_name]:
            homebridge_json['name'] = aircon_name + ' ' + name
            homebridge_json['service_name'] = aircon_name + ' ' + name
            homebridge_json['characteristic'] = 'TargetHeatingCoolingState'
            homebridge_json['value'] = self.aircon_thermostat_incoming_mode_map[thermostat_status[name]['Mode']]
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['characteristic'] = 'CurrentHeatingCoolingState'
            homebridge_json['value'] = 0
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['characteristic'] = 'CurrentTemperature'
            homebridge_json['value'] = thermostat_status[name]['Current Temperature']
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['characteristic'] = 'TargetTemperature'
            homebridge_json['value'] = thermostat_status[name]['Target Temperature']
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        self.reset_aircon_ventilation_button(aircon_name)
            
    def reset_aircon_control_thermostat(self, aircon_name):
        homebridge_json = {}
        homebridge_json['name'] = aircon_name + ' ' + self.aircon_control_thermostat_name[aircon_name]
        homebridge_json['service_name'] = aircon_name + ' ' + self.aircon_control_thermostat_name[aircon_name]
        homebridge_json['characteristic'] = 'TargetHeatingCoolingState'
        homebridge_json['value'] = 0
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'CurrentHeatingCoolingState'
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def reset_aircon_ventilation_button(self, aircon_name):
        homebridge_json = {}
        homebridge_json['name'] = self.aircon_ventilation_button_format[aircon_name]['name']
        homebridge_json['service_name'] = self.aircon_ventilation_button_format[aircon_name]['service_name']
        homebridge_json['service'] = self.aircon_ventilation_button_format[aircon_name]['service']
        homebridge_json['characteristic'] = 'On'
        homebridge_json['value'] = False
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        
    def reset_reboot_button(self):
        homebridge_json = {}
        homebridge_json['name'] = self.reboot_format['name']
        homebridge_json['service_name'] = self.reboot_arm_format['service_name']
        homebridge_json['service'] = self.reboot_arm_format['service']
        homebridge_json['characteristic'] = 'On' 
        homebridge_json['value'] = False
        # Return reboot arm switch state to off
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['service_name'] = self.reboot_trigger_format['service_name']
        # Return reboot trigger state to off
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['service_name'] = self.restart_trigger_format['service_name']
        # Return restart trigger state to off
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
               
    def reset_restart_button(self):
        homebridge_json = {}
        homebridge_json['name'] = self.reboot_format['name']
        homebridge_json['service_name'] = self.reboot_arm_format['service_name']
        homebridge_json['service'] = self.reboot_arm_format['service']
        homebridge_json['characteristic'] = 'On'
        homebridge_json['value'] = False
        # Return reboot arm switch state to off
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['service_name'] = self.restart_trigger_format['service_name']
        homebridge_json['value'] = False
        # Return restart trigger state to off
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        
    def update_aircon_status(self, aircon_name, status_item, status, settings):
        homebridge_json = {}
        state = status[status_item]
        if status_item == 'Filter':
            homebridge_json['name'] = self.aircon_filter_indicator_format[aircon_name]['name']
        else:
            homebridge_json['name'] = self.aircon_status_format[aircon_name]['name']
        homebridge_json['service_name'] = status_item
        if status_item == 'Damper':
            homebridge_json['service'] = self.aircon_damper_format[aircon_name]['service']
            homebridge_json['characteristic'] = 'CurrentPosition'
            #print('Damper Day Zone is set to ' + str(state) + ' percent')
            if state == 100 or state == 0: # Update active thermostats' current heating cooling states if the damper is now either totally closed or totally opened
                if status['Heat']:
                    self.update_active_thermostat_current_states(aircon_name, 1, state)
                elif status['Cool']:
                    self.update_active_thermostat_current_states(aircon_name, 2, state)
                else:
                    self.update_active_thermostat_current_states(aircon_name, 0, state)
            homebridge_json['value'] = state
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json)) # Update relevant aircon damper position
            target_damper_position = settings['target_day_zone']
            homebridge_json['characteristic'] = 'PositionState'
            if state > target_damper_position:
                homebridge_json['value'] = 0
            elif state < target_damper_position:
                homebridge_json['value'] = 1
            else:
                homebridge_json['value'] = 2
            #print('Target Damper', target_damper_position, 'Current Damper', state, 'Value', homebridge_json['value'])
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json)) # Update relevant aircon damper position state
        else:
            homebridge_json['service'] = self.aircon_remote_operation_format[aircon_name]['service']
            homebridge_json['characteristic'] = 'On'
            homebridge_json['value'] = state
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json)) # Update relevant non-damper aircon status
        # Update Aircon Thermostats' current heating cooling states
        if ((status_item == 'Heat' and state and status['Compressor'] and status['Heating'] == False)
            or (status_item == 'Heating' and state == False and status['Heat'] and status['Compressor'])
            or (status_item == 'Compressor' and state == True and status['Heat'] and status['Heating'] == False)):
            self.update_control_thermostat_current_state(aircon_name, 1) # Active Heat
            self.update_active_thermostat_current_states(aircon_name, 1, status['Damper'])
        elif (status_item == 'Cool' and state and status['Compressor']) or (status_item == 'Compressor' and state and status['Cool']):
            self.update_control_thermostat_current_state(aircon_name, 2) # Active Cool
            self.update_active_thermostat_current_states(aircon_name, 2, status['Damper'])
        elif (status_item == 'Fan' and state or status_item == 'Remote Operation' and state == False
              or status_item == 'Compressor' and state == False or status_item == 'Heating' and state):
            self.update_control_thermostat_current_state(aircon_name, 0) # Not Heating or Cooling
            self.update_active_thermostat_current_states(aircon_name, 0, status['Damper'])
        else:
            pass         

    def update_control_thermostat_current_state(self, aircon_name, heating_cooling_state):
        homebridge_json = {}
        homebridge_json['name'] = aircon_name + ' ' + self.aircon_control_thermostat_name[aircon_name]
        homebridge_json['service_name'] = aircon_name + ' ' + self.aircon_control_thermostat_name[aircon_name]
        homebridge_json['characteristic'] = 'CurrentHeatingCoolingState'
        homebridge_json['value'] = heating_cooling_state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json)) # Update Control Thermostat

    def update_active_thermostat_current_states(self, aircon_name, heating_cooling_state, damper_position): # Called by 'update_aircon_status' method to set the active thermostats'
        # current heating cooling states when there is a possible change required to that state
        homebridge_json = {}
        homebridge_json['characteristic'] = 'CurrentHeatingCoolingState'
        for thermostat in aircon[aircon_name].indoor_zone: # Update active thermostats with current heating or cooling states unless the damp is 100% in the opposite zone. Update inactive thermostats if the state is 'off'
            self.update_individual_thermostat_current_state(aircon_name, thermostat, heating_cooling_state, damper_position) # Update each thermostat heating cooling state

    def update_individual_thermostat_current_state(self, aircon_name, thermostat, heating_cooling_state, damper_position): # Called by 'update_active_thermostat_current_states' and 'aircon.[aircon_name].set_thermostat'
        # methods to update one thermostat heating cooling state
        homebridge_json = {}
        homebridge_json['characteristic'] = 'CurrentHeatingCoolingState'
        if thermostat in aircon[aircon_name].day_zone: # Update active thermostat with current heating or cooling states unless the damp is 100% in the opposite zone. Update inactive thermostats if the state is 'off'
            if damper_position == 0: # Don't allow heating or cooling current states for day zone thermostats if the damper is wholly in the night position
                homebridge_json['value'] = 0
            else:
                homebridge_json['value'] = heating_cooling_state
        elif thermostat in aircon[aircon_name].night_zone:
            if damper_position == 100: # Don't allow heating or cooling current states for night zone thermostats if the damper is wholly in the day position
                homebridge_json['value'] = 0
            else:
                homebridge_json['value'] = heating_cooling_state
        else:
            print('Error: Thermostat', thermostat, 'not allocated to either a day zone or a night zone')
            homebridge_json['value'] = 0
        if aircon[aircon_name].thermostat_status[thermostat]['Active'] == 1 or homebridge_json['value'] == 0:
            homebridge_json['name'] = aircon_name + ' ' + thermostat
            homebridge_json['service_name'] = aircon_name + ' ' + thermostat
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))   

    def set_target_damper_position(self, aircon_name, damper_percent, position_state):
        homebridge_json = self.aircon_damper_format[aircon_name]
        homebridge_json['characteristic'] = 'TargetPosition'
        homebridge_json['value'] = damper_percent
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'PositionState'
        homebridge_json['value'] = self.aircon_damper_position_state_map[position_state]
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_aircon_thermostat(self, aircon_name, thermostat, mode):
        homebridge_json = {}
        homebridge_json['name'] = aircon_name + ' ' + thermostat
        homebridge_json['service_name'] = aircon_name + ' ' + thermostat
        homebridge_json['characteristic'] = 'TargetHeatingCoolingState'
        homebridge_json['value'] = self.aircon_thermostat_incoming_mode_map[mode]
        #print('Aircon Thermostat update', homebridge_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        
    def update_control_thermostat_temps(self, aircon_name, target_temp, current_temp):
        homebridge_json = {}
        homebridge_json['name'] = aircon_name + ' Master'
        homebridge_json['service_name'] = aircon_name + ' Master'
        homebridge_json['characteristic'] = 'TargetTemperature'
        homebridge_json['value'] = target_temp
        #print('Aircon Control Thermostat Target Temp update', homebridge_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'CurrentTemperature'
        homebridge_json['value'] = current_temp
        #print('Aircon Control Thermostat Current Temp update', homebridge_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        
    def update_thermostat_target_temp(self, aircon_name, thermostat, temp):
        homebridge_json = {}
        homebridge_json['name'] = aircon_name + ' ' + thermostat
        homebridge_json['service_name'] = aircon_name + ' ' + thermostat
        homebridge_json['characteristic'] = 'TargetTemperature'
        homebridge_json['value'] = temp
        #print('Update Aircon Thermostat Target Temp', homebridge_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_blueair_aqi(self, name, part_2_5, co2, voc, aqi, max_co2, co2_threshold, part_2_5_threshold):
        homebridge_json = {}
        homebridge_json['name'] = name + self.air_quality_format['name']
        homebridge_json['service_name'] = name + self.air_quality_format['service_name']
        homebridge_json['characteristic'] = 'AirQuality'
        homebridge_json['value'] = aqi
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'PM2_5Density' # Requires homebridge-mqtt >=0.6.2
        homebridge_json['value'] = part_2_5
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'VOCDensity'
        homebridge_json['value'] = voc
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['name'] = name + self.CO2_level_format['name']
        homebridge_json['service_name'] = name + self.CO2_level_format['service_name']
        homebridge_json['characteristic'] = 'CarbonDioxideLevel'
        homebridge_json['value'] = co2
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'CarbonDioxideDetected'
        if co2 < co2_threshold:
            homebridge_json['value'] = 0
        else:
            homebridge_json['value'] = 1
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'CarbonDioxidePeakLevel'
        homebridge_json['value'] = max_co2
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['name'] = name + self.PM2_5_alert_format['name']
        homebridge_json['service_name'] = name + self.PM2_5_alert_format['service_name']
        homebridge_json['characteristic'] = 'MotionDetected'
        if part_2_5 >= part_2_5_threshold:
            homebridge_json['value'] = True
        else:
            homebridge_json['value'] = False
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def set_air_purifier_state(self, name, mode, fan_speed, child_lock, led_brightness, filter_status):
        #print('Updating BlueAir Homebridge Settings', name, mode, fan_speed, child_lock, led_brightness, filter_status)
        homebridge_json = {}
        homebridge_json['name'] = name + self.air_purifier_format['name']
        homebridge_json['service_name'] = name
        homebridge_json['characteristic'] = 'CurrentAirPurifierState'
        if mode == 'auto' or fan_speed != '0':
            homebridge_json['value'] = 2
        else:
            homebridge_json['value'] = 0
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'Active'
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'RotationSpeed'
        if fan_speed == '3':
            speed = 100
        elif fan_speed == '2':
            speed = 75
        elif fan_speed == '1':
            speed = 25
        else:
            speed = 0
        homebridge_json['value'] = speed
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'TargetAirPurifierState'
        if mode == 'auto':
            homebridge_json['value'] = 1
        else:
            homebridge_json['value'] = 0
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'LockPhysicalControls'
        if child_lock == '1':
            homebridge_json['value'] = 1
        else:
            homebridge_json['value'] = 0
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['service'] = 'Lightbulb'
        homebridge_json['characteristic'] = 'Brightness'
        homebridge_json['service_name'] = name + ' LED'
        if led_brightness == '4':
            brightness = 100
        elif led_brightness == '3':
            brightness = 70
        elif led_brightness == '2':
            brightness = 50
        elif led_brightness == '1':
            brightness = 20
        else:
            brightness = 0
        homebridge_json['value'] = brightness
        #print('Setting Air Purifier LED Brightness', homebridge_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'On'
        if brightness == 0:
           homebridge_json['value'] = False
        else:
            homebridge_json['value'] = True
        #print('Setting Air Purifier LED State', homebridge_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['service_name'] = name + ' Filter'
        homebridge_json['service'] =' FilterMaintenance'
        homebridge_json['characteristic'] = 'FilterChangeIndication'
        if filter_status == 'OK':
            homebridge_json['value'] = 0
        else:
            homebridge_json['value'] = 1
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

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
        if enviro_config['Capture Temp/Hum/Bar/Lux']: # If there are Temp/Hum/Bar/Lux Readings
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
            homebridge_json['name'] = name + self.enviro_lux_format['name']
            homebridge_json['service_name'] = name + self.enviro_lux_format['service_name']
            homebridge_json['characteristic'] = 'CurrentAmbientLightLevel'
            light_level = parsed_json['Lux']
            if light_level < 0.0001:
                light_level = 0.0001 #HomeKit minValue is set to 0.0001 Lux
            homebridge_json['value'] = light_level
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            
    def update_ev_charger_state(self, state, locked_state):
        homebridge_json = {}
        homebridge_json['name'] = self.ev_charger_state_format['name']
        homebridge_json['characteristic'] = 'On'
        for item in state:
            homebridge_json['service_name'] = item # Match homebridge service name with status item
            homebridge_json['value'] = state[item]
            # Publish homebridge payload with updated EV Charger state
            #print('Update EV Status', homebridge_json)
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        if not state["Charging"]: # Clear "Reset Charger ACK" once charging has been completed
            homebridge_json['name'] = self.ev_charger_ack_format['name']
            homebridge_json['service_name'] = 'Reset'
            homebridge_json['value'] = False
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))          
        homebridge_json['name'] = self.ev_charger_control_format['name'] # Set Locked Button State
        homebridge_json['service_name'] = self.ev_charger_lock_format['service_name']
        if locked_state == True:
            homebridge_json['value'] = True
        else:
            homebridge_json['value'] = False
        #print(json.dumps(homebridge_json))
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['service_name'] = self.ev_charger_unlock_format['service_name'] # Set Unlocked Button State
        if locked_state == True:
            homebridge_json['value'] = False
        else:
            homebridge_json['value'] = True
        #print(json.dumps(homebridge_json))
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        
    def process_ev_charger_acks(self, parsed_json):
        homebridge_json = {}
        homebridge_json['name'] = self.ev_charger_ack_format['name']
        homebridge_json['characteristic'] = 'On'
        if parsed_json == 'Lock Outlet ACK':
            homebridge_json['service_name'] = 'Lock'
            homebridge_json['value'] = True
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['value'] = False
            homebridge_json['service_name'] = 'Unlock'
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['service_name'] = 'Reset'
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        elif parsed_json == 'Unlock Outlet ACK':
            homebridge_json['service_name'] = 'Unlock'
            homebridge_json['value'] = True
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['value'] = False
            homebridge_json['service_name'] = 'Lock'
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['service_name'] = 'Reset'
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        elif parsed_json == 'Reset Charger ACK':
            homebridge_json['service_name'] = 'Reset'
            homebridge_json['value'] = True
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['value'] = False
            homebridge_json['service_name'] = 'Lock'
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['service_name'] = 'Unlock'
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        elif parsed_json == 'Clear ACKs':
            homebridge_json['service_name'] = 'Reset'
            homebridge_json['value'] = False
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['service_name'] = 'Lock'
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            homebridge_json['service_name'] = 'Unlock'
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        else:
            pass
        
class DomoticzClass(object): # Manages communications to and from the z-wave objects
    def __init__(self):
        self.outgoing_mqtt_topic = 'domoticz/in'
        # Set up Domoticz label formats so that incoming message names can be decoded
        self.temperature_humidity_label = ' Climate'
        self.light_level_label = ' Light Level'
        self.motion_label = ' Motion'
        self.door_label = ' Door'
        self.dimmer_label = ' Dimmer'
        self.flood_label = ' Flooding'
        self.powerpoint_label = ' Powerpoint'
        self.aircon_names = ['Aircon']
        self.aircon_sensor_enable_label = {'Aircon': ' Aircon'}
        self.aircon_mode_label = {'Aircon': 'Aircon Mode'}
        self.aircon_mode_map = {'0': 'Off', '10': 'Heat', '20': 'Cool'}
        self.aircon_thermostat_label = ' Thermostat'
        self.aircon_sensor_names_idx = {'Aircon': {'Living': {'Active': 683, 'Temperature': 675}, 'Kitchen': {'Active': 684, 'Temperature': 678}, 'Study': {'Active': 685, 'Temperature': 679}, 'Main': {'Active': 686, 'Temperature': 680}, 'South': {'Active': 687, 'Temperature': 681}, 'North': {'Active': 688, 'Temperature': 682}}}
        self.aircon_sensor_enable_map = {'Off': 0, 'Heat': 1, 'Cool': 1}
        self.aircon_status_idx = {'Aircon': {'Mode':{'idx': 695, 'Off': '0', 'Fan': '10', 'Heat': '20', 'Cool': '30'}, 'Damper': 696}}
        self.aircon_mode = {'Aircon': {'idx': 693, 'Off': '0', 'Heat': '10', 'Cool': '20'}}
        # Set up dimmer domoticz message formats
        self.dimmer_brightness_format = {'command': 'switchlight', 'switchcmd': 'Set Level'}
        self.dimmer_switch_format = {'command': 'switchlight'}
        self.dimmer_hue_saturation_format = {'command': 'setcolbrightnessvalue'}
        # Map dimmer switch functions to translate True to On-switch/100-brightness and
        # False to Off-switch/0-brightness for domoticz_json
        self.dimmer_switch_map = {True:['On', 100], False:['Off', 0]}
        # Set up powerpoint domoticz message formats
        self.powerpoint_format = {'command': 'switchlight'}
        # Map powerpoint switch functions to translate True to On and False to Off for domoticz_json
        self.powerpoint_map = {True: 'On', False:'Off'}
        self.blueair_aqi_map = {'Living':{'part_2_5': 708, 'co2': 705, 'voc': 706, 'max_aqi': 707}}

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
        elif self.dimmer_label in sensor_name: # If it's a light dimmer
            light_dimmer[sensor_name[0:sensor_name.find(self.dimmer_label)]].process_dimmer_state_change(parsed_json)
        elif self.powerpoint_label in sensor_name: # If it's a powerpoint
            powerpoint[sensor_name[0:sensor_name.find(self.powerpoint_label)]].process_powerpoint_state_change(parsed_json)
        else: # Test for aircon buttons and process if true
            identified_label = False
            for aircon_name in self.aircon_names:
                if sensor_name == self.aircon_mode_label[aircon_name]: # If it's an aircon mode switch
                    self.process_aircon_mode_change(aircon_name, parsed_json)
                    identified_label = True
                else:
                    for sensor in self.aircon_sensor_names_idx[aircon_name]:
                        if sensor_name == sensor + self.aircon_sensor_enable_label[aircon_name]:
                            self.process_aircon_sensor_enable_change(aircon_name, parsed_json)
                            identified_label = True
                        elif sensor_name == sensor + self.aircon_thermostat_label:
                            self.process_aircon_thermostat(aircon_name, parsed_json)
                            identified_label = True
            if identified_label == False: # If parsed_json['name'] is unknown
                #print('Unknown Domoticz Sensor: ' + sensor_name)
                pass

    def set_dimmer_brightness(self, idx, brightness):
        # Publishes a dimmer brightness mqtt message to Domoticz when called by a light dimmer object
        domoticz_json = self.dimmer_brightness_format
        domoticz_json['idx'] = idx
        domoticz_json['level'] = brightness
        #print('Brightness Domoticz json', domoticz_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))

    def set_dimmer_state(self, idx, dimmer_state):
        # Publishes a dimmer state mqtt message to Domoticz when called by a light dimmer object
        domoticz_json = self.dimmer_switch_format
        domoticz_json['idx'] = idx
        domoticz_json['switchcmd'] = self.dimmer_switch_map[dimmer_state][0]
        domoticz_json['level'] = self.dimmer_switch_map[dimmer_state][1]
        #print('State Domoticz json', domoticz_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))

    def set_dimmer_hue_saturation(self, idx, hue_value, saturation_value, brightness):
        # Publishes a dimmer hue and saturation mqtt message to Domoticz when called by a light dimmer object
        domoticz_json = self.dimmer_hue_saturation_format
        domoticz_json['idx'] = idx
        domoticz_json['brightness'] = brightness
        c_value = brightness/100 * saturation_value/100
        x_value = c_value * (1-abs((hue_value/60) % 2 - 1))
        m_value = brightness/100 - c_value
        if (hue_value >= 0 and hue_value < 60):
            red_value = c_value
            green_value = x_value
            blue_value = 0
        elif (hue_value >= 60  and hue_value < 120):
            red_value = x_value
            green_value = c_value
            blue_value = 0
        elif (hue_value >= 120  and hue_value < 180):
            red_value = 0
            green_value = c_value
            blue_value = x_value
        elif (hue_value >= 180  and hue_value < 240):
            red_value = 0
            green_value = x_value
            blue_value = c_value
        elif (hue_value >= 240  and hue_value < 300):
            red_value = x_value
            green_value = 0
            blue_value = c_value
        elif (hue_value >= 300  and hue_value < 360):
            red_value = c_value
            green_value = 0
            blue_value = x_value
        else:
            pass
        red = (red_value + m_value) * 255
        green = (green_value + m_value) * 255
        blue = (blue_value + m_value) * 255
        domoticz_json['color'] = {'b': blue, 'g': green, 'cw': 0, 'ww': 0, 'r': red, 'm': 3, 't': 0}
        #print('Hue Domoticz json', domoticz_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))

    def switch_powerpoint(self, idx, powerpoint_state):
        # Publishes a powerpoint state mqtt message to Domoticz when called by a powerpoint object
        domoticz_json = self.powerpoint_format
        domoticz_json['idx'] = idx
        domoticz_json['switchcmd'] = self.powerpoint_map[powerpoint_state]
        client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))

    def reset_aircon_thermostats(self, aircon_name, thermostat_status): # Called on start-up and shutdown to reset all Domoticz aircon sensor and target temperature switches
        # Initialise Thermostat States
        domoticz_json = {}
        for sensor_name in self.aircon_sensor_names_idx[aircon_name]:
            domoticz_json['idx'] = self.aircon_sensor_names_idx[aircon_name][sensor_name]['Active']
            domoticz_json['nvalue'] = thermostat_status[sensor_name]['Active']
            client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))
            domoticz_json['idx'] = self.aircon_sensor_names_idx[aircon_name][sensor_name]['Temperature']
            domoticz_json['svalue'] = str(thermostat_status[sensor_name]['Target Temperature'])
            client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))

    def process_aircon_mode_change(self, aircon_name, parsed_json):
        print ('Domoticz: Process Aircon Mode Change', parsed_json)
        thermostat_name = aircon[aircon_name].control_thermostat
        control = 'Mode'
        setting = self.aircon_mode_map[parsed_json['svalue1']]
        aircon[aircon_name].set_thermostat(thermostat_name, control, setting)
        homebridge.update_aircon_thermostat(aircon_name, aircon[aircon_name].control_thermostat, setting) # Set Homebridge thermostat

    def process_aircon_sensor_enable_change(self, aircon_name, parsed_json):
        #print ('Domoticz: Process Aircon Sensor Enable Change', parsed_json)
        thermostat_name = parsed_json['name'][0:parsed_json['name'].find(self.aircon_sensor_enable_label[aircon_name])] # Remove aircon sensor enable label
        control = 'Mode'
        if parsed_json['nvalue'] == 1:
            setting = aircon[aircon_name].settings['indoor_thermo_mode'] # Set the same as the aircon's indoor_thermo_mode if it's active
        else:
            setting = 'Off'
        aircon[aircon_name].set_thermostat(thermostat_name, control, setting)
        homebridge.update_aircon_thermostat(aircon_name, thermostat_name, setting) # Set Homebridge thermostat
        
    def process_aircon_thermostat(self, aircon_name, parsed_json):
        #print ('Domoticz: Process Aircon Thermostat', parsed_json)
        thermostat_name = parsed_json['name'][0:parsed_json['name'].find(self.aircon_thermostat_label)] # Remove aircon thermostat label
        control = 'Target Temperature'
        temp = float(parsed_json['svalue1'])
        aircon[aircon_name].set_thermostat(thermostat_name, control, temp)
        homebridge.update_thermostat_target_temp(aircon_name, thermostat_name, temp) # Set Homebridge thermostat

    def update_aircon_status(self, aircon_name, status_item, state):
        #print ('Domoticz: Update Aircon Status', status_item, state)
        domoticz_json = {}
        publish = False
        if status_item == 'Damper':
            domoticz_json['idx'] = self.aircon_status_idx[aircon_name]['Damper']
            domoticz_json['nvalue'] = 0
            domoticz_json['svalue'] = str(state)
            publish = True
        else:
            domoticz_json['idx'] = self.aircon_status_idx[aircon_name]['Mode']['idx']
            if status_item == 'Remote Operation' and state == False:
                domoticz_json['svalue'] = self.aircon_status_idx[aircon_name]['Mode']['Off']
                publish = True
            elif status_item == 'Heat' and state:
                domoticz_json['svalue'] = self.aircon_status_idx[aircon_name]['Mode']['Heat']
                publish = True
            elif status_item == 'Cool' and state:
                domoticz_json['svalue'] = self.aircon_status_idx[aircon_name]['Mode']['Cool']
                publish = True
            elif status_item == 'Fan' and state:
                domoticz_json['svalue'] = self.aircon_status_idx[aircon_name]['Mode']['Fan']
                publish = True
        if publish:
            client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))

    def update_blueair_aqi(self, name, part_2_5, co2, voc, max_aqi):
        domoticz_json = {}
        if name in self.blueair_aqi_map:
            #print('Updating Domoticz Air Quality')
            domoticz_json['idx'] = self.blueair_aqi_map[name]['part_2_5']
            domoticz_json['nvalue'] = 0
            domoticz_json['svalue'] = str(round(part_2_5, 0))
            client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))
            domoticz_json['idx'] = self.blueair_aqi_map[name]['max_aqi']
            domoticz_json['svalue'] = str(max_aqi)
            client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))
            domoticz_json = {}
            domoticz_json['idx'] = self.blueair_aqi_map[name]['voc']
            domoticz_json['nvalue'] = voc
            client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))
            domoticz_json = {}
            domoticz_json['idx'] = self.blueair_aqi_map[name]['co2']
            domoticz_json['nvalue'] = co2
            client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))

    def update_aquarium(self, ph, temp, nh3):
        domoticz_json = {}
        print('Updating Domoticz Aquarium')
        domoticz_json['idx'] = 769
        domoticz_json['nvalue'] = 0
        domoticz_json['svalue'] = ph
        client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))
        domoticz_json['idx'] = 770
        domoticz_json['nvalue'] = 0
        domoticz_json['svalue'] = nh3
        client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))
        domoticz_json['idx'] = 772
        domoticz_json['nvalue'] = 0
        domoticz_json['svalue'] = temp
        client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))

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

class FloodSensorClass(object): 
    def __init__(self, name):        
        self.name = name
        #print ('Instantiated Flood Sensor', self, name)
        self.low_battery = False # Initial battery state is OK
        self.flood_state_map = {'Flood State':{0: 'No Flooding', 1: 'Flooding'},
                                       'Battery State':{0: 'normal', 1: 'low'}}

    def process_flood_state_change(self, parsed_json):
        #print(parsed_json)
        flood_value =  int(parsed_json['svalue1'])
        battery_value = int(parsed_json['Battery'])
        if flood_value == 255:
            self.flooding = 1 # Indicates that there is flooding
        else:
            self.flooding = 0 # Indicates that there is no flooding
        if battery_value < 20: # Check if the battery level is less than 20%
            self.low_battery = 1 # Battery low flag
        else:
            self.low_battery = 0 # Battery OK flag
        mgr.print_update("Updating Flood Detection for " + self.name + " Sensor to " + self.flood_state_map['Flood State'][self.flooding]
                         + ". Battery Level " + self.flood_state_map['Battery State'][self.low_battery] + " on ")
        # Update homebridge with the new flood state
        homebridge.update_flood_state(self.name, self.flooding, self.low_battery)

class DoorSensorClass(object): 
    def __init__(self, door, location, window_blind_config, doorbell_door):        
        self.door = door
        #print ('Instantiated Door Sensor', self, door)
        self.location = location
        self.window_blind_config = window_blind_config
        self.previous_door_opened = True # Assume the door is open upon instantiation
        self.current_door_opened = True # Initial door state is open
        self.low_battery = False # Initial battery state is OK
        self.door_state_changed = False
        self.doorbell_door = False
        # Map the door opened and battery states to strings for printouts
        self.door_state_map = {'door_opened':{False: 'closed', True: 'open'},
                                'low_battery':{False: 'normal', True: 'low'}}
        # Check the blind config dictionary to see if this door does control a blind
        self.blind_door = {'Blind Control': False, 'Blind Name': ''}
        for blind in self.window_blind_config:
            for door in self.window_blind_config[blind]['blind_doors']:
                if door == self.door:
                    # Flag that this door does control a blind, with the blind name, if it's found in a blind's configuration
                    self.blind_door = {'Blind Control': True, 'Blind Name': blind}
        if self.door == doorbell_door:
            # Flag that this door does control the doorbell, if it's found in the doorbell's configuration
            self.doorbell_door = True
        else:
            # Flag that this door doesn't control the doorbell, it's not found in the doorbell's configuration
            self.doorbell_door = False
        
    def process_door_state_change(self, parsed_json):
        door_opened_value =  int(parsed_json['svalue1'])
        battery_value = int(parsed_json['Battery'])
        #print('Door State Change', self.door)
        #print('door_opened_value', door_opened_value)
        #print('battery_value', battery_value)
        if door_opened_value == 255:
            self.current_door_opened = True # Indicates that the door is open
        else:
            self.current_door_opened = False # Indicates that the door is closed
        if battery_value < 20: # Check if the battery level is less than 20%
            self.low_battery = True # Battery low flag
        else:
            self.low_battery = False # Battery OK flag
        if self.current_door_opened != self.previous_door_opened: # If the door state has changed
            self.door_state_changed = True
            # Update homebridge with the new door state
            homebridge.update_door_state(self.door, self.location, self.current_door_opened, self.low_battery)
            # If it's a blind control door
            if self.blind_door['Blind Control']: # If it's a door that controls a blind
                # Flag current door state in window_blind_config so that sunlight blind adjustments can be made
                blind_name = self.blind_door['Blind Name']
                if self.current_door_opened:
                    door_state = 'Open'
                else:
                    door_state = 'Closed'
                window_blind[blind_name].window_blind_config['blind_doors'][self.door]['door_state'] = door_state
                window_blind[blind_name].window_blind_config['blind_doors'][self.door]['door_state_changed'] = self.door_state_changed
                #print('Window Blind Config for ', blind_name, window_blind[blind_name].window_blind_config[blind_name]['blind_doors'])
                # Trigger a blind change in the main mgr loop if a blind control door is opened
                mgr.blind_control_door_changed = {'State': self.current_door_opened, 'Blind': blind_name, 'Changed': self.door_state_changed}
                #print('Blind Control Door Opened', mgr.blind_control_door_changed)
            # Update Doorbell Door State if it's a doorbell door
            if self.doorbell_door:
                # Send change of door state to doorbell monitor
                doorbell.update_doorbell_door_state(self.door, self.current_door_opened)
            mgr.print_update("Updating Door Detection for " + self.door + " from " +
                              self.door_state_map['door_opened'][self.previous_door_opened] + " to " +
                              self.door_state_map['door_opened'][self.current_door_opened] +
                              ". Battery Level " + self.door_state_map['low_battery'][self.low_battery] + " on ")         
            self.previous_door_opened = self.current_door_opened
            self.door_state_changed = False
            mgr.log_key_states("Door State Change")
        
class MultisensorClass(object):
    def __init__(self, name, aircon_temp_sensor_names, aircon_sensor_name_aircon_map, window_blind_config, log_aircon_temp_data):
        self.name = name
        #print ('Instantiated Multisensor', self, name)
        # The dictionary that records the readings of each sensor object
        self.sensor_types_with_value = {'Temperature': 1, 'Humidity': 1, 'Motion': False, 'Light Level': 1}
        self.aircon_temp_sensor_names = aircon_temp_sensor_names
        self.aircon_sensor_name_aircon_map = aircon_sensor_name_aircon_map
        self.window_blind_config = window_blind_config
        self.log_aircon_temp_data = log_aircon_temp_data
        # Check the blind config dictionary to see if the light sensor in this multisensor does control a blind
        for blind in self.window_blind_config:
            if self.name == self.window_blind_config[blind]['light sensor']:
                # Flag that this sensor does control a blind, with the blind name, if it's found in a blind's configuration
                self.blind_sensor = {'Blind Control': True, 'Blind Name': blind}
            else:
                # Flag that this sensor doesn't control a blind, it's not found in any blind's configuration
                self.blind_sensor = {'Blind Control': False, 'Blind Name': ''}     

    # The method that records sensor temperature/humidity and updates homebridge current temperatures with those readings.
    # Also updates aircon zone temperatures, aircon temperature histories and homebridge aircon thermostats.
    def process_temperature_humidity(self, parsed_json):
        temperature = float(parsed_json['svalue1']) # Capture the sensor temperature reading
        # If aircon temp logging is enabled, update the temperature history for logging of aircon sensors - even if the temp hasn't changed
        if self.name in self.aircon_temp_sensor_names and self.log_aircon_temp_data:
            aircon_name = self.aircon_sensor_name_aircon_map[self.name]
            aircon[aircon_name].update_temp_history(self.name, temperature)
        # Only update homebridge current temperature record if the temp changes
        if temperature != self.sensor_types_with_value['Temperature']:
            # print('Updating Temperature for', self.name, 'sensor from',
                             #self.sensor_types_with_value['Temperature'], 'degrees to', str(temperature), 'degrees on ')
            self.sensor_types_with_value['Temperature'] = temperature # Update sensor object's temperature record
            homebridge.update_temperature(self.name, temperature)
            # Only update aircon thermostat current temperature readings if it's an indoor sensor
            if self.name in self.aircon_temp_sensor_names:
                homebridge.update_thermostat_current_temperature(self.name, temperature)
                aircon_name = self.aircon_sensor_name_aircon_map[self.name] # Find the aircon that manages this sensor
                # Update the aircon's current temperature record for this sensor
                aircon[aircon_name].thermostat_status[self.name]['Current Temperature'] = temperature
                # Update the "Day", "Night" and "Indoor" Zone current temperatures with new active temperature sensor readings
                aircon[aircon_name].update_zone_temps()
        humidity =  int(parsed_json['svalue2'])# Capture the sensor humidity reading
        if abs(humidity - self.sensor_types_with_value['Humidity']) >= 2: #Only update humidity record if difference is >= 2
            self.sensor_types_with_value['Humidity'] = humidity
            homebridge.update_humidity(self.name, humidity)
             
    # The method that records sensor light levels, updates homebridge light levels with those readings
    # and if the sensor is used to control blinds, invokes the adjust_blind method
    def process_light_level(self, parsed_json):
        light_level =  int(parsed_json['svalue1'])
        if abs(light_level - self.sensor_types_with_value['Light Level']) >= 2: #Only update if difference is >= 2
            self.sensor_types_with_value['Light Level'] = light_level
            homebridge.update_light_level(self.name, light_level)
            if self.blind_sensor['Blind Control']: # Check if this light sensor is used to control a window blind
                mgr.call_room_sunlight_control = {'State': True, 'Blind': self.blind_sensor['Blind Name'], 'Light Level': light_level}
                #print ('Triggered Blind Light Sensor', mgr.call_room_sunlight_control)            
        
    def process_motion(self, parsed_json):
        motion_value =  int(parsed_json['svalue1'])
        if motion_value == 255: # Convert motion sensor value to a bool state
            motion_detected = True
        else:
            motion_detected = False
        if motion_detected != self.sensor_types_with_value['Motion']: # Only update the state if it has changed
            self.sensor_types_with_value['Motion'] = motion_detected
            homebridge.update_motion(self.name, motion_detected)

class LightDimmerClass(object):
    def __init__(self, name, idx, dimmer_state, brightness):
        self.name = name
        #print ('Instantiated Light Dimmer', self, name)
        self.idx = idx
        self.dimmer_state = dimmer_state
        self.brightness = brightness
        self.hue_value = 0
        self.saturation_value = 0

    def adjust_brightness(self, brightness): # The method to adjust dimmer brightness
        if self.brightness != brightness: # If the dimmer brightness has changed
            self.brightness = brightness
            domoticz.set_dimmer_brightness(self.idx, self.brightness)
        
    def on_off(self, dimmer_state): # The method to turn dimmer on or off
        self.dimmer_state = dimmer_state
        domoticz.set_dimmer_state(self.idx, dimmer_state)

    def adjust_hue(self, hue_value):
        self.hue_value = hue_value
        domoticz.set_dimmer_hue_saturation(self.idx, self.hue_value, self.saturation_value, self.brightness)

    def adjust_saturation(self, saturation_value):
        self.saturation_value = saturation_value
        domoticz.set_dimmer_hue_saturation(self.idx, self.hue_value, self.saturation_value, self.brightness)

    def process_dimmer_state_change(self, parsed_json):
        # The method to capture a state change that is triggered by a change in the dimmer switch
        self.dimmer_state = parsed_json['nvalue']
        if self.dimmer_state < 2: # If the dimmer is switched on or off (ignore dim messages)
            homebridge.update_dimmer_state(self.name, self.dimmer_state)

class PowerpointClass(object):
    def __init__(self, name, idx, powerpoint_state):
        self.name = name
        #print ('Instantiated Powerpoint', self, name, idx)
        self.idx = idx
        self.powerpoint_state = powerpoint_state
        
    def on_off(self, powerpoint_state): # The method to turn a powerpoint on or off
        self.powerpoint_state = powerpoint_state
        domoticz.switch_powerpoint(self.idx, self.powerpoint_state)
        mgr.log_key_states("Powerpoint State Change")

    def process_powerpoint_state_change(self, parsed_json):
        # The method to capture a state change that is triggered by a change in the powerpoint switch
        self.powerpoint_state = parsed_json['nvalue']
        homebridge.update_powerpoint_state(self.name, self.powerpoint_state)
        mgr.log_key_states("Powerpoint State Change")

class GaragedoorClass(object):
    def __init__(self):
        #print ('Instantiated Garage Door', self)
        self.garage_door_mqtt_topic = 'GarageControl'  
        self.garage_door_state = 'Closed'
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
            #print_update('Received Heartbeat from Garage Door Opener and sending Ack on ')
            client.publish(self.garage_door_mqtt_topic, '{"service": "Heartbeat Ack"}')
        else:
            self.garage_door_state = parsed_json['service']
            homebridge.update_garage_door(self.garage_door_state)

class DoorbellClass(object):
    def __init__(self):
        #print ('Instantiated Doorbell', self)
        self.outgoing_mqtt_topic = 'DoorbellButton'
        # Set up Doorbell status dictionary with initial states set
        self.status = {'Terminated': False, 'Auto Possible': False, 'Triggered': False,
                        'Ringing': False, 'Idle': False, 'Automatic': False, 'Manual': False}
        
    def capture_doorbell_status(self, parsed_json):
        # Sync HomeManager's doorbell status and homebridge doorbell button settings with the doorbell
        # monitor status when an mqtt status update message is received from the doorbell monitor 
        #mgr.print_update('Doorbell Status update on ')
        #print(parsed_json)
        if parsed_json['service'] == 'Restart':
            mgr.print_update('Doorbell Restarted on ')
        elif parsed_json['service'] == 'Heartbeat':
            #mgr.print_update('Received Heartbeat from Doorbell and sending Ack on ')
            client.publish(self.outgoing_mqtt_topic, '{"service": "Heartbeat Ack"}')
        elif parsed_json['service'] == 'Status Update':
            mgr.print_update('Doorbell Status Update on ')
            for status_item in self.status:
                if self.status[status_item] != parsed_json[status_item]:
                    print('Doorbell', status_item, 'changed from', self.status[status_item], 'to', parsed_json[status_item])
                    self.status[status_item] = parsed_json[status_item]
                homebridge.update_doorbell_status(parsed_json, status_item) # Send update to homebridge
        else:
            print('Invalid Doorbell Status', parsed_json)

        
    def process_button(self, button_name):
        doorbell_json = {}
        doorbell_json['service'] = button_name
        # Send button message to the doorbell
        client.publish(self.outgoing_mqtt_topic, json.dumps(doorbell_json))
            
    def update_doorbell_status(self):
        doorbell_json = {}
        doorbell_json['service'] = 'Update Status'
        client.publish(self.outgoing_mqtt_topic, json.dumps(doorbell_json))
        
    def update_doorbell_door_state(self, door, door_opened):
        doorbell_json = {}
        doorbell_json['service'] = 'Door Status Change'
        if door_opened:
            doorbell_json['new_door_state'] = 1
        else:
            doorbell_json['new_door_state'] = 0
        doorbell_json['door'] = door + ' Door'
        #print('Update Doorbell Door State', doorbell_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(doorbell_json))   

class WindowBlindClass(object):
    def __init__(self, blind_room, window_blind_config):
        self.blind = blind_room
        #print ('Instantiated Window Blind', self, blind_room)
        self.window_blind_config = window_blind_config
        self.blind_host_name = self.window_blind_config['blind host name']
        self.blind_port = self.window_blind_config['blind port']
        self.blind_ip_address=socket.gethostbyname(self.blind_host_name)
        self.current_high_sunlight = 0 # Set initial sunlight level to 0
        self.blind_sunlight_position = 0 # Set initial sunlight position to 0
        self.previous_blind_temp_threshold = False
        self.call_control_blinds = False
        self.door_blind_override = False
        self.previous_high_sunlight = 0
        self.auto_override = False
        self.auto_override_changed = False
        self.previous_door_open = True
        self.non_sunny_season_sunlight_level_3_4_persist_time = self.window_blind_config['non_sunny_season_sunlight_level_3_4_persist_time']
        self.sunny_season_sunlight_level_3_4_persist_time = self.window_blind_config['sunny_season_sunlight_level_3_4_persist_time']
        self.sunlight_level_3_4_persist_time = 0
        self.last_sunlight_level_3_4_recording_time = time.time()
        self.sunlight_level_3_4_persist_time_previously_exceeded = False
                                                              
    def control_blinds(self, blind, blind_controls):
        mgr.print_update('Invoked Manual Blind Control on ')
        blind_id = blind_controls['Blind_id']
        blind_position = blind_controls['Blind_position']
        ignore_blind_command = False
        door_blind_override = False
        # Check if at least one door is open
        door_open = False
        for door in self.window_blind_config['blind_doors']:
            if self.window_blind_config['blind_doors'][door]['door_state'] == 'Open':
                door_open = True
        if blind_position == 'Open':
            print('Opening Blinds')
            self.move_blind(blind_id, 'up')
        elif blind_position == 'Closed':
            print('Closing Blinds')
            # If both doors are closed and it's a blind command that closes one or more door blinds
            if (door_open == False and (blind_id == 'Left Door' or blind_id == 'Right Door' or blind_id == 'All Doors' or blind_id == 'All Blinds')):
                print_update = self.close_door_impacting_blind(blind_id)
            elif blind_id == 'Left Window' or blind_id == 'Right Window' or blind_id == 'All Windows': # If it's a window command
                self.close_window_blind(blind_id)
            # If one door is open and it's a command that impacts the doors
            elif (door_open == True and (blind_id == 'Left Door' or blind_id == 'Right Door' or blind_id == 'All Doors' or blind_id == 'All Blinds')):
                door_blind_override = True # Flag that lowering of door blinds has been overridden
                if blind_id == 'All Blinds':
                    print('Trying to close all blinds when a door is open. Only closing window blinds')
                    revised_blind_id = 'All Windows' # Change All Blinds to All Windows so that door blinds stay open
                    self.close_window_blind(revised_blind_id)
                    self.window_blind_config['status'][revised_blind_id] = 'Closed'
                else: # Don't do anything if it's a Door Command
                    print('Trying to close door blinds when a door is open. Ignoring command')
                    ignore_blind_command = True
                    homebridge.update_blind_status(blind, self.window_blind_config)
            else:
                print('Unknown Blind Control Request. Blind Controls:', blind_controls, 'window_blind_config:', self.window_blind_config)
                pass # No other conditions
        elif blind_position == 'Venetian':
            print('Setting Blinds to Venetian')
            # If both doors are closed and it's a blind command that closes one or more door blinds
            if (door_open == False and (blind_id == 'Left Door' or blind_id == 'Right Door' or blind_id == 'All Doors' or blind_id == 'All Blinds')):
                blind_change = self.venetian_door_impacting_blind(blind_id)
            elif blind_id == 'Left Window' or blind_id == 'Right Window' or blind_id == 'All Windows': # If it's a window command
                self.move_blind(blind_id, 'down')
            # If one door is open and it's a command that impacts the doors
            elif (door_open == True and (blind_id == 'Left Door' or blind_id == 'Right Door' or blind_id == 'All Doors' or blind_id == 'All Blinds')):
                door_blind_override = True # Flag that lowering of door blinds has been overridden
                if blind_id == 'All Blinds':
                    revised_blind_id = 'All Windows' # Change All Blinds to All Windows so that door blinds stay open
                    self.move_blind(revised_blind_id, 'down')
                    self.window_blind_config['status'][blind_id] = 'Venetian'
                else: # Don't do anything if it's a Door Command
                    ignore_blind_command = True
                    homebridge.update_blind_status(blind, self.window_blind_config)                   
        else: # Ignore any other setting
            ignore_blind_command = True
            homebridge.update_blind_status(blind, self.window_blind_config)
        if ignore_blind_command == False:
            self.window_blind_config['status'][blind_id] = blind_position # Match window blind status with the blind's new position
            if blind_id == 'All Blinds' and door_blind_override == False: # Match individual blind status with that of 'All Blinds' if not overridden
                self.window_blind_config['status']['Left Window'] = blind_position
                self.window_blind_config['status']['Left Door'] = blind_position
                self.window_blind_config['status']['Right Door'] = blind_position
                self.window_blind_config['status']['Right Window'] = blind_position
                self.window_blind_config['status']['All Doors'] = blind_position
                self.window_blind_config['status']['All Windows'] = blind_position
            elif blind_id == 'All Blinds' and door_blind_override: # Match individual blind status for windows with that of 'All Blinds' and set door blinds 'Open' if overridden
                self.window_blind_config['status']['All Blinds'] = blind_position
                self.window_blind_config['status']['All Doors'] = 'Open'
                self.window_blind_config['status']['Left Door'] = 'Open'
                self.window_blind_config['status']['Right Door'] = 'Open'
                self.window_blind_config['status']['Left Window'] = blind_position
                self.window_blind_config['status']['Right Window'] = blind_position
                self.window_blind_config['status']['All Windows'] = blind_position         
            elif blind_id == 'All Windows':# Match individual window blind status with that of 'All Windows'
                self.window_blind_config['status']['Left Window'] = blind_position
                self.window_blind_config['status']['Right Window'] = blind_position
            elif blind_id == 'All Doors' and door_blind_override == False: # Match individual door blind status with that of 'All Doors' if not overridden
                self.window_blind_config['status']['Left Door'] = blind_position
                self.window_blind_config['status']['Right Door'] = blind_position
            elif blind_id == 'All Doors' and door_blind_override: # Set door blinds 'Open' if overridden
                self.window_blind_config['status']['All Blinds'] = 'Open'
                self.window_blind_config['status']['All Doors'] = 'Open'
                self.window_blind_config['status']['Left Door'] = 'Open'
                self.window_blind_config['status']['Right Door'] = 'Open'
            else:
                pass
            if door_blind_override:
                print('Changed blind command because a door is open')
            door_blind_override = False # Reset blind override flag
            homebridge.update_blind_status(blind, self.window_blind_config)
        else:
            print('Ignored door blind command because a door is open')
        mgr.log_key_states("Manual Blind State Change")

    def room_sunlight_control(self, light_level):
        # Called when there's a change in the blind's light sensor, doors or auto_override button
        current_temperature = multisensor[self.window_blind_config['temp sensor']].sensor_types_with_value['Temperature']
        sunny_season = self.check_season(self.window_blind_config['sunny_season_start'], self.window_blind_config['sunny_season_finish'])
        if sunny_season:
            self.sunlight_level_3_4_persist_time = self.sunny_season_sunlight_level_3_4_persist_time
        else:
            self.sunlight_level_3_4_persist_time = self.non_sunny_season_sunlight_level_3_4_persist_time
        if current_temperature != 1: # Wait for valid temp reading (1 is startup temp)
            #mgr.print_update('Blind Control invoked on ')
            # Has temp passed thresholds?
            temp_passed_threshold, current_blind_temp_threshold = self.check_outdoor_temperature(current_temperature,
                                                                                                  self.previous_blind_temp_threshold, 1)
            self.previous_blind_temp_threshold = current_blind_temp_threshold
            door_open, door_state_changed = self.check_door_state(self.previous_door_open)
            self.previous_door_open = door_open # Set new door state for the next time that self.check_door_state is called
            if light_level >= self.window_blind_config['sunlight threshold 3']: # If it's strong direct sunlight
                new_high_sunlight = 4
                self.last_sunlight_level_3_4_recording_time = time.time() # Set time when sunlight levels 3 or 4 were measured
                self.sunlight_level_3_4_persist_time_previously_exceeded = False # Reset flag that records that a falling sunlight level 2 blind change has been actioned
            elif (light_level >= self.window_blind_config['sunlight threshold 2'] and
                  light_level < self.window_blind_config['sunlight threshold 3']): # If it's medium direct sunlight
                new_high_sunlight = 3
                self.last_sunlight_level_3_4_recording_time = time.time() # Set time when sunlight levels 3 or 4 were measured
                self.sunlight_level_3_4_persist_time_previously_exceeded = False # Reset flag that records that a falling sunlight level 2 blind change has been actioned
            elif (light_level >= self.window_blind_config['sunlight threshold 1']
                  and light_level < self.window_blind_config['sunlight threshold 2']): # If it's strong indirect sunlight
                new_high_sunlight = 2
            elif (light_level < self.window_blind_config['sunlight threshold 1'] and
                  light_level > self.window_blind_config['sunlight threshold 0']): # If it's medium indirect sunlight
                new_high_sunlight = 1 # If it's low indirect sunlight
            else:
                new_high_sunlight = 0 # If it's night time
            #print('High Sunlight Levels checked')
            #print ('New Sensor Light Level Reading', light_level, 'Lux', 'Current High Sunlight Level:',
                   #self.current_high_sunlight, 'New High Sunlight Level:', new_high_sunlight,
                   #'Daylight?', light_level > self.window_blind_config['sunlight threshold 0'])
            sunlight_level_change = (new_high_sunlight != self.current_high_sunlight)
            if sunlight_level_change: # Capture the previous sunlight level if the sunlight level has changed
                self.previous_high_sunlight = self.current_high_sunlight # Used in Sunlight Levels 2 and 3 to determine is the sunlight level has increased or decreased
            auto_override_newly_disabled = (self.auto_override_changed == True and self.auto_override == False)
            sunlight_level_3_4_persist_time_now_exceeded = ((time.time() - self.last_sunlight_level_3_4_recording_time) >= self.sunlight_level_3_4_persist_time)
            trigger_falling_sunlight_level_2_blind_change = (new_high_sunlight == 2 and self.previous_high_sunlight > 2 and self.sunlight_level_3_4_persist_time_previously_exceeded == False and
                                                                    sunlight_level_3_4_persist_time_now_exceeded)
            if (sunlight_level_change or door_state_changed or temp_passed_threshold or auto_override_newly_disabled or trigger_falling_sunlight_level_2_blind_change): # Has there been a blind-affecting change?
                mgr.print_update ('Blind change algorithm triggered on ')
                print('Sunlight Level Change:', sunlight_level_change, 'Door State Changed:', door_state_changed, 'Temp Passed Threshold:',
                       temp_passed_threshold, 'Auto Override Newly Disabled:', auto_override_newly_disabled, 'Trigger Falling Sunlight Level 2 Blind Change:', trigger_falling_sunlight_level_2_blind_change)
                print_blind_change = False
                if new_high_sunlight == 4:
                    print_blind_change, self.blind_sunlight_position = self.set_blind_sunlight_4(door_open, door_state_changed, self.auto_override, sunny_season, self.blind_sunlight_position, self.auto_override_changed)
                elif new_high_sunlight == 3:
                    print_blind_change, self.blind_sunlight_position = self.set_blind_sunlight_3(door_open, door_state_changed, self.previous_high_sunlight, self.auto_override, sunny_season, self.blind_sunlight_position,
                                                                                                  self.auto_override_changed)           
                elif new_high_sunlight == 2:
                    print_blind_change, self.sunlight_level_3_4_persist_time_previously_exceeded, self.blind_sunlight_position = self.set_blind_sunlight_2(door_open, door_state_changed, self.previous_high_sunlight,
                                                                                                                                                            self.auto_override, current_blind_temp_threshold, temp_passed_threshold,
                                                                                                                                                            current_temperature, sunny_season, self.last_sunlight_level_3_4_recording_time,
                                                                                                                                                            self.sunlight_level_3_4_persist_time, self.blind_sunlight_position, self.auto_override_changed)    
                elif new_high_sunlight == 1:
                    print_blind_change, self.blind_sunlight_position = self.set_blind_sunlight_1(door_open, door_state_changed, self.auto_override, current_blind_temp_threshold, temp_passed_threshold, current_temperature,
                                                                                                  self.blind_sunlight_position, self.auto_override_changed)                                                                                     
                elif new_high_sunlight == 0:
                    print_blind_change, self.blind_sunlight_position = self.set_blind_sunlight_0(door_open, door_state_changed, self.auto_override, self.blind_sunlight_position, self.auto_override_changed)
                else:
                    pass # Invalid sunlight level              
                if print_blind_change: # If there's a change in blind position
                    mgr.print_update('Blind State Change on ')
                    if new_high_sunlight != self.current_high_sunlight: # If there's a blind position change due to sun protection state
                        print("High Sunlight Level was:", self.current_high_sunlight, "It's Now Level:", new_high_sunlight, "with a light reading of", light_level, "Lux")
                    if door_state_changed: # If a change in door states, reset door state changed flags and print blind update due to door state change
                        for door in self.window_blind_config['blind_doors']: # Reset all door state changed flags
                            self.window_blind_config['blind_doors'][door]['door_state_changed'] = False
                        if door_open == False:
                            print('Blinds were adjusted due to door closure')
                        else:
                            print('Blinds were adjusted due to door opening')
                    if temp_passed_threshold:
                        if current_blind_temp_threshold == False:
                            print('Blinds adjusted due to the outdoor temperature moving inside the defined range')
                        else:
                            print('Blinds adjusted due to an outdoor temperature moving outside the defined range')
                        print('Current Temp is', current_temperature,  'degrees. Low Temp Threshold is', self.window_blind_config['low_temp_threshold'],
                              'degrees. High Temp Threshold is', self.window_blind_config['high_temp_threshold'], 'degrees')
                    if self.auto_override_changed:
                        self.auto_override_changed = False # Reset auto blind override flag 
                        if self.auto_override == False:
                           print('Blinds adjusted due to auto_override being switched off')
                    if trigger_falling_sunlight_level_2_blind_change:
                        print('Blinds Adjusted due to sunlight level falling to Level 2 and the Levels 3/4 persist time of', round(self.sunlight_level_3_4_persist_time/60,0),'minutes was exceeded')
                else: # No blind change, just a threshold change in the blind hysteresis gaps
                    #print("High Sunlight Level Now", new_high_sunlight, "with a light reading of", light_level, "Lux and no change of blind position")
                    pass
                self.current_high_sunlight = new_high_sunlight # Update sunlight threshold status with the latest reading to determine if there's a sunlight level change required at the next sunlight reading
                homebridge.update_blind_status(self.blind, self.window_blind_config) # Update blind status
                mgr.log_key_states("Sunlight Blind State Change") # Log change in blind states
            else: # Nothing changed that affects blind states
                #print('Blind Status Unchanged')
                pass

    def check_season(self, sunny_season_start, sunny_season_finish): # Determines whether or not the sunny season blind settings are invoked
        # Allows for two seasonal blind settings
        now = datetime.now()
        month = now.month
        if month >= sunny_season_start or month <= sunny_season_finish:
            sunny_season = True
        else:
            sunny_season = False
        return sunny_season

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
        else: # If the temp was previously outside the blind temp threshold.
            if (current_temperature <= (self.window_blind_config['high_temp_threshold'] - hysteresis_gap)
                and current_temperature >= (self.window_blind_config['low_temp_threshold'] + hysteresis_gap)):
                temp_passed_threshold = True
                current_blind_temp_threshold = False
            else: # Set that it hasn't jumped the thresholds
                temp_passed_threshold = False
                current_blind_temp_threshold = True
        #print('Outdoor Temperature checked')
        #print('Current temperature is', current_temperature, 'degrees.', 'Previously External Temp Thresholds?',
               #previous_blind_temp_threshold, 'Currently Outside Temp Thresholds?', current_blind_temp_threshold,
               #'Temp Moved Inside or Outside Thresholds?', temp_passed_threshold)
        return(temp_passed_threshold, current_blind_temp_threshold)

    def check_door_state(self, previous_door_open):
        all_doors_closed = True
        one_door_has_opened = False
        a_door_state_has_changed = False
        blind_door_state_changed = False
        for door in self.window_blind_config['blind_doors']:
            if self.window_blind_config['blind_doors'][door]['door_state'] == 'Open':
                all_doors_closed = False
                if self.window_blind_config['blind_doors'][door]['door_state_changed']:
                    one_door_has_opened = True
            if self.window_blind_config['blind_doors'][door]['door_state_changed']:
                a_door_state_has_changed = True    
        if one_door_has_opened == True and previous_door_open == False: # One door has now been opened when all doors were previously closed
            door_state_changed = True
            door_open = True
        elif all_doors_closed == True and a_door_state_has_changed: # All doors are now closed
            door_state_changed = True
            door_open = False
        else: # Ignore states when not all doors have been closed or a door has already been opened
            door_state_changed = False
            door_open = not all_doors_closed
            pass
        #print('Door State checked')
        #print ('Door State Changed?', door_state_changed, 'Any Doors Open?', door_open)
        return(door_open, door_state_changed)

    def set_blind_sunlight_4(self, door_open, door_state_changed, auto_override, sunny_season, blind_sunlight_position, auto_override_changed):
        print('High Sunlight Level 4 Invoked with Sunny Season', sunny_season)
        print_blind_change = False
        if auto_override == False:
            if sunny_season:
                if door_open == False:
                    if blind_sunlight_position != 4: # Set blinds to sunlight level 4 state if not already invoked
                        # Set right window blind to Venetian, close doors and left blind if both doors closed
                        print_blind_change = self.all_blinds_venetian()
                        self.move_blind('Left Window', 'up') # Raise left window blind for 0.5 seconds
                        time.sleep(0.495)
                        self.move_blind('Left Window', 'stop') # Stop left window blind
                        self.move_blind('All Doors', 'up') # Raise all door blinds for 0.5 seconds
                        time.sleep(0.495)
                        self.move_blind('All Doors', 'stop') # Stop all door blinds
                        # Set blind status to align with blind position
                        self.window_blind_config['status']['Left Window'] = 'Closed'
                        self.window_blind_config['status']['Right Window'] = 'Venetian'
                        self.window_blind_config['status']['All Windows'] = 'Closed'
                        self.window_blind_config['status']['All Doors'] = 'Closed'
                        self.window_blind_config['status']['Left Door'] = 'Closed'
                        self.window_blind_config['status']['Right Door'] = 'Closed'
                        self.window_blind_config['status']['All Blinds'] = 'Closed'
                    if door_state_changed: # Close door blinds when doors have been closed while in this sunlight state
                        print_blind_change = self.close_door_impacting_blind('All Doors')
                        self.window_blind_config['status']['All Doors'] = 'Closed'
                        self.window_blind_config['status']['Left Door'] = 'Closed'
                        self.window_blind_config['status']['Right Door'] = 'Closed'
                else: # If at least one door is open
                    self.move_blind('All Doors', 'up') # Raise all door blinds
                    # Set blind status to align with blind position
                    self.window_blind_config['status']['All Doors'] = 'Open'
                    self.window_blind_config['status']['Left Door'] = 'Open'
                    self.window_blind_config['status']['Right Door'] = 'Open'
                    print_blind_change = True
                    if blind_sunlight_position != 4: # Set window blinds to sunlight level 4 if it hasn't already been invoked
                        self.move_blind('All Windows', 'down')
                        time.sleep(25)
                        self.move_blind('Left Window', 'up')
                        time.sleep(0.495)
                        self.move_blind('Left Window', 'stop')
                        # Set blind status to align with blind position
                        self.window_blind_config['status']['Left Window'] = 'Closed'
                        self.window_blind_config['status']['Right Window'] = 'Venetian'
                        self.window_blind_config['status']['All Windows'] = 'Closed'
                        self.window_blind_config['status']['All Doors'] = 'Closed'
                        self.window_blind_config['status']['Left Door'] = 'Closed'
                        self.window_blind_config['status']['Right Door'] = 'Closed'
                        self.window_blind_config['status']['All Blinds'] = 'Closed'
            else: # If not sunny_season
                if self.blind_sunlight_position != 4: # Set blinds to sunlight level 4 (Left Window venetian when not sunny season) if not already invoked
                    self.move_blind('Left Window', 'down') # Set left window to venetian
                    self.window_blind_config['status']['Left Window'] = 'Venetian'
                    self.window_blind_config['status']['All Windows'] = 'Venetian'
                    self.window_blind_config['status']['All Blinds'] = 'Venetian'
                    print_blind_change = True
                if door_open: # Raise all door blinds if a door is open. Caters for the case when a door blind has been manually closed when in sunlight level 4.
                    self.move_blind('All Doors', 'up')
                    # Set blind status to align with blind position
                    self.window_blind_config['status']['All Doors'] = 'Open'
                    self.window_blind_config['status']['Left Door'] = 'Open'
                    self.window_blind_config['status']['Right Door'] = 'Open'
                    print_blind_change = True           
            blind_sunlight_position = 4
            if auto_override_changed:
                print_blind_change = True
        else:
            #print('No Blind Change. Auto Blind Control is overridden')
            pass
        return(print_blind_change, blind_sunlight_position)

    def set_blind_sunlight_3(self, door_open, door_state_changed, previous_high_sunlight, auto_override, sunny_season, blind_sunlight_position, auto_override_changed):
        print('High Sunlight Level 3 Invoked with Sunny Season', sunny_season)
        print_blind_change = False
        if auto_override == False:
            if sunny_season:
                if previous_high_sunlight < 3: # If this level has been reached after being in levels 0, 1 or 2
                    if door_open == False: # If both doors closed, all blinds to Venetian
                        if blind_sunlight_position < 3 and door_state_changed == False: # Set all blinds to Venetian if blinds are not aleady in positions 3 or 4
                            print_blind_change = self.all_blinds_venetian()
                            blind_sunlight_position = 3
                        if door_state_changed:
                            if blind_sunlight_position <= 3: # Set door blinds to Venetian if doors have just been closed while in sunlight position 3 or lower
                                print_blind_change = self.venetian_door_impacting_blind('All Doors')
                                self.window_blind_config['status']['All Doors'] = 'Venetian'
                                self.window_blind_config['status']['Left Door'] = 'Venetian'
                                self.window_blind_config['status']['Right Door'] = 'Venetian'
                            else: # Close door blinds if doors have just been closed while in sunlight position 4
                                print_blind_change = self.close_door_impacting_blind('All Doors')
                                self.window_blind_config['status']['All Doors'] = 'Closed'
                                self.window_blind_config['status']['Left Door'] = 'Closed'
                                self.window_blind_config['status']['Right Door'] = 'Closed'
                    else: # Open door blinds if least one door is open 
                        self.move_blind('All Doors', 'up')
                        self.window_blind_config['status']['All Doors'] = 'Open'
                        self.window_blind_config['status']['Left Door'] = 'Open'
                        self.window_blind_config['status']['Right Door'] = 'Open'
                        print_blind_change = True
                        if blind_sunlight_position < 3: # Set window blinds to venetian if blinds are not already in positions 3 or 4
                            self.move_blind('All Windows', 'down')
                            self.window_blind_config['status']['All Windows'] = 'Venetian'
                            self.window_blind_config['status']['Left Window'] = 'Venetian'
                            self.window_blind_config['status']['Right Window'] = 'Venetian'
                            self.window_blind_config['status']['All Blinds'] = 'Venetian'
                            print_blind_change = True
                            blind_sunlight_position = 3
                else: # If this level has been reached after being in level 4
                    if door_state_changed: # If the door state has changed
                        if door_open == False: # Close door blinds if both doors are closed
                            print_blind_change = self.close_door_impacting_blind('All Doors')
                            self.window_blind_config['status']['All Doors'] = 'Closed'
                            self.window_blind_config['status']['Left Door'] = 'Closed'
                            self.window_blind_config['status']['Right Door'] = 'Closed'
                        else: # Open door blinds if the doors have been opened 
                            self.move_blind('All Doors', 'up')
                            print_blind_change = True
                            # Set blind status
                            self.window_blind_config['status']['All Doors'] = 'Open'
                            self.window_blind_config['status']['Left Door'] = 'Open'
                            self.window_blind_config['status']['Right Door'] = 'Open'
                    else: # Do nothing if there has been no change to the door state
                        pass
            else: # Ensure that door blinds are open when a door is opened and it's not in the sunny season
                if door_open: # If one of the doors is now open
                    self.move_blind('All Doors', 'up')
                    print_blind_change = True
                    # Set blind status
                    self.window_blind_config['status']['All Doors'] = 'Open'
                    self.window_blind_config['status']['Left Door'] = 'Open'
                    self.window_blind_config['status']['Right Door'] = 'Open'
            if auto_override_changed:
                print_blind_change = True
        else:
            #print('No Blind Change. Auto Blind Control is overridden')
            pass
        return(print_blind_change, blind_sunlight_position)

    def set_blind_sunlight_2(self, door_open, door_state_changed, previous_high_sunlight, auto_override, current_blind_temp_threshold, temp_passed_threshold, current_temperature, sunny_season, last_sunlight_level_3_4_recording_time,
                              sunlight_level_3_4_persist_time, blind_sunlight_position, auto_override_changed):
        print('High Sunlight Level 2 Invoked with Sunny Season', sunny_season)
        print_blind_change = False
        sunlight_level_3_4_persist_time_exceeded = (time.time() - last_sunlight_level_3_4_recording_time > sunlight_level_3_4_persist_time)
        if auto_override == False:
            if previous_high_sunlight < 2: # If this level has been reached after being in levels 0 or 1, only change blind setting if there has been a relevant change in outdoor temperatures
                if current_blind_temp_threshold == True and door_open == False: # Set blinds to Venetian if the outdoor temperature is outside the pre-set thresholds and doors are closed
                    print_blind_change = self.all_blinds_venetian()
                else: # Open all blinds if the outdoor temperature is now within the pre-set thresholds or a door is open
                    print_blind_change = self.raise_all_blinds()
                blind_sunlight_position = 2
            else: # If this level has been reached after being in levels 3 or 4
                if sunny_season:
                    # Set all blinds to venetian state if both doors are closed with no change in state and the persist has been exceeded
                    if door_open == False and door_state_changed == False and sunlight_level_3_4_persist_time_exceeded:
                        print_blind_change = self.all_blinds_venetian()
                        blind_sunlight_position = 2
                    # Set door blinds to venetian if a door has just been closed and the persist has been exceeded
                    elif door_open == False and door_state_changed == True and sunlight_level_3_4_persist_time_exceeded:
                        print_blind_change = self.venetian_door_impacting_blind('All Doors')
                        self.window_blind_config['status']['All Doors'] = 'Venetian'
                        self.window_blind_config['status']['Left Door'] = 'Venetian'
                        self.window_blind_config['status']['Right Door'] = 'Venetian'
                        blind_sunlight_position = 2
                    # Close door blinds if a door has just been closed and the persist has not been exceeded
                    elif door_open == False and door_state_changed == True and not sunlight_level_3_4_persist_time_exceeded:
                        if previous_high_sunlight == 4:
                            print_blind_change = self.close_door_impacting_blind('All Doors')
                            self.window_blind_config['status']['All Doors'] = 'Closed'
                            self.window_blind_config['status']['Left Door'] = 'Closed'
                            self.window_blind_config['status']['Right Door'] = 'Closed'
                        else: # previous_high_sunlight == 3
                            print_blind_change = self.venetian_door_impacting_blind('All Doors')
                            self.window_blind_config['status']['All Doors'] = 'Venetian'
                            self.window_blind_config['status']['Left Door'] = 'Venetian'
                            self.window_blind_config['status']['Right Door'] = 'Venetian'
                    # Set window blinds to venetian state if at least one door is open and the persist has been exceeded   
                    elif door_open == True and sunlight_level_3_4_persist_time_exceeded:
                        self.move_blind('All Windows', 'down')
                        self.window_blind_config['status']['All Windows'] = 'Venetian'
                        self.window_blind_config['status']['Left Window'] = 'Venetian'
                        self.window_blind_config['status']['Right Window'] = 'Venetian'
                        self.move_blind('All Doors', 'up')
                        self.window_blind_config['status']['All Doors'] = 'Open'
                        self.window_blind_config['status']['Left Door'] = 'Open'
                        self.window_blind_config['status']['Right Door'] = 'Open'
                        print_blind_change = True
                        blind_sunlight_position = 2
                    # Open door blinds if a door has just been opened, even if the persist has not been exceeded
                    elif door_open == True and door_state_changed:
                        self.move_blind('All Doors', 'up')
                        self.window_blind_config['status']['All Doors'] = 'Open'
                        self.window_blind_config['status']['Left Door'] = 'Open'
                        self.window_blind_config['status']['Right Door'] = 'Open'
                        print_blind_change = True
                    else:
                        pass # Do nothing in other situations
                else: # Not in Sunny Season
                    if sunlight_level_3_4_persist_time_exceeded: # Open all blinds if a level 3 or level 4 sunlight level was recorded earlier than the persist time
                        print_blind_change = self.raise_all_blinds()
                        blind_sunlight_position = 2
                    else: # Ensure door blinds are raised if a door has been opened, even though the persist time has not been exceeded. Caters for manual door blind closure cases.
                        if door_open == True and door_state_changed:
                            self.move_blind('All Doors', 'up')
                            self.window_blind_config['status']['All Doors'] = 'Open'
                            self.window_blind_config['status']['Left Door'] = 'Open'
                            self.window_blind_config['status']['Right Door'] = 'Open'
                            print_blind_change = True
            if auto_override_changed:
                print_blind_change = True
        else:
            #print('No Blind Change. Auto Blind Control is overridden')
            pass
        return(print_blind_change, sunlight_level_3_4_persist_time_exceeded, blind_sunlight_position)

    def set_blind_sunlight_1(self, door_open, door_state_changed, auto_override, current_blind_temp_threshold, temp_passed_threshold, current_temperature, blind_sunlight_position, auto_override_changed):
        print('High Sunlight Level 1 Invoked')
        print_blind_change = False
        if auto_override == False:
            blind_sunlight_position = 1
            if current_blind_temp_threshold == True and door_open == False: # Lower all blinds if the outdoor temperature is outside the pre-set thresholds and the doors are closed.
                print_blind_change = self.all_blinds_venetian()
            else: # Raise all blinds if the outdoor temperature is within the pre-set thresholds or the doors are opened.
                print_blind_change = self.raise_all_blinds()
            if auto_override_changed:
                print_blind_change = True
        else:
            #print('No Blind Change. Auto Blind Control is overridden')
            pass
        return(print_blind_change, blind_sunlight_position)

    def set_blind_sunlight_0(self, door_open, door_state_changed, auto_override, blind_sunlight_position, auto_override_changed):
        print('High Sunlight Level 0 Invoked')
        # The use of this level is to open the blinds in the morning when level 1 is reached and the outside temperature is within the pre-set levels
        # Make no change in this blind state because it's night time unless a door is opened (caters for case where blinds remain
        # closed due to temperatures being outside thresholds when moving from level 1 to level 0 or the blinds have been manually closed while in level 0)
        print_blind_change = False
        if auto_override == False:
            blind_sunlight_position = 0
            if door_open == True and door_state_changed: # Raise door blinds if a door is opened. Caters for the case where blinds are still set to 50% after
                # sunlight moves from level 1 to level 0 because the temp is outside thresholds or blinds have been manually closed
                #print('Opening door blinds due to a door being opened')
                self.move_blind('All Doors', 'up')
                print_blind_change = True
                self.window_blind_config['status']['All Doors'] = 'Open'
                self.window_blind_config['status']['Left Door'] = 'Open'
                self.window_blind_config['status']['Right Door'] = 'Open'
            elif (door_open == False and door_state_changed == True): # Set Door Blinds to same state as 'All Windows' if both doors have been closed
                if self.window_blind_config['status']['All Windows'] == 'Closed':
                    print_blind_change = self.close_door_impacting_blind('All Doors')
                    self.window_blind_config['status']['All Doors'] = 'Closed'
                    self.window_blind_config['status']['Left Door'] = 'Closed'
                    self.window_blind_config['status']['Right Door'] = 'Closed'
                elif self.window_blind_config['status']['All Windows'] == 'Venetian':
                    print_blind_change = self.venetian_door_impacting_blind('All Doors')
                    self.window_blind_config['status']['All Doors'] = 'Venetian'
                    self.window_blind_config['status']['Left Door'] = 'Venetian'
                    self.window_blind_config['status']['Right Door'] = 'Venetian'                 
                else:
                    print_blind_change = True              
            elif auto_override_changed:
                print_blind_change = True
            else:
                pass
        else:
            #print('No Blind Change. Auto Blind Control is overridden')
            pass
        return(print_blind_change, blind_sunlight_position)

    def change_auto_override(self, auto_override):
        #mgr.print_update('Auto Blind Override button pressed on ')
        self.auto_override = auto_override
        if auto_override:
            mgr.log_key_states("Sunlight Blind Auto Override Enabled")
        self.auto_override_changed = True
        
    def set_high_temp(self, high_temp):
        self.window_blind_config['high_temp_threshold'] = high_temp
        mgr.log_key_states('Blind High Temp Threshold Changed')
        
    def set_low_temp(self, low_temp):
        self.window_blind_config['low_temp_threshold'] = low_temp
        mgr.log_key_states('Blind Low Temp Theshold Changed')
            
    def change_blind_position(self, blind_id, blind_position):
        # Sets the flag that triggers a blind change in the main homemanager loop that then calls the control_blinds method in the window_blind[blind] object
        mgr.call_control_blinds = {'State': True, 'Blind': self.blind, 'Blind_id': blind_id,
                                   'Blind_position': blind_position}

    def move_blind(self, blind_id, command):
        homebridge.update_blind_position_state(self.blind, blind_id, command)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            blind_json = self.window_blind_config['blind commands'][command + ' ' + blind_id]
            try:
                s.connect((self.blind_ip_address, self.blind_port))
                s.sendall(blind_json)
                data = s.recv(1024)
            except TimeoutError:
                print ('Window Blind Connection Failed', self.blind_ip_address, self.blind_port)             

    def close_door_impacting_blind(self, blind_id): # This method closes any blind that covers a door and opens it if a door is opened during that blind closure
        self.move_blind(blind_id, 'down')
        self.check_door_state_while_closing(25) # Checks door state while closing and reverses if a door opens
        self.move_blind(blind_id, 'up')
        time.sleep(0.495)
        self.move_blind(blind_id, 'stop')
        return(True) 
        
    def close_window_blind(self, blind_id):
        self.move_blind(blind_id, 'down')
        time.sleep(25) # Normal close
        self.move_blind(blind_id, 'up')
        time.sleep(0.495)
        self.move_blind(blind_id, 'stop')

    def venetian_door_impacting_blind(self, blind_id): # This method sets any blind that covers a door to venetian and opens it if a door is opened during that blind setting
        self.move_blind(blind_id, 'down')
        self.check_door_state_while_closing(25)
        return(True)
    
    def venetian_window_blind(self, blind_id):
        self.move_blind(blind_id, 'down')

    def raise_all_blinds(self):
        self.move_blind('All Blinds', 'up')
        # Set blind status
        for blind_button in self.window_blind_config['status']:
            self.window_blind_config['status'][blind_button] = 'Open' 
        return(True)

    def all_blinds_venetian(self):
        # Set blind status
        #print('Setting Blind Status')
        for blind_button in self.window_blind_config['status']:
            self.window_blind_config['status'][blind_button] = 'Venetian'        
        return self.venetian_door_impacting_blind('All Blinds')
                  
    def check_door_state_while_closing(self, delay): # Checks if a door has been opened while a door blind is closing and reverses the blind closure if the door has been opened
        loop = True
        count = 0
        door_opened = False
        already_opened = False
        while count < delay:
            # Check if there's been a change in door state and flag in door_state_changed
            for door in self.window_blind_config['blind_doors']:
                # If the door state changed and it's now open. These parameters are set by the process_door_state_change method in the relevant door_sensor object
                if self.window_blind_config['blind_doors'][door]['door_state_changed'] == True and self.window_blind_config['blind_doors'][door]['door_state'] == 'Open':
                    door_opened = True
            if door_opened:
                if already_opened == False:
                    #mgr.print_update(door + ' opened while blind is closing. Door blinds now opening on ')
                    already_opened = True
                    self.door_blind_override = True
                    self.move_blind('All Doors', 'up')
                    self.window_blind_config['status']['All Doors'] = 'Open'
                    self.window_blind_config['status']['Left Door'] = 'Open'
                    self.window_blind_config['status']['Right Door'] = 'Open'
                    self.window_blind_config['status']['All Blinds'] = 'Open'
            time.sleep(0.5)
            count += 0.5

class AirconClass(object):
    def __init__(self, name, aircon_config, log_aircon_cost_data, log_damper_data, log_aircon_temp_data):
        self.name = name
        self.aircon_config = aircon_config
        #print ('Instantiated Aircon', self, name)
        self.outgoing_mqtt_topic = self.aircon_config['mqtt Topics']['Outgoing']
        self.day_zone = self.aircon_config['Day Zone']
        self.night_zone = self.aircon_config['Night Zone']
        self.indoor_zone = self.day_zone + self.night_zone
        self.damper_balanced = 50 # Allows for a bias to be set for the aircon's damper. 50 sets an equal balance between the two zones.
        # > 50 biases the airflow towards the Day Zone and < 50 biases the airflow towards the Night Zone
        self.control_thermostat = self.aircon_config['Master']
        self.thermostat_names = self.day_zone + self.night_zone
        self.thermostat_names.append(self.aircon_config['Master'])
        self.active_temperature_change_rate = {name: 0 for name in self.thermostat_names}
        self.outdoor_temp_sensor = self.aircon_config['Outdoor Temp Sensor']
        # Set up Aircon status data
        self.status = {'Remote Operation': False,'Heat': False, 'Cool': False,'Fan': False, 'Fan Hi': False, 'Fan Lo': False,
                        'Heating': False, 'Filter':False, 'Compressor': False, 'Malfunction': False, 'Damper': self.damper_balanced }
        
        self.settings = {'Thermo Heat': False, 'Thermo Cool': False, 'Thermo Off': True, 'Ventilate' : False, 'indoor_thermo_mode': 'Cool', 'day_zone_target_temperature': 21,
                          'day_zone_current_temperature': 1, 'night_zone_target_temperature': 21, 'night_zone_current_temperature': 1,
                         'indoor_zone_target_temperature': 21, 'indoor_zone_current_temperature': 1, 'target_day_zone': self.damper_balanced, 'day_zone_sensor_active': 0,
                          'night_zone_sensor_active': 0, 'indoor_zone_sensor_active': 0, 'aircon_previous_power_mode': 'Off', 'aircon_previous_power_rate': 0,
                          'aircon_previous_update_time': time.time(), 'aircon_previous_cost_per_hour': 0, 'previous_day_zone_gap': 0, 'previous_night_zone_gap': 0,
                          'previous_optimal_day_zone': self.damper_balanced, 'previous_aircon_mode_command': 'Off'}
        
        # Set up effectiveness logging data
        self.aircon_log_items = self.indoor_zone + ['Day'] + ['Night']
        self.active_temperature_history = {name: [0.0 for x in range(11)] for name in self.indoor_zone}
        self.max_heating_effectiveness = {name: 0.0 for name in self.aircon_log_items}
        self.min_heating_effectiveness = {name: 9.9 for name in self.aircon_log_items}
        self.max_cooling_effectiveness = {name: 0.0 for name in self.aircon_log_items}
        self.min_cooling_effectiveness = {name: 9.9 for name in self.aircon_log_items}
        # Set up initial sensor data with a dictionary comprehension
        self.thermostat_status = {name: {'Current Temperature': 1, 'Target Temperature': 25, 'Mode': 'Off', 'Active': 0} for name in self.thermostat_names}
        self.thermostat_mode_active_map = {'Off': 0, 'Heat': 1, 'Cool': 1} # 1 Indicates that a thermostat is active (i.e. in either Heat or Cool Mode)
        self.start_time = time.time()
        self.temperature_update_time = {name: self.start_time for name in self.indoor_zone}
        self.log_damper_data = log_damper_data

        # Set up Aircon Power Consumption Dictionary
        self.aircon_power_consumption = {'Heat': 4.97, 'Cool': 5.42, 'Idle': 0.13, 'Off': 0} # Power consumption in kWh for each power_mode
        self.aircon_seasons_months = {'January': 'Summer', 'February': 'Summer', 'March': 'Summer', 'April': 'Spring', 'May': 'Spring', 'June': 'Winter',
                                      'July': 'Winter', 'August': 'Winter', 'September': 'Spring', 'October': 'Spring', 'November': 'Summer',
                                      'December': 'Summer'}
        self.aircon_weekday_power_rates = {'Summer': {0:{'name': 'EV', 'rate': 0.10104, 'stop_hour': 3}, 4:{'name': 'off_peak1', 'rate': 0.1641, 'stop_hour': 6},
                                                      7:{'name':'shoulder1', 'rate': 0.2017, 'stop_hour': 13}, 14:{'name':'peak', 'rate':0.3797, 'stop_hour': 19},
                                                      20: {'name': 'shoulder2', 'rate': 0.2021, 'stop_hour': 21}, 22:{'name': 'off_peak2', 'rate': 0.1641, 'stop_hour': 23}},
                                           'Autumn': {0:{'name': 'EV', 'rate': 0.10104, 'stop_hour': 3}, 4:{'name': 'off_peak1', 'rate': 0.1641, 'stop_hour': 6},
                                                      7:{'name':'shoulder', 'rate': 0.2017, 'stop_hour': 21}, 22:{'name': 'off_peak2', 'rate': 0.1641, 'stop_hour': 23}},
                                           'Winter': {0:{'name': 'EV', 'rate': 0.10104, 'stop_hour': 3}, 4:{'name': 'off_peak1', 'rate': 0.1641, 'stop_hour': 6},
                                                      7:{'name':'shoulder1', 'rate': 0.2017, 'stop_hour': 16}, 17:{'name':'peak', 'rate':0.3797, 'stop_hour': 20},
                                                      21: {'name': 'shoulder2', 'rate': 0.2021, 'stop_hour': 21}, 22:{'name': 'off_peak2', 'rate': 0.1641, 'stop_hour': 23}},
                                           'Spring': {0:{'name': 'EV', 'rate': 0.10104, 'stop_hour': 3}, 4:{'name': 'off_peak1', 'rate': 0.1641, 'stop_hour': 6},
                                                      7:{'name':'shoulder', 'rate': 0.2021, 'stop_hour': 21}, 22:{'name': 'off_peak2', 'rate': 0.1641, 'stop_hour': 23}}}
        self.aircon_weekend_power_rates = {0:{'name': 'off_peak1', 'rate': 0.1641, 'stop_hour': 6}, 7:{'name':'shoulder', 'rate': 0.2021, 'stop_hour': 21},
                              22:{'name': 'off_peak2', 'rate': 0.1641, 'stop_hour': 23}}
        self.aircon_running_costs = {'total_cost':0, 'total_hours': 0}
        self.log_aircon_cost_data = log_aircon_cost_data

    def start_up(self, load_previous_aircon_effectiveness):
        # Reset Homebridge Thermostats/Ventilation Buttons and set zone temps on start-up
        homebridge.reset_aircon_thermostats(self.name, self.thermostat_status)
        self.update_zone_temps()
        # Reset Domoticz Thermostats on start-up
        domoticz.reset_aircon_thermostats(self.name, self.thermostat_status)
        if load_previous_aircon_effectiveness:
            # Initialise aircon effectiveness dictionary based on previously logged data
            self.populate_starting_aircon_effectiveness()
        # Initialise aircon power dictionary based on previously logged data
        self.populate_aircon_power_status()
        self.send_aircon_command('Update Status') # Get aircon status on startup
        self.send_aircon_command('Off') # Set aircon to Thermo Off setting on startup
        self.settings['previous_aircon_mode_command'] = 'Off'

    def shut_down(self):
        self.send_aircon_command('Update Status') # Get aircon status on shut-down
        self.send_aircon_command('Off') # Set aircon to Thermo Off setting on shut-down
        self.settings['previous_aircon_mode_command'] = 'Off'
        # Reset Homebridge Thermostats and Ventilation buttons on shut-down
        homebridge.reset_aircon_thermostats(self.name, self.thermostat_status)
        # Reset Domoticz Thermostats on shut-down
        domoticz.reset_aircon_thermostats(self.name, self.thermostat_status)

    def reset_effectiveness_log(self):
        self.active_temperature_history = {name: [0.0 for x in range(11)] for name in self.indoor_zone}
        self.max_heating_effectiveness = {name: 0.0 for name in self.aircon_log_items}
        self.min_heating_effectiveness = {name: 9.9 for name in self.aircon_log_items}
        self.max_cooling_effectiveness = {name: 0.0 for name in self.aircon_log_items}
        self.min_cooling_effectiveness = {name: 9.9 for name in self.aircon_log_items}
        today = datetime.now()
        time_data = self.get_local_time()
        time_stamp = today.strftime('%A %d %B %Y @ %H:%M:%S')
        json_log_data = {'Time Data': time_data, 'Time': time_stamp, 'Message': 'Log Reset', 'Mode': 'Cool', 'Max': self.max_cooling_effectiveness, 'Min': self.min_cooling_effectiveness}
        with open(self.aircon_config['Effectiveness Log'], 'a') as f:
            f.write(',\n' + json.dumps(json_log_data))
        json_log_data = {'Time Data': time_data, 'Time': time_stamp, 'Message': 'Log Reset', 'Mode': 'Heat', 'Max': self.max_heating_effectiveness, 'Min': self.min_heating_effectiveness}
        with open(self.aircon_config['Effectiveness Log'], 'a') as f:
            f.write(',\n' + json.dumps(json_log_data))

    def process_ventilation_button(self, ventilation):
        #print('Process Aircon Ventilation Button. Ventilation:', ventilation, 'Thermo Off:', self.settings['Thermo Off'])
        if self.settings['Thermo Off']: # Aircon Ventilation setting can only be set if the aircon is in Thermo Off setting
            if ventilation:
                self.settings['Ventilate'] = True
                self.send_aircon_command('Ventilate')
                self.settings['previous_aircon_mode_command'] = 'Ventilate'
            else:
                self.settings['Ventilate'] = False
                self.send_aircon_command('Off')
                self.settings['previous_aircon_mode_command'] = 'Off'
            #print('Setting Ventilation', self.settings['Ventilate'])
        else: # Reset Homebridge Ventilation Button to previous state if it's not possible to be in that setting
            time.sleep(0.5)
            homebridge.reset_aircon_ventilation_button(self.name)      

    def set_thermostat(self, thermostat_name, control, setting):
        #print (thermostat_name, control, setting)
        if thermostat_name == self.control_thermostat: # Only invoke setting changes if it's the control thermostat
            print('Control Thermostat Change', thermostat_name, control, setting)
            if control == 'Mode':
                if setting == 'Off':
                    self.settings['Thermo Heat'] = False
                    self.settings['Thermo Cool'] = False
                    self.settings['Thermo Off'] = True
                    self.settings['Ventilate'] = False
                    homebridge.reset_aircon_ventilation_button(self.name) # Reset Homebridge ventilation button whenever the control thermostat mode is invoked
                    self.thermostat_status[thermostat_name]['Mode'] = setting
                    self.thermostat_status[thermostat_name]['Active'] = self.thermostat_mode_active_map[setting]
                    self.send_aircon_command('Off')
                    self.settings['previous_aircon_mode_command'] = 'Off'
                    homebridge.set_target_damper_position(self.name, self.damper_balanced, 'Stopped') # Reset Homebridge Damper position indicator when releasing control of the aircon
                if setting == 'Heat':
                    if self.settings['indoor_zone_sensor_active'] == 1: #Only do something if at least one sensor is active
                        self.settings['Thermo Heat'] = True
                        self.settings['Thermo Cool'] = False
                        self.settings['Thermo Off'] = False
                        self.settings['Ventilate'] = False
                        homebridge.reset_aircon_ventilation_button(self.name) # Reset Homebridge ventilation button whenever the control thermostat mode is invoked
                        self.settings['indoor_thermo_mode'] = 'Heat'
                        self.thermostat_status[thermostat_name]['Mode'] = setting
                        self.thermostat_status[thermostat_name]['Active'] = self.thermostat_mode_active_map[setting]
                        self.send_aircon_command('Thermostat Heat')
                        self.settings['previous_aircon_mode_command'] = 'Off'
                    else:
                        print('Trying to start aircon without any sensor active. Command ignored')
                        homebridge.reset_aircon_control_thermostat(self.name) # Set homebridge aircon control thermostat back to Off
                if setting == 'Cool': 
                    if self.settings['indoor_zone_sensor_active'] == 1: #Only do something if at least one sensor is active
                        self.settings['Thermo Heat'] = False
                        self.settings['Thermo Cool'] = True
                        self.settings['Thermo Off'] = False
                        self.settings['Ventilate'] = False
                        homebridge.reset_aircon_ventilation_button(self.name) # Reset Homebridge ventilation button whenever the control thermostat mode is invoked
                        self.settings['indoor_thermo_mode'] = 'Cool'
                        self.thermostat_status[thermostat_name]['Mode'] = setting
                        self.thermostat_status[thermostat_name]['Active'] = self.thermostat_mode_active_map[setting]
                        self.send_aircon_command('Thermostat Cool')
                        self.settings['previous_aircon_mode_command'] = 'Off'
                    else:
                        print('Trying to start aircon without any sensor active. Command ignored')
                        homebridge.reset_aircon_control_thermostat(self.name) # Set homebridge aircon control thermostat back to Off
            self.update_zone_temps() # Update the "Day", "Night" and "Indoor" Zones current temperatures with active temperature sensor readings and the "Indoor" Target Temperature is updated with the target temperatures of the active sensor settings
            indoor_control_mode = self.thermostat_status[self.control_thermostat]['Mode']
            self.update_active_thermostats(indoor_control_mode)  # Ensure that active thermostats have the same mode setting as the control thermostat
            mgr.log_key_states("Aircon Control Thermostat Change")
        else:
            if control == 'Target Temperature':
                self.thermostat_status[thermostat_name]['Target Temperature'] = setting
                #mgr.print_update('Updating ' + thermostat_name + ' Target Temperature to ' + str(setting) + " Degrees, Actual Temperature = " + str(self.thermostat_status[thermostat_name]['Current Temperature']) + " Degrees on ")
            if control == 'Mode':
                self.thermostat_status[thermostat_name]['Mode'] = setting
                self.thermostat_status[thermostat_name]['Active'] = self.thermostat_mode_active_map[setting]
                if setting != 'Off':
                    if self.status['Heat'] and self.status['Compressor'] and self.status['Heating'] == False:
                        heating_cooling_state = 1
                    elif self.status['Cool'] and self.status['Compressor']:
                        heating_cooling_state = 2
                    else:
                        heating_cooling_state = 0
                else:
                    heating_cooling_state = 0
                homebridge.update_individual_thermostat_current_state(self.name, thermostat_name, heating_cooling_state, self.status['Damper']) # Update thermostat current heating cooling state in homebridge
            self.update_zone_temps() # Update the "Day", "Night" and "Indoor" Zones current temperatures with active temperature sensor readings
            indoor_control_mode = self.thermostat_status[self.control_thermostat]['Mode']
            self.update_active_thermostats(indoor_control_mode) # Ensure that active sensors have the same mode setting as the Indoor Control
            mgr.log_key_states("Aircon Thermostat Change")

    def send_aircon_command(self, command): # Send command to aircon controller
        aircon_command = {}
        aircon_command['service'] = command
        client.publish(self.outgoing_mqtt_topic, json.dumps(aircon_command))

    def capture_status(self, parsed_json):
        if parsed_json['service'] == 'Heartbeat':
            #mgr.print_update('Received Heartbeat from Aircon and sending Ack on ')
            self.send_aircon_command('Heartbeat Ack')
        if parsed_json['service'] == 'Restart':
            mgr.print_update(self.name + ' Controller Restarted on ')
        elif parsed_json['service'] == 'Status Update':
            mgr.print_update(self.name + ' status updated on ')
            #print(parsed_json)
            for status_item in self.status:
                if self.status[status_item] != parsed_json[status_item]:
                    print(status_item, 'changed from', self.status[status_item], 'to', parsed_json[status_item])
                    self.status[status_item] = parsed_json[status_item]
                homebridge.update_aircon_status(self.name, status_item, self.status, self.settings)
                domoticz.update_aircon_status(self.name, status_item, self.status[status_item])
                       
    def update_temp_history(self, name, temperature): # Called by a multisensor object upon a temperature reading so that temperature history can be logged
        #print('')
        #print('Temperature History Logging', 'Name', name, 'Temperature', temperature)
        current_temp_update_time = time.time()
        #print('Current Time', current_temp_update_time, 'Previous Update Time for', name, self.temperature_update_time[name])
        if (current_temp_update_time - self.temperature_update_time[name]) > 10: # Ignore duplicate temp data if temp comes in less than 10 seconds (Each sensor sends its temp twice)
            #print('name', name, 'Temperature', temperature, 'History', self.active_temperature_history[name])
            #print('Temp History Before Shift', self.active_temperature_history)
            for pointer in range(10, 0, -1): # Move previous temperatures one position in the list to prepare for new temperature to be recorded
                self.active_temperature_history[name][pointer] = self.active_temperature_history[name][pointer - 1]
            #print('Temp History after shift no pop', self.active_temperature_history)
            #print('')
            if (self.status['Cool'] == True or self.status['Heat'] == True) and self.status['Remote Operation'] == True and self.status['Heating'] == False and self.status['Compressor'] == True and self.status['Malfunction'] == False:
                # Only update the Active Temperature if cooling or heating, under Raspberry Pi control and the aircon isn't passive
                if self.status['Damper'] == 100: # Don't treat any Night Zone sensors as active if the damper is 100% in the Day position
                    #print('Day Zone Active')
                    self.night_mode = 0
                    self.day_mode = 1
                elif self.status['Damper'] == 0: # Don't treat any Day Zone sensors as active if the damper is 100% in the Night position
                    #print ('Night Zone Active')
                    self.day_mode = 0
                    self.night_mode = 1
                else: # Treat both zones as active if the damper is anywhere between open and closed
                    #print('Both Zones Active')
                    self.night_mode = 1
                    self.day_mode = 1
                if name in self.day_zone:
                    self.active_temperature_history[name][0] = temperature * self.day_mode
                elif name in self.night_zone:
                    self.active_temperature_history[name][0] = temperature * self.night_mode
                else:
                    print('Invalid aircon sensor', name)
            else:
                self.active_temperature_history[name][0] = 0.0
            #print(name, 'Temp History after shift and pop', self.active_temperature_history[name])
            #print('')
            valid_temp_history = True
            for pointer in range(0, 11):
                if self.active_temperature_history[name][pointer] == 0:
                    valid_temp_history = False
            #print('Valid temp history', valid_temp_history, 'Latest Reading', self.active_temperature_history[name][0])
            if valid_temp_history: #Update active temp change rate if we have 10 minutes of valid active temperatures
                active_temp_change = round((self.active_temperature_history[name][0] - self.active_temperature_history[name][10])*6, 1) # calculate the temp change per hour over the past 10 minutes, given that there are two sensor reports every minute. +ve heating, -ve cooling
                #print('Active Temp Change', active_temp_change)
                if abs(active_temp_change - self.active_temperature_change_rate[name]) >= 0.1: #Log if there's a change in the rate
                    self.active_temperature_change_rate[name] = active_temp_change
                    self.active_temperature_change_rate['Day'] = self.mean_active_temp_change_rate(self.day_zone) # Calculate Day zone temperature change rate by taking the mean temp change rates of active day zone sensors
                    self.active_temperature_change_rate['Night'] = self.mean_active_temp_change_rate(self.night_zone) # Calculate Night zone temperature change rate by taking the mean temp change rates of active night zone sensors
                    self.active_temperature_change_rate['Indoor'] = self.mean_active_temp_change_rate(self.indoor_zone) # Calculate Indoor zone temperature change rate by taking the mean temp change rates of active indoor sensors
                    #print("Day Zone Active Change Rate:", self.active_temperature_change_rate['Day'], "Night Zone Active Change Rate:", self.active_temperature_change_rate['Night'], "Indoor Zone Active Change Rate:", self.active_temperature_change_rate['Indoor'])
                    today = datetime.now()
                    time_data = self.get_local_time()
                    time_stamp = today.strftime('%A %d %B %Y @ %H:%M:%S')
                    json_log_data = {'Time Data': time_data, 'Time': time_stamp, 'Sensor': name, 'Latest Temp': self.active_temperature_history[name][0],
                                      'Ten Minute Historical Temp': self.active_temperature_history[name][10],
                                      'Active Temp Change Rate': self.active_temperature_change_rate[name], 'Active Day Change Rate': self.active_temperature_change_rate['Day'],
                                     'Active Night Change Rate': self.active_temperature_change_rate['Night'], 'Active Indoor Change Rate': self.active_temperature_change_rate['Indoor'],
                                     'Damper Position': self.status['Damper'], 'Outdoor Temp': multisensor[self.outdoor_temp_sensor].sensor_types_with_value['Temperature']}
                    with open(self.aircon_config['Spot Temperature History Log'], 'a') as f:
                        f.write(',\n' + json.dumps(json_log_data))
                    if self.status['Heat']:
                        log = False
                        if self.active_temperature_change_rate[name] > self.max_heating_effectiveness[name]: # Record Maximum only
                            self.max_heating_effectiveness[name] = self.active_temperature_change_rate[name]
                            log = True
                        if round(self.active_temperature_change_rate['Day'], 1) > self.max_heating_effectiveness['Day'] and self.day_mode == 1: # Record Maximum when in Day Mode only
                            self.max_heating_effectiveness['Day'] = round(self.active_temperature_change_rate['Day'], 1)
                            log = True
                        if round(self.active_temperature_change_rate['Night'], 1) > self.max_heating_effectiveness['Night'] and self.night_mode == 1:  # Record Maximum when in Night Mode only
                            self.max_heating_effectiveness['Night'] = round(self.active_temperature_change_rate['Night'], 1)
                            log = True
                        #print("Aircon Maximum Heating Effectiveness:", self.max_heating_effectiveness)
                        if self.active_temperature_change_rate[name] < self.min_heating_effectiveness[name]: # Record Minimum only
                            self.min_heating_effectiveness[name] = self.active_temperature_change_rate[name]
                            log = True
                        if round(self.active_temperature_change_rate['Day'], 1) < self.min_heating_effectiveness['Day'] and self.day_mode == 1: # Record Minimum when in Day Mode only
                            self.min_heating_effectiveness['Day'] = round(self.active_temperature_change_rate['Day'], 1)
                            log = True
                        if round(self.active_temperature_change_rate['Night'], 1) < self.min_heating_effectiveness['Night'] and self.night_mode == 1: # Record Minimum when in Night Mode only
                            self.min_heating_effectiveness['Night'] = round(self.active_temperature_change_rate['Night'], 1)
                            log = True
                        #print("Aircon Minimum Heating Effectiveness:", min_heating_effectiveness)
                        if log:
                            today = datetime.now()
                            time_data = self.get_local_time()
                            time_stamp = today.strftime('%A %d %B %Y @ %H:%M:%S')
                            json_log_data = {'Time Data': time_data, 'Time': time_stamp, 'Sensor': name, 'Mode': 'Heat', 'Max': self.max_heating_effectiveness, 'Min': self.min_heating_effectiveness,
                                              'Latest Temp': self.active_temperature_history[name][0], 'Ten Minute Historical Temp': self.active_temperature_history[name][10],
                                              'Outdoor Temp': multisensor[self.outdoor_temp_sensor].sensor_types_with_value['Temperature']}
                            with open(self.aircon_config['Effectiveness Log'], 'a') as f:
                                f.write(',\n' + json.dumps(json_log_data))
                    elif self.status['Cool']:
                        log = False
                        if 0 - self.active_temperature_change_rate[name] > self.max_cooling_effectiveness[name]: # Record Maximum only
                            self.max_cooling_effectiveness[name] = 0 - self.active_temperature_change_rate[name]
                            log = True
                        if 0 - round(self.active_temperature_change_rate['Day'], 1) > self.max_cooling_effectiveness['Day']: # Record Maximum only
                            self.max_cooling_effectiveness['Day'] = 0 - round(self.active_temperature_change_rate['Day'], 1)
                            log = True
                        if 0 - round(self.active_temperature_change_rate['Night'], 1) > self.max_cooling_effectiveness['Night']: # Record Maximum only
                            self.max_cooling_effectiveness['Night'] = 0 - round(self.active_temperature_change_rate['Night'], 1)
                            log = True
                        #print("Aircon Maximum Cooling Effectiveness:", max_cooling_effectiveness)
                        if 0 - self.active_temperature_change_rate[name] < self.min_cooling_effectiveness[name]: # Record Minimum only
                            self.min_cooling_effectiveness[name] = 0 - self.active_temperature_change_rate[name]
                            log = True
                        if 0 - round(self.active_temperature_change_rate['Day'], 1) < self.min_cooling_effectiveness['Day'] and self.day_mode == 1: # Record Minimum when in Day Mode only
                            self.min_cooling_effectiveness['Day'] = 0 - round(self.active_temperature_change_rate['Day'], 1)
                            log = True
                        if 0 - round(self.active_temperature_change_rate['Night'], 1) < self.min_cooling_effectiveness['Night']and self.night_mode == 1: # Record Minimum when in Day Mode only
                            self.min_cooling_effectiveness['Night'] = 0 - round(self.active_temperature_change_rate['Night'], 1)
                            log = True
                        #print("Aircon Minimum Cooling Effectiveness:", min_cooling_effectiveness)
                        if log:
                            today = datetime.now()
                            time_data = self.get_local_time()
                            time_stamp = today.strftime('%A %d %B %Y @ %H:%M:%S')       
                            json_log_data = {'Time Data': time_data, 'Time': time_stamp, 'Sensor': name, 'Mode': 'Cool', 'Max': self.max_cooling_effectiveness, 'Min': self.min_cooling_effectiveness,
                                              'Latest Temp': self.active_temperature_history[name][0], 'Ten Minute Historical Temp': self.active_temperature_history[name][10],
                                              'Outdoor Temp': multisensor[self.outdoor_temp_sensor].sensor_types_with_value['Temperature']}
                            with open(self.aircon_config['Effectiveness Log'], 'a') as f:
                                f.write(',\n' + json.dumps(json_log_data))
                    else:
                        time.sleep(0.01)# No update if not in heat mode or cool mode
        self.temperature_update_time[name] = current_temp_update_time # Record the time of the temp update. Used to ignore double temp updates from the sensors
  
    def mean_active_temp_change_rate(self, zone_list): # Called by update_temp_history to calculate the mean zone temperature change rate for active sensors within the specified zone
        den_sum = 0
        for item in zone_list:
            if self.active_temperature_change_rate[item] != 0:
                den_sum += 1
        if den_sum != 0:
            num_sum = 0
            for item in zone_list:
                num_sum += self.active_temperature_change_rate[item]
            active_zone_change_rate = round(num_sum/den_sum, 1)
        else:
            active_zone_change_rate = 0.0
        return active_zone_change_rate
    
    def update_active_thermostats(self, mode): # Called by 'set_thermostat' method to ensure that active sensors have the same mode setting as the Indoor Control
        for thermostat in self.indoor_zone:
            if self.thermostat_status[thermostat]['Active'] == 1 and mode != 'Off':
                self.thermostat_status[thermostat]['Mode'] = mode
                homebridge.update_aircon_thermostat(self.name, thermostat, mode)

    def update_zone_temps(self): # Called by 'process_aircon_buttons' and the 'capture_domoticz_sensor_data' modules to ensure that the "Day", "Night" and "Indoor" Zones current temperatures
        #are updated with active temperature sensor readings and the "Indoor" Target Temperature is updated with the target temperatures of the active sensor settings
        self.settings['day_zone_sensor_active'], self.settings['day_zone_target_temperature'], self.settings['day_zone_current_temperature'] = self.mean_active_temperature(self.day_zone)
        self.settings['night_zone_sensor_active'], self.settings['night_zone_target_temperature'], self.settings['night_zone_current_temperature'] = self.mean_active_temperature(self.night_zone)
        self.settings['indoor_zone_sensor_active'], self.settings['indoor_zone_target_temperature'], self.settings['indoor_zone_current_temperature'] = self.mean_active_temperature(self.indoor_zone)
        if self.settings['indoor_zone_sensor_active'] != 0: # Only update the Indoor Climate Control Temperatures if at least one sensor is active
            homebridge.update_control_thermostat_temps(self.name, self.settings['indoor_zone_target_temperature'], self.settings['indoor_zone_current_temperature'])
            self.thermostat_status[self.control_thermostat]['Current Temperature'] = self.settings['indoor_zone_current_temperature']
            self.thermostat_status[self.control_thermostat]['Target Temperature'] = self.settings['indoor_zone_target_temperature']
    
    def mean_active_temperature(self, zone): # Called by update_zone_temps to calculate the mean target and current zone temperatures of a zone using the data from active sensors
        den_sum = 0
        for name in zone: # Add the settings of each sensor in the zone to determine how many are active
            den_sum += self.thermostat_status[name]['Active']
        if den_sum != 0: # Use den_sum as the denominator for the mean calculation if at least one sensor in the zone is active 
            sensor_active = 1
            target_num_sum = 0
            current_num_sum = 0
            for name in zone: # Calculate the numerator for both target and current temperatures
                #print('Name', name, 'Target Temperature', self.thermostat_status[name]['Target Temperature'], 'Active', self.thermostat_status[name]['Active'])
                #print('Current Temperature', self.thermostat_status[name]['Current Temperature'])
                target_num_sum += self.thermostat_status[name]['Target Temperature'] * self.thermostat_status[name]['Active']
                current_num_sum += self.thermostat_status[name]['Current Temperature'] * self.thermostat_status[name]['Active']
            target_temperature = round(target_num_sum / den_sum, 1)
            current_temperature = round(current_num_sum / den_sum, 1)  
        else:
            sensor_active = 0
            target_temperature = 1
            current_temperature = 1
        return sensor_active, target_temperature, current_temperature

    def get_local_time(self):
        non_dst = time.time() - time.timezone
        dst = non_dst - time.altzone
        if time.daylight < 0:
            return dst
        else:
            return non_dst

    def control_aircon(self):
        if self.status['Remote Operation']: # Only invoke aircon control is the aircon is under control of the Raspberry Pi
            #print ("Thermo Off Setting", self.settings)
            if self.settings['Thermo Off'] == False: # Only invoke aircon control if the control thermostat is not set to 'Off'
                if self.settings['aircon_previous_power_mode'] == 'Off': # Start up in idle
                    self.set_aircon_mode("Idle")
                self.settings['Ventilate'] = False
                #print("Thermo On Setting")
                if self.settings['indoor_zone_sensor_active'] == 1: # Only invoke aircon control if at least one aircon temp sensor is active
                    #print("Indoor Active")
                    if self.settings['day_zone_sensor_active'] ^ self.settings['night_zone_sensor_active'] == 1: #If only one zone is active
                        #print("Only One Zone Active")
                        previous_target_day_zone = self.settings['target_day_zone'] # Record the current damper position to determine if a change needs to invoked
                        if self.settings['day_zone_sensor_active'] == 1:
                            self.settings['target_day_zone'] = 100
                            self.settings['target_temperature'] = self.settings['day_zone_target_temperature']
                            temperature_key = 'day_zone_current_temperature'
                            active_zone = 'Day Zone'
                            #print("Day Zone Active")
                        else:
                            self.settings['target_day_zone'] = 0
                            self.settings['target_temperature'] = self.settings['night_zone_target_temperature']
                            temperature_key = 'night_zone_current_temperature'
                            active_zone = 'Night Zone'
                            #print("Night Zone Active")
                        #print(" ")
                        if self.settings[temperature_key] != 1: # Don't do anything until the Temp is updated on startup
                            # Set the temp boundaries for a mode change to provide hysteresis
                            target_temp_high = self.settings['target_temperature'] + 0.4
                            target_temp_low = self.settings['target_temperature'] - 0.4
                            if self.settings['Thermo Heat']: # If in Thermo Heat Setting
                                #print("Thermo Heat Setting")
                                if self.settings[temperature_key] < self.settings['target_temperature']: # If actual temp is lower than target temp, stay in heat mode, fan hi
                                    self.set_aircon_mode("Heat")
                                if self.settings[temperature_key] > target_temp_high:# If target temperature is 0.5 degree higher than target temp, put in fan mode, lo
                                    self.set_aircon_mode("Idle")
                            if self.settings['Thermo Cool']: #If in Thermo Cool Setting
                                #print("Thermo Cool Setting")
                                if self.settings[temperature_key] > self.settings['target_temperature']: #if actual temp is higher than target temp, turn aircon on in cool mode, fan hi
                                    self.set_aircon_mode("Cool")
                                if self.settings[temperature_key] < target_temp_low: #if actual temp is 0.5 degree lower than target temp, put in fan mode lo
                                    self.set_aircon_mode("Idle")
                            power_mode, self.settings = self.check_power_change(self.status, self.settings, self.log_aircon_cost_data) # Check for power rate or consumption change
                            if self.settings['target_day_zone'] != previous_target_day_zone: # Move Damper if Target Zone changes
                                mgr.print_update("Only " + active_zone + " is active for " + self.name + ". Moving Damper from " + str(previous_target_day_zone) + " percent to " +
                                                  str(self.settings['target_day_zone']) + " percent on ")
                                self.move_damper(self.settings['target_day_zone'], power_mode, self.log_damper_data)
                    else:
                        # Both Zones Active
                        # Set the temp boundaries for a mode change to provide hysteresis
                        day_target_temp_high = self.settings['day_zone_target_temperature'] + 0.4
                        day_target_temp_low = self.settings['day_zone_target_temperature'] - 0.4
                        night_target_temp_high = self.settings['night_zone_target_temperature'] + 0.4
                        night_target_temp_low = self.settings['night_zone_target_temperature'] - 0.4 
                        if self.settings['day_zone_current_temperature'] != 1 and self.settings['night_zone_current_temperature'] != 1: # Don't do anything until the Temps are updated on startup
                            if self.settings['Thermo Heat']: # If in Thermo Heat Setting
                                if self.settings['day_zone_current_temperature'] < self.settings['day_zone_target_temperature'] or self.settings['night_zone_current_temperature'] < self.settings['night_zone_target_temperature']: # Go into heat mode and stay there if there's gap against the target in at least one zone
                                    self.set_aircon_mode("Heat")
                                if self.settings['day_zone_current_temperature'] > day_target_temp_high and self.settings['night_zone_current_temperature'] > night_target_temp_high: # If both zones are 0.5 degree higher than target temps, put in fan mode, lo
                                    self.set_aircon_mode("Idle")
                                day_zone_gap = round(self.settings['day_zone_target_temperature'] - self.settings['day_zone_current_temperature'],1)
                                night_zone_gap = round(self.settings['night_zone_target_temperature'] - self.settings['night_zone_current_temperature'],1)
                                day_zone_gap_max = round(day_target_temp_high - self.settings['day_zone_current_temperature'],1)
                                night_zone_gap_max = round(night_target_temp_high - self.settings['night_zone_current_temperature'],1)
                                power_mode, self.settings = self.check_power_change(self.status, self.settings, self.log_aircon_cost_data) # Check for power rate or consumption change
                                self.set_dual_zone_damper(day_zone_gap, night_zone_gap, day_zone_gap_max, night_zone_gap_max, power_mode) # Set Damper based on gap between current and target temperatures 
                            elif self.settings['Thermo Cool']: # If in Thermo Cool Setting
                                if self.settings['day_zone_current_temperature'] > self.settings['day_zone_target_temperature'] or self.settings['night_zone_current_temperature'] > self.settings['night_zone_target_temperature']: # Go into cool mode and stay there if there's gap against the target in at least one zone
                                    self.set_aircon_mode("Cool")
                                if self.settings['day_zone_current_temperature'] < day_target_temp_low and self.settings['night_zone_current_temperature'] < night_target_temp_low: # If both zones are 0.5 degree lower than target temps, put in fan mode, lo
                                    self.set_aircon_mode("Idle")
                                day_zone_gap = round(self.settings['day_zone_current_temperature'] - self.settings['day_zone_target_temperature'],1)
                                night_zone_gap = round(self.settings['night_zone_current_temperature'] - self.settings['night_zone_target_temperature'],1)
                                day_zone_gap_max = round(self.settings['day_zone_current_temperature'] - day_target_temp_low,1)
                                night_zone_gap_max = round(self.settings['night_zone_current_temperature'] - night_target_temp_low,1)
                                power_mode, self.settings = self.check_power_change(self.status, self.settings, self.log_aircon_cost_data) # Check for power rate or consumption change
                                self.set_dual_zone_damper(day_zone_gap, night_zone_gap, day_zone_gap_max, night_zone_gap_max, power_mode) # Set Damper based on gap between current and target temperatures
                            else:
                                mgr.print_update ("Thermo Off Setting Invoked on ")                     
                else: # Stay in Fan Mode if no valid actual temp reading
                    print ("No Valid Temp")
                    self.set_aircon_mode("Idle")
            else: # If Aircon is off or in Ventilation Setting
                if self.settings['Ventilate'] == False: # If the aircon is off
                    if self.settings['aircon_previous_power_mode'] != 'Off': # Update the aircon power log when put into Thermo Off Setting
                        power_mode = 'Off'
                        update_date_time = datetime.now()
                        current_power_rate = self.check_power_rate(update_date_time)
                        self.update_aircon_power_log(power_mode, current_power_rate, time.time(), self.log_aircon_cost_data)
                else: # If the aircon is in Ventilation Setting
                    if self.settings['target_day_zone'] != self.damper_balanced: # If the damper is not set to both zones
                        previous_target_day_zone = self.settings['target_day_zone'] # Record the current damper position to determine if a change needs to invoked
                        self.settings['target_day_zone'] = self.damper_balanced # Set the damper to both zones
                        self.move_damper(self.settings['target_day_zone'], 'Idle', self.log_damper_data)
                    power_mode, self.settings = self.check_power_change(self.status, self.settings, self.log_aircon_cost_data)         

    def set_aircon_mode(self, mode): # Called by 'control_aircon' to set aircon mode.
        if mode == 'Heat':
            if self.settings['previous_aircon_mode_command'] != 'Heat Mode': # Only set to heat mode if it's not already been done
                mgr.print_update("Heat Mode Selected on ")
                self.print_zone_temp_states()
                self.send_aircon_command('Heat Mode')
                self.settings['previous_aircon_mode_command'] = 'Heat Mode'
        if mode == 'Cool':
            if self.settings['previous_aircon_mode_command'] != 'Cool Mode': # Only set to cool mode if it's not already been done
                mgr.print_update("Cool Mode Selected on ")
                self.print_zone_temp_states()
                self.send_aircon_command('Cool Mode')
                self.settings['previous_aircon_mode_command'] = 'Cool Mode'
        if mode == 'Idle':
            if self.settings['previous_aircon_mode_command'] != 'Fan Mode': # Only set to Fan Mode if it's not already been done
                mgr.print_update("Idle Mode Selected on ")
                self.print_zone_temp_states() 
                self.send_aircon_command('Fan Mode')
                self.settings['previous_aircon_mode_command'] = 'Fan Mode'

    def print_zone_temp_states(self):
        if self.settings['day_zone_sensor_active'] == 1 and self.settings['night_zone_sensor_active'] == 1: # If both zones are active
            print(self.name, "Day Temp is", self.settings['day_zone_current_temperature'], "Degrees. Day Target Temp is", self.settings['day_zone_target_temperature'], "Degrees. Night Temp is",
                                          self.settings['night_zone_current_temperature'], "Degrees. Night Target Temp is", self.settings['night_zone_target_temperature'], "Degrees")
        elif self.settings['day_zone_sensor_active'] == 1 and self.settings['night_zone_sensor_active'] == 0: # If only day zone is active
            print(self.name, "Day Temp is", self.settings['day_zone_current_temperature'], "Degrees. Day Target Temp is", self.settings['day_zone_target_temperature'], "Degrees.")
        elif self.settings['day_zone_sensor_active'] == 0 and self.settings['night_zone_sensor_active'] == 1: # If only night zone is active
            print(self.name, "Night Temp is", self.settings['night_zone_current_temperature'], "Degrees. Night Target Temp is", self.settings['night_zone_target_temperature'], "Degrees")
        else: # If neither zone is active
            pass

    def check_power_change(self, status, settings, log_aircon_cost_data):
        # Prepare data for power consumption logging
        update_date_time = datetime.now()
        current_power_rate = self.check_power_rate(update_date_time)
        if settings['Ventilate'] == False: # Set power_mode based on aircon status if the aircon is not in Ventilate Setting
            if settings['previous_aircon_mode_command'] == 'Cool Mode':
                power_mode = 'Cool'
            elif settings['previous_aircon_mode_command'] == 'Heat Mode':
                power_mode = 'Heat'
            elif settings['previous_aircon_mode_command'] == 'Fan Mode':
                power_mode = 'Idle'
            else:
                power_mode = 'Off'
        else: # Always set power_mode to 'Idle' if the aircon is in Ventilate Setting
            power_mode = 'Idle'
        #print('aircon_previous_power_rate =', settings['aircon_previous_power_rate'], 'aircon_current_power_rate =', current_power_rate)
        if current_power_rate != settings['aircon_previous_power_rate']: # If the power rate has changed
            mgr.print_update("Power Rate Changed from $" + str(settings['aircon_previous_power_rate']) + " per kWh to $" + str(current_power_rate) + " per kWh on ")
            self.update_aircon_power_log(power_mode, current_power_rate, time.time(), log_aircon_cost_data)  # Update aircon power log if there's a change of power rate
        if power_mode != settings['aircon_previous_power_mode']: # If the aircon power_mode has changed
            self.update_aircon_power_log(power_mode, current_power_rate, time.time(), log_aircon_cost_data)  # Update aircon power log if there's a change of power_mode
        return power_mode, settings                   
        
    def check_power_rate(self, update_date_time):
        update_day = update_date_time.strftime('%A')
        if update_day == 'Saturday' or update_day == 'Sunday':
            power_rates = self.aircon_weekend_power_rates # Weekend rates not seasonal
        else:
            power_rates = self.aircon_weekday_power_rates[self.aircon_seasons_months[update_date_time.strftime('%B')]] # Weekday rates are seasonal
        update_hour = int(update_date_time.strftime('%H'))
        for time in power_rates:
            if update_hour >= time and update_hour <= power_rates[time]['stop_hour']:
                current_aircon_power_rate = power_rates[time]['rate']
        return current_aircon_power_rate
     
    def update_aircon_power_log(self, power_mode, current_power_rate, update_time, log_aircon_cost_data):
        #print('Current Power Rate is $' + current_power_rate + ' per kWh')
        aircon_current_cost_per_hour = round(current_power_rate * self.aircon_power_consumption[power_mode], 2)
        if self.settings['aircon_previous_power_mode'] == 'Off': # Don't log anything if the previous aircon power_mode was off
            mgr.print_update(self.name + ' started in ' + power_mode + ' mode at a cost of $' + str(aircon_current_cost_per_hour) + ' per hour on ')
        else:
            aircon_previous_power_mode_time_in_hours = (update_time - self.settings['aircon_previous_update_time'])/3600
            aircon_previous_cost = round(aircon_previous_power_mode_time_in_hours * self.settings['aircon_previous_cost_per_hour'], 2)
            self.aircon_running_costs['total_cost'] = self.aircon_running_costs['total_cost'] + aircon_previous_cost
            self.aircon_running_costs['total_hours'] = self.aircon_running_costs['total_hours'] + aircon_previous_power_mode_time_in_hours
            self.total_aircon_average_cost_per_hour = self.aircon_running_costs['total_cost'] / self.aircon_running_costs['total_hours']
            if power_mode != 'Off':
                mgr.print_update('Aircon changed to ' + power_mode + ' mode that will cost $' + str(aircon_current_cost_per_hour) + ' per hour on ')
            else:
                mgr.print_update('Aircon changed to ' + power_mode + ' mode on ')
            print('Previous ' + self.name + ' mode was', self.settings['aircon_previous_power_mode'], 'for', str(round(aircon_previous_power_mode_time_in_hours*60, 1)), 'minutes at a cost of $' + str(round(aircon_previous_cost, 2)))
            print('Total ' + self.name + ' operating cost is $'+ str(round(self.aircon_running_costs['total_cost'], 2)) + ' over ' + str(round(self.aircon_running_costs['total_hours'], 1))
                  + ' hours with an average operating cost of $' + str(round(self.total_aircon_average_cost_per_hour, 2)) + ' per hour')
            if log_aircon_cost_data:
                today = datetime.now()
                time_data = self.get_local_time()
                time_stamp = today.strftime('%A %d %B %Y @ %H:%M:%S')
                json_log_data = {'Time Data': time_data, 'Time': time_stamp, 'Total Hours': round(self.aircon_running_costs['total_hours'], 1), 'Total Cost': round(self.aircon_running_costs['total_cost'], 2),
                                 'Current Mode': power_mode, 'Previous Mode': self.settings['aircon_previous_power_mode'], 'Previous Mode Minutes': round(aircon_previous_power_mode_time_in_hours*60, 1),
                                 'Previous Cost': round(aircon_previous_cost, 2)}
                with open(self.aircon_config['Cost Log'], 'a') as f:
                    f.write(',\n' + json.dumps(json_log_data))  
        #print('aircon_previous_power_rate =', self.settings['aircon_previous_power_rate'], 'aircon_previous_power_mode =', self.settings['aircon_previous_power_mode'])
        self.settings['aircon_previous_power_rate'] = current_power_rate
        self.settings['aircon_previous_update_time'] = update_time
        self.settings['aircon_previous_power_mode'] = power_mode
        self.settings['aircon_previous_cost_per_hour'] = aircon_current_cost_per_hour
        #print('aircon_previous_power_rate =', self.settings['aircon_previous_power_rate'], 'aircon_previous_power_mode =', self.settings['aircon_previous_power_mode'])

    def move_damper(self, damper_percent, power_mode, log_damper_data): # Called by 'control_aircon' to move damper to a nominated zone
        #print_update("Move Damper to " + str(damper_percent) + " percent at ")
        if log_damper_data:
            today = datetime.now()
            time_data = self.get_local_time()
            time_stamp = today.strftime('%A %d %B %Y @ %H:%M:%S')
            current_temps = {thermostat: self.thermostat_status[thermostat]['Current Temperature'] for thermostat in self.thermostat_status}
            target_temps = {thermostat: self.thermostat_status[thermostat]['Target Temperature'] for thermostat in self.thermostat_status}
            json_log_data = {'Time Data': time_data, 'Time': time_stamp, 'Damper Percent': damper_percent, 'Mode': power_mode, 'Thermostat Current Temps': current_temps, 'Thermostat Target Temps': target_temps,
                             'Day Zone Current Temp': self.settings['day_zone_current_temperature'], 'Night Zone Current Temp': self.settings['night_zone_current_temperature'],
                              'Day Zone Target Temp': self.settings['day_zone_target_temperature'], 'Night Zone Target Temp': self.settings['night_zone_target_temperature']}
            with open(self.aircon_config['Damper Log'], 'a') as f:
                f.write(',\n' + json.dumps(json_log_data))
        aircon_json = {}
        aircon_json['service'] = 'Damper Percent'
        aircon_json['value'] = damper_percent
        if damper_percent > self.status['Damper']:
            position_state = 'Opening'
        elif damper_percent < self.status['Damper']:
            position_state = 'Closing'
        else:
            position_state = 'Stopped'
        client.publish(self.outgoing_mqtt_topic, json.dumps(aircon_json))
        homebridge.set_target_damper_position(self.name, damper_percent, position_state)

    def set_dual_zone_damper(self, day_zone_gap, night_zone_gap, day_zone_gap_max, night_zone_gap_max, power_mode): # Called by control_aircon in dual zone mode to set the damper to an optimal position, based on relative temperature gaps
        optimal_day_zone = self.settings['previous_optimal_day_zone'] # Start with optimal_day_zone set to the previous setting
        if power_mode != 'Idle': # Only set damper based on temp zone gaps if the aircon is not in idle mode
            # Only adjust damper if either zone gap has changed by at least 0.2 degrees in order to minimise damper movements
            if abs(day_zone_gap - self.settings['previous_day_zone_gap']) >= 0.2 or abs(night_zone_gap - self.settings['previous_night_zone_gap']) >= 0.2:
                # The first three checks are to avoid cases where the dual damper algorithm has its denominator = 0
                if day_zone_gap == 0 and night_zone_gap == 0: # If both zones are equal to their target temperatures
                    print('Damper Algorithm: Both Zone are equal to their target temperatures. Balance Zones')
                    optimal_day_zone = self.damper_balanced # Balance zones
                elif day_zone_gap > 0 and night_zone_gap < 0: # If the Night Zone is the only zone that's passed its target temperature
                    print('Damper Algorithm: Night Zone Passed Target Temperature. Move Damper towards Day Zone')
                    optimal_day_zone = self.settings['previous_optimal_day_zone'] + 50 # Move damper 50% towards Day Zone
                elif day_zone_gap < 0 and night_zone_gap > 0: # If the Day Zone is the only zone that's passed its target temperature
                    print('Damper Algorithm: Day Zone Passed Target Temperature. Move Damper towards Night Zone')
                    optimal_day_zone = self.settings['previous_optimal_day_zone'] - 50 # Move damper 50% towards Night Zone
                else: # If both zones have passed their target temperatures or neither zone has passed its target temperature or only one zone is equal to its target temperature
                    day_proportion = day_zone_gap / (day_zone_gap + night_zone_gap)
                    night_proportion = night_zone_gap / (day_zone_gap + night_zone_gap)
                    if day_zone_gap >= 0 and night_zone_gap >= 0: # If neither zone has passed its target temperature
                        print('Damper Algorithm: Neither Zone Passed its target Temperature')
                        optimal_day_zone_not_passed = self.damper_balanced * day_proportion / (self.damper_balanced/100 * day_proportion + (1-self.damper_balanced/100) * night_proportion)
                        optimal_day_zone = optimal_day_zone_not_passed
                    else: # At least one zone has passed its target temperature
                        print('Damper Algorithm: At least one zone has passed its Target Temperature')
                        if day_zone_gap_max == 0 and night_zone_gap_max == 0: # Don't change damper if both zones are almost at their max/min temps by equal amounts. This avoids an unnecessary damper change and potential temp overshoots/undershoots
                            optimal_day_zone = self.settings['previous_optimal_day_zone']
                        elif day_zone_gap_max < 0 and night_zone_gap_max >= 0: # Move damper towards night zone if only day zone has met or exceeded its max/min temp 
                            optimal_day_zone = self.settings['previous_optimal_day_zone'] - 50 # Move damper 50% towards Night Zone
                        elif night_zone_gap_max < 0 and day_zone_gap_max >= 0: # Move damper towards day zone if only night zone has met or exceeded its max/min temp 
                            optimal_day_zone = self.settings['previous_optimal_day_zone'] + 50 # Move damper 50% towards Day Zone
                        elif day_zone_gap_max >= 0 and night_zone_gap_max >= 0: # Optimise damper if neither zone has met its max/min temp
                            optimal_day_zone_passed = self.damper_balanced * night_proportion / (self.damper_balanced/100 * night_proportion + (1-self.damper_balanced/100) * day_proportion) # Inverted for negative zone temp gaps
                            optimal_day_zone = optimal_day_zone_passed
                        elif day_zone_gap_max < 0 and night_zone_gap_max < 0: # Optimise damper against max gaps if both zones have met or exceeded their max/min temps
                            if day_zone_gap_max == night_zone_gap_max:
                                optimal_day_zone = self.settings['previous_optimal_day_zone'] # Don't change damper if both zones have met or exceeded their max/min temps by the same amount. This avoids an unnecessary damper change and potential temp overshoots/undershoots
                            elif day_zone_gap_max < night_zone_gap_max:
                                optimal_day_zone = self.settings['previous_optimal_day_zone'] - 50 # Move damper 50% towards Night Zone if the Day Zone has exceeded its max/min temp by more than the Night Zone
                            else:
                                optimal_day_zone = self.settings['previous_optimal_day_zone'] + 50 # Move damper 50% towards Day Zone if the Night Zone has exceeded its max/min temp by more than the Day Zone
                        else:
                            print('Unforseen Max Temp Gap Damper setting. Day Zone Gap', day_zone_gap, 'Night Zone Gap', night_zone_gap)
                            optimal_day_zone = self.damper_balanced # Balance zones
                self.settings['previous_day_zone_gap'] = day_zone_gap # Capture the new day_zone_gap
                self.settings['previous_night_zone_gap'] = night_zone_gap # Capture the new night_zone_gap
        else:
            optimal_day_zone = self.damper_balanced # Balance zones if the aircon is in in Idle Mode
        self.settings['previous_optimal_day_zone'] = optimal_day_zone # Capture the new optimal_day_zone level
        if optimal_day_zone >= 95:
            set_day_zone = 100
        elif optimal_day_zone >= 85 and optimal_day_zone < 95:
            set_day_zone = 90
        elif optimal_day_zone >= 75 and optimal_day_zone < 85:
            set_day_zone = 80
        elif optimal_day_zone >= 65 and optimal_day_zone < 75:
            set_day_zone = 70
        elif optimal_day_zone >= 55 and optimal_day_zone < 65:
            set_day_zone = 60
        elif optimal_day_zone >= 45 and optimal_day_zone < 55:
            set_day_zone = 50
        elif optimal_day_zone >= 35 and optimal_day_zone < 45:
            set_day_zone = 40
        elif optimal_day_zone >= 25 and optimal_day_zone < 35:
            set_day_zone = 30
        elif optimal_day_zone >= 15 and optimal_day_zone < 25:
            set_day_zone = 20
        elif optimal_day_zone >= 5 and optimal_day_zone < 15:
            set_day_zone = 10
        else:
            set_day_zone = 0
        if self.settings['target_day_zone'] != set_day_zone: # If there's a change in the damper position
            self.settings['target_day_zone'] = set_day_zone # Capture the new damper position
            self.move_damper(self.settings['target_day_zone'], power_mode, self.log_damper_data)
            mgr.print_update('Both zones active for ' + self.name + '. Moving Damper to ' + str(self.settings['target_day_zone']) + ' Percent on ')
            print (self.name + ' Day Zone Gap is ' + str(day_zone_gap) + ' Degrees. Night Zone Gap is ' + str(night_zone_gap) + ' Degrees')
            print(self.name + ' Day Temp is ' + str(self.settings['day_zone_current_temperature']) + ' Degrees. Day Target Temp is '
                  + str(self.settings['day_zone_target_temperature']) + ' Degrees. Night Temp is ' +
                  str(self.settings['night_zone_current_temperature']) + ' Degrees. Night Target Temp is ' + str(self.settings['night_zone_target_temperature']) + ' Degrees')
              
    def populate_starting_aircon_effectiveness(self):
        # Read log file
        print('Retrieving', self.name, 'Effectiveness Log File')
        name = self.aircon_config['Effectiveness Log']
        with open(name, 'r') as f:
            logged_data = f.read()
        logged_data = logged_data + ']'
        if "Mode" in logged_data: # Only parse the data if something has been logged
            parsed_data = json.loads(logged_data)
            latest_heat_entry = 0
            latest_cool_entry = 0  
            for entry in range(len(parsed_data)):
                if parsed_data[entry]['Mode'] == 'Heat':
                    if entry > latest_heat_entry:
                        latest_heat_entry = entry
                if parsed_data[entry]['Mode'] == 'Cool':
                    if entry > latest_cool_entry:
                        latest_cool_entry = entry
            if latest_heat_entry != 0:
                for key in self.max_heating_effectiveness:
                    #print(key, 'Max Heat', parsed_data[latest_heat_entry]["Max"][key])
                    #print(key, 'Min Heat', parsed_data[latest_heat_entry]["Min"][key])
                    self.max_heating_effectiveness[key] = parsed_data[latest_heat_entry]['Max'][key]
                    self.min_heating_effectiveness[key] = parsed_data[latest_heat_entry]['Min'][key]
            if latest_cool_entry != 0:
                for key in self.max_cooling_effectiveness:
                    #print(key, 'Max Cool', parsed_data[latest_cool_entry]["Max"][key])
                    #print(key, 'Min Cool', parsed_data[latest_cool_entry]["Min"][key])
                    self.max_cooling_effectiveness[key] = parsed_data[latest_cool_entry]['Max'][key]
                    self.min_cooling_effectiveness[key] = parsed_data[latest_cool_entry]['Min'][key]

    def populate_aircon_power_status(self):
        # Read log file
        name = self.aircon_config['Cost Log']
        with open(name, 'r') as f:
            data_log = f.read()
        data_log = data_log + ']'
        if "Total Cost" in data_log: # Only retrieve data is something has been logged
            parsed_data = json.loads(data_log)
            last_log_entry = parsed_data[-1]
            hours = last_log_entry["Total Hours"]
            print('Logged ' + self.name + ' Total Hours are', hours)
            self.aircon_running_costs['total_hours'] = hours     
            cost = last_log_entry["Total Cost"]
            print('Logged ' + self.name + ' Total Cost is $' + str(cost))
            self.aircon_running_costs['total_cost'] = cost
            print('Logged ' + self.name + ' Running Cost per Hour is $', str(round(cost/hours, 2)))
        else:
            print('No ' + self.name + ' Cost Data Logged')

class Foobot:
    def __init__(self, apikey, username, password):
        ## Minor adaptation to https://github.com/philipbl/pyfoobot to use the BlueAir homehost
        ## Thanks to https://github.com/mylesagray/homebridge-blueair
        
        """Authenticate the username and password."""
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.blueair_authorised = False
        self.homehost_found = False
        self.valid_user = False
        self.blueair_devices_found = False
        self.auth_header = {'Accept': 'application/json;charset=UTF-8',
                            'X-API-KEY-TOKEN': apikey}
        self.auth_header_1 = {'X-API-KEY-TOKEN': apikey}
        self.foobot_url = 'https://api.blueair.io'
        try:
            blue_air_authorisation = self.session.get(self.foobot_url, headers=self.auth_header_1)
            self.blueair_authorised = True
            print('BlueAir Authorised', blue_air_authorisation.json())
        except:
            print('BlueAir Authorisation Failed')
        if self.blueair_authorised:  
            blue_air_authorisation_json = blue_air_authorisation.json()
            homehost_request_url = self.foobot_url + '/v2/user/' + self.username + '/homehost/'
            try:
                home_host = self.session.get(homehost_request_url, headers=self.auth_header_1)
                self.homehost_found = True
                print('BlueAir Home Host Found', home_host.json())
            except:
                print('BlueAir Home Host not Found')
            if self.homehost_found:
                self.BASE_URL = 'https://' + home_host.json() + '/v2'
                token = self.login()
                if token is None:
                    print("BlueAir username or password is invalid")
                else:
                    self.auth_header['X-AUTH-TOKEN'] = token

    def login(self):
        """Log into a foobot device."""
        url = '{base}/user/{user}/login/'.format(base=self.BASE_URL,
                                                 user=self.username)
        try:
            req = self.session.get(url,
                               auth=(self.username, self.password),
                               headers=self.auth_header)
            if req.text == "true":
                self.valid_user = True
                print('BlueAir Logged In', req.json())
                return req.headers['X-AUTH-TOKEN']
            else:
                print('Invalid BlueAir Login')
                return None
        except:
            print('BlueAir Token Capture Failed')
            return None

    def devices(self):
        """Get list of foobot devices owned by logged in user."""
        url = '{base}/owner/{user}/device/'.format(base=self.BASE_URL,
                                                   user=self.username)
        try:
            req = self.session.get(url, headers=self.auth_header)
            self.blueair_devices_found = True
            print('Found BlueAir Devices', req.json())
        except:
            print("No BlueAir Devices Found")
        if self.blueair_devices_found:
            def create_device(device):
                """Helper to create a FoobotDevice based on a dictionary."""
                return FoobotDevice(auth_header=self.auth_header,
                                    user_id=device['userId'],
                                    uuid=device['uuid'],
                                    name=device['name'],
                                    mac=device['mac'], base_url=self.BASE_URL)
            return [create_device(device) for device in req.json()]
        else:
            return None

class FoobotDevice:
    ## Extracted from https://github.com/philipbl/pyfoobot
    """Represents a foobot device."""

    def __init__(self, auth_header, user_id, uuid, name, mac, base_url):
        """Create a foobot device instance used for getting data samples."""
        self.auth_header = auth_header
        self.user_id = user_id
        self.uuid = uuid
        self.name = name
        self.mac = mac
        self.BASE_URL = base_url
        self.session = requests.Session()

    def latest(self):
        """Get latest sample from foobot device."""
        url = '{base}/device/{uuid}/datapoint/{period}/last/{sampling}/'
        url = url.format(base=self.BASE_URL,
                         uuid=self.uuid,
                         period=0,
                         sampling=0)
        try:
            response_json = self.session.get(url, headers=self.auth_header, timeout=5).json()
            #print("Readings json", response_json)
            return response_json
        except requests.exceptions.ConnectionError as blueair_comms_error:
            print('BlueAir Latest Readings Connection Error', blueair_comms_error)
            return ('BlueAir Comms Error')
        except requests.exceptions.Timeout as blueair_comms_error:
            print('BlueAir Latest Readings Timeout Error', blueair_comms_error)
            return ('BlueAir Comms Error')
        except requests.exceptions.RequestException as blueair_comms_error:
            print('BlueAir Latest Readings Request Error', blueair_comms_error)
            return ('BlueAir Comms Error')
        except ValueError as blueair_comms_error:
            print('BlueAir Latest Readings Value Error', blueair_comms_error)
            return ('BlueAir Comms Error')
    
class BlueAirClass(object):
    ## Adds BlueAir control to Foobot and FoobotDevice Classes from https://github.com/philipbl/pyfoobot to use the BlueAir homehost
    ## Thanks to https://github.com/mylesagray/homebridge-blueair
    def __init__(self, name, air_purifier_devices, identifier):
        self.base_url = fb.BASE_URL
        self.session = requests.Session()
        self.auto = identifier['Auto']
        self.device = air_purifier_devices[identifier['Foobot Device']]
        self.name = name
        self.max_co2 = 0
        self.air_readings = {'part_2_5': 1, 'co2': 1, 'voc': 1, 'pol':1}
        self.air_reading_bands = {'part_2_5':[6, 12, 35, 150], 'co2': [500, 1000, 1600, 2000], 'voc': [120, 220, 660, 2200], 'pol': [20, 45, 60, 80]}
        self.co2_threshold = self.air_reading_bands['co2'][2]
        self.part_2_5_threshold = self.air_reading_bands['part_2_5'][2]
        self.previous_air_purifier_settings = {'Mode': 'null', 'Fan Speed': 'null', 'Child Lock':'null', 'LED Brightness': 'null', 'Filter Status':'null'}
        self.current_air_purifier_settings = {'Mode': 'null', 'Fan Speed': 'null', 'Child Lock':'null', 'LED Brightness': 'null', 'Filter Status':'null'}
        self.max_aqi = 1
        # Specify PM2_5 calibration adjustments
        self.part_2_5_offset = 0 # For calibration
        self.part_2_5_factor = 1 # For calibration

    def capture_readings(self): # Capture device readings
        if self.auto: # Readings only come from auto units
            self.readings_update_time = time.time()
            latest_data = self.device.latest()
            if (latest_data != 'BlueAir Comms Error') and (type(latest_data['datapoints'][0]) is list) and (len(latest_data['datapoints'][0]) > 6): # Capture New readings is there's valid data, otherwise, keep previous readings
                #mgr.print_update('Capturing Air Purifier Readings on ')
                part_2_5_raw_reading = latest_data['datapoints'][0][1]
                part_2_5_adjusted_reading = (part_2_5_raw_reading + self.part_2_5_offset) / self.part_2_5_factor
                if part_2_5_adjusted_reading >= 0: # Adjust PM2.5 Reading using calibration factor, ensuring that it never goes negative
                    self.air_readings['part_2_5'] = part_2_5_adjusted_reading
                else:
                    self.air_readings['part_2_5'] = 0
                self.air_readings['co2'] = latest_data['datapoints'][0][4]
                if self.air_readings['co2'] > self.max_co2:
                    self.max_co2 = self.air_readings['co2']
                    mgr.log_key_states("Max Co2 Change")
                self.air_readings['voc'] = latest_data['datapoints'][0][5]
                self.air_readings['pol'] = latest_data['datapoints'][0][6]
                self.max_aqi = 1
                for reading in self.air_readings: # Check each air quality parameter's reading
                    for boundary in range(3): # Check each reading against its AQI boundary
                        if self.air_readings[reading] >= self.air_reading_bands[reading][boundary]: # Find the boundary that the reading has exceeded 
                            aqi = boundary + 2 # Convert the boundary to the AQI reading
                            #print('Search Max AQI', aqi, reading, self.air_readings[reading])
                            if aqi > self.max_aqi: # If this reading has the maximum AQI so far, make it the max AQI
                                self.max_aqi = aqi
                                max_reading = reading
                    #print('Air Quality Component:', reading, 'has an AQI Level of', aqi, 'with a reading of', round(self.air_readings[reading],0))
                if self.max_aqi > 1:
                    #print('AQI is at Level', self.max_aqi, 'due to', max_reading, 'with a reading of', round(self.air_readings[max_reading],0))
                    pass
                else:
                    #print('AQI is at Level 1')
                    pass
            else:
                mgr.print_update(self.name + ' Air Purifier Readings Error on ')
            return(self.readings_update_time, self.air_readings['part_2_5'], self.air_readings['co2'], self.air_readings['voc'], self.max_aqi, self.max_co2, self.co2_threshold, self.part_2_5_threshold)
        else:
            pass

    def capture_settings(self): # Capture device settings
        self.settings_update_time = time.time()
        self.settings_changed = False
        air_purifier_settings = self.get_device_settings()
        if air_purifier_settings != 'BlueAir Comms Error': # Capture new settings is there's valid data, otherwise, keep previous settings
            #print('Capturing Air Purifier Settings for', self.name)
            if (type(air_purifier_settings) is list) and (len(air_purifier_settings) > 9):
                self.current_air_purifier_settings['LED Brightness'] = air_purifier_settings[1]['currentValue']
                self.current_air_purifier_settings['Child Lock'] = air_purifier_settings[2]['currentValue']
                self.current_air_purifier_settings['Fan Speed'] = air_purifier_settings[5]['currentValue']
                self.current_air_purifier_settings['Filter Status'] = air_purifier_settings[8]['currentValue']
                self.current_air_purifier_settings['Mode'] = air_purifier_settings[9]['currentValue']
                for setting in self.previous_air_purifier_settings:
                    if self.previous_air_purifier_settings[setting] != self.current_air_purifier_settings[setting]:
                        self.settings_changed = True
                        mgr.print_update(self.name + ' Air Purifier ' + setting + ' setting changed from ' + self.previous_air_purifier_settings[setting] + ' to ' +
                                         self.current_air_purifier_settings[setting] + ' on ')
                        self.previous_air_purifier_settings[setting] = self.current_air_purifier_settings[setting]
            else:
                mgr.print_update('Air Purifier Settings Data Format Error for ' + self.name + ' on ')
                print(air_purifier_settings)
        else:
            mgr.print_update(self.name + ' Air Purifier Settings Comms Error on ')
        return (self.settings_changed, self.settings_update_time, self.current_air_purifier_settings['Mode'],
                self.current_air_purifier_settings['Fan Speed'], self.current_air_purifier_settings['Child Lock'],
                self.current_air_purifier_settings['LED Brightness'], self.current_air_purifier_settings['Filter Status'])
            
    def inactive(self):
        self.set_fan_speed('0')

    def manual_mode(self):
        if self.auto:
            #print('Setting Manual Mode for the', self.device.name , 'Air Purifier')
            url = self.base_url + '/device/' + self.device.uuid + '/attribute/mode/'
            header = self.device.auth_header
            uuid = self.device.uuid
            body = {"currentValue": "manual", "scope": "device", "defaultValue": "auto", "name": "mode", "uuid": uuid}
            try:
                response = self.session.post(url, headers=header, json=body, timeout=5)
            except requests.exceptions.ConnectionError as blueair_comms_error:
                print('BlueAir Manual Mode Connection Error', blueair_comms_error)
            except requests.exceptions.Timeout as blueair_comms_error:
                print('BlueAir Manual Mode Timeout Error', blueair_comms_error)
            except requests.exceptions.RequestException as blueair_comms_error:
                print('BlueAir Manual Mode Request Error', blueair_comms_error)

    def auto_mode(self):
        if self.auto:
            #print('Setting Auto Mode for the', self.device.name , 'Air Purifier')
            url = self.base_url + '/device/' + self.device.uuid + '/attribute/mode/'
            header = self.device.auth_header
            uuid = self.device.uuid
            body = {"currentValue": "auto", "scope": "device", "defaultValue": "auto", "name": "mode", "uuid": uuid}
            try:
                response = self.session.post(url, headers=header, json=body, timeout=5)
            except requests.exceptions.ConnectionError as blueair_comms_error:
                print('BlueAir Auto Mode Connection Error', blueair_comms_error)
            except requests.exceptions.Timeout as blueair_comms_error:
                print('BlueAir Auto Mode Timeout Error', blueair_comms_error)
            except requests.exceptions.RequestException as blueair_comms_error:
                print('BlueAir Auto Mode Request Error', blueair_comms_error)
        else: # Set Fan Speed to 1 of it's a manual air purifier
            self.set_fan_speed('1')

    def set_fan_speed(self, fan_speed):
        #print('Setting Fan Speed to', fan_speed, 'for the', self.device.name + 'Air Purifier')
        url = self.base_url + '/device/' + self.device.uuid + '/attribute/fanspeed/'
        header = self.device.auth_header
        uuid = self.device.uuid
        body = {"currentValue": fan_speed, "scope": "device", "defaultValue": "1", "name": "fan_speed", "uuid": uuid}
        try:
            response = self.session.post(url, headers=header, json=body, timeout=5)
        except requests.exceptions.ConnectionError as blueair_comms_error:
            print('BlueAir Fan Speed Connection Error', blueair_comms_error)
        except requests.exceptions.Timeout as blueair_comms_error:
            print('BlueAir Fan Speed Timeout Error', blueair_comms_error)
        except requests.exceptions.RequestException as blueair_comms_error:
            print('BlueAir Fan Speed Request Error', blueair_comms_error)

    def set_led_brightness(self, brightness):
        #print('Setting LED Brightness for the', self.device.name , 'Air Purifier')
        url = self.base_url + '/device/' + self.device.uuid + '/attribute/brightness/'
        header = self.device.auth_header
        uuid = self.device.uuid
        body = {"currentValue": brightness, "scope": "device", "defaultValue": "4", "name": "brightness", "uuid": uuid}
        try:
            response = self.session.post(url, headers=header, json=body, timeout=5)
        except requests.exceptions.ConnectionError as blueair_comms_error:
            print('BlueAir LED Brightness Connection Error', blueair_comms_error)
        except requests.exceptions.Timeout as blueair_comms_error:
            print('BlueAir LED Brightness Timeout Error', blueair_comms_error)
        except requests.exceptions.RequestException as blueair_comms_error:
            print('BlueAir LED Brightness Request Error', blueair_comms_error)
        
    def set_child_lock(self, lock):
        #print('Setting Child Lock for the', self.device.name , 'Air Purifier')
        url = self.base_url + '/device/' + self.device.uuid + '/attribute/child_lock/'
        header = self.device.auth_header
        uuid = self.device.uuid
        body = {"currentValue": lock, "scope": "device", "defaultValue": "0", "name": "child_lock", "uuid": uuid}
        try:
            response = self.session.post(url, headers=header, json=body, timeout=5)
        except requests.exceptions.ConnectionError as blueair_comms_error:
            print('BlueAir Child Lock Connection Error', blueair_comms_error)
        except requests.exceptions.Timeout as blueair_comms_error:
            print('BlueAir Child Lock Timeout Error', blueair_comms_error)
        except requests.exceptions.RequestException as blueair_comms_error:
            print('BlueAir Child Lock Request Error', blueair_comms_error)
            
    def get_device_settings(self):
        url = '{base}/device/{uuid}/attributes/'
        url = url.format(base=self.base_url, uuid=self.device.uuid)
        try:
            response_json = self.session.get(url, headers=self.device.auth_header, timeout=5).json()
            #print("Settings json", response_json)
            return response_json
        except requests.exceptions.ConnectionError as blueair_comms_error:
            print('BlueAir Settings Connection Error', blueair_comms_error)
            return ('BlueAir Comms Error')  
        except requests.exceptions.Timeout as blueair_comms_error:
            print('BlueAir Settings Timeout Error', blueair_comms_error)
            return ('BlueAir Comms Error')
        except requests.exceptions.RequestException as blueair_comms_error:
            print('BlueAir Settings Request Error', blueair_comms_error)
            return ('BlueAir Comms Error')
        except ValueError as blueair_comms_error:
            print('BlueAir Settings Value Error', blueair_comms_error)
            return ('BlueAir Comms Error')

class SeneyeClass:
    def __init__(self, username, password):   
        """Authenticate the username and password."""
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.BASE_URL = 'https://api.seneye.com/v1'

    def devices(self):
        """Get list of Seneye devices owned by logged in user."""
        url = '{base}/devices?user={user}&pwd={password}'.format(base=self.BASE_URL,
                                                   user=self.username,password=self.password)
        req = self.session.get(url, timeout=5)
        return req.json()
    
    def latest(self):
        """Get latest sample from Seneye device."""
        url = '{base}/devices/?IncludeState=1&user={user}&pwd={password}'
        url = url.format(base=self.BASE_URL,user=self.username,password=self.password)
        try:
            valid_reading = True
            readings = self.session.get(url, timeout=5).json()
            out_of_water = readings[0]['status']['out_of_water']
            if out_of_water != "0":
                print('Seneye Out of Water')
                valid_reading = False
            wrong_slide = readings[0]['status']['wrong_slide']
            if wrong_slide != "0":
                print('Wrong Seneye Slide')
                valid_reading = False
            disconnected = readings[0]['status']['disconnected']
            if disconnected != "0":
                print('Seneye Disconnected')
                valid_reading = False
            slide_expires = int(readings[0]['status']['slide_expires'])
            if time.time() > slide_expires:
                print('Seneye Slide Expired')
                valid_reading = False
            last_experiment = int(readings[0]['status']['last_experiment'])
            if valid_reading:
                ph = readings[0]['exps']['ph']['curr']
                temp = readings[0]['exps']['temperature']['curr']
                nh3 = readings[0]['exps']['nh3']['curr']
                return valid_reading, 'Seneye Comms Good', ph, temp, nh3, last_experiment
            else:
                return valid_reading,'Seneye Comms Good', 0, 0, 0, 0
        except requests.exceptions.ConnectionError as seneye_comms_error:
            valid_reading = False
            print('Seneye Latest Readings Connection Error', seneye_comms_error)
            return valid_reading,'Seneye Comms Error', 0, 0, 0, 0
        except requests.exceptions.Timeout as seneye_comms_error:
            valid_reading = False
            print('Seneye Latest Readings Timeout Error', seneye_comms_error)
            return valid_reading,'Seneye Comms Error', 0, 0, 0, 0
        except requests.exceptions.RequestException as seneye_comms_error:
            valid_reading = False
            print('Seneye Latest Readings Request Error', seneye_comms_error)
            return valid_reading,'Seneye Comms Error', 0, 0, 0, 0
        except ValueError as seneye_comms_error:
            valid_reading = False
            print('Seneye Latest Readings Value Error', seneye_comms_error)
            return valid_reading,'Seneye Comms Error', 0, 0, 0, 0

class EnviroClass(object):
    def __init__(self, name, enviro_config):
        #print ('Created Enviro Instance', name, enviro_config)
        self.name = name
        self.valid_enviro_aqi_readings = ['P1', 'P2.5', 'P10', 'Red', 'Oxi', 'NH3', 'CO2', 'VOC']
        self.valid_enviro_aqi_readings_no_gas = ['P1', 'P2.5', 'P10', 'CO2', 'VOC']
        self.valid_enviro_non_aqi_readings = ['Temp', 'Hum', 'Bar', 'Lux']
        self.valid_luftdaten_readings = ['P2.5', 'P10']
        self.air_reading_bands = {'P1':[0, 6, 17, 27, 35], 'P2.5':[0, 11, 35, 53, 70], 'P10': [0, 16, 50, 75, 100],
                                  'NH3': [0, 6, 2, 10, 15], 'Red': [0, 6, 10, 50, 75], 'Oxi': [0, 0.2, 0.4, 0.8, 1],
                                  'CO2': [0, 500, 1000, 1600, 2000], 'VOC': [0, 120, 220, 660, 2200]}
        self.PM2_5_alert_level = 35
        self.max_aqi = 1
        self.enviro_config = enviro_config
        self.max_CO2 = 0
        self.CO2_threshold = self.air_reading_bands['CO2'][2]

    def capture_readings(self, source, parsed_json):
        #print('Capturing Enviro Readings', source, parsed_json)
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
                    # Convert ppm to ug/m3 for Outdoor homebridge gases data (except for Red and NH3, which is in mg/m3)
                    if reading == 'Oxi':
                        homebridge_data[reading] = round(1000* parsed_json[reading] * 46/24.45, 0)
                    elif reading == 'Red':
                        homebridge_data[reading] = round(parsed_json[reading] * 28/24.45, 2)
                    elif reading == 'NH3':
                        homebridge_data[reading] = round(parsed_json[reading] * 17/24.45, 2)
                    else:
                        homebridge_data[reading] = parsed_json[reading]
                    if reading == 'CO2':
                        if parsed_json[reading] > self.max_CO2:
                            print('Old Max CO2:', self.max_CO2)
                            self.max_CO2 = parsed_json[reading]
                            print('New Max CO2:', self.max_CO2)
                            mgr.log_key_states("Enviro Max CO2 Change")
                elif reading in self.valid_enviro_non_aqi_readings:
                    if self.enviro_config['Capture Temp/Hum/Bar/Lux']:
                        homebridge_data[reading] = parsed_json[reading]
                        domoticz_data[reading] = parsed_json[reading]
                else:
                    pass # Ignore other readings  
            #print(self.name, 'Air Quality Update. Overall AQI:', self.max_aqi, 'Individual AQI:', individual_aqi)
            #print(self.name, 'Domoticz Data:', domoticz_data)
            #print(self.name, 'Homebridge Data:', homebridge_data)
            homebridge.update_enviro_aqi(self.name, self.enviro_config, self.max_aqi, homebridge_data, individual_aqi,
                                         self.PM2_5_alert_level, gas_readings, self.max_CO2, self.CO2_threshold)
            domoticz.update_enviro_aqi(self.name, self.enviro_config, self.max_aqi, domoticz_data)

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
                #except ConnectionRefusedError as e:
                    #captured_data = {}
                    #print('Luftdaten Connection Refused Error', e)
                    #return "Data Not Captured", captured_data
                #except aiohttp.client_exceptions.ClientConnectorError as e:
                    #captured_data = {}
                    #print('Luftdaten Connection Error', e)
                    #return "Data Not Captured", captured_data
                #except requests.exceptions.ConnectionError as e:
                    #captured_data = {}
                    #print('Luftdaten Connection Error', e)
                    #return "Data Not Captured", captured_data
                #except ValueError as e:
                    #captured_data = {}
                    #print('Luftdaten Value Error', e)
                    #return "Data Not Captured", captured_data
            loop = asyncio.get_event_loop()
            message, captured_data = loop.run_until_complete(main())
            if message == "Data Captured":
                self.capture_readings('Luftdaten', captured_data)
        except:
            print('Luftdaten Error, No Outdoor Enviro Data Available')
            
class EVChargerClass(object):
    def __init__(self):
        #print ('Instantiated EV Charger', self)
        self.outgoing_mqtt_topic = 'ttn/<Your TTN Application ID>/down'
        # Set up EV Charger status dictionary with initial states set
        self.state = {'Not Connected': False, 'Connected and Locked': False, 'Charging': False,
                        'Charged': False}
        self.locked_state = False
        
    def capture_ev_charger_state(self, parsed_json):
        # Sync HomeManager's charger status and homebridge EV charger button settings with the EV charger
        # monitor status when an mqtt status update message is received from the EV charger monitor 
        if "ACK" in parsed_json:
            print("Received", parsed_json)
            homebridge.process_ev_charger_acks(parsed_json)           
        else: # Process State Update
            mgr.print_update('EV Charger State Update on ')
            #print(parsed_json)
            for state_item in self.state:# Check which state has been received
                if state_item == parsed_json: # Found which received state
                    if self.state[state_item]: # If it's already set to True
                        state_changed = False # Flag that it hasn't changed
                    else:
                        state_changed = True # Flag that it's changed so that it can be logged as a key_state change
                        new_state = state_item
                        self.state[state_item] = True # Set received item state to True
                else:
                    self.state[state_item] = False # Set other states to False
            if state_changed:
                mgr.print_update('EV Charger State Changed to ' + new_state + ' on ')
                mgr.log_key_states("EV Charger State Change") # Log state change
            homebridge.update_ev_charger_state(self.state, self.locked_state) # Send update to homebridge
        
    def process_ev_button(self, button_name):
        #print("Button Name", button_name)
        ev_charger_json = {"port": 1, "confirmed": True}
        valid_button = True
        if button_name == 'Lock Charger':
            print ("Locking EV Charger")
            self.locked_state = True
            homebridge.update_ev_charger_state(self.state, self.locked_state) # Send update to homebridge
            mgr.log_key_states("EV Charger Lock State Change")
            ev_charger_json["payload_fields"] = {"mode": "Lock Outlet"}
        elif button_name == 'Unlock Charger':
            print ("Unlocking EV Charger")
            self.locked_state = False
            homebridge.update_ev_charger_state(self.state, self.locked_state) # Send update to homebridge
            mgr.log_key_states("EV Charger Lock State Change")
            ev_charger_json["payload_fields"] = {"mode": "Unlock Outlet"}
        elif button_name == 'Reset Charger':
            print ("Resetting EV Charger")
            self.locked_state = False
            homebridge.update_ev_charger_state(self.state, self.locked_state) # Send update to homebridge
            mgr.log_key_states("EV Charger Lock State Change")
            ev_charger_json["payload_fields"] = {"mode": "Reset Charger"}
        else:
            valid_button = False
        if valid_button:
            # Send button message to the EV Controller
            client.publish(self.outgoing_mqtt_topic, json.dumps(ev_charger_json))
            
if __name__ == '__main__': # This is where to overall code kicks off
    # Create a Home Manager instance
    mgr = NorthcliffHomeManagerClass(log_aircon_cost_data = True, log_aircon_damper_data = False, log_aircon_temp_data = False,
                                     load_previous_aircon_effectiveness = True, perform_homebridge_config_check = False)
    # Create a Homebridge instance
    homebridge = HomebridgeClass(mgr.outdoor_multisensor_names, mgr.outdoor_sensors_homebridge_name, mgr.aircon_config, mgr.auto_air_purifier_names,
                                 mgr.window_blind_config, mgr.door_sensor_names_locations, mgr.light_dimmer_names_device_id, mgr.colour_light_dimmer_names,
                                 mgr.air_purifier_names, mgr.multisensor_names, mgr.powerpoint_names_device_id, mgr.flood_sensor_names, mgr.enviro_config)
    # Create a Domoticz instance
    domoticz = DomoticzClass()
    if mgr.doorbell_present:
        # Create Doorbell instance
        doorbell = DoorbellClass()
    if mgr.aircons_present:
        # Use a dictionary comprehension to create an aircon instance for each aircon.
        aircon = {aircon_name: AirconClass(aircon_name, mgr.aircon_config[aircon_name], mgr.log_aircon_cost_data,
                                      mgr.log_aircon_damper_data, mgr.log_aircon_temp_data) for aircon_name in mgr.aircon_config}
    if mgr.window_blinds_present:
        # Use a dictionary comprehension to create a window blind instance for each window blind
        window_blind = {blind_room: WindowBlindClass(blind_room, mgr.window_blind_config[blind_room]) for blind_room in mgr.window_blind_config}    
    if mgr.multisensors_present:
        # Use a dictionary comprehension to create a multisensor instance for each multisensor
        multisensor = {name: MultisensorClass(name, mgr.aircon_temp_sensor_names, mgr.aircon_sensor_name_aircon_map, mgr.window_blind_config,
                                          mgr.log_aircon_temp_data) for name in mgr.multisensor_names}      
    if mgr.door_sensors_present:
        # Use a dictionary comprehension to create a door sensor instance for each door
        door_sensor = {name: DoorSensorClass(name, mgr.door_sensor_names_locations[name], mgr.window_blind_config, mgr.doorbell_door) for name in mgr.door_sensor_names_locations}      
    if mgr.light_dimmers_present:
        # Use a dictionary comprehension to create a light dimmer instance for each dimmer, with its idx number, initial switch state as False and initial brightness value 0%
        light_dimmer = {name: LightDimmerClass(name, mgr.light_dimmer_names_device_id[name], False, 0) for name in mgr.light_dimmer_names_device_id}
    if mgr.powerpoints_present:
        # Use a dictionary comprehension to create a powerpoint instance for each powerpoint, with its idx number, initial switch state as False
        powerpoint = {name: PowerpointClass(name, mgr.powerpoint_names_device_id[name], 0) for name in mgr.powerpoint_names_device_id}
    if mgr.flood_sensors_present:
        # Use a dictionary comprehension to create a flood sensor instance for each flood sensor
        flood_sensor = {name: FloodSensorClass(name) for name in mgr.flood_sensor_names}
    if mgr.garage_door_present:
        # Create a Garage Door Controller instance
        garage_door = GaragedoorClass()
    if mgr.air_purifiers_present:
        # Create a Foobot instance
        key = "<foobot_api_key>"
        fb = Foobot(key, "<foobot_user_name>", "<foobot_user_password>")
        if fb.valid_user:
            air_purifier_devices = fb.devices() # Capture foobot device data
            if air_purifier_devices != None:
                # Use a dictionary comprehension to create an air purifier instance for each air purifier
                air_purifier = {name: BlueAirClass(name, air_purifier_devices, mgr.air_purifier_names[name]) for name in mgr.air_purifier_names}
            else:
                mgr.air_purifiers_present = False
        else:
            mgr.air_purifiers_present = False
    if mgr.aquarium_monitor_present:
        # Create a Seneye Aquarium Sensor instance
        aquarium_sensor = SeneyeClass("<seneye_user_name>", "<seneye_user_password>")
    if mgr.enviro_monitors_present:
        # Create Enviro Monitor instance for each Enviro Name
        enviro_monitor = {name: EnviroClass(name, mgr.enviro_config[name]) for name in mgr.enviro_config}
    if mgr.ev_charger_present:
        # Create EV Charger instance
        ev_charger = EVChargerClass()
    # Create and set up an mqtt instance                             
    client = mqtt.Client("<mqtt client name>")
    client.on_connect = mgr.on_connect
    client.on_message = mgr.on_message
    client.connect("<mqtt broker name>", 1883, 60)
    # Blocking call that processes network traffic, dispatches callbacks and handles reconnecting.
    client.loop_start()
    mgr.run()
