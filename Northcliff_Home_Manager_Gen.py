#Northcliff Home Manager - 7.32 Gen
#!/usr/bin/env python

import paho.mqtt.client as mqtt
import struct
import time
from datetime import datetime
import string
import json
import socket
import requests
import os

class NorthcliffHomeManagerClass(object):
    def __init__(self):
        #print ('Instantiated Home Manager', self)
        # Set up property data
        # List the rooms under management
        self.property_rooms = ['Lounge', 'Living', 'TV', 'Dining', 'Study', 'Kitchen', 'Hallway', 'North', 'South', 'Main', 'Rear Balcony', 'North Balcony', 'South Balcony']
        # List the multisensor names
        self.multisensor_names = ['Living', 'Study', 'Kitchen', 'North', 'South', 'Main', 'Rear Balcony', 'North Balcony', 'South Balcony']
        # List the outdoor sensors
        self.outdoor_zone = ['Rear Balcony', 'North Balcony', 'South Balcony']
        # Group outdoor sensors in one homebridge "room" name for passing to the homebridge object
        self.outdoor_sensors_homebridge_name = 'Balconies'
        # Name each door sensor and identify the room that contains that door sensor
        self.door_sensor_names_locations = {'North Living Room': 'Living Room', 'South Living Room': 'Living Room', 'Entry': 'Entry'}
        # Name each powerpoint and map to its device id
        self.powerpoint_names_device_id = {'Living': 646, 'South Balcony': 626, 'North Balcony': 647}
        # List the flood sensors
        self.flood_sensor_names = ['Kitchen', 'Laundry']
        # Name each light dimmer and map to its device id
        self.light_dimmer_names_device_id = {'Lounge': 323, 'TV': 325, 'Dining': 324, 'Study': 648, 'Kitchen': 504, 'Hallway': 328, 'North': 463,
                                              'South': 475, 'Main': 451, 'North Balcony': 517, 'South Balcony': 518, 'Window': 721}
        # Set up the config for each aircon. At present, the homebridge, domoticz and aircon classes don't have the ability to manage multiple aircons.
        # They're currently hard coded with the 'Aircon' object label but this config dictionary allows multiple aircon to be supported in the future.
        self.aircon_config = {'Aircon': {'mqtt Topics': {'Outgoing':'AirconControl', 'Incoming': 'AirconStatus'}, 'Day Zone': ['Living', 'Study', 'Kitchen'],
                                         'Night Zone': ['North', 'South', 'Main'], 'Indoor Zone': ['Indoor']}}
        self.log_aircon_cost_data = True # Flags if the aircon cost data is to be logged
        self.log_aircon_damper_data = True # Flags if the aircon damper data is to be logged
        self.log_aircon_temp_data = True # Flags if the aircon temperature data is to be logged
        self.homebridge_incoming_mqtt_topic = 'homebridge/from/set'
        self.homebridge_outgoing_mqtt_topic = 'homebridge/to/set'
        self.domoticz_incoming_mqtt_topic = 'domoticz/out'
        self.domoticz_outgoing_mqtt_topic = 'domoticz/in'
        self.doorbell_incoming_mqtt_topic = 'DoorbellStatus'
        self.doorbell_outgoing_mqtt_topic = 'DoorbellButton'
        self.garage_door_incoming_mqtt_topic = 'GarageStatus'
        self.garage_door_outgoing_mqtt_topic = 'GarageControl'  
        # Set up the config for each window blind
        self.window_blind_config = {'Living Room Blinds': {'blind ip address': '<mylink ip address>', 'blind port': 44100, 'light sensor': 'South Balcony',
                                                            'temp sensor': 'North Balcony', 'sunlight threshold 0': 100,'sunlight threshold 1': 1000,
                                                            'sunlight threshold 2': 12000, 'sunlight threshold 3': 20000, 'high_temp_threshold': 27.5,
                                                            'low_temp_threshold': 15.5,
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
        # List the temperature sensors that control aircons
        self.aircon_temp_sensor_names = []
        for aircon in self.aircon_config:
            self.aircon_temp_sensor_names = self.aircon_temp_sensor_names + self.aircon_config[aircon]['Day Zone'] + self.aircon_config[aircon]['Night Zone']
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
                   
    def on_connect(self, client, userdata, flags, rc):
        # Sets up the mqtt subscriptions. Subscribing in on_connect() means that if we lose the connection and reconnect then subscriptions will be renewed.
        self.print_update('Northcliff Home Manager Connected with result code '+str(rc)+' on ')
        print('') 
    
    def on_message(self, client, userdata, msg):
        # Calls the relevant methods for the Home Manager, based on the mqtt publish messages received from the doorbell monitor, the homebridge buttons,
        # Domoticz, the aircon controller and the garage door controller
        decoded_payload = str(msg.payload.decode("utf-8"))
        parsed_json = json.loads(decoded_payload)
        if msg.topic == self.homebridge_incoming_mqtt_topic: # If coming from homebridge
            homebridge.capture_homebridge_buttons(parsed_json) # Capture the homebridge button
        elif msg.topic == self.domoticz_incoming_mqtt_topic: # If coming from domoticz
            domoticz.process_device_data(parsed_json) # Process the domoticz device data
        elif msg.topic == self.garage_door_incoming_mqtt_topic: # If coming from the Garage Door Controller
            garage_door.capture_status(parsed_json) # Capture garage door status
        elif msg.topic == self.doorbell_incoming_mqtt_topic: # If coming from the Doorbell Monitor
            doorbell.capture_doorbell_status(parsed_json) # Capture doorbell status
        else: # Test for aircon messages
            identified_message = False
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
        key_state_log = {'Door State': {}, 'Blind Status': {}, 'Blind Door State': {}, 'Blind Auto Override': {}, 'Powerpoint State': {}, 'Aircon Thermostat Status': {},
                          'Reason': reason}
        for aircon_name in self.aircon_config:
            key_state_log['Aircon Thermostat Status'][aircon_name] = {}
        for name in self.door_sensor_names_locations:
            key_state_log['Door State'][name] = door_sensor[name].current_door_opened
        for blind in self.window_blind_config:
            key_state_log['Blind Status'][blind] = self.window_blind_config[blind]['status']
            key_state_log['Blind Door State'][blind] = self.window_blind_config[blind]['blind_doors']
            key_state_log['Blind Auto Override'][blind] = window_blind[blind].auto_override
        for name in self.powerpoint_names_device_id:
            key_state_log['Powerpoint State'][name] = powerpoint[name].powerpoint_state
        for aircon_name in self.aircon_config:
            logged_thermostats = self.aircon_config[aircon_name]['Day Zone'] + self.aircon_config[aircon_name]['Night Zone']
            for thermostat in logged_thermostats:
                key_state_log['Aircon Thermostat Status'][aircon_name][thermostat] = aircon[aircon_name].thermostat_status[thermostat]
        #print('Key State Log', key_state_log)
        with open('/home/pi/HomeManager/key_state.log', 'w') as f:
            f.write(json.dumps(key_state_log))

    def retrieve_key_states(self):
        name = '/home/pi/HomeManager/key_state.log'
        f = open(name, 'r')
        parsed_key_states = json.loads(f.read())
        #print('Retrieved Key States', parsed_key_states)
        print ('Previous shutdown reason was', parsed_key_states['Reason'])
        for name in parsed_key_states['Door State']:
            door_sensor[name].current_door_opened = parsed_key_states['Door State'][name]
            door_sensor[name].previous_door_opened = parsed_key_states['Door State'][name]
            homebridge.update_door_state(name, self.door_sensor_names_locations[name], parsed_key_states['Door State'][name], False)
            if door_sensor[name].doorbell_door == True:
                doorbell.update_doorbell_door_state(self.doorbell_door, parsed_key_states['Door State'][name])
        for blind in parsed_key_states['Blind Status']:
            self.window_blind_config[blind]['status'] = parsed_key_states['Blind Status'][blind]
            homebridge.update_blind_status(blind, self.window_blind_config[blind])
        for blind in parsed_key_states['Blind Door State']:
            self.window_blind_config[blind]['blind_doors'] = parsed_key_states['Blind Door State'][blind]
        for blind in parsed_key_states['Blind Auto Override']:
            window_blind[blind].auto_override = parsed_key_states['Blind Auto Override'][blind]
            homebridge.set_auto_blind_override_button(blind, parsed_key_states['Blind Auto Override'][blind])
        for name in parsed_key_states['Powerpoint State']:
            powerpoint[name].powerpoint_state = parsed_key_states['Powerpoint State'][name]
            homebridge.update_powerpoint_state(name, parsed_key_states['Powerpoint State'][name])
        for aircon_name in self.aircon_config:
            for thermostat in parsed_key_states['Aircon Thermostat Status'][aircon_name]:
                aircon[aircon_name].thermostat_status[thermostat]['Target Temperature'] = parsed_key_states['Aircon Thermostat Status'][aircon_name][thermostat]['Target Temperature']
                homebridge.update_thermostat_target_temp(thermostat, parsed_key_states['Aircon Thermostat Status'][aircon_name][thermostat]['Target Temperature'])
                aircon[aircon_name].thermostat_status[thermostat]['Mode'] = parsed_key_states['Aircon Thermostat Status'][aircon_name][thermostat]['Mode']
                homebridge.update_aircon_thermostat(thermostat, parsed_key_states['Aircon Thermostat Status'][aircon_name][thermostat]['Mode'])
                aircon[aircon_name].thermostat_status[thermostat]['Active'] = parsed_key_states['Aircon Thermostat Status'][aircon_name][thermostat]['Active']
                
    def shutdown(self, reason):
        self.log_key_states(reason)
        # Shut down Aircons
        for aircon_name in self.aircon_config:
            aircon[aircon_name].shut_down()
        client.loop_stop() # Stop mqtt monitoring
        self.print_update('Home Manager Shut Down due to ' + reason + ' on ')
            

    def run(self): # The main Home Manager start-up, loop and shut-down code                          
        try:
            # Retrieve logged key states
            self.retrieve_key_states()
            homebridge.reset_reboot_button()
            # Capture Air Purifier readings and settings on startup and update homebridge
            for name in self.air_purifier_names:
                if self.air_purifier_names[name]['Auto'] == True: # Readings only come from auto units
                    self.purifier_readings_update_time, part_2_5, co2, voc, max_aqi, max_co2, co2_threshold, part_2_5_threshold = air_purifier[name].capture_readings()
                    homebridge.update_air_quality(name, part_2_5, co2, voc, max_aqi, max_co2, co2_threshold, part_2_5_threshold)
                    domoticz.update_air_quality(name, part_2_5, co2, voc, max_aqi)
                settings_changed, self.purifier_settings_update_time, mode, fan_speed, child_lock, led_brightness,filter_status = air_purifier[name].capture_settings()
                homebridge.set_air_purifier_state(name, mode, fan_speed, child_lock, led_brightness, filter_status)    
            # Start up Aircons
            for aircon_name in mgr.aircon_config:
                aircon[aircon_name].start_up()
            doorbell.update_doorbell_status() # Get doorbell status on startup
            # Initialise multisensor readings on homebridge to start-up settings
            for name in self.multisensor_names:    
                homebridge.update_temperature(name, multisensor[name].sensor_types_with_value['Temperature'])
                homebridge.update_humidity(name, multisensor[name].sensor_types_with_value['Humidity'])
                homebridge.update_light_level(name, multisensor[name].sensor_types_with_value['Light Level'])
                homebridge.update_motion(name, multisensor[name].sensor_types_with_value['Motion'])
            # Initialise Garage Door state
            homebridge.update_garage_door('Closing')
            homebridge.update_garage_door('Closed')
            while True: # The main Home Manager Loop
                aircon['Aircon'].control_aircon() # Call the method that controls the aircon. To do: Add support for mutliple aircons
                # The following tests and method calls are here in the main code loop, rather than the on_message method to avoid time.sleep calls in the window blind object delaying incoming mqtt message handling
                if self.call_room_sunlight_control['State'] == True: # If there's a new reading from the blind control light sensor
                    blind = self.call_room_sunlight_control['Blind'] # Identify the blind
                    light_level = self.call_room_sunlight_control['Light Level'] # Capture the light level
                    window_blind_config = self.window_blind_config[blind] # Use the config for the relevant blind
                    window_blind[blind].room_sunlight_control(light_level, window_blind_config) # Call the blind's sunlight control method, passing the light level and blind config
                    self.call_room_sunlight_control['State'] = False # Reset this flag because any light level update has now been actioned
                if self.blind_control_door_changed['Changed'] == True: # If a blind control door has changed state
                    blind = self.blind_control_door_changed['Blind'] # Identify the blind that is controlled by the door
                    light_level = self.call_room_sunlight_control['Light Level'] # Capture the light level
                    window_blind_config = self.window_blind_config[blind] # Use the config for the relevant blind. That config contains the updated door states
                    window_blind[blind].room_sunlight_control(light_level, window_blind_config) # Call the blind's sunlight control method, passing the light level and blind config
                    self.blind_control_door_changed['Changed'] = False # Reset Door Changed Flag because any change of door state has now been actioned
                if self.auto_blind_override_changed['Changed'] == True: # If a blind auto override button has changed state
                    blind = self.auto_blind_override_changed['Blind'] # Identify the blind that is controlled by the button
                    window_blind_config = self.window_blind_config[blind] # Use the config for the relevant blind. That config contains the updated override state
                    light_level = self.call_room_sunlight_control['Light Level'] # Capture the light level
                    window_blind[blind].room_sunlight_control(light_level, window_blind_config) # Call the blind's sunlight control method, passing the light level and blind config
                    self.auto_blind_override_changed['Changed'] = False # Reset Auto Override Flag because any change of override state has now been actioned
                if self.call_control_blinds['State'] == True: # If a manual blind change has been invoked
                    blind = self.call_control_blinds['Blind'] # Identify the blind that has been changed
                    self.window_blind_config[blind] = window_blind[blind].control_blinds(blind, self.call_control_blinds, self.window_blind_config[blind]) # Call the blind's manual control method, passing the blind config
                    self.call_control_blinds['State'] = False # Reset Control Blinds Flag because any control blind request has now been actioned
                purifier_readings_check_time = time.time()
                if (purifier_readings_check_time - self.purifier_readings_update_time) >= 300: # Update air purifier readings if last update was >= 5 minutes ago
                    for name in self.air_purifier_names:
                        if self.air_purifier_names[name]['Auto'] == True:# Readings only come from auto units
                            self.purifier_readings_update_time, part_2_5, co2, voc, max_aqi, max_co2, co2_threshold, part_2_5_threshold = air_purifier[name].capture_readings()
                            homebridge.update_air_quality(name, part_2_5, co2, voc, max_aqi, max_co2, co2_threshold, part_2_5_threshold)
                            domoticz.update_air_quality(name, part_2_5, co2, voc, max_aqi)
                purifier_settings_check_time = time.time()
                if (purifier_settings_check_time - self.purifier_settings_update_time) >= 5: # Update air purifier settings if last update was >= 5 seconds ago
                    for name in self.air_purifier_names:
                        settings_changed, self.purifier_settings_update_time, mode, fan_speed, child_lock, led_brightness, filter_status = air_purifier[name].capture_settings()
                        if settings_changed == True: # Only update Homebridge if a setting has changed (To minimise mqtt traffic)
                            homebridge.set_air_purifier_state(name, mode, fan_speed, child_lock, led_brightness, filter_status)
                  
        except KeyboardInterrupt:
            self.shutdown('Keyboard Interrupt')

class HomebridgeClass(object): # To do. Add ability to manage multiple aircons
    def __init__(self, outgoing_mqtt_topic, outdoor_zone, outdoor_sensors_name, aircon_config):
        #print ('Instantiated Homebridge', self)
        self.outgoing_mqtt_topic = outgoing_mqtt_topic
        self.outdoor_zone = outdoor_zone
        self.outdoor_sensors_name = outdoor_sensors_name
        self.temperature_format = {'service': 'TemperatureSensor', 'characteristic': 'CurrentTemperature'}
        self.indoor_temp_name = 'Temperature'
        self.temperature_service_name_format = ' Temp'
        self.humidity_format = {'service': 'HumiditySensor', 'characteristic': 'CurrentRelativeHumidity'}
        self.indoor_humidity_name = 'Temperature'
        self.humidity_service_name_format = ' Hum'
        self.light_level_format = {'service': 'LightSensor', 'characteristic': 'CurrentAmbientLightLevel'}
        self.indoor_light_level_name = 'Light'
        self.light_level_service_name_format = ' Lux'
        self.motion_format = {'service': 'MotionSensor', 'characteristic': 'MotionDetected'}
        self.indoor_motion_name = 'Motion'
        self.motion_service_name_format = ' Motion'
        self.door_state_format = {'service': 'ContactSensor'}
        self.door_state_characteristic = 'ContactSensorState'
        self.door_state_service_name_format = ' Door'
        self.door_battery_characteristic = 'StatusLowBattery'
        self.door_state_map = {'door_opened':{False: 0, True: 1}, 'low_battery':{False: 0, True: 1}}
        self.dimmer_format = {'name': 'Dimmer'}
        self.dimmer_characteristics = {'Adjust Light Brightness': 'Brightness', 'Switch Light State': 'On', 'Adjust Light Hue': 'Hue', 'Adjust Light Saturation': 'Saturation'}
        self.dimmer_state_map = {0: False, 1: True}
        self.blinds_format = {'name': ' Blinds'}
        self.blind_position_map = {100: 'Open', 50: 'Venetian', 0: 'Closed'}
        self.doorbell_format = {'name': 'Doorbell', 'characteristic': 'On'}
        # Set up homebridge switch types for doorbell (Indicator, Switch or TimedMomentary)
        self.doorbell_button_type = {'Terminated': 'Indicator', 'AutoPossible': 'Indicator', 'Triggered': 'Indicator',
                                     'OpenDoor': 'Momentary', 'Activated': 'Indicator', 'Automatic': 'Switch', 'Manual': 'Switch', 'Ringing': 'Motion'}
        self.powerpoint_format = {'name': 'Powerpoint', 'service': 'Outlet', 'service_name': ''}
        self.garage_door_format = {'name': 'Garage', 'service_name': 'Garage Door'}
        self.garage_door_characteristics = {'Current': 'CurrentDoorState','Target': 'TargetDoorState'}
        self.flood_state_format = {'name': 'Flood', 'service': 'LeakSensor'}
        self.flood_state_characteristic = 'LeakDetected'
        self.flood_battery_characteristic = 'StatusLowBattery'
        self.auto_blind_override_button_format = {'service_name': 'Auto Blind Override', 'characteristic': 'On'}
        self.aircon_thermostat_format = {'name': 'Aircon', 'service': 'Thermostat'} # To do. Add ability to manage multiple aircons
        self.aircon_ventilation_button_format = {'name': 'Aircon', 'service_name': 'Ventilation', 'characteristic': 'On'}
        self.aircon_thermostat_characteristics = {'Mode': 'TargetHeatingCoolingState', 'Current Temperature': 'CurrentTemperature', 'Target Temperature':'TargetTemperature'}
        self.aircon_thermostat_mode_map = {0: 'Off', 1: 'Heat', 2: 'Cool'}
        self.aircon_thermostat_incoming_mode_map = {'Off': 0, 'Heat': 1, 'Cool': 2}
        self.aircon_control_thermostat_name = aircon_config['Aircon']['Indoor Zone'][0]
        self.aircon_thermostat_names =  aircon_config['Aircon']['Day Zone'] + aircon_config['Aircon']['Night Zone'] + aircon_config['Aircon']['Indoor Zone'] # To do. Add ability to manage multiple aircons
        self.aircon_damper_format = {'name': 'Aircon', 'service': 'Door', 'service_name': 'Damper'} # To do. Add ability to manage multiple aircons
        self.aircon_status_format = {'name': 'Aircon'} # To do. Add ability to manage multiple aircons
        # Set up aircon homebridge button types (Indicator, Position Indicator or Thermostat Control)
        self.aircon_button_type = {'Remote Operation': 'Indicator', 'Heat': 'Indicator', 'Cool': 'Indicator',
                                    'Fan': 'Indicator', 'Fan Hi': 'Indicator', 'Fan Lo': 'Indicator',
                                    'Heating': 'Indicator', 'Compressor': 'Indicator', 'Terminated': 'Indicator',
                                    'Damper': 'Position Indicator', 'Clean Filter': 'Indicator', 'Malfunction': 'Indicator', 'Ventilation': 'Switch'}
        for name in self.aircon_thermostat_names:
            self.aircon_button_type[name] = 'Thermostat Control' # To do. Add ability to manage multiple aircons
        self.window_blind_position_map = {'Open': 100, 'Venetian': 50, 'Closed': 0}
        self.air_quality_format = {'name': 'Air Purifier'}
        self.air_quality_service_name_map = {'Living': 'Living Air Quality'}
        self.CO2_service_name_map = {'Living': 'Living CO2'}
        self.PM2_5_service_name_map = {'Living': 'Living PM2.5'}
        self.air_purifier_format = {'name': 'Air Purifier', 'service' :'AirPurifier'}
        self.air_purifier_filter_format = {'name': 'Air Purifier', 'service' :'FilterMaintenance'}
        self.reboot_format = {'name': 'Reboot', 'service_name': 'Reboot Arm', 'characteristic': 'On'}
        self.reboot_trigger_format = {'name': 'Reboot', 'service_name': 'Reboot Trigger', 'characteristic': 'On'}
        self.reboot_armed = False

    def capture_homebridge_buttons(self, parsed_json):
        if parsed_json['name'] == self.dimmer_format['name']: # If it's a dimmer button
            self.adjust_light_dimmer(parsed_json)
        elif self.blinds_format['name'] in parsed_json['name']: # If it's a blind button
            self.process_blind_button(parsed_json)
        elif parsed_json['name'] == self.doorbell_format['name']: # If it's a doorbell button
            self.process_doorbell_button(parsed_json)
        elif parsed_json['name'] == self.powerpoint_format['name']: # If it's a powerpoint button
            self.switch_powerpoint(parsed_json)
        elif parsed_json['name'] == self.garage_door_format['name']: # If it's a garage door button
            self.process_garage_door_button(parsed_json)
        elif parsed_json['name'] == self.aircon_thermostat_format['name']: # If it's an aircon button. # To do. Add ability to manage multiple aircons
            self.process_aircon_button(parsed_json)
        elif parsed_json['name'] == self.air_purifier_format['name']: # If it's an air purifier button.
            self.process_air_purifier_button(parsed_json)
        elif parsed_json['name'] == self.reboot_format['name']: # If it's a reboot button.
            self.process_reboot_button(parsed_json)
        else:
            print('Invalid homebridge button received:', parsed_json['name'])
            pass

    def adjust_light_dimmer(self, parsed_json):
        # Determine which dimmer needs to be adjusted and call the relevant dimmer object method
        # that then calls the Domoticz method to adjust the dimmer brightness or state
        dimmer_name = parsed_json['service_name']
        if parsed_json['characteristic'] == self.dimmer_characteristics['Adjust Light Brightness']:
            #print('Adjust Dimmer Brightness')
            brightness = int(parsed_json['value'])
            light_dimmer[dimmer_name].adjust_brightness(brightness)
        # Adjust dimmer state if a switch light state command has come from homebridge
        elif parsed_json['characteristic'] == self.dimmer_characteristics['Switch Light State']:
            light_state = parsed_json['value']
            light_dimmer[dimmer_name].on_off(light_state)
        # Adjust dimmer hue if a switch hue command has come from homebridge
        elif parsed_json['characteristic'] == self.dimmer_characteristics['Adjust Light Hue']:
            hue_value = parsed_json['value']
            light_dimmer[dimmer_name].adjust_hue(hue_value)
        # Adjust dimmer saturation if a saturation command has come from homebridge
        elif parsed_json['characteristic'] == self.dimmer_characteristics['Adjust Light Saturation']:
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
        else:
            blind_id = parsed_json['service_name']
            # Convert blind position from a value to a string: 100 Open, 0 Closed, 50 Venetian
            blind_position = self.blind_position_map[parsed_json['value']]
            window_blind[blind_name].change_blind_position(blind_id, blind_position)

    def process_doorbell_button(self, parsed_json):
        #print('Homebridge: Process Doorbell Button', parsed_json)
        # Ignore the button press if it's only an indicator and reset to its pre-pressed state
        if self.doorbell_button_type[parsed_json['service_name']] == 'Indicator':
            #print('Indicator')
            time.sleep(1)
            homebridge_json = self.doorbell_format
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
            homebridge_json = self.doorbell_format
            homebridge_json['service_name'] = parsed_json['service_name']
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

    def process_garage_door_button(self, parsed_json):
        #print('Homebridge: Process Garage Door Button', parsed_json)
        if parsed_json['value'] == 0: # Open garage door if it's an open door command
            garage_door.open_garage_door(parsed_json)
        else: # Ignore any other commands and set homebridge garage door button to closed state
            homebridge_json = self.garage_door_format
            homebridge_json['value'] = 1
            for characteristic in self.garage_door_characteristics:
                homebridge_json['characteristic'] = self.garage_door_characteristics[characteristic]
                client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json)) # Close Current and Target Homebridge GarageDoor

    def process_aircon_button(self, parsed_json):
        #print('Homebridge: Process Aircon Button', parsed_json)
        # Ignore the button press if it's only an indicator and reset to its pre-pressed state
        if self.aircon_button_type[parsed_json['service_name']] == 'Indicator':
            time.sleep(0.5)
            homebridge_json = parsed_json
            homebridge_json['value'] = not parsed_json['value']
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        elif self.aircon_button_type[parsed_json['service_name']] == 'Thermostat Control':
            control = 'Undefined Characteristic'
            for key in self.aircon_thermostat_characteristics:
                # Determine the type of thermostat control being invoked
                if self.aircon_thermostat_characteristics[key] == parsed_json['characteristic']:
                    control = key
            if control == 'Mode':
                # Set Thermostat mode if it's a mode message
                setting = self.aircon_thermostat_mode_map[parsed_json['value']]
            else:
                # Set the thermostat target temperature
                setting = parsed_json['value']
            if control != 'Undefined Characteristic':
                # Send thermostat control and settin to the aircon object
                aircon['Aircon'].set_thermostat(parsed_json['service_name'], control, setting) # To do. Add ability to manage multiple aircons
            else:
                print('Undefined aircon thermostat characteristic')
        elif self.aircon_button_type[parsed_json['service_name']] == 'Position Indicator':
            # If the damper position indicator has been pressed, reset it to the target position
            mgr.print_update('Trying to vary damper position on ')
            if parsed_json['characteristic'] == 'TargetPosition': # Don't let the Damper be varied manually
                time.sleep(0.1)
                homebridge_json = self.aircon_damper_format # To do. Add ability to manage multiple aircons
                homebridge_json['characteristic'] = parsed_json['characteristic']
                homebridge_json['value'] = aircon['Aircon'].settings['target_day_zone'] # To do. Add ability to manage multiple aircons
                client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
            else:
                pass
        elif self.aircon_button_type[parsed_json['service_name']] == 'Switch':
            if parsed_json['service_name'] == 'Ventilation':
                ventilation = parsed_json['value']
                #print('Ventilation Button Pressed')
                aircon['Aircon'].process_ventilation_button(ventilation)
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
            if value == 1:
                air_purifier[purifier_name].active()
            else:
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
        if parsed_json['service_name'] == self.reboot_format['service_name']:
            self.reboot_armed = parsed_json['value']
            if self.reboot_armed == True:
                mgr.print_update('Reboot Armed on ')
            else:
                mgr.print_update('Reboot Disarmed on ')
        if parsed_json['service_name'] == self.reboot_trigger_format['service_name']:
            if self.reboot_armed == True:
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

    def switch_powerpoint(self, parsed_json):
        powerpoint_name = parsed_json['service_name']
        switch_state = parsed_json['value']
        # Call the on_off method for the relevant powerpoint object
        powerpoint[powerpoint_name].on_off(switch_state)

    def update_temperature(self, name, temperature):
        homebridge_json = self.temperature_format
        if name in self.outdoor_zone: # Check to see if this is an outdoor sensor
            # The homebridge JSON name for outdoor sensors is different from the internal sensors
            homebridge_json['name'] = self.outdoor_sensors_name
        else:
            homebridge_json['name'] = self.indoor_temp_name
        homebridge_json['service_name'] = name + self.temperature_service_name_format # Add the name to the service name
        homebridge_json['value'] = temperature
        # Update homebridge with the current temperature
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_thermostat_current_temperature(self, name, temperature):
        homebridge_json = self.aircon_thermostat_format # To do. Add ability to manage multipleaircons
        homebridge_json['characteristic'] = self.aircon_thermostat_characteristics['Current Temperature']
        # Set the service name to the thermostat name
        homebridge_json['service_name'] = name
        homebridge_json['value'] = temperature
        # Update homebridge with the thermostat current temperature
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_humidity(self, name, humidity):
        homebridge_json = self.humidity_format
        if name in self.outdoor_zone: # Check to see if this is an outdoor sensor
            # The homebridge JSON name for outdoor sensors is different from the internal sensors
            homebridge_json['name'] = self.outdoor_sensors_name
        else:
            homebridge_json['name'] = self.indoor_humidity_name
        homebridge_json['service_name'] = name + self.humidity_service_name_format # Add the humidity service name to the name
        homebridge_json['value'] = humidity
        # Update homebridge with the current hunidity
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json)) # Update homebridge with the current humidity

    def update_light_level(self, name, light_level):
        homebridge_json = self.light_level_format
        if name in self.outdoor_zone: # Check to see if this is an outdoor sensor
            # The homebridge JSON name for outdoor sensors is different from the internal sensors
            homebridge_json['name'] = self.outdoor_sensors_name
        else:
            homebridge_json['name'] = self.indoor_light_level_name
        homebridge_json['service_name'] = name + self.light_level_service_name_format # Add the light level service name to the name
        if light_level == 0:
            light_level = 0.0001 #Homebridge doesn't like zero Lux
        homebridge_json['value'] = light_level
        # Update homebridge with the current light level
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_motion(self, name, motion_detected):
        homebridge_json = self.motion_format
        if name in self.outdoor_zone: # Check to see if this is an outdoor sensor
            # The homebridge JSON name for outdoor sensors is different from the internal sensors
            homebridge_json['name'] = self.outdoor_sensors_name
        else:
             homebridge_json['name'] = self.indoor_motion_name 
        homebridge_json['service_name'] = name + self.motion_service_name_format # Add the motion service name to the name
        homebridge_json['value'] = motion_detected
        # Update homebridge with the current motion state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        
    def update_door_state(self, door, location, door_opened, low_battery):
        homebridge_json = self.door_state_format
        homebridge_json['name'] = location
        homebridge_json['characteristic'] = self.door_state_characteristic
        homebridge_json['service_name'] = door + self.door_state_service_name_format
        homebridge_json['value'] = self.door_state_map['door_opened'][door_opened]
        # Update homebridge with the current door state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = self.door_battery_characteristic
        homebridge_json['value'] = self.door_state_map['low_battery'][low_battery]
        # Update homebridge with the current door battery state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_flood_state(self, name, flooding, low_battery):
        #print('Homebridge: Update Flood State', name, flooding, low_battery)
        homebridge_json = self.flood_state_format
        homebridge_json['characteristic'] = self.flood_state_characteristic
        homebridge_json['service_name'] = name
        homebridge_json['value'] = flooding
        # Update homebridge with the current flood state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = self.flood_battery_characteristic
        homebridge_json['value'] = low_battery
        # Update homebridge with the current flood sensor battery state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))       

    def update_doorbell_status(self, parsed_json, status_item):
        homebridge_json = self.doorbell_format
        homebridge_json['service_name'] = status_item # Match homebridge service name with status item
        homebridge_json['value'] = parsed_json[status_item]
        if status_item != 'Ringing':
            homebridge_json['characteristic'] = 'On'    
            # Convert status bool states to strings for sending to homebridge
        else:
            homebridge_json['characteristic'] = 'MotionDetected' # Ringing uses a motion sensor on homebridge
        homebridge_payload = json.dumps(homebridge_json)
        # Publish homebridge payload with updated doorbell status
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_dimmer_state(self, name, dimmer_state):
        homebridge_json = self.dimmer_format
        homebridge_json['characteristic'] = self.dimmer_characteristics['Switch Light State']
        homebridge_json['service_name'] = name
        homebridge_json['value'] = self.dimmer_state_map[dimmer_state]
        homebridge_payload = json.dumps(homebridge_json)
        # Publish homebridge payload with updated dimmer state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_powerpoint_state(self, name, powerpoint_state):
        homebridge_json = self.powerpoint_format
        homebridge_json['characteristic'] = 'On'
        homebridge_json['service_name'] = name
        homebridge_json['value'] = powerpoint_state
        homebridge_payload = json.dumps(homebridge_json)
        # Publish homebridge payload with updated powerpoint state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_garage_door(self, state):
        #print('Homebridge: Update Garage Door', state)
        homebridge_json = self.garage_door_format
        if state =='Opened':
            mgr.print_update("Garage Door Opened on ")
            homebridge_json['characteristic'] = self.garage_door_characteristics['Current']
            homebridge_json['value'] = 0
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json)) # Send Current Garage Door Open Message to Homebridge
        elif state == 'Closing':
            mgr.print_update("Garage Door Closing on ")
            homebridge_json['characteristic'] = self.garage_door_characteristics['Target']
            homebridge_json['value'] = 1
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json)) # Send Target Garage Door Closing Message to Homebridge
        elif state == 'Closed':
            mgr.print_update("Garage Door Closed on ")
            homebridge_json['characteristic'] = self.garage_door_characteristics['Current']
            homebridge_json['value'] = 1
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json)) # Send Current Garage Door Closed Message to Homebridge
        else:
            print("Invalid Garage Door Status Message", service)
               
    def set_auto_blind_override_button(self, blind_room, state):
        #print('Homebridge: Reset Auto Blind Override Button', blind_room)
        homebridge_json = self.auto_blind_override_button_format
        homebridge_json['name'] = blind_room
        homebridge_json['value'] = state
        homebridge_payload = json.dumps(homebridge_json)
        # Publish homebridge payload with button state off
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_blind_status(self, blind_room, window_blind_config):
        homebridge_json = {}
        homebridge_json['name'] = blind_room
        homebridge_json['characteristic'] = 'TargetPosition'
        for blind in window_blind_config['status']:
            homebridge_json['service_name'] = blind
            homebridge_json['value'] = self.window_blind_position_map[window_blind_config['status'][blind]]
            client.publish('homebridge/to/set', json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'CurrentPosition'
        for blind in window_blind_config['status']:
            homebridge_json['service_name'] = blind
            homebridge_json['value'] = self.window_blind_position_map[window_blind_config['status'][blind]]
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def reset_aircon_thermostats(self, thermostat_status): # Called on start-up to set all Homebridge sensors to "off", current temps to 1 degree, target temps to 25 degrees and Ventilation Button 'Off'
        # Initialise Thermostat functions
        homebridge_json = self.aircon_thermostat_format # To do. Add ability to manage multiple aircons
        for name in self.aircon_thermostat_names:
            homebridge_json['service_name'] = name
            for function in self.aircon_thermostat_characteristics:
                homebridge_json['characteristic'] = self.aircon_thermostat_characteristics[function]
                if function == 'Mode':
                    homebridge_json['value'] = self.aircon_thermostat_incoming_mode_map[thermostat_status[name][function]]
                else:
                    homebridge_json['value'] = thermostat_status[name][function]
                client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        self.reset_aircon_ventilation_button()

    def reset_aircon_control_thermostat(self):
        homebridge_json = self.aircon_thermostat_format # To do. Add ability to manage multiple aircons
        homebridge_json['service_name'] = self.aircon_control_thermostat_name
        homebridge_json['characteristic'] = self.aircon_thermostat_characteristics['Mode']
        homebridge_json['value'] = 0
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def reset_aircon_ventilation_button(self):
        homebridge_json = self.aircon_ventilation_button_format
        homebridge_json['value'] = False
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def reset_reboot_button(self):
        homebridge_json = self.reboot_format
        homebridge_json['value'] = False # Prepare to return reboot switch state to off
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json = self.reboot_trigger_format
        homebridge_json['value'] = False # Prepare to return reboot trigger state to off
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        
    def update_aircon_status(self, status_item, state):
        #print('Homebridge: Update Aircon Status', status_item, state)
        homebridge_json = self.aircon_status_format # To do. Add ability to manage multiple aircons
        homebridge_json['service_name'] = status_item
        if status_item == 'Damper':
            homebridge_json['characteristic'] = 'CurrentPosition'
            print('Damper Day Zone is set to ' + str(state) + ' percent')
        else:
            homebridge_json['characteristic'] = 'On'
        homebridge_json['value'] = state
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def set_target_damper_position(self, damper_percent):
        homebridge_json = self.aircon_damper_format # To do. Add ability to manage multiple aircons
        homebridge_json['name'] = 'Aircon'
        homebridge_json['characteristic'] = 'TargetPosition'
        homebridge_json['value'] = damper_percent
        homebridge_air_payload = json.dumps(homebridge_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_aircon_thermostat(self, thermostat, mode):
        homebridge_json = self.aircon_thermostat_format # To do. Add ability to manage multiple aircons
        homebridge_json['service_name'] = thermostat
        homebridge_json['characteristic'] = self.aircon_thermostat_characteristics['Mode']
        homebridge_json['value'] = self.aircon_thermostat_incoming_mode_map[mode]
        #print('Aircon Thermostat update', homebridge_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_control_thermostat_temps(self, target_temp, current_temp):
        homebridge_json = self.aircon_thermostat_format # To do. Add ability to manage multiple aircons
        homebridge_json['service_name'] = self.aircon_control_thermostat_name
        homebridge_json['characteristic'] = self.aircon_thermostat_characteristics['Target Temperature']
        homebridge_json['value'] = target_temp
        #print('Aircon Control Thermostat Target Temp update', homebridge_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = self.aircon_thermostat_characteristics['Current Temperature']
        homebridge_json['value'] = current_temp
        #print('Aircon Control Thermostat Current Temp update', homebridge_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_thermostat_target_temp(self, thermostat, temp):
        homebridge_json = self.aircon_thermostat_format # To do. Add ability to manage multiple aircons
        homebridge_json['service_name'] = thermostat
        homebridge_json['characteristic'] = self.aircon_thermostat_characteristics['Target Temperature']
        homebridge_json['value'] = temp
        #print('Update Aircon Thermostat Target Temp', homebridge_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def update_air_quality(self, name, part_2_5, co2, voc, aqi, max_co2, co2_threshold, part_2_5_threshold):
        homebridge_json = self.air_quality_format
        homebridge_json['service_name'] = self.air_quality_service_name_map[name]
        homebridge_json['characteristic'] = 'AirQuality'
        homebridge_json['value'] = aqi
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'PM10Density' # Use 10 because homebridge-mqtt doesn't like 2_5
        homebridge_json['value'] = part_2_5
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['characteristic'] = 'VOCDensity'
        homebridge_json['value'] = voc
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        homebridge_json['service_name'] = self.CO2_service_name_map[name]
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
        homebridge_json['service_name'] = self.PM2_5_service_name_map[name]
        homebridge_json['characteristic'] = 'MotionDetected'
        if part_2_5 >= part_2_5_threshold:
            homebridge_json['value'] = True
        else:
            homebridge_json['value'] = False
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def set_air_purifier_state(self, name, mode, fan_speed, child_lock, led_brightness, filter_status):
        #print('Updating BlueAir Homebridge Settings', name, mode, fan_speed, child_lock, led_brightness, filter_status)
        homebridge_json = self.air_purifier_format
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
        homebridge_json = self.air_purifier_filter_format
        homebridge_json['service_name'] = name + ' Filter'
        homebridge_json['characteristic'] = 'FilterChangeIndication'
        if filter_status == 'OK':
            homebridge_json['value'] = 0
        else:
            homebridge_json['value'] = 1
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
                                                        
class DomoticzClass(object): # Manages communications to and from the z-wave objects
    def __init__(self):
        self.outgoing_mqtt_topic = 'domoticz/in'
        self.incoming_mqtt_topic = 'domoticz/out'
        # Set up Domoticz label formats so that incoming message names can be decoded
        self.temperature_humidity_label = ' Climate'
        self.light_level_label = ' Light Level'
        self.motion_label = ' Motion'
        self.door_label = ' Door'
        self.dimmer_label = ' Dimmer'
        self.flood_label = ' Flooding'
        self.powerpoint_label = ' Powerpoint'
        self.aircon_sensor_enable_label = ' Aircon'
        self.aircon_mode_label = 'Aircon Mode'
        self.aircon_mode_map = {'0': 'Off', '10': 'Heat', '20': 'Cool'}
        self.aircon_thermostat_label = ' Thermostat'
        self.aircon_sensor_names_idx = {'Living': {'Active': 683, 'Temperature': 675}, 'Kitchen': {'Active': 684, 'Temperature': 678},
                                         'Study': {'Active': 685, 'Temperature': 679}, 'Main': {'Active': 686, 'Temperature': 680},
                                         'South': {'Active': 687, 'Temperature': 681}, 'North': {'Active': 688, 'Temperature': 682}}
        self.aircon_sensor_enable_map = {'Off': 0, 'Heat': 1, 'Cool': 1}
        self.aircon_status_idx = {'Mode':{'idx': 695, 'Off': '0', 'Fan': '10', 'Heat': '20', 'Cool': '30'}, 'Damper': 696}
        self.aircon_mode = {'idx': 693, 'Off': '0', 'Heat': '10', 'Cool': '20'}
        # Set up dimmer domoticz message formats
        self.dimmer_brightness_format = {'command': 'switchlight', 'switchcmd': 'Set Level'}
        self.dimmer_switch_format = {'command': 'switchlight'}
        self.dimmer_hue_saturation_format = {'command': 'setcolbrightnessvalue'}
        #self.dimmer_color_format = {'b': 255, 'g': 255, 'cw': 0, 'ww': 0, 'r': 255, 'm': 3, 't': 0}
        # Map dimmer switch functions to translate True to On-switch/100-brightness and
        # False to Off-switch/0-brightness for domoticz_json
        self.dimmer_switch_map = {True:['On', 100], False:['Off', 0]}
        # Set up powerpoint domoticz message formats
        self.powerpoint_format = {'command': 'switchlight'}
        # Map powerpoint switch functions to translate True to On and False to Off for domoticz_json
        self.powerpoint_map = {True: 'On', False:'Off'}
        self.air_quality_idx_map = {'Living':{'part_2_5': 708, 'co2': 705, 'voc': 706, 'max_aqi': 707}}

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
            door_sensor[sensor_name[0:sensor_name.find(self.door_label)]].process_door_state_change(parsed_json)
        elif self.flood_label in sensor_name: # If it's a flood sensor
            print('Flood Message', sensor_name, parsed_json)
            flood_sensor[sensor_name[0:sensor_name.find(self.flood_label)]].process_flood_state_change(parsed_json)
        elif self.dimmer_label in sensor_name: # If it's a light dimmer
            #print('Dimmer Message', sensor_name, parsed_json)
            light_dimmer[sensor_name[0:sensor_name.find(self.dimmer_label)]].process_dimmer_state_change(parsed_json)
        elif self.powerpoint_label in sensor_name: # If it's a powerpoint
            powerpoint[sensor_name[0:sensor_name.find(self.powerpoint_label)]].process_powerpoint_state_change(parsed_json)
        elif self.aircon_mode_label in sensor_name: # If it's an aircon mode switch
            self.process_aircon_mode_change(parsed_json)
        elif self.aircon_sensor_enable_label in sensor_name : # If it's an aircon sensor switch
            self.process_aircon_sensor_enable_change(parsed_json)
        elif self.aircon_thermostat_label in sensor_name : # If it's an aircon thermostat
            self.process_aircon_thermostat(parsed_json)
        else:
            #print('Unknown Sensor Label: ' + sensor_name)
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

    def reset_aircon_thermostats(self, thermostat_status): # Called on start-up and shutdown to reset all Domoticz aircon sensor and target temperature switches
        # Initialise Thermostat States
        domoticz_json = {}
        for name in self.aircon_sensor_names_idx: # To do. Add ability to manage multiple aircons
            domoticz_json['idx'] = self.aircon_sensor_names_idx[name]['Active']
            domoticz_json['nvalue'] = thermostat_status[name]['Active']
            client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))
            domoticz_json['idx'] = self.aircon_sensor_names_idx[name]['Temperature']
            domoticz_json['svalue'] = str(thermostat_status[name]['Target Temperature'])
            client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))

    def process_aircon_mode_change(self, parsed_json):
        print ('Domoticz: Process Aircon Mode Change', parsed_json)
        thermostat_name = aircon['Aircon'].control_thermostat
        control = 'Mode'
        setting = self.aircon_mode_map[parsed_json['svalue1']]
        aircon['Aircon'].set_thermostat(thermostat_name, control, setting)
        homebridge.update_aircon_thermostat(aircon['Aircon'].control_thermostat, setting) # Set Homebridge thermostat

    def process_aircon_sensor_enable_change(self, parsed_json):
        #print ('Domoticz: Process Aircon Sensor Enable Change', parsed_json)
        thermostat_name = parsed_json['name'][0:parsed_json['name'].find(self.aircon_sensor_enable_label)] # Remove aircon sensor enable label
        control = 'Mode'
        if parsed_json['nvalue'] == 1:
            setting = aircon['Aircon'].settings['indoor_thermo_mode'] # Set the same as the aircon's indoor_thermo_mode if it's active
        else:
            setting = 'Off'
        aircon['Aircon'].set_thermostat(thermostat_name, control, setting)
        homebridge.update_aircon_thermostat(thermostat_name, setting) # Set Homebridge thermostat

    def process_aircon_thermostat(self, parsed_json):
        #print ('Domoticz: Process Aircon Thermostat', parsed_json)
        thermostat_name = parsed_json['name'][0:parsed_json['name'].find(self.aircon_thermostat_label)] # Remove aircon thermostat label
        control = 'Target Temperature'
        temp = float(parsed_json['svalue1'])
        aircon['Aircon'].set_thermostat(thermostat_name, control, temp)
        homebridge.update_thermostat_target_temp(thermostat_name, temp) # Set Homebridge thermostat

    def set_aircon_mode(self, mode): # Not used because of control loops
        print ('Domoticz: Set Aircon Mode', mode)
        domoticz_json = {}
        domoticz_json['idx'] = self.aircon_mode['idx']
        domoticz_json['svalue'] = self.aircon_mode[mode]
        client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))

    def set_aircon_thermostat_target_temp(self, thermostat, temp): # Not used because of control loops
        print ('Domoticz: Set Aircon Target Temp', thermostat, temp)
        domoticz_json = {}
        domoticz_json['idx'] = self.aircon_sensor_names_idx[thermostat]['Temperature']
        domoticz_json['svalue'] = str(temp)
        client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))

    def change_aircon_sensor_enable(self, sensor, state): # Not used because of control loops
        print ('Domoticz: Change Aircon Sensor Enable', sensor, state)
        domoticz_json = {}
        domoticz_json['idx'] = self.aircon_sensor_names_idx[sensor]['Active']
        domoticz_json['nvalue'] = self.aircon_sensor_enable_map[state]
        client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))        

    def update_aircon_status(self, status_item, state): # To do. Add ability to manage multiple aircons
        #print ('Domoticz: Update Aircon Status', status_item, state)
        domoticz_json = {}
        publish = False
        if status_item == 'Damper':
            domoticz_json['idx'] = self.aircon_status_idx['Damper']
            domoticz_json['nvalue'] = 0
            domoticz_json['svalue'] = str(state)
            publish = True
        else:
            domoticz_json['idx'] = self.aircon_status_idx['Mode']['idx']
            if status_item == 'Remote Operation' and state == False:
                domoticz_json['svalue'] = self.aircon_status_idx['Mode']['Off']
                publish = True
            elif status_item == 'Heat' and state == True:
                domoticz_json['svalue'] = self.aircon_status_idx['Mode']['Heat']
                publish = True
            elif status_item == 'Cool' and state == True:
                domoticz_json['svalue'] = self.aircon_status_idx['Mode']['Cool']
                publish = True
            elif status_item == 'Fan' and state == True:
                domoticz_json['svalue'] = self.aircon_status_idx['Mode']['Fan']
                publish = True
        if publish == True:
            client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))

    def update_air_quality(self, name, part_2_5, co2, voc, max_aqi):
        domoticz_json = {}
        if name in self.air_quality_idx_map:
            #print('Updating Domoticz Air Quality')
            domoticz_json['idx'] = self.air_quality_idx_map[name]['part_2_5']
            domoticz_json['nvalue'] = 0
            domoticz_json['svalue'] = str(round(part_2_5, 0))
            client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))
            domoticz_json['idx'] = self.air_quality_idx_map[name]['max_aqi']
            domoticz_json['svalue'] = str(max_aqi)
            client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))
            domoticz_json = {}
            domoticz_json['idx'] = self.air_quality_idx_map[name]['voc']
            domoticz_json['nvalue'] = voc
            client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))
            domoticz_json = {}
            domoticz_json['idx'] = self.air_quality_idx_map[name]['co2']
            domoticz_json['nvalue'] = co2
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
        mgr.print_update("Updating Flood Detection for " + self.name + " Sensor to " +
                     self.flood_state_map['Flood State'][self.flooding] + ". Battery Level " +
                     self.flood_state_map['Battery State'][self.low_battery] + " on ")
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
            if self.blind_door['Blind Control'] == True: # If it's a door that controls a blind
                # Flag current door state in window_blind_config so that sunlight blind adjustments can be made
                blind_name = self.blind_door['Blind Name']
                if self.current_door_opened == True:
                    door_state = 'Open'
                else:
                    door_state = 'Closed'    
                mgr.window_blind_config[blind_name]['blind_doors'][self.door]['door_state'] = door_state
                mgr.window_blind_config[blind_name]['blind_doors'][self.door]['door_state_changed'] = self.door_state_changed
                #print('Window Blind Config for ', blind_name, mgr.window_blind_config[blind_name]['blind_doors'])
                # Trigger a blind change in the main mgr loop if a blind control door is opened
                mgr.blind_control_door_changed = {'State': self.current_door_opened, 'Blind': blind_name, 'Changed': self.door_state_changed}
                #print('Blind Control Door Opened', mgr.blind_control_door_changed)
            # Update Doorbell Door State if it's a doorbell door
            if self.doorbell_door == True:
                # Send change of door state to doorbell monitor
                doorbell.update_doorbell_door_state(self.door, self.current_door_opened)
            mgr.print_update("Updating Door Detection for " + self.door + " from " +
                         self.door_state_map['door_opened'][self.previous_door_opened] + " to " +
                         self.door_state_map['door_opened'][self.current_door_opened]
                         + ". Battery Level " + self.door_state_map['low_battery'][self.low_battery] + " on ")         
            self.previous_door_opened = self.current_door_opened
            self.door_state_changed = False
        
