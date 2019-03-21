#Northcliff Home Manager - 6.4 Gen
#!/usr/bin/env python

import paho.mqtt.client as mqtt
import struct
import time
from datetime import datetime
import string
import json
import socket

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
        # Group outdoor sensors in one homebridge "room" name that for passing to the homebridge object
        self.outdoor_sensors_homebridge_name = 'Balconies'
        # Name each door sensor and identify the room that contains that door sensor
        self.door_sensor_names_locations = {'North Living Room': 'Living Room', 'South Living Room': 'Living Room', 'Entry': 'Entry'}
        # Name each powerpoint and map to its device id
        self.powerpoint_names_device_id = {'Living': 646, 'South Balcony': 626, 'North Balcony': 647}
        # List the flood sensors
        self.flood_sensor_names = ['Kitchen', 'Laundry']
        # Name each light dimmer and map to its device id
        self.light_dimmer_names_device_id = {'Lounge': 323, 'TV': 325, 'Dining': 324, 'Study': 648, 'Kitchen': 504, 'Hallway': 328, 'North': 463,
                                              'South': 475, 'Main': 451, 'North Balcony': 517, 'South Balcony': 518}
        # Set up the config for each aircon. At present, the homebridge, domoticz and aircon classes don't have the ability to manage multiple aircons.
        # They're hard coded with 'Aircon' object label but this config dictionary allows multiple aircon to be supported in the future.
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
        # When True, flags that a change in sunlight had occurred, referencing the relevant blind and light level
        self.call_room_sunlight_control = {'State': False, 'Blind': '', 'Light Level': 100}
        # When True, flags that a blind-impacting door has been opened, referencing the relevant blind
        self.blind_control_door_opened = {'State': False, 'Blind': ''}
        # Identify the door that controls the doorbell "Auto Possible" mode
        self.doorbell_door = 'Entry'
                   
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
            homebridge.capture_homebridge_buttons(parsed_json) # Capture the homrbridge button
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

    def run(self): # The main Home Manager start-up, loop and shut-down code                          
        try:
            # Start up Aircons
            for aircon_name in mgr.aircon_config:
                aircon[aircon_name].start_up()
            doorbell.update_doorbell_status() # Get doorbell status on startup
            # Switch Auto Blind Override Homebridge buttons off
            for blind_room in self.window_blind_config:
                homebridge.reset_auto_blind_override_button(blind_room)
            # Initialise multisensor readings on homebridge to start-up settings
            for name in self.multisensor_names:    
                homebridge.update_temperature(name, multisensor[name].sensor_types_with_value['Temperature'])
                homebridge.update_humidity(name, multisensor[name].sensor_types_with_value['Humidity'])
                homebridge.update_light_level(name, multisensor[name].sensor_types_with_value['Light Level'])
                homebridge.update_motion(name, multisensor[name].sensor_types_with_value['Motion'])              
            while True: # The main Home Manager Loop
                aircon['Aircon'].control_aircon() # Call the method that controls the aircon. To do: dd support for mutliple aircons
                # The following tests and method calls are here in the main code loop, rather than the on_message method to avoid time.sleep calls in the window blind object delaying incoming mqtt message handling
                if self.call_room_sunlight_control['State'] == True: # If there's a new reading from the blind control light sensor
                    blind = self.call_room_sunlight_control['Blind'] # Identify the blind
                    light_level = self.call_room_sunlight_control['Light Level'] # Capture the light level
                    window_blind_config = self.window_blind_config[blind] # Use the config for the relevant blind
                    window_blind[blind].room_sunlight_control(light_level, window_blind_config) # Call the blind's sunlight control method, passing the light level and blind config
                    self.call_room_sunlight_control['State'] = False # Reset this flag because any light level update has now been actioned
                if self.blind_control_door_opened['State'] == True: # If a blind control door has been opened
                    blind = self.blind_control_door_opened['Blind'] # Identify the blind that is controlled by the door
                    light_level = self.call_room_sunlight_control['Light Level' ] # Capture the light level
                    window_blind_config = self.window_blind_config[blind] # Use the config for the relevant blind. That config contains the updated door states
                    window_blind[blind].room_sunlight_control(light_level, window_blind_config) # Call the blind's sunlight control method, passing the light level and blind config
                    self.blind_control_door_opened['State'] = False # Reset Door Opened Flag because any change of door state has now been actioned
                if self.call_control_blinds['State'] == True: # If a manual blind change has been invoked
                    blind = self.call_control_blinds['Blind'] # Identify the blind that has been changed
                    window_blind_config = self.window_blind_config[blind] # Use the config for the relevant blind
                    window_blind[blind].control_blinds(self.call_control_blinds, window_blind_config) # Call the blind's manual control method, passing the blind config
                    self.call_control_blinds['State'] = False # Reset Control Blinds Flag because any control blind request has now been actioned
        except KeyboardInterrupt:
            # Shut down Aircons
            for aircon_name in mgr.aircon_config:
                aircon[aircon_name].shut_down()
            client.loop_stop() # Stop mqtt monitoring
            self.print_update('Home Manager Shut Down at ')


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
        self.dimmer_characteristics = {'Adjust Light Brightness': 'Brightness', 'Switch Light State': 'On'}
        self.dimmer_state_map = {0: False, 1: True}
        self.blinds_format = {'name': ' Blinds'}
        self.blind_position_map = {100: 'Open', 50: 'Venetian', 0: 'Closed'}
        self.doorbell_format = {'name': 'Doorbell', 'characteristic': 'On'}
        # Set up homebridge switch types for doorbell (Indicator, Switch or TimedMomentary)
        self.doorbell_button_type = {'Terminated': 'Indicator', 'AutoPossible': 'Indicator', 'Triggered': 'Indicator',
                                     'OpenDoor': 'Momentary', 'Activated': 'Indicator', 'Automatic': 'Switch', 'Manual': 'Switch', 'Ringing': 'Motion'}
        self.powerpoint_format = {'name': 'Powerpoint', 'service': 'Outlet', 'service_name': ''}
        self.garage_door_format = {'name': 'Garage', 'service_name': 'OpenGarage'}
        self.garage_door_characteristics = {'Current': 'CurrentDoorState','Target': 'TargetDoorState'}
        self.flood_state_format = {'name': 'Flood', 'service': 'LeakSensor'}
        self.flood_state_characteristic = 'LeakDetected'
        self.flood_battery_characteristic = 'StatusLowBattery'
        self.auto_blind_override_button_format = {'service_name': 'Auto Blind Override', 'characteristic': 'On'}
        self.aircon_thermostat_format = {'name': 'Aircon', 'service': 'Thermostat'} # To do. Add ability to manage multiple aircons
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
                                    'Damper': 'Position Indicator', 'Clean Filter': 'Indicator', 'Malfunction': 'Indicator'}
        for name in self.aircon_thermostat_names:
            self.aircon_button_type[name] = 'Thermostat Control' # To do. Add ability to manage multiple aircons
        self.window_blind_position_map = {'Open': 100, 'Venetian': 50, 'Closed': 0}

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
            # Call the adjust_brightness method for the relevant dimmer object
            light_dimmer[dimmer_name].adjust_brightness(brightness)
        # Adjust dimmer state if a switch light state command has come from homebridge
        elif parsed_json['characteristic'] == self.dimmer_characteristics['Switch Light State']:
            light_state = parsed_json['value']
            light_dimmer[dimmer_name].on_off(light_state)  # Call the on_off method for the relevant dimmer object
        else:
            # Print an error message if the homebridge dimmer message has an unknown characteristic
            print('Unknown dimmer characteristic received from ' + dimmer_service_name + ': ' + parsed_json['characteristic'])
            pass

    def process_blind_button(self, parsed_json):
        #print('Homebridge: Process Blind Button', parsed_json)
        blind_name = parsed_json['name'] # Capture the blind's name
        # Set blind override status if it's a auto blind control override switch
        if parsed_json['service_name'] == 'Auto Blind Override':
            auto_override = parsed_json['value']
            window_blind[blind_name].change_auto_override(auto_override)
        else:
            blind_id = parsed_json['service_name']
            # Convert blind position from a value to a string: 100 Open, 0 Closed, 50 Venetian
            blind_position = self.blind_position_map[parsed_json['value']]
            window_blind[blind_name].change_blind_position(blind_id, blind_position)

    def process_doorbell_button(self, parsed_json):
        #print('Homebridge: Process Doorbell Button', parsed_json)
        # Ignore the button press if it's only an indicator and reset to its pre-pressed state
        if self.doorbell_button_type[parsed_json['service_name']] == 'Indicator':
            time.sleep(0.5)
            homebridge_json = self.doorbell_format
            homebridge_json['service_name'] = parsed_json['service_name']
            homebridge_json['value'] = doorbell.status[parsed_json['service_name']]
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))       
        # Send the doorbell button message to the doorbell if the button is a switch
        elif self.doorbell_button_type[parsed_json['service_name']] == 'Switch':
            doorbell.process_button(parsed_json['service_name'])
        # Send the doorbell button message to the doorbell and reset to the off position if the button is a momentary switch
        elif self.doorbell_button_type[parsed_json['service_name']] == 'Momentary':
            doorbell.process_button(parsed_json['service_name'])
            time.sleep(1)
            homebridge_json = self.doorbell_format
            homebridge_json['service_name'] = parsed_json['service_name']
            homebridge_json['value'] = False # Prepare to return switch state to off
            # Publish homebridge payload with pre-pressed switch state
            client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))
        elif self.doorbell_button_type[parsed_json['service_name']] == 'Motion':
            pass
        else:
            print('Unrecognised Doorbell Button Type')
            pass    

    def process_garage_door_button(self, parsed_json):
        print('Homebridge: Process Garage Door Button', parsed_json)
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
        else:
            print("Unknown Aircon Homebridge Message", str(parsed_json))
            time.sleep(0.1)

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
        print('Homebridge: Update Garage Door', state)
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
            client.publish('homebridge/to/set', '{"name":"Garage","service_name":"OpenGarage","characteristic":"CurrentDoorState","value":1}') # Send Current Garage Door Closed Message to Homebridge
        else:
            print("Invalid Garage Door Status Message", service)
               
    def reset_auto_blind_override_button(self, blind_room):
        #print('Homebridge: Reset Auto Blind Override Button', blind_room)
        homebridge_json = self.auto_blind_override_button_format
        homebridge_json['name'] = blind_room
        homebridge_json['value'] = False
        homebridge_payload = json.dumps(homebridge_json)
        # Publish homebridge payload with button state off
        client.publish(self.outgoing_mqtt_topic, json.dumps(homebridge_json))

    def reset_aircon_thermostats(self, thermostat_status): # Called on start-up to set all Homebridge sensors to "off", current temps to 1 degree and target temps to 21 degrees
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
        # Map dimmer switch functions to translate True to On-switch/100-brightness and
        # False to Off-switch/0-brightness for domoticz_json
        self.dimmer_switch_map = {True:['On', 100], False:['Off', 0]}
        # Set up powerpoint domoticz message formats
        self.powerpoint_format = {'command': 'switchlight'}
        # Map powerpoint switch functions to translate True to On and False to Off for domoticz_json
        self.powerpoint_map = {True: 'On', False:'Off'}

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
        client.publish(self.outgoing_mqtt_topic, json.dumps(domoticz_json))

    def set_dimmer_state(self, idx, dimmer_state):
        # Publishes a dimmer state mqtt message to Domoticz when called by a light dimmer object
        domoticz_json = self.dimmer_switch_format
        domoticz_json['idx'] = idx
        domoticz_json['switchcmd'] = self.dimmer_switch_map[dimmer_state][0]
        domoticz_json['level'] = self.dimmer_switch_map[dimmer_state][1]
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
                mgr.blind_control_door_opened = {'State': self.current_door_opened, 'Blind': blind_name}
                #print('Blind Control Door Opened', mgr.blind_control_door_opened)
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
            if self.name in self.window_blind_config[blind]['light sensor']:
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
                print ('Triggered Blind Light Sensor', mgr.call_room_sunlight_control)            
        
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

    def adjust_brightness(self, brightness): # The method to adjust dimmer brightness
        if self.brightness != brightness: # If the dimmer brightness has changed
            self.brightness = brightness
            domoticz.set_dimmer_brightness(self.idx, self.brightness)
        
    def on_off(self, dimmer_state): # The method to turn dimmer on or off
        self.dimmer_state = dimmer_state
        domoticz.set_dimmer_state(self.idx, dimmer_state)

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
        
    def open_garage_door(self, parsed_json):
        garage_json = {}
        garage_json['service'] = parsed_json['service_name']
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
        # mgr.print_update('Doorbell Status update on ')
        for status_item in self.status: # For each status item in the doorbell status
            self.status[status_item] = parsed_json[status_item] # Update doorbell status
            homebridge.update_doorbell_status(parsed_json, status_item) # Send update to homebridge
        # print(self.status)
        
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
        self.previous_high_sunlight = 0
        self.current_high_sunlight = 0
        self.previous_blind_temp_threshold = False
        self.call_control_blinds = False
        self.door_blind_override = False
        self.last_pre2_sunlight_state = 0
        self.auto_override = False
        self.auto_override_changed = False
        # Set up door states dictionary
        self.door_state = {}
                                                              
    def change_auto_override(self, auto_override):
        #mgr.print_update('Auto Blind Override button pressed on ')
        #print ('Auto Blind Override Change Flag before button pressed was', self.auto_override_changed,
               #'Auto Blind Override State =',self.auto_override)
        self.auto_override = auto_override
        self.auto_override_changed = True
        #print ('Auto Blind Override Change Flag after button pressed is', self.auto_override_changed,
               #'Auto Blind Override State =', self.auto_override)

    def change_blind_position(self, blind_id, blind_position):
        # Set flag that triggers a blind change in the main homemanager loop and pass 
        mgr.call_control_blinds = {'State': True, 'Blind': self.blind, 'Blind_id': blind_id,
                                   'Blind_position': blind_position}

    def control_blinds(self, blind_controls, window_blind_config):
        mgr.print_update('Invoked Manual Blind Control on ')
        self.window_blind_config = window_blind_config
        blind_id = blind_controls['Blind_id']
        blind_position = blind_controls['Blind_position']
        ignore_blind_command = False
        # Check if at least one door is open
        door_open = False
        for door in self.window_blind_config['blind_doors']:
            if self.window_blind_config['blind_doors'][door]['door_state'] == 'Open':
                door_open = True
        if blind_position == 'Open':
            print('Opening Blinds')
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                blind_json = self.window_blind_config['blind commands']['up ' + blind_id]
                s.connect((self.blind_ip_address, self.blind_port))
                s.sendall(blind_json)
                data = s.recv(1024)
        elif blind_position == 'Closed':
            print('Closing Blinds')
            # If both doors are closed and it's a blind command that closes one or more door blinds
            if (door_open == False and (blind_id == 'Left Door' or blind_id == 'Right Door' or blind_id == 'All Doors' or blind_id == 'All Blinds')):
                # If blind is open, close first and wait until it closes
                if self.window_blind_config['status'][blind_id] == 'Open':
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        blind_json = self.window_blind_config['blind commands']['down ' + blind_id]
                        s.connect((self.blind_ip_address, self.blind_port))
                        s.sendall(blind_json)
                        data = s.recv(1024)
                    # Check door state while closing and reverse if a door opens
                    self.check_door_state_while_closing(self.window_blind_config, 25)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    blind_json = self.window_blind_config['blind commands']['up '+ blind_id]
                    #print(blind_json)
                    s.connect((self.blind_ip_address, self.blind_port))
                    s.sendall(blind_json)
                    data = s.recv(1024)
                time.sleep(0.495)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    blind_json = self.window_blind_config['blind commands']['stop '+ blind_id]
                    #print(blind_json)
                    s.connect((self.blind_ip_address, self.blind_port))
                    s.sendall(blind_json)
                    data = s.recv(1024)
            elif blind_id == 'Left Window' or blind_id == 'Right Window' or blind_id == 'All Windows': # If it's a window command
                if self.window_blind_config['status'][blind_id] == 'Open': # If Open, close first and wait until it closes
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        blind_json = self.window_blind_config['blind commands']['down ' + blind_id]
                        s.connect((self.blind_ip_address, self.blind_port))
                        s.sendall(blind_json)
                        data = s.recv(1024)
                    time.sleep(25) # Normal close 
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    blind_json = self.window_blind_config['blind commands']['up '+ blind_id]
                    #print(blind_json)
                    s.connect((self.blind_ip_address, self.blind_port))
                    s.sendall(blind_json)
                    data = s.recv(1024)
                time.sleep(0.495)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    blind_json = self.window_blind_config['blind commands']['stop '+ blind_id]
                    #print(blind_json)
                    s.connect((self.blind_ip_address, self.blind_port))
                    s.sendall(blind_json)
                    data = s.recv(1024)         
             # If one door is open and it's a command that impacts the doors
            elif (door_open == True and (blind_id == 'Left Door' or blind_id == 'Right Door' or blind_id == 'All Doors' or blind_id == 'All Blinds')):
                self.door_blind_override = True # Flag that lowering of door blinds has been overridden
                if blind_id == 'All Blinds':
                    #blind_id = 'All Windows' # Change All Blinds to All Windows
                    if self.window_blind_config['status'][blind_id] == 'Open': # If Open, close first and wait until it closes
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            blind_json = self.window_blind_config['blind commands']['down ' + 'All Windows']
                            s.connect((self.blind_ip_address, self.blind_port))
                            s.sendall(blind_json)
                            data = s.recv(1024)
                        time.sleep(25)
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        blind_json = self.window_blind_config['blind commands']['up '+ 'All Windows']
                        #print(blind_json)
                        s.connect((self.blind_ip_address, self.blind_port))
                        s.sendall(blind_json)
                        data = s.recv(1024)
                    time.sleep(0.495)
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        blind_json = self.window_blind_config['blind commands']['stop '+ 'All Windows']
                        #print(blind_json)
                        s.connect((self.blind_ip_address, self.blind_port))
                        s.sendall(blind_json)
                        data = s.recv(1024)
                    self.window_blind_config['status'][blind_id] = 'Closed'
                else: # Don't do anything if it's a Door Command
                    ignore_blind_command = True
                    homebridge.update_blind_status(self.blind, self.window_blind_config)
            else:
                pass
        elif blind_position == 'Venetian':
            # If both doors are closed and it's a blind command that closes one or more door blinds
            if (door_open == False and (blind_id == 'Left Door' or blind_id == 'Right Door' or blind_id == 'All Doors' or blind_id == 'All Blinds')):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    blind_json = self.window_blind_config['blind commands']['down '+ blind_id]
                    #print(blind_json)
                    s.connect((self.blind_ip_address, self.blind_port))
                    s.sendall(blind_json)
                    data = s.recv(1024)
                # Check door state while closing and reverse if a door opens
                self.check_door_state_while_closing(self.window_blind_config, 25)
            elif blind_id == 'Left Window' or blind_id == 'Right Window' or blind_id == 'All Windows': # If it's a window command
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    blind_json = self.window_blind_config['blind commands']['down ' + blind_id]
                    s.connect((self.blind_ip_address, self.blind_port))
                    s.sendall(blind_json)
                    data = s.recv(1024)# Normal close
            # If one door is open and it's a command that impacts the doors
            elif (door_open == False and (blind_id == 'Left Door' or blind_id == 'Right Door' or blind_id == 'All Doors' or blind_id == 'All Blinds')):
                self.door_blind_override = True # Flag that lowering of door blinds has been overridden
                if blind_id == 'All Blinds':
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        blind_json = self.window_blind_config['blind commands']['down '+ 'All Windows']
                        #print(blind_json)
                        s.connect((self.blind_ip_address, self.blind_port))
                        s.sendall(blind_json)
                        data = s.recv(1024)
                    self.window_blind_config['status'][blind_id] = 'Venetian'
                else: # Don't do anything if it's a Door Command
                    ignore_blind_command = True
                    homebridge.update_blind_status(self.blind, self.window_blind_config)
        else: # Ignore any other setting
            ignore_blind_command = True
            homebridge.update_blind_status(self.blind, self.window_blind_config)
        if ignore_blind_command == False:
            self.window_blind_config['status'][blind_id] = blind_position
            if blind_id == 'All Blinds' and self.door_blind_override == False:
                self.window_blind_config['status']['Left Window'] = blind_position
                self.window_blind_config['status']['Left Door'] = blind_position
                self.window_blind_config['status']['Right Door'] = blind_position
                self.window_blind_config['status']['Right Window'] = blind_position
                self.window_blind_config['status']['All Doors'] = blind_position
                self.window_blind_config['status']['All Windows'] = blind_position
            elif blind_id == 'All Blinds' and self.door_blind_override == True:
                self.window_blind_config['status']['All Blinds'] = 'Open'
                self.window_blind_config['status']['All Doors'] = 'Open'
                self.window_blind_config['status']['Left Door'] = 'Open'
                self.window_blind_config['status']['Right Door'] = 'Open'
                self.window_blind_config['status']['Left Window'] = blind_position
                self.window_blind_config['status']['Right Window'] = blind_position
                self.window_blind_config['status']['All Windows'] = blind_position         
            elif blind_id == 'All Windows':
                self.window_blind_config['status']['Left Window'] = blind_position
                self.window_blind_config['status']['Right Window'] = blind_position
            elif blind_id == 'All Doors' and self.door_blind_override == False:
                self.window_blind_config['status']['Left Door'] = blind_position
                self.window_blind_config['status']['Right Door'] = blind_position
            elif blind_id == 'All Doors' and self.door_blind_override == True:
                self.window_blind_config['status']['All Blinds'] = 'Open'
                self.window_blind_config['status']['All Doors'] = 'Open'
                self.window_blind_config['status']['Left Door'] = 'Open'
                self.window_blind_config['status']['Right Door'] = 'Open'
            else:
                pass
            if self.door_blind_override == True:
                print('Changed blind command because a door is open')
            self.door_blind_override = False
            homebridge.update_blind_status(self.blind, self.window_blind_config)
        else:
            print('Ignored door blind command because a door is open')

    def room_sunlight_control(self, light_level, window_blind_config):
        # Called when the blind's light sensor is updated or there's a change in the state the blind's doors
        self.window_blind_config = window_blind_config
        # Capture the blind's temeprature sensor reading
        current_temperature = multisensor[window_blind_config['temp sensor']].sensor_types_with_value['Temperature']
        #print(current_temperature)
        # Only invoke room sunlight control if a valid temperature reading has been received from the sensor
        # (1 degree is the default set at initialisation) and indicates that a valid temp reading hasn't been received
        if current_temperature != 1:
            mgr.print_update('Blind Control invoked on ')
            # Check to determine whether a change in the outside temperature requires a potential blind change
            # If the temp was previously within the blind temp thresholds
            if self.previous_blind_temp_threshold == False:
                if (current_temperature > self.window_blind_config['high_temp_threshold']
                    or current_temperature < self.window_blind_config['low_temp_threshold']):
                    # Set that it's jumped the thresholds if the outside temperature has moved outside the blind temp thresholds.
                    # Used later to determine if a blind change is required
                    temp_passed_threshold = True
                    # Set that the outside temperature is now outside the thresholds.
                    # Used later to determine if a blind change is required
                    current_blind_temp_threshold = True
                else: # Temp is still inside the blind temp thresholds
                    # Set that it hasn't jumped the thresholds.
                    # Used later to determine if a blind change is required
                    temp_passed_threshold = False
                    # Set that the outside temperature is now inside the thresholds.
                    # Used later to determine if a blind change is required
                    current_blind_temp_threshold = False
            else: # If the temp was previously outside the blind temp threshold.
                # Provide +-1 degrees of hysteresis to avoid blind flapping 
                # If it's moved inside the blind temp thresholds
                if (current_temperature < (self.window_blind_config['high_temp_threshold'] - 1)
                    and current_temperature > (self.window_blind_config['low_temp_threshold'] + 1)):
                    # Set that it's jumped the thresholds.
                    # Used later to determine if a blind change is required
                    temp_passed_threshold = True
                    # Set that the outside temperature is now inside the thresholds.
                    # Used later to determine if a blind change is required
                    current_blind_temp_threshold = False
                else:
                    # Set that it hasn't jumped the thresholds.
                    # Used later to determine if a blind change is required
                    temp_passed_threshold = False
                    # Set that the outside temperature is now outside the thresholds.
                    # Used later to determine if a blind change is required
                    current_blind_temp_threshold = True
            print('Outside Temperatures checked')
            print('Current temperature is', current_temperature, 'degrees.', 'Previously Outside Temp Thresholds?',
                  self.previous_blind_temp_threshold, 'Currently Outside Temp Thresholds?', current_blind_temp_threshold,
                  'Temp Moved Inside or Outside Thresholds?', temp_passed_threshold)
            # Record the whether the current outside temperature is outside thresholds
            # for the next time room_sunlight_control is called
            self.previous_blind_temp_threshold = current_blind_temp_threshold
            # Check to determine whether a change in door states requires a potential blind change
            # Set the door_state_change flag to false in preparation for the door state change check
            door_state_changed = False
            # Check if there's been a change in door state and flag in door_state_changed
            for door in self.window_blind_config['blind_doors']:
                if self.window_blind_config['blind_doors'][door]['door_state_changed'] == True: # Check each relevant door
                    door_state_changed = True
            # Are any doors open?
            door_open = False
            for door in self.window_blind_config['blind_doors']:
                if self.window_blind_config['blind_doors'][door]['door_state'] == 'Open':
                    door_open = True
            print('Door State checked')
            print ('Door State Changed?', door_state_changed, 'Doors Now Open?', door_open)
            # Check the sunlight level against pre-set thresholds
            if light_level >= self.window_blind_config['sunlight threshold 3']: # If it's strong direct sunlight
                self.current_high_sunlight = 4
            elif (light_level >= self.window_blind_config['sunlight threshold 2'] and
                  light_level < self.window_blind_config['sunlight threshold 3']): # If it's medium direct sunlight
                self.current_high_sunlight = 3
            elif (light_level >= self.window_blind_config['sunlight threshold 1']
                  and light_level < self.window_blind_config['sunlight threshold 2']): # If it's strong indirect sunlight
                self.current_high_sunlight = 2
            elif (light_level < self.window_blind_config['sunlight threshold 1'] and
                  light_level > self.window_blind_config['sunlight threshold 0']): #If it's medium indirect sunlight
                self.current_high_sunlight = 1 # If it's low indirect sunlight
            else:
                self.current_high_sunlight = 0 # If it's night time
            print('High Sunlight Levels checked')
            print ('New Sensor Light Level Reading', light_level, 'Lux', 'Previous High Sunlight Level:',
                   self.previous_high_sunlight, 'Current High Sunlight Level:', self.current_high_sunlight,
                   'Daylight?', light_level > self.window_blind_config['sunlight threshold 0'])
            # Invoke a blind change check if the sunlight has moved between sunlight levels or
            # there's a change in door state or the outside temperature has move in or out of the pre-set thresholds
            # or there's a change in the blind auto override state
            if (self.current_high_sunlight != self.previous_high_sunlight or door_state_changed == True or
                temp_passed_threshold == True or self.auto_override_changed == True):
                mgr.print_update ('Blind change algorithm triggered on ')
                #print ('Auto Blind Override Change =', self.auto_override_changed, 'Auto Blind Override State =', self.auto_override)
                # Don't print blind state change. It will be set to true if the algorithm determines that a blind change is necessary
                print_blind_change = False
                # Run the algorithm for each sunlight level
                if self.current_high_sunlight == 4: # If it's strong direct sunlight
                    print('High Sunlight Level 4 Invoked')
                    self.last_pre2_sunlight_state = 4 # Used to determine what sunlight state was invoked before entering sunlight level 2
                    if self.auto_override == False: # Only change blinds if not overriden
                        if door_open == False: # Set right blind to 50%, close doors and left blind if both doors closed
                            if self.previous_high_sunlight != 4: # If it's not already in state 4, move all blinds to correct position
                                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # Lower all blinds
                                    s.connect((self.blind_ip_address, self.blind_port))
                                    s.sendall(self.window_blind_config['blind commands']['down All Blinds'])
                                    data = s.recv(1024)
                                # Check door state while closing the blinds, so closure can be reversed if a door is opened during blind closure
                                self.check_door_state_while_closing(self.window_blind_config, 25)
                                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # Raise left window blind for 0.5 seconds
                                    s.connect((self.blind_ip_address, self.blind_port))
                                    s.sendall(self.window_blind_config['blind commands']['up Left Window'])
                                    data = s.recv(1024)
                                time.sleep(0.495)
                                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # Stop left window blind
                                    s.connect((self.blind_ip_address, self.blind_port))
                                    s.sendall(self.window_blind_config['blind commands']['stop Left Window'])
                                    data = s.recv(1024)
                            else: # If it's already in state 4, the window blinds don't need to be moved
                                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # Lower door blinds
                                    s.connect((self.blind_ip_address, self.blind_port))
                                    s.sendall(self.window_blind_config['blind commands']['down All Doors'])
                                    data = s.recv(1024)
                                # Check door state while closing the blinds, so closure can be reversed if a door is opened during blind closure
                                self.check_door_state_while_closing(self.window_blind_config, 25)
                            # Set blind status. 50 is venetian, 0 is closed
                            print_blind_change = True
                            self.window_blind_config['status']['Left Window'] = 'Closed'
                            self.window_blind_config['status']['All Doors'] = 'Closed'
                            self.window_blind_config['status']['Left Door'] = 'Closed'
                            self.window_blind_config['status']['Right Door'] = 'Closed'
                            self.window_blind_config['status']['Right Window'] = 'Venetian'
                            self.window_blind_config['status']['All Blinds'] = 'Open'
                            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # Raise door blinds for 0.5 seconds
                                s.connect((self.blind_ip_address, self.blind_port))
                                s.sendall(self.window_blind_config['blind commands']['up All Doors'])
                                data = s.recv(1024)
                            time.sleep(0.495)
                            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # Stop door blinds
                                s.connect((self.blind_ip_address, self.blind_port))
                                s.sendall(self.window_blind_config['blind commands']['stop All Doors'])
                                data = s.recv(1024)
                                print_blind_change = True
                        # If at least one door is open, open the door blinds and if the previous blind state was not 4,
                        # set right window to venetian mode and completely close the left window
                        else:
                            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # Raise door blinds 
                                s.connect((self.blind_ip_address, self.blind_port))
                                s.sendall(self.window_blind_config['blind commands']['up All Doors'])
                                data = s.recv(1024)                     
                            if self.previous_high_sunlight != 4:
                                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # Lower window blinds
                                    s.connect((self.blind_ip_address, self.blind_port))
                                    s.sendall(self.window_blind_config['blind commands']['down All Windows'])
                                    data = s.recv(1024)
                                time.sleep(25)
                                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # Raise left window blind for 0.5 seconds
                                    s.connect((self.blind_ip_address, self.blind_port))
                                    s.sendall(self.window_blind_config['blind commands']['up Left Window'])
                                    data = s.recv(1024)
                                time.sleep(0.495)
                                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # Stop left window blind
                                    s.connect((self.blind_ip_address, self.blind_port))
                                    s.sendall(self.window_blind_config['blind commands']['stop Left Window'])
                                    data = s.recv(1024)
                            print_blind_change = True
                            # Set blind status to align with blind position
                            self.window_blind_config['status']['Left Window'] = 'Closed'
                            self.window_blind_config['status']['Right Window'] = 'Venetian'
                            self.window_blind_config['status']['All Doors'] = 'Open'
                            self.window_blind_config['status']['Left Door'] = 'Open'
                            self.window_blind_config['status']['Right Door'] = 'Open'
                            self.window_blind_config['status']['All Blinds'] = 'Open'
                elif self.current_high_sunlight == 3: # If it's medium direct sunlight
                    print('High Sunlight Level 3 Invoked')
                    self.last_pre2_sunlight_state = 3  # Used to determine what sunlight state was invoked before entering sunlight level 2
                    if self.auto_override == False: # Only change blinds if not overriden
                        # If the immediately previous sunlight level was 0, 1 or 2, put all blinds to 50% if the doors are closed
                        # or all windows to 50% if the doors are open. Do nothing if the immediately previous sunlight level was
                        # 3 or 4 to avoid blind flapping (i.e. add hysteresis)
                        if self.previous_high_sunlight < 3:
                            if door_open == False: # If both doors closed, all blinds to 50%
                                print_blind_change, self.window_blind_config['status'] = self.all_blinds_venetian(self.window_blind_config)
                            else: # Open door blinds and set window blinds to 50% if at least one door is open
                                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                                    s.connect((self.blind_ip_address, self.blind_port))
                                    s.sendall(self.window_blind_config['blind commands']['up All Doors']) # Raise door blinds
                                    data = s.recv(1024)
                                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                                    s.connect((self.blind_ip_address, self.blind_port))
                                    s.sendall(self.window_blind_config['blind commands']['down All Windows'])  # Lower window blinds
                                    data = s.recv(1024)
                                print_blind_change = True
                                # Set blind status
                                self.window_blind_config['status']['All Windows'] = 'Venetian'
                                self.window_blind_config['status']['Left Window'] = 'Venetian'
                                self.window_blind_config['status']['Right Window'] = 'Venetian'
                                self.window_blind_config['status']['All Doors'] = 'Open'
                                self.window_blind_config['status']['Left Door'] = 'Open'
                                self.window_blind_config['status']['Right Door'] = 'Open'
                                self.window_blind_config['status']['All Blinds'] = 'Open'
                        elif door_state_changed == True: # Check if there's been a change in door state
                            if door_open == False: # Move door blinds to venetian state
                                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                                    s.connect((self.blind_ip_address, self.blind_port))
                                    s.sendall(self.window_blind_config['blind commands']['down All Doors'])  # Lower door blinds
                                    data = s.recv(1024)
                                print_blind_change = True
                                # Set blind status
                                self.window_blind_config['status']['All Windows'] = 'Venetian'
                                self.window_blind_config['status']['Left Window'] = 'Venetian'
                                self.window_blind_config['status']['Right Window'] = 'Venetian'
                                self.window_blind_config['status']['All Doors'] = 'Venetian'
                                self.window_blind_config['status']['Left Door'] = 'Venetian'
                                self.window_blind_config['status']['Right Door'] = 'Venetian'
                                self.window_blind_config['status']['All Blinds'] = 'Venetian'
                                self.check_door_state_while_closing(self.window_blind_config, 25) # This method ensures that the door state is checked while closing the blinds, so closure can be reversed if a door is opened during that closure
                            else: # Open door blinds if the doors have been opened 
                                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                                    s.connect((self.blind_ip_address, self.blind_port))
                                    s.sendall(self.window_blind_config['blind commands']['up All Doors']) # Raise door blinds
                                    data = s.recv(1024)
                                print_blind_change = True
                                # Set blind status
                                self.window_blind_config['status']['All Doors'] = 'Open'
                                self.window_blind_config['status']['Left Door'] = 'Open'
                                self.window_blind_config['status']['Right Door'] = 'Open'
                                self.window_blind_config['status']['All Blinds'] = 'Open'
                        else:# Do nothing if the immediately previous Sunlight level was 3 or 4, or there was no change in door state
                            print_blind_change = False # Don't print a change of blind position
                elif self.current_high_sunlight == 2: # This is the hysteresis gap between open and closed to avoid excessive blind changes as the sunlight moves below sunlight level 3
                    # Moves blinds to 50% closed if sunlight level 2 was invoked after previously being in sunlight levels 3 or 4 and the doors are closed. 
                    # Opens door blinds and moves window blinds to 50% if sunlight level 2 was invoked after previously being in sunlight levels 3 or 4 and the doors are open.
                    # Moves blinds to 50% if the outside temp is beyond the pre-set limits after level 2 was invoked after previously being in sunlight levels 0, 1 or 2 and the doors are closed
                    # Opens all blinds if level 2 if the outside temp is within the pre-set limits and level 2 was invoked after previously being in sunlight levels 0 or 1
                    print('High Sunlight Level 2 Invoked')
                    print('Last Pre 2 High Sunlight Level:', self.last_pre2_sunlight_state, 'Previous High Sunlight Level:', self.previous_high_sunlight)
                    if self.auto_override == False: # Only change blinds if not overriden
                        if self.previous_high_sunlight > 2: # If the previous sunlight level was either 3 or 4
                            if door_open == False: # If both doors closed, all blinds to venetian state
                                print_blind_change, self.window_blind_config['status'] = self.all_blinds_venetian(self.window_blind_config)
                            else: # Open door blinds and set window blinds to venetian state if at least one door is open
                                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                                    s.connect((self.blind_ip_address, self.blind_port))
                                    s.sendall(self.window_blind_config['blind commands']['up All Doors']) # Raise door blinds
                                    data = s.recv(1024)
                                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                                    s.connect((self.blind_ip_address, self.blind_port))
                                    s.sendall(self.window_blind_config['blind commands']['down All Windows'])  # Lower window blinds
                                    data = s.recv(1024)
                                print_blind_change = True
                                # Set blind status
                                self.window_blind_config['status']['All Windows'] = 'Venetian'
                                self.window_blind_config['status']['Left Window'] = 'Venetian'
                                self.window_blind_config['status']['Right Window'] = 'Venetian'
                                self.window_blind_config['status']['All Doors'] = 'Open'
                                self.window_blind_config['status']['Left Door'] = 'Open'
                                self.window_blind_config['status']['Right Door'] = 'Open'
                                self.window_blind_config['status']['All Blinds'] = 'Open'
                        else: # If the previous high sunlight level was 0, 1 or 2
                            if current_blind_temp_threshold == True: # If the outside temperature is outside the pre-set thresholds
                                if door_open == False: # All blinds to venetian state if the outside temps are outside the pre-set thresholds and the doors are closed.
                                    print('All blinds set to venetian state because the outdoor temperature is now outside the pre-set thresholds with doors closed')
                                    print('Pre-set upper temperature threshold is', self.window_blind_config['high_temp_threshold'], 'degrees', 'Pre-set lower temperature limit is', self.window_blind_config['low_temp_threshold'], 'degrees',
                                          'Current temperature is', current_temperature, 'degrees')
                                    print_blind_change, self.window_blind_config['status'] = self.all_blinds_venetian(self.window_blind_config)
                                else: # Do nothing if the doors are open
                                    print_blind_change = False # Don't print a change of blind position
                            else: # If the outside temperature is now within the pre-set thresholds
                                if self.last_pre2_sunlight_state <= 1: # Open all blinds if the outside temperature is now within the pre-set thresholds and the algorithm has entered state 2 from states 0 or 1
                                    print('All blinds opening because the last sunlight state before reaching level 2 was 0 or 1 and the outdoor temperature is now 1 degree inside the pre-set thresholds')
                                    print('Pre-set upper temperature threshold is', self.window_blind_config['high_temp_threshold'], 'degrees', 'pre-set lower temperature threshold is', self.window_blind_config['low_temp_threshold'], 'degrees',
                                          'Current temperature is', current_temperature, 'degrees')
                                    print_blind_change, self.window_blind_config['status'] = self.raise_all_blinds(self.window_blind_config)
                                else: # No blind change if temp is within limits and the algorithm has entered state 2 from states 3 or 4
                                    print_blind_change = False  # Don't print a change of blind position
                elif self.current_high_sunlight == 1: # If sunlight level is lower than threshold 1 but still daylight
                    print('High Sunlight Level 1 Invoked')
                    self.last_pre2_sunlight_state = 1 # Identifies what sunlight state was invoked before entering sunlight level 2.
                    # Used to determine if the blinds are opened (when it's set to 0 or 1) or closed (when it's 3 or 4) in sunlight level 2
                    # Unlike self.previous_high_sunlight, this never be set to sunlight level 2
                    if self.auto_override == False: # Only change blinds if not overriden
                        if current_blind_temp_threshold == True and door_open == False: # Lower all blinds if the outside temperature is outside the pre-set thresholds and the doors are closed.
                            print('All blinds set to Venetian because the outdoor temperature is outside the pre-set thresholds with the doors closed')
                            print('Pre-set upper temperature threshold is', self.window_blind_config['high_temp_threshold'], 'Pre-set lower temperature threshold is', self.window_blind_config['low_temp_threshold'],
                                   'Current temperature is', current_temperature, 'degrees')
                            print_blind_change, self.window_blind_config['status'] = self.all_blinds_venetian(self.window_blind_config)
                        else: # Raise all blinds if the outside temperature is well within the pre-set thresholds or the doors are opened.
                            if current_blind_temp_threshold == True and door_open == True:
                                print('Opening all blinds due to doors being opened, even though the outdoor temperature is outside the pre-set thresholds')       
                            elif current_blind_temp_threshold == False and door_open == False:
                                print("Opening all blinds because the outdoor temperature is within the pre-set thresholds")
                            else: # If current_blind_temp_threshold == False and door_open == True:
                                print("Opening all blinds due to doors being opened and the outdoor temperature is within the pre-set thresholds")
                            print('Pre-set upper temperature threshold is', self.window_blind_config['high_temp_threshold'], 'Pre-set lower temperature threshold is', self.window_blind_config['low_temp_threshold'],
                                   'Current temperature is', current_temperature, 'degrees')
                            print_blind_change, self.window_blind_config['status'] = self.raise_all_blinds(self.window_blind_config)             
                elif self.current_high_sunlight == 0: # If it's night time
                    print('High Sunlight Level 0 Invoked')
                    self.last_pre2_sunlight_state = 0 # Used to determine what sunlight state was invoked before entering sunlight level 2.
                    # Used to determine if the blinds are opened (when it's set to 0 or 1) or closed (when it's 2 or 3)
                    # Unlike self.previous_high_sunlight, this never be set to sunlight level 2
                    # Make no change in this blind state because it's night time unless a door is opened (caters for case where blinds remain
                    # closed due to temperatures being outside thresholds when moving from level 1 to level 0 or the blinds have been manually closed while in level 0).
                    # The use of this level is to open the blinds in the morning when level 1 is reached and the outside temperature is within the pre-set levels
                    if self.auto_override == False: # Only change blinds if not overriden
                        if door_open == True: # Raise door blinds if a door is opened.Caters for the case where blinds are still set to 50% after
                            # sunlight moves from level 1 to level 0 because the temp is outside thresholds
                            print('Opening all blinds due to a door being opened')
                            print_blind_change, self.window_blind_config['status'] = self.raise_all_blinds(self.window_blind_config)       
                else:
                    pass # Invalid sunlight level              
                if print_blind_change == True: # If there's a change in blind position
                    print('Blind Change Summary')
                    if self.current_high_sunlight != self.previous_high_sunlight: # If there's a blind position change due to sun protection state
                        #print_update("Change in Balcony Sun Protection Mode on ")
                        print("High Sunlight Level was:", self.previous_high_sunlight, "It's Now Level:", self.current_high_sunlight, "with a light reading of", light_level, "Lux")
                    if door_state_changed == True: # If a change in door states, print blind update due to door state change
                        if door_open == False:
                            print('Blinds were adjusted due to door closure')
                        else:
                            print('Blinds were adjusted due to door opening')
                    if temp_passed_threshold == True:
                        if current_blind_temp_threshold == False:
                            print('Blinds adjusted due to the external temperature moving outside the defined range')
                        else:
                            print('Blinds adjusted due to an external temperature moving inside the defined range')
                    if self.auto_override_changed == True:
                        if self.auto_override == False:
                           print('Blinds adjusted due to auto_override being switched off')   
                else: # No blind change, just a threshold change in the blind hysteresis gaps
                    #print("High Sunlight Level Now", self.current_high_sunlight, "with a light reading of", light_level, "Lux and no change of blind position")
                    pass
                self.previous_high_sunlight = self.current_high_sunlight # Update sunlight threshold status with the latest reading
                self.auto_override_changed = False # Reset auto blind override flag 
                homebridge.update_blind_status(self.blind, self.window_blind_config) # Update blind status 
            else: # Nothing changed that affects blind states
                #print('Blind Status Unchanged')
                pass
            for door in self.window_blind_config['blind_doors']: # Reset all door state change flags
                self.window_blind_config['blind_doors'][door]['door_state_changed'] = False
        
    def raise_all_blinds(self, window_blind_config):
        self.window_blind_config = window_blind_config
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.blind_ip_address, self.blind_port))
            s.sendall(self.window_blind_config['blind commands']['up All Blinds']) # Raise all blinds
            data = s.recv(1024)
        # Set blind status
        self.window_blind_config['status']['All Windows'] = 'Open'
        self.window_blind_config['status']['Left Window'] = 'Open'
        self.window_blind_config['status']['Right Window'] = 'Open'
        self.window_blind_config['status']['All Doors'] = 'Open'
        self.window_blind_config['status']['Left Door'] = 'Open'
        self.window_blind_config['status']['Right Door'] = 'Open'
        self.window_blind_config['status']['All Blinds'] = 'Open'
        return True, self.window_blind_config['status']

    def all_blinds_venetian(self, window_blind_config):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.blind_ip_address, self.blind_port))
            s.sendall(self.window_blind_config['blind commands']['down All Blinds']) # Lower all blinds
            data = s.recv(1024)
        # Set blind status
        self.window_blind_config['status']['All Windows'] = 'Venetian'
        self.window_blind_config['status']['Left Window'] = 'Venetian'
        self.window_blind_config['status']['Right Window'] = 'Venetian'
        self.window_blind_config['status']['All Doors'] = 'Venetian'
        self.window_blind_config['status']['Left Door'] = 'Venetian'
        self.window_blind_config['status']['Right Door'] = 'Venetian'
        self.window_blind_config['status']['All Blinds'] = 'Venetian'
        # This method ensures that the door state is checked while closing the blinds,
        # so closure can be reversed if a door is opened during that closure
        self.check_door_state_while_closing(self.window_blind_config, 25)
        return True, self.window_blind_config['status']
                  
    def check_door_state_while_closing(self, window_blind_config, delay):
        self.window_blind_config = window_blind_config
        loop = True
        count = 0
        door_opened = False
        already_opened = False
        while count < delay:
            # Check if there's been a change in door state and flag in door_state_changed
            for door in self.window_blind_config['blind_doors']:
                # If the door state changed and it's now open
                if self.window_blind_config['blind_doors'][door]['door_state_changed'] == True and self.window_blind_config['blind_doors'][door]['door_state'] == 'Open':
                    door_opened = True
            if door_opened == True:
                if already_opened == False:
                    mgr.print_update(door + ' opened while blind is closing. Door blinds now opening on ')
                    already_opened = True
                    self.door_blind_override = True
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.connect((self.blind_ip_address, self.blind_port))
                        s.sendall(self.window_blind_config['blind commands']['up All Doors']) # Open Door blinds
                        data = s.recv(1024)
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
        self.mqtt_commands = {'Update Status': 'Update Status', 'Off': 'Off', 'Indoor Heat': 'Thermostat Heat', 'Indoor Cool': 'Thermostat Cool', 'Indoor Auto': 'Thermostat Auto',
                                                     'Heat Mode': 'Heat Mode', 'Cool Mode': 'Cool Mode', 'Fan Mode': 'Fan Mode', 'Fan Hi': 'Fan Hi', 'Fan Med': 'Fan Med',
                                                     'Fan Lo': 'Fan Lo', 'Damper Percent': 'Damper Percent'}
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
        
        self.settings = {'Thermo Heat': False, 'Thermo Cool': False, 'Thermo Off': True, 'indoor_thermo_mode': 'Cool', 'Day_zone_target_temperature': 21,
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
        self.thermostat_status = {name: {'Current Temperature': 1, 'Target Temperature': 21, 'Mode': 'Off', 'Active': 0} for name in self.thermostat_names}
        self.thermostat_mode_active_map = {'Off': 0, 'Heat': 1, 'Cool': 1}
        self.start_time = time.time()
        self.temperature_update_time = {name: self.start_time for name in self.indoor_zone}
        self.log_damper_data = log_damper_data

        # Set up Aircon Power Consumption Dictionary
        self.aircon_power_consumption = {'Heat': 4.97, 'Cool': 5.42, 'Idle': 0.13, 'Off': 0}
        self.aircon_weekday_power_rates = {0:{'name': 'off_peak1', 'rate': 0.1155, 'stop_hour': 6}, 7:{'name':'shoulder1', 'rate': 0.1771, 'stop_hour': 13},
                              14:{'name':'peak', 'rate':0.4218, 'stop_hour': 19}, 20: {'name': 'shoulder2', 'rate': 0.1771, 'stop_hour': 21},
                              22:{'name': 'off_peak2', 'rate': 0.1155, 'stop_hour': 23}}
        self.aircon_weekend_power_rates = {0:{'name': 'off_peak1', 'rate': 0.1155, 'stop_hour': 6}, 7:{'name':'shoulder', 'rate': 0.1771, 'stop_hour': 21},
                              22:{'name': 'off_peak2', 'rate': 0.1155, 'stop_hour': 23}}
        self.aircon_running_costs = {'total_cost':0, 'total_hours': 0}
        self.log_aircon_cost_data = log_aircon_cost_data

    def start_up(self):
        # Reset Homebridge Thermostats on start-up
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
        # Reset Homebridge Thermostats on shut-down
        self.thermostat_status = {name: {'Current Temperature': 1, 'Target Temperature': 21, 'Mode': 'Off', 'Active': 0} for name in self.thermostat_names}
        homebridge.reset_aircon_thermostats(self.thermostat_status)
        # Reset Domoticz Thermostats on shut-down
        domoticz.reset_aircon_thermostats(self.thermostat_status)

    def set_thermostat(self, thermostat_name, control, setting): 
        if thermostat_name == self.control_thermostat:
            if control == 'Mode':
                if setting == 'Off':
                    #print (str(parsed_json))
                    self.settings['Thermo Heat'] = False
                    self.settings['Thermo Cool'] = False
                    self.settings['Thermo Off'] = True
                    self.thermostat_status[thermostat_name]['Mode'] = setting
                    self.thermostat_status[thermostat_name]['Active'] = self.thermostat_mode_active_map[setting]
                    client.publish(self.outgoing_mqtt_topic, '{"service": "Off"}')
                    #domoticz.set_aircon_mode('Off') # Mirror state on domoticz. Deleted due to control loop.
                if setting == 'Heat':
                    #print (str(parsed_json))
                    if self.settings['Indoor_zone_sensor_active'] == 1: #Only do something if at least one sensor is active
                        self.settings['Thermo Heat'] = True
                        self.settings['Thermo Cool'] = False
                        self.settings['Thermo Off'] = False
                        self.settings['indoor_thermo_mode'] = 'Heat'
                        self.thermostat_status[thermostat_name]['Mode'] = setting
                        self.thermostat_status[thermostat_name]['Active'] = self.thermostat_mode_active_map[setting]
                        client.publish(self.outgoing_mqtt_topic, '{"service": "Thermostat Heat"}')
                        #domoticz.set_aircon_mode('Heat') # Mirror state on domoticz. Deleted due to control loop.
                    else:
                        print('Trying to start aircon without any sensor active. Command ignored')
                        client.publish('homebridge/to/set', '{"name":"Aircon","service_name":"Indoor","service":"Thermostat", "characteristic":"TargetHeatingCoolingState","value":0}')
                if setting == 'Cool': 
                    #print (str(parsed_json))
                    if self.settings['Indoor_zone_sensor_active'] == 1: #Only do something if at least one sensor is active
                        self.settings['Thermo Heat'] = False
                        self.settings['Thermo Cool'] = True
                        self.settings['Thermo Off'] = False
                        self.settings['indoor_thermo_mode'] = 'Cool'
                        self.thermostat_status[thermostat_name]['Mode'] = setting
                        self.thermostat_status[thermostat_name]['Active'] = self.thermostat_mode_active_map[setting]
                        client.publish(self.outgoing_mqtt_topic, '{"service": "Thermostat Cool"}')
                        #domoticz.set_aircon_mode('Cool') # Mirror state on domoticz. Deleted due to control loop.
                    else:
                        print('Trying to start aircon without any sensor active. Command ignored')
                        client.publish('homebridge/to/set', '{"name":"Aircon","service_name":"Indoor","service":"Thermostat", "characteristic":"TargetHeatingCoolingState","value":0}')
            self.update_zone_temps() # Update the "Day", "Night" and "Indoor" Zones current temperatures with active temperature sensor readings and the "Indoor" Target Temperature is updated with the target temperatures of the active sensor settings
            indoor_control_mode = self.thermostat_status[self.control_thermostat]['Mode']
            self.update_active_thermostats(indoor_control_mode)  # Ensure that active sensors have the same mode setting as the Indoor Control
            #print(str(self.settings))
        else:
            if control == 'Target Temperature':
                self.thermostat_status[thermostat_name]['Target Temperature'] = setting
                #domoticz.set_aircon_thermostat_target_temp(thermostat_name, setting) # Mirror target temp on domoticz. Deleted due to control loop.
                #mgr.print_update('Updating ' + thermostat_name + ' Target Temperature to ' + str(setting) + " Degrees, Actual Temperature = " + str(self.thermostat_status[thermostat_name]['Current Temperature']) + " Degrees on ")
            if control == 'Mode':
                self.thermostat_status[thermostat_name]['Mode'] = setting
                self.thermostat_status[thermostat_name]['Active'] = self.thermostat_mode_active_map[setting]
                #domoticz.change_aircon_sensor_enable(thermostat_name, setting) # Mirror state on domoticz. Deleted due to control loop.
            self.update_zone_temps() # Update the "Day", "Night" and "Indoor" Zones current temperatures with active temperature sensor readings
            indoor_control_mode = self.thermostat_status[self.control_thermostat]['Mode']
            self.update_active_thermostats(indoor_control_mode) # Ensure that active sensors have the same mode setting as the Indoor Control


    def send_aircon_command(self, command): # Send command to aircon controller
        aircon_command = {}
        aircon_command['service'] = self.mqtt_commands[command]
        client.publish(self.outgoing_mqtt_topic, json.dumps(aircon_command))

    def capture_status(self, parsed_json):
        if parsed_json['service'] == 'Heartbeat':
            #mgr.print_update('Received Heartbeat from Aircon and sending Ack on ')
            client.publish(self.outgoing_mqtt_topic, '{"service": "Heartbeat Ack"}')
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
                #if find_key != None: # Only capture temperature history for known indoor names
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
    # NEEDS REFACTORING
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
    
    def update_active_thermostats(self, mode): # Called by 'set_thermosat' method to ensure that active sensors have the same mode setting as the Indoor Control
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
    #REFACTORED
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
                #print("Thermo On Mode")
                if self.settings['Indoor_zone_sensor_active'] == 1: # Only invoke aircon control if at least one aircon temp sensor is active
                    #print("Indoor Active")
                    # Prepare data for power consumption logging
                    update_date_time = datetime.now()
                    current_power_rate = self.check_power_rate(update_date_time)
                    if self.status['Cool'] == True:
                        mode = 'Cool'
                    elif self.status['Heat'] == True:
                        mode = 'Heat'
                    elif self.status['Fan'] == True:
                        mode = 'Idle'
                    else:
                        mode = 'Off'
                    #print('aircon_previous_power_rate =', self.settings['aircon_previous_power_rate'], 'aircon_current_power_rate =', current_power_rate)
                    if current_power_rate != self.settings['aircon_previous_power_rate']: # If the power rate has changed
                        mgr.print_update("Power Rate Changed from $" + str(self.settings['aircon_previous_power_rate']) + " per kWH to $" + str(current_power_rate) + " per kWH on ")
                        self.update_aircon_power_log(mode, current_power_rate, time.time(), self.log_aircon_cost_data)  # Update aircon power log if there's a change of power rate
                    if mode != self.settings['aircon_previous_mode']: # If the airon mode has changed
                        self.update_aircon_power_log(mode, current_power_rate, time.time(), self.log_aircon_cost_data)  # Update aircon power log if there's a change of mode
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
            else: # Update the aircon power log when put into Thermo Off Mode
                if self.settings['aircon_previous_mode'] != 'Off':
                    mode = 'Off'
                    update_date_time = datetime.now()
                    current_power_rate = self.check_power_rate(update_date_time)
                    self.update_aircon_power_log(mode, current_power_rate, time.time(), self.log_aircon_cost_data)

    def set_aircon_mode(self, mode): # Called by 'control_aircon' to set aircon mode
        if mode == 'Heat':
            if self.status['Heat'] == False: # Only set to heat mode if it's not already been done
                mgr.print_update("Heat Mode Selected on ")
                print("Day Temp is", self.settings['Day_zone_current_temperature'], "Degrees. Day Target Temp is", self.settings['Day_zone_target_temperature'], "Degrees. Night Temp is",
                                          self.settings['Night_zone_current_temperature'], "Degrees. Night Target Temp is", self.settings['Night_zone_target_temperature'], "Degrees") 
                client.publish(self.outgoing_mqtt_topic, '{"service": "Heat Mode"}')
                self.status['Heat'] = True
            if self.status['Fan Hi'] == False: # Only set to Fan to Hi if it's not already been done
                client.publish(self.outgoing_mqtt_topic, '{"service": "Fan Hi"}')
                self.status['Fan Hi'] = True
        if mode == 'Cool':
            if self.status['Cool'] == False: # Only set to cool mode if it's not already been done
                mgr.print_update("Cool Mode Selected on ")
                print("Day Temp is", self.settings['Day_zone_current_temperature'], "Degrees. Day Target Temp is", self.settings['Day_zone_target_temperature'], "Degrees. Night Temp is",
                                          self.settings['Night_zone_current_temperature'], "Degrees. Night Target Temp is", self.settings['Night_zone_target_temperature'], "Degrees") 
                client.publish(self.outgoing_mqtt_topic, '{"service": "Cool Mode"}')
                self.status['Cool'] = True
            if self.status['Fan Hi'] == False: # Only set to Fan to Hi if it's not already been done
                client.publish(self.outgoing_mqtt_topic, '{"service": "Fan Hi"}')
                self.status['Fan Hi'] = True
        if mode == 'Idle':
            if self.status['Fan'] == False: # Only set to Fan Mode if it's not already been done
                mgr.print_update("Idle Mode Selected on ")
                print("Day Temp is", self.settings['Day_zone_current_temperature'], "Degrees. Day Target Temp is", self.settings['Day_zone_target_temperature'], "Degrees. Night Temp is",
                                          self.settings['Night_zone_current_temperature'], "Degrees. Night Target Temp is", self.settings['Night_zone_target_temperature'], "Degrees") 
                client.publish(self.outgoing_mqtt_topic, '{"service": "Fan Mode"}')
                self.status['Fan'] = True
            if self.status['Fan Lo'] == False: # Only set Fan to Lo if it's not already been done
                client.publish(self.outgoing_mqtt_topic, '{"service": "Fan Lo"}')
                self.status['Fan Lo'] = True

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

    #def reset_active_temp_dictionaries(): #Reset Active Temperature Dictionary and change rate when the relevant aircon status is updated, in order to get stable active temp history readings
        #for key in active_temperature_history:
            #active_temperature_history[key] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        #for key in self.active_temperature_change_rate:
            #self.active_temperature_change_rate[key] = 0

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
            #optimal_day_zone_not_passed = 60 * day_proportion / (0.6 * day_proportion + 0.4 * night_proportion) # Damper is biased towards Day Zone
            #optimal_day_zone_passed = 60 * night_proportion / (0.6 * night_proportion + 0.4 * day_proportion) # Damper is biased towards Day Zone
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
        # NEEDS REFACTORING.
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
        #time.sleep(5)
        #print("Max Heating Log:", self.max_heating_effectiveness)
        #print("Max Cooling Log:", self.max_cooling_effectiveness)
        #print("Min Heating Log:", self.max_heating_effectiveness)
        #print("Min Cooling Log:", self.min_cooling_effectiveness)

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
    powerpoint = {name: PowerpointClass(name, mgr.powerpoint_names_device_id[name], False) for name in mgr.powerpoint_names_device_id}
    # Use a dictionary comprehension to create a flood sensor instance for each flood sensor
    flood_sensor = {name: FloodSensorClass(name) for name in mgr.flood_sensor_names}
    # Create a Garage Door Controller instance
    garage_door = GaragedoorClass(mgr.garage_door_outgoing_mqtt_topic)   
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