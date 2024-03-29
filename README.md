# Home Manager
This is a Raspberry Pi based Home Automation Manager. It utilises mosquitto, Homebridge, Homebridge-mqtt, Domoticz, the Apple HomeKit app and the projects contained in my other GitHub repositories to automate a Mitsubishi ducted air conditioner, a Fermax Door Intercom, z-wave lighting/power outlets/flood sensors/door sensors, Somfy window blinds, a garage door opener, BlueAir air purifiers, a Seneye aquarium sensor, environment monitors and an EV charger.

## System Overview
![System Overview](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Home%20Automation%20System%20Overview.png).

The [System Overview](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Home%20Automation%20System%20Overview.pdf) shows the four Raspberry Pi based controllers that comprise the system, the mqtt messages that allow them to communicate with each other and the end devices that they manage.  This system overview does not include the EV charger functionality. That can be found [here](https://github.com/roscoe81/ev-charger-monitor/blob/main/Documentation/Northcliff%20EV%20Charger%20Monitor%20Overview%20Gen.png). It also does not include the Fan Monitor functionality. That can be found [here](https://github.com/roscoe81/fan-monitor/blob/main/Documentation/Northcliff%20Fan%20Monitor%20Overview%20Gen.png).

## Home Manager Functional Overview
![Functional Overview](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Home%20Automation%20OOP%20Functional%20Overview.png).

The [Functional Overview](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Home%20Automation%20OOP%20Functional%20Overview.pdf) outlines the Python objects of the Home Manager controller and how they interact with Domoticz, Homebridge and the three other controllers that comprise the overall system.  This functional overview does not yet include the EV charger or Fan Monitor functionality.

## Aircon Controller
This is a [controller](https://github.com/roscoe81/Aircon-Controller) for a Mitsubishi air conditioner (Model FDC508HES3) to provide mqtt control of the airconditioner using the serial communications link that runs between Mitsubishi's RCD-H-E remote control unit and the CNB port on the air conditioner's control board. Also provides the ability to control a damper so that airflow can be directed to the correct air conditioning zone. An inclinometer is provided for the damper in order to detect its position and control the air flow between zones with greater precision. This Home Manager code captures the actual temperatures of each room, compares those temperatures to desired temperature levels and controls the air conditioner and damper to align the desired and actual temperatures. Room temperatures can be set and monitored by the Apple Home App on an iOS device or via Domoticz. Logs are captured allow the aircon's performance to be monitored, analysed and adjusted. Examples of such analysis is shown below.

### Aircon Damper Movement Log Chart Example
![Aircon Damper Movement Log Chart](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Damper_Movement.png)

### Aircon Damper Analytics Example
![Aircon Damper Analytics Screenshot](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Damper_Analytics.png)

### Aircon Cost Log Chart Example
![Aircon Cost Log Chart](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Cost.png)

### Aircon Zone Temp Changes Log Chart Example
![Aircon Zone Temp Changes Log Chart](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Zone_Temp_Changes.png)

### Aircon Heating Effectiveness Log Chart Example
![Aircon Heating Effectiveness Log Char](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Heating_Effectiveness.png)

### Aircon Controller Apple Home App Screenshot
![Aircon Home Screenshot](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Aircon_Screen.png)

## Doorbell-Monitor
This [monitor](https://github.com/roscoe81/Doorbell-Monitor/blob/master/README.md) provides doorbell automation for a Fermax 4 + N Electronic Door Entry System 
This project uses a Raspberry Pi to:
* Auto Mode: Play a recoded message when the doorbell is rung and open the door so that deliveries can be left in a secure location
* Manual Mode: Places a Video SIP call to your mobile phone when the doorbell is rung so that you can see the person at the door and converse with them
* Idle Mode: Normal door station functions take place.
In all modes, a photo of the caller is taken and stored for later reference and a pushover message is sent that contains the photo. There is also the option to only allow Auto mode during certain hours of the day and days of the week and to disable auto mode if the apartment's door is open.

In addition to the mode setting buttons and indicators, an mqtt interface is provided in the doorbell monitor to allow the Home Manager to remotely set modes and to open the door manually.

### Doorbell Monitor Packaging
![Doorbell Monitor Packaging](https://github.com/roscoe81/Doorbell-Monitor/blob/master/Schematics%20and%20Photos/IMG_3065.png)

### Doorbell Monitor Apple Home App Screenshot
![Doorbell Monitor Screenshot](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Doorbell_Screen.png)

## Garage Door Opener
This [Garage Door Opener](https://github.com/roscoe81/Garage-Door-Opener) is a simple Raspberry Pi project to open a garage door remotely using mqtt commands generated by this Home Manager when requested by the Apple Home App button. It uses an existing garage door remote.

### Garage Door Opener Packaging
![Garage Door Opener Packaging](https://github.com/roscoe81/Garage-Door-Opener/blob/master/Schematics%20and%20Photos/IMG_3204.png)

### Garage Door Opener Apple Home App Screenshot (with EV Charger Controls)
![Garage Door Opener Screenshot (with EV Charger Controls)](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Garage_Screen.png)

## Window Blind Control
Control of window blinds is enabled via a Somfy myLink Interface. Each blind can be manually adjusted via the Apple Home App to one of three positions (closed, open or venetian). Home Manager also provides the capability to:
* Link the blind control to an external light sensor and temperature sensor so that the blinds will automatically adjust to external light and temperature levels. That automatic mode can be manually over-ridden from the Apple HomeKit App.
* Link the blind control to door states so that any blinds covering doors cannot be closed if the door is open.

### Window Blind Control Apple Home App Screenshot
![Window Blind Screenshot](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Living_Screen.png)

## Z-Wave Sensor Readings and Device Control
The Home Manager interacts with Z-Wave sensors and devices via Domoticz and uses Homebridge to allow users to view and control those sensors and devices using the Apple Home App. The following screenshots provide some examples:
![Sensors and Devices](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/B776A2B2-D773-44D4-B98A-E37C2AB8AD12.jpeg)

## BlueAir Air Purifier Readings and Device Control
The Home Manager monitors and controls BlueAir air purifiers to capture air quality readings, capture settings and to control the air purifier settings through the Foobot API.

### BlueAir Air Purifier Apple Home App Screenshot
![BlueAir Screenshot](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/IMG_4349.png)

## Seneye Aquarium Sensor Readings
The Home Manager monitors a Seneye Aquarium Sensor to monitor ph, NH3 and Temperature Levels via the Seneye API. The readings are then sent via mqtt messages to be recorded and displayed in Domoticz.

## Environment Monitor Readings
The [Environment Monitor](https://github.com/roscoe81/enviro-monitor) captures, displays and reports on air particles and gases. Its readings are received via mqtt messages and are recorded/displayed in Domoticz and sent to Homebridge.

## EV Charger Monitor
The Home Manager can remotely monitor and control an EV charger by interworking with an [EV Charger Monitor](https://github.com/roscoe81/ev-charger-monitor). Requires the mqtt broker to be bridged with topic prefix of TTN.

## Fan Monitor
The Home Manager can remotely monitor a building's ventilation fan status with a [Fan Monitor](https://github.com/roscoe81/fan-monitor). Requires the mqtt broker to be bridged with topic prefix of TTN1.

### Fan Monitor Apple Home App Screenshot
![Fan Monitor Screenshot](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Plant_Room_Screen.png)

## License
This project is licensed under the MIT License - see the LICENSE.md file for details

## Acknowledgements
I'd like to acknowledge the work done by https://github.com/philipbl with https://github.com/philipbl/pyfoobot to provide the Foobot interface, which I modified slightly to access BlueAir's Foobot home host and https://github.com/mylesagray with https://github.com/mylesagray/homebridge-blueair and his work on creating a Postman Collection and Environment for BlueAir.