class MultisensorClass(object):
    def __init__(self, name, aircon_temp_sensor_names, window_blind_config, log_aircon_temp_data):
        self.name = name
        #print ('Instantiated Multisensor', self, name)
        # The dictionary that records the readings of each sensor object
        self.sensor_types_with_value = {'Temperature': 1, 'Humidity': 1, 'Motion': False, 'Light Level': 1}
        self.aircon_temp_sensor_names = aircon_temp_sensor_names
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
        # Update the temperature history for logging - even if the temp hasn't changed
        aircon['Aircon'].update_temp_history(self.name, temperature, self.log_aircon_temp_data)
        # Only update homebridge current temperature record if the temp changes
        if temperature != self.sensor_types_with_value['Temperature']:
            # print('Updating Temperature for', self.name, 'sensor from',
                             #self.sensor_types_with_value['Temperature'], 'degrees to', str(temperature), 'degrees on ')
            self.sensor_types_with_value['Temperature'] = temperature # Update sensor object's temperature record
            homebridge.update_temperature(self.name, temperature)
            # Only update aircon thermostat current temperature readings if it's an indoor sensor
            if self.name in self.aircon_temp_sensor_names:
                homebridge.update_thermostat_current_temperature(self.name, temperature)
                # Update the "Day", "Night" and "Indoor" Zone current temperatures with new active temperature sensor readings
                aircon['Aircon'].update_zone_temps()
                # Update the aircon's current temperature record for this sensor
                aircon['Aircon'].thermostat_status[self.name]['Current Temperature'] = temperature
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
            if self.blind_sensor['Blind Control'] == True: # Check if this light sensor is used to control a window blind
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

    def process_powerpoint_state_change(self, parsed_json):
        # The method to capture a state change that is triggered by a change in the powerpoint switch
        self.powerpoint_state = parsed_json['nvalue']
        homebridge.update_powerpoint_state(self.name, self.powerpoint_state)

