# Home Manager
This is a Raspberry Pi based Home Automation Manager. Utilises mosquitto, Homebridge, Homebridge-mqtt, Domoticz and the projects contained in my other GitHub repositories to automate airconditioning, doorbell, lighting, power outlets, flood sensors, door sensors, window blinds and a garage door opener.

## System Overview
![System Overview](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/55D92C2D-CF98-4A29-BD3A-A8FD7610C9C5.jpeg)
The [System Overview](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Home%20Automation%20Overview.pdf) shows the four Raspberry Pi based controllers that comprise the system, the mqtt messages that allow them to communicate with each other and the end devices that they manage.

## Home Manager Functional Overview
![Functional Overview](Documentation/179B4F81-E7F5-43CF-9A22-A9158B1CA6D5.jpeg)
The [Functional Overview](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Home%20Automation%20OOP%20Functional%20Overview.pdf) outlines the Python objects of the Home Manager controller and how they interact with Domoticz, Homebridge and the three other controllers that comprise the overall system.

## Aircon Controller
This is a [controller](https://github.com/roscoe81/Aircon-Controller) for a Mitsubishi air conditioner (Model FDC508HES3) to provide mqtt control of the airconditioner using the serial communications link that runs between Mitsubishi's RCD-H-E remote control unit and the CNB port on the air conditioner's control board. Also provides the ability to control a damper so that airflow can be directed to the correct air conditioning zone. An inclinometer is provided for the damper in order to detect its position and control the air flow between zones with greater precision. This Home Manager code captures the actual temperatures of each room, compares those temperatures to desired temperature levels and controls the air conditioner and damper to align the desired and actual temperatures. Room temperatures can be set and monitored by the Apple Home App on an iOS device or via Domoticz.

### Aircon Controller Apple Home App Screenshot
![Aircon Home Screenshot](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/76F68873-22C9-4C22-BA85-81DC36B0BF0A.png)


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
![Doorbell Monitor Screenshot](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/DF74AC2F-36ED-4782-8AA6-039EA844923C.jpeg)


## License
This project is licensed under the MIT License - see the LICENSE.md file for details