class GaragedoorClass(object):
    def __init__(self, outgoing_mqtt_topic):
        #print ('Instantiated Garage Door', self)
        self.garage_door_mqtt_topic = outgoing_mqtt_topic
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
    def __init__(self, outgoing_mqtt_topic):
        #print ('Instantiated Doorbell', self)
        self.outgoing_mqtt_topic = outgoing_mqtt_topic
        # Set up Doorbell status dictionary with initial states set
        self.status = {'Terminated': False, 'AutoPossible': False, 'Triggered': False,
                        'Ringing': False, 'Activated': False, 'Automatic': False, 'Manual': False}
        
    def capture_doorbell_status(self, parsed_json):
        # Sync HomeManager's doorbell status and homebridge doorbell button settings with the doorbell
        # monitor status when an mqtt status update message is received from the doorbell monitor 
        #mgr.print_update('Doorbell Status update on ')
        for status_item in self.status: # For each status item in the doorbell status
            self.status[status_item] = parsed_json[status_item] # Update doorbell status
            homebridge.update_doorbell_status(parsed_json, status_item) # Send update to homebridge
        #print(self.status)
        
    def process_button(self, button_name):
        doorbell_json = {}
        doorbell_json['service'] = button_name
        # Send button message to the doorbell
        client.publish(self.outgoing_mqtt_topic, json.dumps(doorbell_json))
            
    def update_doorbell_status(self):
        doorbell_json = {}
        doorbell_json['service'] = 'UpdateStatus'
        client.publish(self.outgoing_mqtt_topic, json.dumps(doorbell_json))
        
    def update_doorbell_door_state(self, door, door_opened):
        doorbell_json = {}
        doorbell_json['service'] = 'DoorStatusChange'
        if door_opened == True:
            doorbell_json['new_door_state'] = 1
        else:
            doorbell_json['new_door_state'] = 0
        doorbell_json['door'] = door + ' Door'
        #print('Update Doorbell Door State', doorbell_json)
        client.publish(self.outgoing_mqtt_topic, json.dumps(doorbell_json))   

class WindowBlindClass(object): # To do: Provide more flexibility with blind_id and position
    def __init__(self, blind_room, window_blind_config):
        self.blind = blind_room
        #print ('Instantiated Window Blind', self, blind_room)
        self.window_blind_config = window_blind_config
        self.blind_ip_address = self.window_blind_config['blind ip address']
        self.blind_port = self.window_blind_config['blind port']
        self.current_high_sunlight = 0 # Set initial sunlight level to 0
        self.previous_blind_temp_threshold = False
        self.call_control_blinds = False
        self.door_blind_override = False
        self.previous_high_sunlight = 0
        self.auto_override = False
        self.auto_override_changed = False
        self.previous_door_open = True
                                                              
    def control_blinds(self, blind, blind_controls, window_blind_config):
        mgr.print_update('Invoked Manual Blind Control on ')
        blind_id = blind_controls['Blind_id']
        blind_position = blind_controls['Blind_position']
        ignore_blind_command = False
        door_blind_override = False
        # Check if at least one door is open
        door_open = False
        for door in window_blind_config['blind_doors']:
            if window_blind_config['blind_doors'][door]['door_state'] == 'Open':
                door_open = True
        if blind_position == 'Open':
            print('Opening Blinds')
            self.move_blind(blind_id, 'up')
        elif blind_position == 'Closed':
            print('Closing Blinds')
            # If both doors are closed and it's a blind command that closes one or more door blinds
            if (door_open == False and (blind_id == 'Left Door' or blind_id == 'Right Door' or blind_id == 'All Doors' or blind_id == 'All Blinds')):
                print_update, window_blind_config['status'] = self.close_door_impacting_blind(blind_id, window_blind_config)
            elif blind_id == 'Left Window' or blind_id == 'Right Window' or blind_id == 'All Windows': # If it's a window command
                self.close_window_blind(blind_id)
            # If one door is open and it's a command that impacts the doors
            elif (door_open == True and (blind_id == 'Left Door' or blind_id == 'Right Door' or blind_id == 'All Doors' or blind_id == 'All Blinds')):
                door_blind_override = True # Flag that lowering of door blinds has been overridden
                if blind_id == 'All Blinds':
                    print('Trying to close all blinds when a door is open. Only closing window blinds')
                    revised_blind_id = 'All Windows' # Change All Blinds to All Windows so that door blinds stay open
                    self.close_window_blind(revised_blind_id)
                    window_blind_config['status'][revised_blind_id] = 'Closed'
                else: # Don't do anything if it's a Door Command
                    print('Trying to close door blinds when a door is open. Ignoring command')
                    ignore_blind_command = True
                    homebridge.update_blind_status(blind, window_blind_config)
            else:
                print('Unknown Blind Control Request. Blind Controls:', blind_controls, 'window_blind_config:', window_blind_config)
                pass # No other conditions
        elif blind_position == 'Venetian':
            print('Setting Blinds to Venetian')
            # If both doors are closed and it's a blind command that closes one or more door blinds
            if (door_open == False and (blind_id == 'Left Door' or blind_id == 'Right Door' or blind_id == 'All Doors' or blind_id == 'All Blinds')):
                window_blind_config['status'] = self.venetian_door_impacting_blind(blind_id, window_blind_config)
            elif blind_id == 'Left Window' or blind_id == 'Right Window' or blind_id == 'All Windows': # If it's a window command
                self.move_blind(blind_id, 'down')
            # If one door is open and it's a command that impacts the doors
            elif (door_open == True and (blind_id == 'Left Door' or blind_id == 'Right Door' or blind_id == 'All Doors' or blind_id == 'All Blinds')):
                door_blind_override = True # Flag that lowering of door blinds has been overridden
                if blind_id == 'All Blinds':
                    revised_blind_id = 'All Windows' # Change All Blinds to All Windows so that door blinds stay open
                    self.move_blind(revised_blind_id, 'down')
                    window_blind_config['status'][blind_id] = 'Venetian'
                else: # Don't do anything if it's a Door Command
                    ignore_blind_command = True
                    homebridge.update_blind_status(blind, window_blind_config)                   
        else: # Ignore any other setting
            ignore_blind_command = True
            homebridge.update_blind_status(blind, window_blind_config)
        if ignore_blind_command == False:
            window_blind_config['status'][blind_id] = blind_position # Match window blind status with the blind's new position
            if blind_id == 'All Blinds' and door_blind_override == False: # Match individual blind status with that of 'All Blinds' if not overridden
                window_blind_config['status']['Left Window'] = blind_position
                window_blind_config['status']['Left Door'] = blind_position
                window_blind_config['status']['Right Door'] = blind_position
                window_blind_config['status']['Right Window'] = blind_position
                window_blind_config['status']['All Doors'] = blind_position
                window_blind_config['status']['All Windows'] = blind_position
            elif blind_id == 'All Blinds' and door_blind_override == True: # Match individual blind status for windows with that of 'All Blinds' and set door blinds 'Open' if overridden
                window_blind_config['status']['All Blinds'] = blind_position
                window_blind_config['status']['All Doors'] = 'Open'
                window_blind_config['status']['Left Door'] = 'Open'
                window_blind_config['status']['Right Door'] = 'Open'
                window_blind_config['status']['Left Window'] = blind_position
                window_blind_config['status']['Right Window'] = blind_position
                window_blind_config['status']['All Windows'] = blind_position         
            elif blind_id == 'All Windows':# Match individual window blind status with that of 'All Windows'
                window_blind_config['status']['Left Window'] = blind_position
                window_blind_config['status']['Right Window'] = blind_position
            elif blind_id == 'All Doors' and door_blind_override == False: # Match individual door blind status with that of 'All Doors' if not overridden
                window_blind_config['status']['Left Door'] = blind_position
                window_blind_config['status']['Right Door'] = blind_position
            elif blind_id == 'All Doors' and door_blind_override == True: # Set door blinds 'Open' if overridden
                window_blind_config['status']['All Blinds'] = 'Open'
                window_blind_config['status']['All Doors'] = 'Open'
                window_blind_config['status']['Left Door'] = 'Open'
                window_blind_config['status']['Right Door'] = 'Open'
            else:
                pass
            if door_blind_override == True:
                print('Changed blind command because a door is open')
            door_blind_override = False # Reset blind override flag
            homebridge.update_blind_status(blind, window_blind_config)
        else:
            print('Ignored door blind command because a door is open')
        return(window_blind_config)

    def room_sunlight_control(self, light_level, window_blind_config):
        # Called when a changed in the blind's light sensor, doors or auto_override button
        current_temperature = multisensor[window_blind_config['temp sensor']].sensor_types_with_value['Temperature']
        if current_temperature != 1: # Wait for valid temp reading (1 is startup temp)
            mgr.print_update('Blind Control invoked on ')
            # Has temp passed thresholds?
            temp_passed_threshold, current_blind_temp_threshold = self.check_outside_temperatures(window_blind_config, current_temperature,
                                                                                                  self.previous_blind_temp_threshold, 1)
            self.previous_blind_temp_threshold = current_blind_temp_threshold
            door_open, door_state_changed = self.check_door_state(window_blind_config, self.previous_door_open)
            self.previous_door_open = door_open # Set new door state for the next time that self.check_door_state is called
            if light_level >= window_blind_config['sunlight threshold 3']: # If it's strong direct sunlight
                new_high_sunlight = 4
            elif (light_level >= window_blind_config['sunlight threshold 2'] and
                  light_level < window_blind_config['sunlight threshold 3']): # If it's medium direct sunlight
                new_high_sunlight = 3
            elif (light_level >= window_blind_config['sunlight threshold 1']
                  and light_level < window_blind_config['sunlight threshold 2']): # If it's strong indirect sunlight
                new_high_sunlight = 2
            elif (light_level < window_blind_config['sunlight threshold 1'] and
                  light_level > window_blind_config['sunlight threshold 0']): # If it's medium indirect sunlight
                new_high_sunlight = 1 # If it's low indirect sunlight
            else:
                new_high_sunlight = 0 # If it's night time
            print('High Sunlight Levels checked')
            print ('New Sensor Light Level Reading', light_level, 'Lux', 'Current High Sunlight Level:',
                   self.current_high_sunlight, 'New High Sunlight Level:', new_high_sunlight,
                   'Daylight?', light_level > window_blind_config['sunlight threshold 0'])
            if new_high_sunlight != self.current_high_sunlight: # Capture the previous sunlight level if the sunlight level has changed
                self.previous_high_sunlight = self.current_high_sunlight # Used in Sunlight Levels 2 and 3 to determine is the sunlight level has increased or decreased
            if (new_high_sunlight != self.current_high_sunlight or door_state_changed == True or
                temp_passed_threshold == True or (self.auto_override_changed == True and self.auto_override == False)): # Has there been a blind-affecting change?
                mgr.print_update ('Blind change algorithm triggered on ')
                print_blind_change = False
                if new_high_sunlight == 4:
                    print_blind_change, window_blind_config['status'] = self.set_blind_sunlight_4(door_open, self.auto_override, window_blind_config)
                elif new_high_sunlight == 3:
                    print_blind_change, window_blind_config['status'] = self.set_blind_sunlight_3(door_open, door_state_changed, self.previous_high_sunlight, self.auto_override, window_blind_config)           
                elif new_high_sunlight == 2:
                    print_blind_change, window_blind_config['status'] = self.set_blind_sunlight_2(door_open, self.previous_high_sunlight, self.auto_override, window_blind_config,
                                                                                                  current_blind_temp_threshold, current_temperature)    
                elif new_high_sunlight == 1:
                    print_blind_change, window_blind_config['status'] = self.set_blind_sunlight_1(door_open, self.auto_override, window_blind_config, current_blind_temp_threshold, current_temperature)                                                                                     
                elif new_high_sunlight == 0:
                    print_blind_change, window_blind_config['status'] = self.set_blind_sunlight_0(door_open, self.auto_override, window_blind_config)
                else:
                    pass # Invalid sunlight level              
                if print_blind_change == True: # If there's a change in blind position
                    print('Blind Change Summary')
                    if new_high_sunlight != self.current_high_sunlight: # If there's a blind position change due to sun protection state
                        print("High Sunlight Level was:", self.current_high_sunlight, "It's Now Level:", new_high_sunlight, "with a light reading of", light_level, "Lux")
                    if door_state_changed == True: # If a change in door states, print blind update due to door state change
                        if door_open == False:
                            print('Blinds were adjusted due to door closure')
                        else:
                            print('Blinds were adjusted due to door opening')
                    if temp_passed_threshold == True:
                        if current_blind_temp_threshold == False:
                            print('Blinds adjusted due to the external temperature moving inside the defined range')
                        else:
                            print('Blinds adjusted due to an external temperature moving outside the defined range')
                    if self.auto_override_changed == True:
                        if self.auto_override == False:
                           print('Blinds adjusted due to auto_override being switched off')   
                else: # No blind change, just a threshold change in the blind hysteresis gaps
                    print("High Sunlight Level Now", new_high_sunlight, "with a light reading of", light_level, "Lux and no change of blind position")
                    pass
                self.current_high_sunlight = new_high_sunlight # Update sunlight threshold status with the latest reading do determine if there's a sunlight level change required at the next sunlight reading
                self.auto_override_changed = False # Reset auto blind override flag 
                homebridge.update_blind_status(self.blind, window_blind_config) # Update blind status
                for door in window_blind_config['blind_doors']: # Reset all door state change flags
                    window_blind_config['blind_doors'][door]['door_state_changed'] = False
                self.window_blind_config = window_blind_config
            else: # Nothing changed that affects blind states
                print('Blind Status Unchanged')
                pass

    def check_outside_temperatures(self, window_blind_config, current_temperature, previous_blind_temp_threshold, hysteresis_gap):
        if previous_blind_temp_threshold == False:
            if (current_temperature > window_blind_config['high_temp_threshold']
                or current_temperature < window_blind_config['low_temp_threshold']):
                temp_passed_threshold = True
                current_blind_temp_threshold = True
            else: # Temp is still inside the blind temp thresholds
                temp_passed_threshold = False
                current_blind_temp_threshold = False
        else: # If the temp was previously outside the blind temp threshold.
            if (current_temperature <= (window_blind_config['high_temp_threshold'] - hysteresis_gap)
                and current_temperature >= (window_blind_config['low_temp_threshold'] + hysteresis_gap)):
                temp_passed_threshold = True
                current_blind_temp_threshold = False
            else: # Set that it hasn't jumped the thresholds
                temp_passed_threshold = False
                current_blind_temp_threshold = True
        print('Outside Temperatures checked')
        print('Current temperature is', current_temperature, 'degrees.', 'Previously Outside Temp Thresholds?',
               previous_blind_temp_threshold, 'Currently Outside Temp Thresholds?', current_blind_temp_threshold,
               'Temp Moved Inside or Outside Thresholds?', temp_passed_threshold)
        return(temp_passed_threshold, current_blind_temp_threshold)

    def check_door_state(self, window_blind_config, previous_door_open):
        all_doors_closed = True
        one_door_has_opened = False
        a_door_state_has_changed = False
        blind_door_state_changed = False
        for door in window_blind_config['blind_doors']:
            if window_blind_config['blind_doors'][door]['door_state'] == 'Open':
                all_doors_closed = False
                if window_blind_config['blind_doors'][door]['door_state_changed'] == True:
                    one_door_has_opened = True
            if window_blind_config['blind_doors'][door]['door_state_changed'] == True:
                a_door_state_has_changed = True    
        if one_door_has_opened == True and previous_door_open == False: # One door has now been opened when all doors were previously closed
            door_state_changed = True
            door_open = True
        elif all_doors_closed == True and a_door_state_has_changed == True: # All doors are now closed
            door_state_changed = True
            door_open = False
        else: # Ignore states when not all doors have been closed or a door has already been opened
            door_state_changed = False
            door_open = not all_doors_closed
            pass
        #print('Door State checked')
        #print ('Door State Changed?', door_state_changed, 'Any Doors Open?', door_open)
        return(door_open, door_state_changed)

    def set_blind_sunlight_4(self, door_open, auto_override, window_blind_config):
        print('High Sunlight Level 4 Invoked')
        print_blind_change = False
        if auto_override == False:
            if door_open == False: # Set right window blind to Venetian, close doors and left blind if both doors closed
                window_blind_config['status']['Left Window'] = 'Closed'
                window_blind_config['status']['All Doors'] = 'Closed'
                window_blind_config['status']['Left Door'] = 'Closed'
                window_blind_config['status']['Right Door'] = 'Closed'
                window_blind_config['status']['Right Window'] = 'Venetian'
                window_blind_config['status']['All Blinds'] = 'Closed'
                print_blind_change, window_blind_config['status'] = self.all_blinds_venetian(window_blind_config)
                self.move_blind('Left Window', 'up') # Raise left window blind for 0.5 seconds
                time.sleep(0.495)
                self.move_blind('Left Window', 'stop') # Stop left window blind
                self.move_blind('All Doors', 'up') # Raise all door blinds for 0.5 seconds
                time.sleep(0.495)
                self.move_blind('All Doors', 'stop') # Stop all door blinds
            else: # If at least one door is open
                self.move_blind('All Doors', 'up') # Raise all door blinds                   
                self.move_blind('All Windows', 'down')
                time.sleep(25)
                self.move_blind('Left Window', 'up')
                time.sleep(0.495)
                self.move_blind('Left Window', 'stop')
                print_blind_change = True
                # Set blind status to align with blind position
                window_blind_config['status']['Left Window'] = 'Closed'
                window_blind_config['status']['Right Window'] = 'Venetian'
                window_blind_config['status']['All Doors'] = 'Open'
                window_blind_config['status']['Left Door'] = 'Open'
                window_blind_config['status']['Right Door'] = 'Open'
                window_blind_config['status']['All Blinds'] = 'Venetian'
        else:
            print('No Blind Change. Auto Blind Control is overridden')
            pass
        return(print_blind_change, window_blind_config['status'])

    def set_blind_sunlight_3(self, door_open, door_state_changed, previous_high_sunlight, auto_override, window_blind_config):
        print('High Sunlight Level 3 Invoked')
        print_blind_change = False
        if auto_override == False:
            if previous_high_sunlight < 3: # If this level has been reached after being in levels 0, 1 or 2
                if door_open == False: # If both doors closed, all blinds to Venetian
                    print_blind_change, window_blind_config['status'] = self.all_blinds_venetian(window_blind_config)
                else: # Open door blinds and set window blinds to 50% if at least one door is open
                    self.move_blind('All Doors', 'up')
                    self.move_blind('All Windows', 'down')
                    print_blind_change = True
                    # Set blind status
                    window_blind_config['status']['All Windows'] = 'Venetian'
                    window_blind_config['status']['Left Window'] = 'Venetian'
                    window_blind_config['status']['Right Window'] = 'Venetian'
                    window_blind_config['status']['All Doors'] = 'Open'
                    window_blind_config['status']['Left Door'] = 'Open'
                    window_blind_config['status']['Right Door'] = 'Open'
                    window_blind_config['status']['All Blinds'] = 'Venetian'             
            else: # If this level has been reached after being in level 4
                if door_state_changed == True: # If the door state has changed
                    if door_open == False: # If the door are closed
                        window_blind_config['status']['All Doors'] = 'Closed'
                        window_blind_config['status']['Left Door'] = 'Closed'
                        window_blind_config['status']['Right Door'] = 'Closed'
                        print_blind_change, window_blind_config['status'] = self.close_door_impacting_blind('All Doors')
                    else: # Open door blinds if the doors have been opened 
                        self.move_blind('All Doors', 'up')
                        print_blind_change = True
                        # Set blind status
                        window_blind_config['status']['All Doors'] = 'Open'
                        window_blind_config['status']['Left Door'] = 'Open'
                        window_blind_config['status']['Right Door'] = 'Open'
                        window_blind_config['status']['All Blinds'] = 'Venetian'
                else: # Do nothing if there has been no change to the door state
                    pass
        else:
            print('No Blind Change. Auto Blind Control is overridden')
            pass
        return(print_blind_change, window_blind_config['status'])

    def set_blind_sunlight_2(self, door_open, previous_high_sunlight, auto_override, window_blind_config, current_blind_temp_threshold, current_temperature):
        print('High Sunlight Level 2 Invoked')
        print_blind_change = False
        if auto_override == False:
            if previous_high_sunlight < 2: # If this level has been reached after being in levels 0 or 1
                if current_blind_temp_threshold == True: # If the outside temperature is outside the pre-set thresholds
                    if door_open == False: # All blinds to venetian state if the external temperature is outside the pre-set thresholds and the doors are closed.
                        print('All blinds set to venetian state because the outdoor temperature is now outside the pre-set thresholds with doors closed')
                        print('Pre-set upper temperature threshold is', window_blind_config['high_temp_threshold'], 'degrees', 'Pre-set lower temperature limit is', window_blind_config['low_temp_threshold'], 'degrees',
                              'Current temperature is', current_temperature, 'degrees')
                        print_blind_change, window_blind_config['status'] = self.all_blinds_venetian(window_blind_config)
                    else: # Open door blinds if a door is open
                        print('Door blinds opening because a door has been opened while the last sunlight state before reaching level 2 was 0 or 1 and the outdoor temperature is still outside the pre-set thresholds')
                        print('Pre-set upper temperature threshold is', window_blind_config['high_temp_threshold'], 'degrees', 'pre-set lower temperature threshold is', window_blind_config['low_temp_threshold'], 'degrees',
                              'Current temperature is', current_temperature, 'degrees')
                        self.move_blind('All Doors', 'up')
                        print_blind_change = True
                else: # Open all blinds if the external temperature is now within the pre-set thresholds
                    print('All blinds opening because the last sunlight state before reaching level 2 was 0 or 1 and the outdoor temperature is inside the pre-set thresholds')
                    print('Pre-set upper temperature threshold is', window_blind_config['high_temp_threshold'], 'degrees', 'pre-set lower temperature threshold is', window_blind_config['low_temp_threshold'], 'degrees',
                              'Current temperature is', current_temperature, 'degrees')
                    print_blind_change, window_blind_config['status'] = self.raise_all_blinds(window_blind_config)
            else: # If this level has been reached after being in levels 3 or 4
                if door_open == False: # Set all blinds to venetian state if both doors are closed
                    print_blind_change, window_blind_config['status'] = self.all_blinds_venetian(window_blind_config)
                else: # Open door blinds and set window blinds to venetian state if at least one door is open
                    self.move_blind('All Doors', 'up')
                    self.move_blind('All Windows', 'down')
                    print_blind_change = True
                    # Set blind status
                    window_blind_config['status']['All Windows'] = 'Venetian'
                    window_blind_config['status']['Left Window'] = 'Venetian'
                    window_blind_config['status']['Right Window'] = 'Venetian'
                    window_blind_config['status']['All Doors'] = 'Open'
                    window_blind_config['status']['Left Door'] = 'Open'
                    window_blind_config['status']['Right Door'] = 'Open'
                    window_blind_config['status']['All Blinds'] = 'Venetian'
        else:
            print('No Blind Change. Auto Blind Control is overridden')
            pass
        return(print_blind_change, window_blind_config['status'])

    def set_blind_sunlight_1(self, door_open, auto_override, window_blind_config, current_blind_temp_threshold, current_temperature):
        print('High Sunlight Level 1 Invoked')
        print_blind_change = False
        if auto_override == False:
            if current_blind_temp_threshold == True and door_open == False: # Lower all blinds if the outside temperature is outside the pre-set thresholds and the doors are closed.
                print('All blinds set to Venetian because the outdoor temperature is outside the pre-set thresholds with the doors closed')
                print('Pre-set upper temperature threshold is', window_blind_config['high_temp_threshold'], 'Pre-set lower temperature threshold is', window_blind_config['low_temp_threshold'],
                       'Current temperature is', current_temperature, 'degrees')
                print_blind_change, window_blind_config['status'] = self.all_blinds_venetian(window_blind_config)
            else: # Raise all blinds if the external temperature is within the pre-set thresholds or the doors are opened.
                if current_blind_temp_threshold == True and door_open == True:
                    print('Opening all blinds due to doors being opened, even though the outdoor temperature is outside the pre-set thresholds')
                elif current_blind_temp_threshold == False and door_open == False:
                    print("Opening all blinds because the outdoor temperature is within the pre-set thresholds")
                else: # If current_blind_temp_threshold == False and door_open == True:
                    print("Opening all blinds due to doors being opened and the outdoor temperature is within the pre-set thresholds")
                print('Pre-set upper temperature threshold is', window_blind_config['high_temp_threshold'], 'Pre-set lower temperature threshold is', window_blind_config['low_temp_threshold'],
                       'Current temperature is', current_temperature, 'degrees')
                print_blind_change, window_blind_config['status'] = self.raise_all_blinds(window_blind_config)      
        else:
            print('No Blind Change. Auto Blind Control is overridden')
            pass
        return(print_blind_change, window_blind_config['status'])

    def set_blind_sunlight_0(self, door_open, auto_override, window_blind_config):
        print('High Sunlight Level 0 Invoked')
        # The use of this level is to open the blinds in the morning when level 1 is reached and the outside temperature is within the pre-set levels
        # Make no change in this blind state because it's night time unless a door is opened (caters for case where blinds remain
        # closed due to temperatures being outside thresholds when moving from level 1 to level 0 or the blinds have been manually closed while in level 0)
        print_blind_change = False
        if auto_override == False:
            if door_open == True: # Raise door blinds if a door is opened. Caters for the case where blinds are still set to 50% after
                # sunlight moves from level 1 to level 0 because the temp is outside thresholds
                print('Opening door blinds due to a door being opened')
                self.move_blind('All Doors', 'up')
                print_blind_change = True
                window_blind_config['status']['All Doors'] = 'Open'
                window_blind_config['status']['Left Door'] = 'Open'
                window_blind_config['status']['Right Door'] = 'Open'
        else:
            print('No Blind Change. Auto Blind Control is overridden')
            pass
        return(print_blind_change, window_blind_config['status'])

    def change_auto_override(self, auto_override):
        mgr.print_update('Auto Blind Override button pressed on ')
        self.auto_override = auto_override
        self.auto_override_changed = True

    def change_blind_position(self, blind_id, blind_position):
        # Sets the flag that triggers a blind change in the main homemanager loop that then calls the control_blinds method in the window_blind[blind] object
        mgr.call_control_blinds = {'State': True, 'Blind': self.blind, 'Blind_id': blind_id,
                                   'Blind_position': blind_position}

    def move_blind(self, blind_id, command):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            blind_json = self.window_blind_config['blind commands'][command + ' ' + blind_id]
            s.connect((self.blind_ip_address, self.blind_port))
            s.sendall(blind_json)
            data = s.recv(1024)

    def close_door_impacting_blind(self, blind_id, window_blind_config): # This method closes any blind that covers a door and opens it if a door is opened during that blind closure
        self.move_blind(blind_id, 'down')
        window_blind_config['status'] = self.check_door_state_while_closing(25, window_blind_config) # Checks door state while closing and reverses if a door opens
        self.move_blind(blind_id, 'up')
        time.sleep(0.495)
        self.move_blind(blind_id, 'stop')
        return(True, window_blind_config['status']) 
        
    def close_window_blind(self, blind_id):
        self.move_blind(blind_id, 'down')
        time.sleep(25) # Normal close
        self.move_blind(blind_id, 'up')
        time.sleep(0.495)
        self.move_blind(blind_id, 'stop')

    def venetian_door_impacting_blind(self, blind_id, window_blind_config):
        self.move_blind(blind_id, 'down')
        window_blind_config['status'] = self.check_door_state_while_closing(25, window_blind_config)
        return(window_blind_config['status'])
    
    def venetian_window_blind(self, blind_id):
        self.move_blind(blind_id, 'down')

    def raise_all_blinds(self, window_blind_config):
        self.move_blind('All Blinds', 'up')
        # Set blind status
        for blind_button in window_blind_config['status']:
            window_blind_config['status'][blind_button] = 'Open' 
        return(True, window_blind_config['status'])

    def all_blinds_venetian(self, window_blind_config):
        # Set blind status
        #print('Setting Blind Status')
        for blind_button in window_blind_config['status']:
            window_blind_config['status'][blind_button] = 'Venetian'        
        window_blind_config['status'] = self.venetian_door_impacting_blind('All Blinds', window_blind_config)
        return(True, window_blind_config['status'])
                  
    def check_door_state_while_closing(self, delay, window_blind_config): # Checks if a door has been opened while a door blind is closing and reverses the blind closure if the door has been opened
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
            if door_opened == True:
                if already_opened == False:
                    #mgr.print_update(door + ' opened while blind is closing. Door blinds now opening on ')
                    already_opened = True
                    self.door_blind_override = True
                    self.move_blind('All Doors', 'up')
                    window_blind_config['status']['All Doors'] = 'Open'
                    window_blind_config['status']['Left Door'] = 'Open'
                    window_blind_config['status']['Right Door'] = 'Open'
                    window_blind_config['status']['All Blinds'] = 'Open'
            time.sleep(0.5)
            count += 0.5
        return(window_blind_config['status'])

class AirconClass(object):
    def __init__(self, name, aircon_config, log_aircon_cost_data, log_damper_data, log_aircon_temp_data):
        self.name = name
        self.aircon_config = aircon_config
        #print ('Instantiated Aircon', self, name)
        self.outgoing_mqtt_topic = self.aircon_config['mqtt Topics']['Outgoing']
        self.day_zone = self.aircon_config['Day Zone']
        self.night_zone = self.aircon_config['Night Zone']
        self.indoor_zone = self.day_zone + self.night_zone
        self.control_thermostat = self.aircon_config['Indoor Zone'][0]
        self.thermostat_names = self.indoor_zone + self.aircon_config['Indoor Zone']
        self.active_temperature_change_rate = {name: 0 for name in self.thermostat_names}
        self.initial_temperature_history = [0.0 for x in range (10)]
        # Set up Aircon status data
        self.status = {'Remote Operation': False,'Heat': False, 'Cool': False,'Fan': False, 'Fan Hi': False, 'Fan Lo': False,
                        'Heating': False, 'Filter':False, 'Compressor': False, 'Malfunction': False, 'Damper': 50}
        
        self.settings = {'Thermo Heat': False, 'Thermo Cool': False, 'Thermo Off': True, 'Ventilate' : False, 'indoor_thermo_mode': 'Cool', 'Day_zone_target_temperature': 21,
                          'Day_zone_current_temperature': 1, 'Night_zone_target_temperature': 21, 'Night_zone_current_temperature': 1,
                         'Indoor_zone_target_temperature': 21, 'Indoor_zone_current_temperature': 1, 'target_day_zone': 50, 'Day_zone_sensor_active': 0,
                          'Night_zone_sensor_active': 0, 'Indoor_zone_sensor_active': 0, 'aircon_previous_mode': 'Off', 'aircon_mode_change': False,
                          'aircon_rate_change': False, 'aircon_previous_power_rate': 0, 'aircon_previous_update_time': time.time(),
                          'aircon_previous_cost_per_hour': 0}
        
        # Set up effectiveness logging data
        self.aircon_log_items = self.indoor_zone + ['Day'] + ['Night']
        self.active_temperature_history = {name: self.initial_temperature_history for name in self.aircon_log_items}
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
        self.aircon_power_consumption = {'Heat': 4.97, 'Cool': 5.42, 'Idle': 0.13, 'Off': 0} # Power consumption in kWH for each mode
        self.aircon_weekday_power_rates = {0:{'name': 'off_peak1', 'rate': 0.1155, 'stop_hour': 6}, 7:{'name':'shoulder1', 'rate': 0.1771, 'stop_hour': 13},
                              14:{'name':'peak', 'rate':0.4218, 'stop_hour': 19}, 20: {'name': 'shoulder2', 'rate': 0.1771, 'stop_hour': 21},
                              22:{'name': 'off_peak2', 'rate': 0.1155, 'stop_hour': 23}}
        self.aircon_weekend_power_rates = {0:{'name': 'off_peak1', 'rate': 0.1155, 'stop_hour': 6}, 7:{'name':'shoulder', 'rate': 0.1771, 'stop_hour': 21},
                              22:{'name': 'off_peak2', 'rate': 0.1155, 'stop_hour': 23}}
        self.aircon_running_costs = {'total_cost':0, 'total_hours': 0}
        self.log_aircon_cost_data = log_aircon_cost_data

    def start_up(self):
        # Reset Homebridge Thermostats/Ventilation Buttons and set zone temps on start-up
        homebridge.reset_aircon_thermostats(self.thermostat_status)
        self.update_zone_temps()
        # Reset Domoticz Thermostats on start-up
        domoticz.reset_aircon_thermostats(self.thermostat_status)
        # Initialise aircon effectiveness dictionary based on previously logged data
        self.populate_starting_aircon_effectiveness()
        # Initialise aircon power dictionary based on previously logged data
        self.populate_aircon_power_status()
        self.send_aircon_command('Update Status') # Get aircon status on startup
        self.send_aircon_command('Off') # Set aircon to Thermo Off mode on startup

    def shut_down(self):
        self.send_aircon_command('Update Status') # Get aircon status on shut-down
        self.send_aircon_command('Off') # Set aircon to Thermo Off mode on shut-down
        # Reset Homebridge Thermostats and Ventilation buttons on shut-down
        self.thermostat_status = {name: {'Current Temperature': 1, 'Target Temperature': 21, 'Mode': 'Off', 'Active': 0} for name in self.thermostat_names}
        homebridge.reset_aircon_thermostats(self.thermostat_status)
        # Reset Domoticz Thermostats on shut-down
        domoticz.reset_aircon_thermostats(self.thermostat_status)

    def process_ventilation_button(self, ventilation):
        #print('Process Aircon Ventilation Button. Ventilation:', ventilation, 'Thermo Off:', self.settings['Thermo Off'])
        if self.settings['Thermo Off'] == True: # Aircon Ventilation mode can only be set if the aircon is in Thermo Off Mode
            if ventilation == True:
                self.settings['Ventilate'] = True
                self.send_aircon_command('Ventilate')
            else:
                self.settings['Ventilate'] = False
                self.send_aircon_command('Off')
            #print('Setting Ventilation', self.settings['Ventilate'])
        else: # Reset Homebridge Ventilation Button to previous state if it's not possible to be in that mode
            time.sleep(0.5)
            homebridge.reset_aircon_ventilation_button()      

    def set_thermostat(self, thermostat_name, control, setting): 
        if thermostat_name == self.control_thermostat: # Only invoke mode changes if it's the control thermostat
            if control == 'Mode':
                if setting == 'Off':
                    #print (str(parsed_json))
                    self.settings['Thermo Heat'] = False
                    self.settings['Thermo Cool'] = False
                    self.settings['Thermo Off'] = True
                    self.settings['Ventilate'] = False
                    homebridge.reset_aircon_ventilation_button() # Reset Homebridge ventilation button whenever the control thermostat mode is invoked
                    self.thermostat_status[thermostat_name]['Mode'] = setting
                    self.thermostat_status[thermostat_name]['Active'] = self.thermostat_mode_active_map[setting]
                    self.send_aircon_command('Off')
                if setting == 'Heat':
                    #print (str(parsed_json))
                    if self.settings['Indoor_zone_sensor_active'] == 1: #Only do something if at least one sensor is active
                        self.settings['Thermo Heat'] = True
                        self.settings['Thermo Cool'] = False
                        self.settings['Thermo Off'] = False
                        self.settings['Ventilate'] = False
                        homebridge.reset_aircon_ventilation_button() # Reset Homebridge ventilation button whenever the control thermostat mode is invoked
                        self.settings['indoor_thermo_mode'] = 'Heat'
                        self.thermostat_status[thermostat_name]['Mode'] = setting
                        self.thermostat_status[thermostat_name]['Active'] = self.thermostat_mode_active_map[setting]
                        self.send_aircon_command('Thermostat Heat')
                    else:
                        print('Trying to start aircon without any sensor active. Command ignored')
                        homebridge.reset_aircon_control_thermostat() # Set homebridge aircon control thermostat back to Off
                if setting == 'Cool': 
                    #print (str(parsed_json))
                    if self.settings['Indoor_zone_sensor_active'] == 1: #Only do something if at least one sensor is active
                        self.settings['Thermo Heat'] = False
                        self.settings['Thermo Cool'] = True
                        self.settings['Thermo Off'] = False
                        self.settings['Ventilate'] = False
                        homebridge.reset_aircon_ventilation_button() # Reset Homebridge ventilation button whenever the control thermostat mode is invoked
                        self.settings['indoor_thermo_mode'] = 'Cool'
                        self.thermostat_status[thermostat_name]['Mode'] = setting
                        self.thermostat_status[thermostat_name]['Active'] = self.thermostat_mode_active_map[setting]
                        self.send_aircon_command('Thermostat Cool')
                    else:
                        print('Trying to start aircon without any sensor active. Command ignored')
                        homebridge.reset_aircon_control_thermostat() # Set homebridge aircon control thermostat back to Off
            self.update_zone_temps() # Update the "Day", "Night" and "Indoor" Zones current temperatures with active temperature sensor readings and the "Indoor" Target Temperature is updated with the target temperatures of the active sensor settings
            indoor_control_mode = self.thermostat_status[self.control_thermostat]['Mode']
            self.update_active_thermostats(indoor_control_mode)  # Ensure that active thermostats have the same mode setting as the control thermostat
        else:
            if control == 'Target Temperature':
                self.thermostat_status[thermostat_name]['Target Temperature'] = setting
                #mgr.print_update('Updating ' + thermostat_name + ' Target Temperature to ' + str(setting) + " Degrees, Actual Temperature = " + str(self.thermostat_status[thermostat_name]['Current Temperature']) + " Degrees on ")
            if control == 'Mode':
                self.thermostat_status[thermostat_name]['Mode'] = setting
                self.thermostat_status[thermostat_name]['Active'] = self.thermostat_mode_active_map[setting]
            self.update_zone_temps() # Update the "Day", "Night" and "Indoor" Zones current temperatures with active temperature sensor readings
            indoor_control_mode = self.thermostat_status[self.control_thermostat]['Mode']
            self.update_active_thermostats(indoor_control_mode) # Ensure that active sensors have the same mode setting as the Indoor Control


    def send_aircon_command(self, command): # Send command to aircon controller
        aircon_command = {}
        aircon_command['service'] = command
        client.publish(self.outgoing_mqtt_topic, json.dumps(aircon_command))

    def capture_status(self, parsed_json):
        if parsed_json['service'] == 'Heartbeat':
            #mgr.print_update('Received Heartbeat from Aircon and sending Ack on ')
            self.send_aircon_command('Heartbeat Ack')
        elif parsed_json['service'] == 'Status Update':
            #mgr.print_update('Airconditioner Status update on ')
            #print(parsed_json)
            for status_item in self.status:
                #if self.status[status_item] != parsed_json[status_item]:
                    #print('Aircon', status_item, 'changed from', self.status[status_item], 'to', parsed_json[status_item])
                self.status[status_item] = parsed_json[status_item]
                homebridge.update_aircon_status(status_item, self.status[status_item])
                domoticz.update_aircon_status(status_item, self.status[status_item])
                       
    def update_temp_history(self, name, temperature, log_aircon_temp_data): # Called by a multisensor object upon a temperature reading so that temperature history can be logged
        if log_aircon_temp_data == True: # Only log data if requested in log_aircon_temp_data
            if name in self.indoor_zone: # Only capture temperature history for known indoor names
                #print('Temperature History Logging', 'Name', name, 'Temperature', temperature)
                current_temp_update_time = time.time()
                #print('Current Time', current_temp_update_time, 'Previous Update Time for', name, self.temperature_update_time[name])
                if (current_temp_update_time - self.temperature_update_time[name]) > 10: # Ignore duplicate temp data if temp comes in less than 10 seconds (Each sensor sends its temp twice)
                    #print('name', name, 'Temperature', temperature)
                    for pointer in range (9, 0, -1): # Move previous temperatures one position in the list to prepare for new temperature to be recorded
                        self.active_temperature_history[name][pointer] = self.active_temperature_history[name][pointer - 1]
                    if (self.status['Cool'] == True or self.status['Heat'] == True) and self.status['Remote Operation'] == True and self.status['Heating'] == False and self.status['Compressor'] == True and self.status['Malfunction'] == False:
                        # Only update the Active Temperature if cooling or heating, under Raspberry Pi control and the aircon isn't passive
                        if self.status['Damper'] == 100: # Don't treat any Night Zone sensors as active if the damper is 100% in the Day position
                            self.night_mode = 0
                            self.day_mode = 1
                        elif self.status['Damper'] == 0: # Don't treat any Day Zone sensors as active if the damper is 100% in the Night position
                            self.day_mode = 0
                            self.night_mode = 1
                        else: # Treat both zones as active if the damper is anywhere between open and closed
                            self.night_mode = 1
                            self.day_mode = 1
                        if name in self.day_zone:
                            self.active_temperature_history[name] [0] = temperature * self.day_mode
                        elif name in self.night_zone:
                            self.active_temperature_history[name] [0] = temperature * self.night_mode
                        else:
                            print('Invalid aircon sensor', name)
                    else:
                        self.active_temperature_history[name] [0] = 0.0
                    valid_temp_history = True
                    for pointer in range (0, 10):
                        if self.active_temperature_history[name][pointer] == 0:
                            valid_temp_history = False
                    #print('Valid temp history', valid_temp_history, 'Latest Reading', self.active_temperature_history[name] [0])
                    if valid_temp_history == True: #Update active temp change rate if we have 10 minutes of valid active temperatures
                        active_temp_change = round((self.active_temperature_history[name] [0] - self.active_temperature_history[name] [9])*6, 1) # calculate the temp change per hour over the past 10 minutes, given that there are two sensor reports every minute. +ve heating, -ve cooling
                        #print('Active Temp Change', active_temp_change)
                        if abs(active_temp_change - self.active_temperature_change_rate[name]) >= 0.1: #Log if there's a change in the rate
                            self.active_temperature_change_rate[name] = active_temp_change
                            self.active_temperature_change_rate['Day'] = self.mean_active_temp_change_rate(self.day_zone) # Calculate Day zone temperature change rate by taking the mean temp change rates of active day zone sensors
                            self.active_temperature_change_rate['Night'] = self.mean_active_temp_change_rate(self.night_zone) # Calculate Night zone temperature change rate by taking the mean temp change rates of active night zone sensors
                            self.active_temperature_change_rate['Indoor'] = self.mean_active_temp_change_rate(self.indoor_zone) # Calculate Indoor zone temperature change rate by taking the mean temp change rates of active indoor sensors
                            #print("Day Zone Active Change Rate:", self.active_temperature_change_rate['Day'], "Night Zone Active Change Rate:", self.active_temperature_change_rate['Night'], "Indoor Zone Active Change Rate:", self.active_temperature_change_rate['Indoor'])
                            today = datetime.now()
                            time_stamp = today.strftime('%A %d %B %Y @ %H:%M:%S')
                            log_data = ('Time: ' + str(time_stamp) + '; Spot Active Temperature History for ' + str(name) + ' name: ' + str(self.active_temperature_history[name])
                                        + '; Active Temperature Change Rate for ' + str(name) + ' name: ' + str(self.active_temperature_change_rate[name]) + '; Active Day Change Rate: ' +
                                        str(self.active_temperature_change_rate['Day']) + '; Active Night Change Rate: ' + str(self.active_temperature_change_rate['Night']) + '; Active Indoor Change Rate: ' +
                                        str(self.active_temperature_change_rate['Indoor']) + '; Damper Position: ' + str(self.status['Damper']) + '\n')
                            with open('/home/pi/HomeManager/spot_temp_history.log', 'a') as f:
                                    f.write(log_data)
                            if self.status['Heat'] == True:
                                if self.active_temperature_change_rate[name] > self.max_heating_effectiveness[name]: # Record Maximum only
                                    self.max_heating_effectiveness[name] = self.active_temperature_change_rate[name]
                                if round(self.active_temperature_change_rate['Day'], 1) > self.max_heating_effectiveness['Day'] and self.day_mode == 1: # Record Maximum when in Day Mode only
                                    self.max_heating_effectiveness['Day'] = round(self.active_temperature_change_rate['Day'], 1)
                                if round(self.active_temperature_change_rate['Night'], 1) > self.max_heating_effectiveness['Night'] and self.night_mode == 1:  # Record Maximum when in Night Mode only
                                    self.max_heating_effectiveness['Night'] = round(self.active_temperature_change_rate['Night'], 1)
                                #print("Aircon Maximum Heating Effectiveness:", self.max_heating_effectiveness)
                                if self.active_temperature_change_rate[name] < self.min_heating_effectiveness[name]: # Record Minimum only
                                    self.min_heating_effectiveness[name] = self.active_temperature_change_rate[name]
                                if round(self.active_temperature_change_rate['Day'], 1) < self.min_heating_effectiveness['Day'] and self.day_mode == 1: # Record Minimum when in Day Mode only
                                    self.min_heating_effectiveness['Day'] = round(self.active_temperature_change_rate['Day'], 1)
                                if round(self.active_temperature_change_rate['Night'], 1) < self.min_heating_effectiveness['Night'] and self.night_mode == 1: # Record Minimum when in Night Mode only
                                    self.min_heating_effectiveness['Night'] = round(self.active_temperature_change_rate['Night'], 1)
                                #print("Aircon Minimum Heating Effectiveness:", min_heating_effectiveness)
                                today = datetime.now()
                                time_stamp = today.strftime('%A %d %B %Y @ %H:%M:%S')
                                log_data = ('Time: ' + str(time_stamp) + '; Max Heat: ' + str(self.max_heating_effectiveness) + '; Min Heat: ' + str(self.min_heating_effectiveness) +
                                            '; Heating Effectiveness Active Temp History: ' + str(self.active_temperature_history) + '\n')
                                with open('/home/pi/HomeManager/effectiveness.log', 'a') as f:
                                    f.write(log_data)
                            elif self.status['Cool'] == True:
                                if 0 - self.active_temperature_change_rate[name] > self.max_cooling_effectiveness[name]: # Record Maximum only
                                    self.max_cooling_effectiveness[name] = 0 - self.active_temperature_change_rate[name]
                                if 0 - round(self.active_temperature_change_rate['Day'], 1) > self.max_cooling_effectiveness['Day']: # Record Maximum only
                                    self.max_cooling_effectiveness['Day'] = 0 - round(self.active_temperature_change_rate['Day'], 1)
                                if 0 - round(self.active_temperature_change_rate['Night'], 1) > self.max_cooling_effectiveness['Night']: # Record Maximum only
                                    self.max_cooling_effectiveness['Night'] = 0 - round(self.active_temperature_change_rate['Night'], 1)
                                #print("Aircon Maximum Cooling Effectiveness:", max_cooling_effectiveness)
                                if 0 - self.active_temperature_change_rate[name] < self.min_cooling_effectiveness[name]: # Record Minimum only
                                    self.min_cooling_effectiveness[name] = 0 - self.active_temperature_change_rate[name]
                                if 0 - round(self.active_temperature_change_rate['Day'], 1) < self.min_cooling_effectiveness['Day'] and self.day_mode == 1: # Record Minimum when in Day Mode only
                                    self.min_cooling_effectiveness['Day'] = 0 - round(self.active_temperature_change_rate['Day'], 1)
                                if 0 - round(self.active_temperature_change_rate['Night'], 1) < self.min_cooling_effectiveness['Night']and self.night_mode == 1: # Record Minimum when in Day Mode only
                                    self.min_cooling_effectiveness['Night'] = 0 - round(self.active_temperature_change_rate['Night'], 1)
                                #print("Aircon Minimum Cooling Effectiveness:", min_cooling_effectiveness)
                                today = datetime.now()
                                time_stamp = today.strftime('%A %d %B %Y @ %H:%M:%S')
                                log_data = ('Time: ' + str(time_stamp) + '; Max Cool: ' + str(self.max_cooling_effectiveness) + '; Min Cool: ' + str(self.min_cooling_effectiveness) + '; Cooling Effectiveness Active Temp History: ' + 
                                            str(self.active_temperature_history) + '\n')
                                with open('/home/pi/HomeManager/effectiveness.log', 'a') as f:
                                    f.write(log_data)
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
                homebridge.update_aircon_thermostat(thermostat, mode)

    def update_zone_temps(self): # Called by 'process_aircon_buttons' and the 'capture_domoticz_sensor_data' modules to ensure that the "Day", "Night" and "Indoor" Zones current temperatures
        #are updated with active temperature sensor readings and the "Indoor" Target Temperature is updated with the target temperatures of the active sensor settings
        self.settings['Day_zone_sensor_active'], self.settings['Day_zone_target_temperature'], self.settings['Day_zone_current_temperature'] = self.mean_active_temperature(self.day_zone)
        self.settings['Night_zone_sensor_active'], self.settings['Night_zone_target_temperature'], self.settings['Night_zone_current_temperature'] = self.mean_active_temperature(self.night_zone)
        self.settings['Indoor_zone_sensor_active'], self.settings['Indoor_zone_target_temperature'], self.settings['Indoor_zone_current_temperature'] = self.mean_active_temperature(self.indoor_zone)
        if self.settings['Indoor_zone_sensor_active'] != 0: # Only update the Indoor Climate Control Temperatures if at least one sensor is active
            homebridge.update_control_thermostat_temps(self.settings['Indoor_zone_target_temperature'], self.settings['Indoor_zone_current_temperature'])
    
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
            target_temperature = target_num_sum / den_sum
            current_temperature = current_num_sum / den_sum  
        else:
            sensor_active = 0
            target_temperature = 1
            current_temperature = 1
        return sensor_active, target_temperature, current_temperature

    def control_aircon(self):
        if self.status['Remote Operation'] == True: # Only invoke aircon control is the aircon is under control of the Raspberry Pi
            #print ("Thermo Off Mode", self.settings)
            if self.settings['Thermo Off'] == False: # Only invoke aircon control if the control thermostat is not set to 'Off'
                self.settings['Ventilate'] = False
                #print("Thermo On Mode")
                if self.settings['Indoor_zone_sensor_active'] == 1: # Only invoke aircon control if at least one aircon temp sensor is active
                    #print("Indoor Active")
                    mode, self.settings = self.check_power_change(self.status, self.settings, self.log_aircon_cost_data) # Check for power rate or consumption change
                    if self.settings['Day_zone_sensor_active'] ^ self.settings['Night_zone_sensor_active'] == 1: #If only one zone is active
                        #print("Only One Zone Active")
                        previous_target_day_zone = self.settings['target_day_zone'] # Record the current damper position to determine if a change needs to invoked
                        if self.settings['Day_zone_sensor_active'] == 1:
                            self.settings['target_day_zone'] = 100
                            self.settings['target_temperature'] = self.settings['Day_zone_target_temperature']
                            temperature_key = 'Day_zone_current_temperature'
                            #print("Day Zone Active")
                        else:
                            self.settings['target_day_zone'] = 0
                            self.settings['target_temperature'] = self.settings['Night_zone_target_temperature']
                            temperature_key = 'Night_zone_current_temperature'
                            #print("Night Zone Active")
                        #print(" ")
                        if self.settings['target_day_zone'] != previous_target_day_zone: # Move Damper if Target Zone changes
                            mgr.print_update("Updating Homebridge Aircon Day Zone Percent from " + str(previous_target_day_zone) + " to " + str(self.settings['target_day_zone']) + " on ")
                            self.move_damper(self.settings['target_day_zone'], self.log_damper_data)
                        if self.settings[temperature_key] != 1: # Don't do anything until the Temp is updated on startup
                            # Set the temp boundaries for a mode change to provide hysteresis
                            target_temp_high = self.settings['target_temperature'] + 0.4
                            target_temp_low = self.settings['target_temperature'] - 0.4
                            if self.settings['Thermo Heat'] == True: # If in Thermo Heat Mode
                                #print("Thermo Heat Mode")
                                if self.settings[temperature_key] < self.settings['target_temperature']: # If actual temp is lower than target temp, stay in heat mode, fan hi
                                    self.set_aircon_mode("Heat")
                                if self.settings[temperature_key] > target_temp_high:# If target temperature is 0.5 degree higher than target temp, put in fan mode, lo
                                    self.set_aircon_mode("Idle")
                            if self.settings['Thermo Cool'] == True: #If in Thermo Cool Mode
                                #print("Thermo Cool Mode")
                                if self.settings[temperature_key] > self.settings['target_temperature']: #if actual temp is higher than target temp, turn aircon on in cool mode, fan hi
                                    self.set_aircon_mode("Cool")
                                if self.settings[temperature_key] < target_temp_low:#if actual temp is 0.5 degree lower than target temp, put in fan mode hi
                                    self.set_aircon_mode("Idle")
                    else:
                        # Both Zones Active
                        # Set the temp boundaries for a mode change to provide hysteresis
                        day_target_temp_high = self.settings['Day_zone_target_temperature'] + 0.4
                        day_target_temp_low = self.settings['Day_zone_target_temperature'] - 0.4
                        night_target_temp_high = self.settings['Night_zone_target_temperature'] + 0.4
                        night_target_temp_low = self.settings['Night_zone_target_temperature'] - 0.4 
                        if self.settings['Day_zone_current_temperature'] != 1 and self.settings['Night_zone_current_temperature'] != 1: # Don't do anything until the Temps are updated on startup
                            if self.settings['Thermo Heat'] == True: # If in Thermo Heat Mode
                                if self.settings['Day_zone_current_temperature'] < self.settings['Day_zone_target_temperature'] or self.settings['Night_zone_current_temperature'] < self.settings['Night_zone_target_temperature']: # Go into heat mode and stay there if there's gap against the target in at least one zone
                                    self.set_aircon_mode("Heat")
                                if self.settings['Day_zone_current_temperature'] > day_target_temp_high and self.settings['Night_zone_current_temperature'] > night_target_temp_high: # If both zones are 0.5 degree higher than target temps, put in fan mode, lo
                                    self.set_aircon_mode("Idle")
                                day_zone_gap = self.settings['Day_zone_target_temperature'] - self.settings['Day_zone_current_temperature']
                                night_zone_gap = self.settings['Night_zone_target_temperature'] - self.settings['Night_zone_current_temperature']
                                day_zone_gap_max = day_target_temp_high - self.settings['Day_zone_current_temperature']
                                night_zone_gap_max = night_target_temp_high - self.settings['Night_zone_current_temperature']
                                self.set_dual_zone_damper(day_zone_gap, night_zone_gap, day_zone_gap_max, night_zone_gap_max) # Set Damper based on gap between current and target temperatures 
                            elif self.settings['Thermo Cool'] == True: # If in Thermo Cool Mode
                                if self.settings['Day_zone_current_temperature'] > self.settings['Day_zone_target_temperature'] or self.settings['Night_zone_current_temperature'] > self.settings['Night_zone_target_temperature']: # Go into cool mode and stay there if there's gap against the target in at least one zone
                                    self.set_aircon_mode("Cool")
                                if self.settings['Day_zone_current_temperature'] < day_target_temp_low and self.settings['Night_zone_current_temperature'] < night_target_temp_low: # If both zones are 0.5 degree lower than target temps, put in fan mode, lo
                                    self.set_aircon_mode("Idle")
                                day_zone_gap = self.settings['Day_zone_current_temperature'] - self.settings['Day_zone_target_temperature']
                                night_zone_gap = self.settings['Night_zone_current_temperature'] - self.settings['Night_zone_target_temperature']
                                day_zone_gap_max = self.settings['Day_zone_current_temperature'] - day_target_temp_low
                                night_zone_gap_max = self.settings['Night_zone_current_temperature'] - night_target_temp_low
                                self.set_dual_zone_damper(day_zone_gap, night_zone_gap, day_zone_gap_max, night_zone_gap_max) # Set Damper based on gap between current and target temperatures
                            else:
                                mgr.print_update ("Thermo Off Mode Invoked on ")
                else: # Stay in Fan Mode if no valid actual temp reading
                    print ("No Valid Temp")
                    self.set_aircon_mode("Idle")
            else: # If Aircon is off or in Ventilation Mode
                if self.settings['Ventilate'] == False: # If the aircon is off
                    if self.settings['aircon_previous_mode'] != 'Off': # Update the aircon power log when put into Thermo Off Mode
                        mode = 'Off'
                        update_date_time = datetime.now()
                        current_power_rate = self.check_power_rate(update_date_time)
                        self.update_aircon_power_log(mode, current_power_rate, time.time(), self.log_aircon_cost_data)
                else: # If the aircon is in Ventilation Mode
                    if self.settings['target_day_zone'] != 60: # If the damper is not set to both zones
                        previous_target_day_zone = self.settings['target_day_zone'] # Record the current damper position to determine if a change needs to invoked
                        self.settings['target_day_zone'] = 60 # Set the damper to both zones
                        self.move_damper(self.settings['target_day_zone'], self.log_damper_data)
                    mode, self.settings = self.check_power_change(self.status, self.settings, self.log_aircon_cost_data)         

    def set_aircon_mode(self, mode): # Called by 'control_aircon' to set aircon mode
        if mode == 'Heat':
            if self.status['Heat'] == False: # Only set to heat mode if it's not already been done
                mgr.print_update("Heat Mode Selected on ")
                self.print_aircon_mode_state()
                self.send_aircon_command('Heat Mode')
                self.status['Heat'] = True
            if self.status['Fan Hi'] == False: # Only set to Fan to Hi if it's not already been done
                self.send_aircon_command('Fan Hi')
                self.status['Fan Hi'] = True
        if mode == 'Cool':
            if self.status['Cool'] == False: # Only set to cool mode if it's not already been done
                mgr.print_update("Cool Mode Selected on ")
                self.print_aircon_mode_state()
                client.publish(self.outgoing_mqtt_topic, '{"service": "Cool Mode"}')
                self.status['Cool'] = True
            if self.status['Fan Hi'] == False: # Only set to Fan to Hi if it's not already been done
                self.send_aircon_command('Fan Hi')
                self.status['Fan Hi'] = True
        if mode == 'Idle':
            if self.status['Fan'] == False: # Only set to Fan Mode if it's not already been done
                mgr.print_update("Idle Mode Selected on ")
                self.print_aircon_mode_state() 
                self.send_aircon_command('Fan Mode')
                self.status['Fan'] = True
            if self.status['Fan Lo'] == False: # Only set Fan to Lo if it's not already been done
                self.send_aircon_command('Fan Lo')
                self.status['Fan Lo'] = True

    def print_aircon_mode_state(self):
        print("Day Temp is", round(self.settings['Day_zone_current_temperature'], 1), "Degrees. Day Target Temp is", round(self.settings['Day_zone_target_temperature'], 1), "Degrees. Night Temp is",
                                          round(self.settings['Night_zone_current_temperature'], 1), "Degrees. Night Target Temp is", round(self.settings['Night_zone_target_temperature'], 1), "Degrees")

    def check_power_change(self, status, settings, log_aircon_cost_data):
        # Prepare data for power consumption logging
        update_date_time = datetime.now()
        current_power_rate = self.check_power_rate(update_date_time)
        if settings['Ventilate'] == False: # Set mode based on aircon status if the aircon is not in Ventilate Setting
            if status['Cool'] == True:
                mode = 'Cool'
            elif status['Heat'] == True:
                mode = 'Heat'
            elif status['Fan'] == True:
                mode = 'Idle'
            else:
                mode = 'Off'
        else: # Always set mode to 'Idle' if the aircon is in Ventilate Setting
            mode = 'Idle'
        #print('aircon_previous_power_rate =', settings['aircon_previous_power_rate'], 'aircon_current_power_rate =', current_power_rate)
        if current_power_rate != settings['aircon_previous_power_rate']: # If the power rate has changed
            mgr.print_update("Power Rate Changed from $" + str(settings['aircon_previous_power_rate']) + " per kWH to $" + str(current_power_rate) + " per kWH on ")
            self.update_aircon_power_log(mode, current_power_rate, time.time(), log_aircon_cost_data)  # Update aircon power log if there's a change of power rate
        if mode != settings['aircon_previous_mode']: # If the aircon mode has changed
            self.update_aircon_power_log(mode, current_power_rate, time.time(), log_aircon_cost_data)  # Update aircon power log if there's a change of mode
        return mode, settings                   
        
    def check_power_rate(self, update_date_time):
        update_day = update_date_time.strftime('%A')
        if update_day == 'Saturday' or update_day == 'Sunday':
            power_rates = self.aircon_weekend_power_rates
        else:
            power_rates = self.aircon_weekday_power_rates
        update_hour = int(update_date_time.strftime('%H'))
        for time in power_rates:
            if update_hour >= time and update_hour <= power_rates[time]['stop_hour']:
                current_aircon_power_rate = power_rates[time]['rate']
        return current_aircon_power_rate
     
    def update_aircon_power_log(self, mode, current_power_rate, update_time, log_aircon_cost_data):
        #print('Current Power Rate is $' + current_power_rate + ' per kWH')
        aircon_current_cost_per_hour = round(current_power_rate * self.aircon_power_consumption[mode], 2)
        if self.settings['aircon_previous_mode'] == 'Off': # Don't log anything if the previous aircon mode was off
            mgr.print_update('Aircon started in ' + mode + ' mode at a cost of $' + str(aircon_current_cost_per_hour) + ' per hour on ')
        else:
            aircon_previous_mode_time_in_hours = (update_time - self.settings['aircon_previous_update_time'])/3600
            aircon_previous_cost = round(aircon_previous_mode_time_in_hours * self.settings['aircon_previous_cost_per_hour'], 2)
            self.aircon_running_costs['total_cost'] = self.aircon_running_costs['total_cost'] + aircon_previous_cost
            self.aircon_running_costs['total_hours'] = self.aircon_running_costs['total_hours'] + aircon_previous_mode_time_in_hours
            self.total_aircon_average_cost_per_hour = self.aircon_running_costs['total_cost'] / self.aircon_running_costs['total_hours']
            if mode != 'Off':
                mgr.print_update('Aircon changed to ' + mode + ' mode that will cost $' + str(aircon_current_cost_per_hour) + ' per hour on ')
            else:
                mgr.print_update('Aircon changed to ' + mode + ' mode on ')
            print('Previous aircon mode was', self.settings['aircon_previous_mode'], 'for', str(round(aircon_previous_mode_time_in_hours*60, 1)), 'minutes at a cost of $' + str(round(aircon_previous_cost, 2)))
            print('Total aircon operating cost is $'+ str(round(self.aircon_running_costs['total_cost'], 2)) + ' over ' + str(round(self.aircon_running_costs['total_hours'], 1))
                  + ' hours with an average operating cost of $' + str(round(self.total_aircon_average_cost_per_hour, 2)) + ' per hour')
            if log_aircon_cost_data == True:
                today = datetime.now()
                time_stamp = today.strftime('%A %d %B %Y @ %H:%M:%S')
                log_data = (str(time_stamp) + "," + str(round(self.aircon_running_costs['total_hours'], 1)) + "," + str(round(self.aircon_running_costs['total_cost'], 2))
                            + "," + mode + "," + self.settings['aircon_previous_mode'] + "," + str(round(aircon_previous_mode_time_in_hours*60, 1))
                            + "," + str(round(aircon_previous_cost, 2)) + "\n")
                with open("/home/pi/HomeManager/aircon_cost.log", "a") as f:
                    f.write(log_data)
        #print('aircon_previous_power_rate =', self.settings['aircon_previous_power_rate'], 'aircon_previous_mode =', self.settings['aircon_previous_mode'])
        self.settings['aircon_previous_power_rate'] = current_power_rate
        self.settings['aircon_previous_update_time'] = update_time
        self.settings['aircon_previous_mode'] = mode
        self.settings['aircon_previous_cost_per_hour'] = aircon_current_cost_per_hour
        #print('aircon_previous_power_rate =', self.settings['aircon_previous_power_rate'], 'aircon_previous_mode =', self.settings['aircon_previous_mode'])

    def move_damper(self, damper_percent, log_damper_data): # Called by 'control_aircon' to move damper to a nominated zone
        #print_update("Move Damper to " + str(damper_percent) + " percent at ")
        if log_damper_data == True:
            today = datetime.now()
            time_stamp = today.strftime('%A %d %B %Y @ %H:%M:%S')
            log_data = (str(time_stamp) + "," + str(damper_percent) + "\n")
            with open("/home/pi/HomeManager/aircon_damper.log", "a") as f:
                f.write(log_data)
        aircon_json = {}
        aircon_json['service'] = 'Damper Percent'
        aircon_json['value'] = damper_percent
        client.publish(self.outgoing_mqtt_topic, json.dumps(aircon_json))
        homebridge.set_target_damper_position(damper_percent)

    def set_dual_zone_damper(self, day_zone_gap, night_zone_gap, day_zone_gap_max, night_zone_gap_max): # Called by control_aircon in dual zone mode to set the damper to an optimal position, based on relative temperature gaps
        if day_zone_gap == 0 and night_zone_gap == 0: # If both zones are equal to their target temperatures
            #print('Damper: Balance Zones')
            optimal_day_zone = 60 # Balance zones
        elif day_zone_gap > 0 and night_zone_gap < 0: # If the Night Zone is the only zone that's passed its target temperature
            #print('Damper: Night Zone Passed Target Temperature. Set to Day Zone')
            optimal_day_zone = 100 # Move to Day Zone
        elif day_zone_gap < 0 and night_zone_gap > 0: # If the Day Zone is the only zone that's passed its target temperature
            #print('Damper: Day Zone Passed Target Temperature. Set to Night Zone')
            optimal_day_zone = 0 # Move to Night Zone
        else: # If both zones have passed their target temperatures or neither zone has passed its target temperature or only one zone is equal to its target temperature
            day_proportion = day_zone_gap / (day_zone_gap + night_zone_gap)
            night_proportion = night_zone_gap / (day_zone_gap + night_zone_gap)
            if day_zone_gap >= 0 and night_zone_gap >= 0: # If neither zone has passed its target temperature or one has met and the other has not passed its target temperature
                #print('Damper Algorithm: Neither Zone Passed Target Temperature')
                optimal_day_zone_not_passed = 60 * day_proportion / (0.6 * day_proportion + 0.4 * night_proportion) # Damper is biased towards Day Zone
                optimal_day_zone = optimal_day_zone_not_passed # Damper is biased towards Day Zone
            elif day_zone_gap <= 0 and night_zone_gap <= 0: # If both zones have passed their target temperature or one has met and the other has passed their target temperature
                #print('Damper Algorithm: Both Zones Passed Target Temperature')
                if day_zone_gap_max < 0 and night_zone_gap_max >= 0: # Set to night zone if only day zone has reached max gap 
                    optimal_day_zone = 0
                elif night_zone_gap_max < 0 and day_zone_gap_max >= 0: # Set to day zone if only night zone has reached max gap 
                    optimal_day_zone = 100
                elif day_zone_gap_max < 0 and night_zone_gap_max < 0: # Balance zones if both have reached max gaps
                    optimal_day_zone = 60
                else: # No Zones met max gap 
                    optimal_day_zone_passed = 60 * night_proportion / (0.6 * night_proportion + 0.4 * day_proportion) # Damper is biased towards Day Zone but invert for negative zone temp gaps
                    optimal_day_zone = optimal_day_zone_passed
            else:
                print('Unforseen Damper setting. Day Zone Gap', day_zone_gap, 'Night Zone Gap', night_zone_gap)
                optimal_day_zone = 60 # Balance zones
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
        if self.settings['target_day_zone'] != set_day_zone:
            self.settings['target_day_zone'] = set_day_zone
            self.move_damper(self.settings['target_day_zone'], self.log_damper_data)
            mgr.print_update("Moving Damper to " + str(self.settings['target_day_zone']) + " Percent on ")
            print ("Day Zone Gap", round(day_zone_gap, 2), "Degrees. Night Zone Gap", round(night_zone_gap, 2), "Degrees")
            print("Day Temp is", round(self.settings['Day_zone_current_temperature'],1), "Degrees. Day Target Temp is", self.settings['Day_zone_target_temperature'], "Degrees. Night Temp is",
                  round(self.settings['Night_zone_current_temperature'],1), "Degrees. Night Target Temp is", self.settings['Night_zone_target_temperature'], "Degrees")

    def populate_starting_aircon_effectiveness(self):
        # Read log file
        name = '/home/pi/HomeManager/effectiveness.log'
        f = open(name, 'r')
        data_log = f.read()
        max_start, max_end = self.find_last_substring(data_log, '; Max Heat', '}') # Find last instance of Max Heat
        if max_start != 11: # Only update the dictionary if data has been logged
            dictionary_field = data_log[max_start : max_end]
            for key in self.max_heating_effectiveness:
                start_required_data, end_required_data = self.find_dictionary_data(data_log[max_start : max_end], key)
                self.max_heating_effectiveness[key] = round(float(dictionary_field[start_required_data + len(key) + 3 : end_required_data]), 1)
        max_start, max_end = self.find_last_substring(data_log, '; Max Cool', '}') # Find last instance of Max Cool
        if max_start != 11: # Only update the dictionary if data has been logged
            dictionary_field = data_log[max_start : max_end]
            for key in self.max_heating_effectiveness:
                start_required_data, end_required_data = self.find_dictionary_data(data_log[max_start : max_end], key)
                self.max_cooling_effectiveness[key] = round(float(dictionary_field[start_required_data + len(key) + 3 : end_required_data]), 1)
        max_start, max_end = self.find_last_substring(data_log, '; Min Heat', '}') # Find last instance of Min Heat
        if max_start != 11: # Only update the dictionary if data has been logged
            dictionary_field = data_log[max_start : max_end]
            for key in self.max_heating_effectiveness:
                start_required_data, end_required_data = self.find_dictionary_data(data_log[max_start : max_end], key)
                self.max_heating_effectiveness[key] = round(float(dictionary_field[start_required_data + len(key) + 3 : end_required_data]), 1)
        max_start, max_end = self.find_last_substring(data_log, '; Min Cool', '}') # Find last instance of Min Cool
        if max_start != 11: # Only update the dictionary if data has been logged
            dictionary_field = data_log[max_start : max_end]
            for key in self.max_heating_effectiveness:
                start_required_data, end_required_data = self.find_dictionary_data(data_log[max_start : max_end], key)
                self.min_cooling_effectiveness[key] = round(float(dictionary_field[start_required_data + len(key) + 3 : end_required_data]), 1)

    def populate_aircon_power_status(self):
        # Read log file
        name = '/home/pi/HomeManager/aircon_cost.log'
        f = open(name, 'r')
        data_log = f.read()
        if ':' in data_log:
            last_colon = data_log.rfind(':') # Find last colon
            start_hours_field = data_log.find(',', last_colon) + 1
            finish_hours_field = data_log.find(',', start_hours_field)
            hours = float(data_log[start_hours_field : finish_hours_field])
            print('Logged Aircon Total Hours are', hours)
            self.aircon_running_costs['total_hours'] = hours     
            start_cost_field = data_log.find(',', finish_hours_field) + 1
            finish_cost_field = data_log.find(',', start_cost_field)
            cost = float(data_log[start_cost_field : finish_cost_field])
            print('Logged Aircon Total Cost is $' + str(cost))
            self.aircon_running_costs['total_cost'] = cost
            print('Logged Aircon Running Cost per Hour is $', str(round(cost/hours, 2)))
        else:
            print('No Aircon Cost Data Logged')
            pass

    def find_last_substring(self, string, substring_start, substring_end): # Called by populate_starting_aircon_effectiveness to find the aircon effectiveness data field
        start = string.rfind(substring_start) + 12
        end = string.find(substring_end, start) + 1
        #print("last substring", string[start : end])
        return start, end

    def find_dictionary_data(self, data_field, room_string): # Called by populate_starting_aircon_effectiveness to find the individual room data within the aircon effectiveness data field
        #print('Room String', room_string)
        start_required_data = data_field.find("'" + room_string + "': ")
        first_potential_end = data_field.find(',', start_required_data)
        second_potential_end = data_field.find('}', start_required_data)
        if first_potential_end < second_potential_end:
            end_required_data = first_potential_end
        else:
            end_required_data = second_potential_end
        #print("dictionary data", room_string, data_field[start_required_data : end_required_data])
        return start_required_data, end_required_data

class Foobot:
    def __init__(self, apikey, username, password):
        ## Minor adaptation to https://github.com/philipbl/pyfoobot to use the BlueAir homehost
        ## Thanks to https://github.com/mylesagray/homebridge-blueair
        
        """Authenticate the username and password."""
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.auth_header = {'Accept': 'application/json;charset=UTF-8',
                            'X-API-KEY-TOKEN': apikey}
        self.auth_header_1 = {'X-API-KEY-TOKEN': apikey}
        self.foobot_url = 'https://api.foobot.io/'
        blue_air_authorisation = self.session.get(self.foobot_url, headers=self.auth_header_1)
        blue_air_authorisation_json = blue_air_authorisation.json()
        homehost_request_url = self.foobot_url + '/v2/user/' + self.username + '/homehost/'
        home_host = self.session.get(homehost_request_url, headers=self.auth_header_1)
        self.BASE_URL = 'https://' + home_host.json() + '/v2'
        token = self.login()
        if token is None:
            raise ValueError("Provided username or password is not valid.")
        self.auth_header['X-AUTH-TOKEN'] = token

    def login(self):
        """Log into a foobot device."""
        url = '{base}/user/{user}/login/'.format(base=self.BASE_URL,
                                                 user=self.username)
        req = self.session.get(url,
                               auth=(self.username, self.password),
                               headers=self.auth_header)
        return req.headers['X-AUTH-TOKEN'] if req.text == "true" else None

    def devices(self):
        """Get list of foobot devices owned by logged in user."""
        url = '{base}/owner/{user}/device/'.format(base=self.BASE_URL,
                                                   user=self.username)
        req = self.session.get(url, headers=self.auth_header)

        def create_device(device):
            """Helper to create a FoobotDevice based on a dictionary."""
            return FoobotDevice(auth_header=self.auth_header,
                                user_id=device['userId'],
                                uuid=device['uuid'],
                                name=device['name'],
                                mac=device['mac'], base_url=self.BASE_URL)
        return [create_device(device) for device in req.json()]

    def request_json_error_check(self, response):
        try:
            good_json = response.json()
            return(good_json)
        except requests.exceptions.RequestException as blueair_error:
            print ('BlueAir Comms Error', blueair_error)
            return('BlueAir Comms Error')

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
        req = self.session.get(url, headers=self.auth_header)
        response_json = fb.request_json_error_check(req)
        return response_json

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
        self.air_reading_bands = {'part_2_5':[9, 20, 35, 150], 'co2': [500, 1000, 1600, 2000], 'voc': [200, 350, 450, 750], 'pol': [20, 45, 60, 80]}
        self.co2_threshold = self.air_reading_bands['co2'][2]
        self.part_2_5_threshold = self.air_reading_bands['part_2_5'][2]
        self.previous_air_purifier_settings = {'Mode': 'null', 'Fan Speed': 'null', 'Child Lock':'null', 'LED Brightness': 'null', 'Filter Status':'null'}
        self.current_air_purifier_settings = {'Mode': 'null', 'Fan Speed': 'null', 'Child Lock':'null', 'LED Brightness': 'null', 'Filter Status':'null'}
        self.max_aqi = 1

    def capture_readings(self): # Capture device readings
        if self.auto == True: # Readings only come from auto units
            self.readings_update_time = time.time()
            latest_data = self.device.latest()
            if (latest_data != 'BlueAir Comms Error') and (type(latest_data['datapoints'][0]) is list) and (len(latest_data['datapoints'][0]) > 6): # Capture New readings is there's valid data, otherwise, keep previous readings
                mgr.print_update('Capturing Air Purifier Readings on ')
                self.air_readings['part_2_5'] = latest_data['datapoints'][0][1]
                self.air_readings['co2'] = latest_data['datapoints'][0][4]
                if self.air_readings['co2'] > self.max_co2:
                    self.max_co2 = self.air_readings['co2']
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
                    print('AQI is at Level', self.max_aqi, 'due to', max_reading, 'with a reading of', round(self.air_readings[max_reading],0))
                else:
                    print('AQI is at Level 1')
            else:
                mgr.print_update('Air Purifier Readings Error on ')
            return(self.readings_update_time, self.air_readings['part_2_5'], self.air_readings['co2'], self.air_readings['voc'], self.max_aqi, self.max_co2, self.co2_threshold, self.part_2_5_threshold)
        else:
            pass


    def capture_settings(self): # Capture device settings
        self.settings_update_time = time.time()
        self.settings_changed = False
        air_purifier_settings = self.get_device_settings()
        if air_purifier_settings != 'BlueAir Comms Error': # Capture new settings is there's valid data, otherwise, keep previous settings
            #print('Capturing Air Purifier Settings for', self.name)
            if self.auto == True: # Auto BlueAir units have mode and fan speed in different list locations from manual units
                if (type(air_purifier_settings) is list) and (len(air_purifier_settings) > 9):
                    self.current_air_purifier_settings['LED Brightness'] = air_purifier_settings[1]['currentValue']
                    self.current_air_purifier_settings['Child Lock'] = air_purifier_settings[2]['currentValue']
                    self.current_air_purifier_settings['Fan Speed'] = air_purifier_settings[5]['currentValue']
                    self.current_air_purifier_settings['Filter Status'] = air_purifier_settings[8]['currentValue']
                    self.current_air_purifier_settings['Mode'] = air_purifier_settings[9]['currentValue']
                    valid_data = True
                else:
                    valid_data = False
            else:
                if (type(air_purifier_settings) is list) and (len(air_purifier_settings)) > 6:
                    self.current_air_purifier_settings['LED Brightness'] = air_purifier_settings[1]['currentValue']
                    self.current_air_purifier_settings['Child Lock'] = air_purifier_settings[2]['currentValue']
                    self.current_air_purifier_settings['Fan Speed'] = air_purifier_settings[3]['currentValue']
                    self.current_air_purifier_settings['Filter Status'] = air_purifier_settings[5]['currentValue']
                    self.current_air_purifier_settings['Mode'] = air_purifier_settings[6]['currentValue']
                    valid_data = True
                else:
                    valid_data = False
            if valid_data == True:
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
            mgr.print_update('Air Purifier Settings Comms Error on ')
        return (self.settings_changed, self.settings_update_time, self.current_air_purifier_settings['Mode'],
                self.current_air_purifier_settings['Fan Speed'], self.current_air_purifier_settings['Child Lock'],
                self.current_air_purifier_settings['LED Brightness'], self.current_air_purifier_settings['Filter Status'])

    def active(self):
        if self.auto == False:
            self.set_fan_speed('1')
            
    def inactive(self):
        self.set_fan_speed('0')

    def manual_mode(self):
        if self.auto == True:
            #print('Setting Manual Mode for the', self.device.name , 'Air Purifier')
            url = self.base_url + '/device/' + self.device.uuid + '/attribute/mode/'
            header = self.device.auth_header
            uuid = self.device.uuid
            body = {"currentValue": "manual", "scope": "device", "defaultValue": "auto", "name": "mode", "uuid": uuid}
            response = self.session.post(url, headers=header, json=body)

    def auto_mode(self):
        if self.auto == True:
            #print('Setting Auto Mode for the', self.device.name , 'Air Purifier')
            url = self.base_url + '/device/' + self.device.uuid + '/attribute/mode/'
            header = self.device.auth_header
            uuid = self.device.uuid
            body = {"currentValue": "auto", "scope": "device", "defaultValue": "auto", "name": "mode", "uuid": uuid}
            response = self.session.post(url, headers=header, json=body)

    def set_fan_speed(self, fan_speed):
        #print('Setting Fan Speed to', fan_speed, 'for the', self.device.name + 'Air Purifier')
        url = self.base_url + '/device/' + self.device.uuid + '/attribute/fanspeed/'
        header = self.device.auth_header
        uuid = self.device.uuid
        body = {"currentValue": fan_speed, "scope": "device", "defaultValue": "1", "name": "fan_speed", "uuid": uuid}
        response = self.session.post(url, headers=header, json=body)

    def set_led_brightness(self, brightness):
        #print('Setting LED Brightness for the', self.device.name , 'Air Purifier')
        url = self.base_url + '/device/' + self.device.uuid + '/attribute/brightness/'
        header = self.device.auth_header
        uuid = self.device.uuid
        body = {"currentValue": brightness, "scope": "device", "defaultValue": "4", "name": "brightness", "uuid": uuid}
        response = self.session.post(url, headers=header, json=body)
        
    def set_child_lock(self, lock):
        #print('Setting Child Lock for the', self.device.name , 'Air Purifier')
        url = self.base_url + '/device/' + self.device.uuid + '/attribute/child_lock/'
        header = self.device.auth_header
        uuid = self.device.uuid
        body = {"currentValue": lock, "scope": "device", "defaultValue": "0", "name": "child_lock", "uuid": uuid}
        response = self.session.post(url, headers=header, json=body)

    def get_device_settings(self):
        url = '{base}/device/{uuid}/attributes/'
        url = url.format(base=self.base_url, uuid=self.device.uuid)
        req = self.session.get(url, headers=self.device.auth_header)
        response_json = fb.request_json_error_check(req)
        return response_json

            
if __name__ == '__main__': # This is where to overall code kicks off
    # Create a Home Manager instance
    mgr = NorthcliffHomeManagerClass()
    # Create a Homebridge instance
    homebridge = HomebridgeClass(mgr.homebridge_outgoing_mqtt_topic, mgr.outdoor_zone, mgr.outdoor_sensors_homebridge_name, mgr.aircon_config)
    # Create a Domoticz instance
    domoticz = DomoticzClass()
    # Create Doorbell instance
    doorbell = DoorbellClass(mgr.doorbell_outgoing_mqtt_topic)
    # Use a dictionary comprehension to create an aircon instance for each aircon. Allows for multiple aircons in the future
    aircon = {aircon_name: AirconClass(aircon_name, mgr.aircon_config[aircon_name], mgr.log_aircon_cost_data,
                                      mgr.log_aircon_damper_data, mgr.log_aircon_temp_data) for aircon_name in mgr.aircon_config}
    # Use a dictionary comprehension to create a window blind instance for each window blind
    window_blind = {blind_room: WindowBlindClass(blind_room, mgr.window_blind_config[blind_room]) for blind_room in mgr.window_blind_config}    
    # Use a dictionary comprehension to create a multisensor instance for each multisensor
    multisensor = {name: MultisensorClass(name, mgr.aircon_temp_sensor_names, mgr.window_blind_config,
                                          mgr.log_aircon_temp_data) for name in mgr.multisensor_names}      
    # Use a dictionary comprehension to create a door sensor instance for each door
    door_sensor = {name: DoorSensorClass(name, mgr.door_sensor_names_locations[name], mgr.window_blind_config, mgr.doorbell_door) for name in mgr.door_sensor_names_locations}      
    # Use a dictionary comprehension to create a light dimmer instance for each dimmer, with its idx number, initial switch state as False and initial brightness value 0%
    light_dimmer = {name: LightDimmerClass(name, mgr.light_dimmer_names_device_id[name], False, 0) for name in mgr.light_dimmer_names_device_id}
    # Use a dictionary comprehension to create a powerpoint instance for each powerpoint, with its idx number, initial switch state as False
    powerpoint = {name: PowerpointClass(name, mgr.powerpoint_names_device_id[name], 0) for name in mgr.powerpoint_names_device_id}
    # Use a dictionary comprehension to create a flood sensor instance for each flood sensor
    flood_sensor = {name: FloodSensorClass(name) for name in mgr.flood_sensor_names}
    # Create a Garage Door Controller instance
    garage_door = GaragedoorClass(mgr.garage_door_outgoing_mqtt_topic)
    # Create a Foobot instance
    key = "<foobot_api_key>"
    fb = Foobot(key, "<foobot_user_name>", "<foobot_user_password>")
    air_purifier_devices = fb.devices() # Capture foobot device data
    # Use a dictionary comprehension to create an air purifier instance for each air purifier
    air_purifier = {name: BlueAirClass(name, air_purifier_devices, mgr.air_purifier_names[name]) for name in mgr.air_purifier_names}
    # Create and set up an mqtt instance                             
    client = mqtt.Client('home_manager')
    client.on_connect = mgr.on_connect
    client.on_message = mgr.on_message
    client.connect("<mqtt broker name>", 1883, 60)
    # Blocking call that processes network traffic, dispatches callbacks and handles reconnecting.
    client.loop_start()
    client.subscribe(mgr.homebridge_incoming_mqtt_topic) # Subscribe to Homebridge for interworking with Apple Home
    client.subscribe(mgr.domoticz_incoming_mqtt_topic) # Subscribe to Domoticz for access to its devices
    client.subscribe(mgr.doorbell_incoming_mqtt_topic) # Subscribe to the Doorbell Monitor
    client.subscribe(mgr.garage_door_incoming_mqtt_topic) # Subscribe to the Garage Door Controller
    for aircon_name in mgr.aircon_config: # Subscribe to the Aircon Controllers
        client.subscribe(mgr.aircon_config[aircon_name]['mqtt Topics']['Incoming'])
    time.sleep(1)
    mgr.run()
