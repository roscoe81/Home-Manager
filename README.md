# Home Manager
This is a Raspberry Pi based Home Automation Manager. Utilises mosquitto, Homebridge, Homebridge-mqtt, Domoticz and the projects contained in my other GitHub repositories to automate airconditioning, doorbell, lighting, power outlets, flood sensors, door sensors, window blinds and a garage door opener.

## System Overview
![System Overview](https://github.com/roscoe81/Home-Manager/blob/roscoe81-function/Documentation/55D92C2D-CF98-4A29-BD3A-A8FD7610C9C5.jpeg
The [System Overview](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Home%20Automation%20Overview.pdf) shows the four Raspberry Pi based controllers that comprise the system, the mqtt messages that allow them to communicate with each other and the end devices that they manage.

## Home Manager Functional Overview
![Functional Overview](Documentation/179B4F81-E7F5-43CF-9A22-A9158B1CA6D5.jpeg)
The [Functional Overview](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Home%20Automation%20OOP%20Functional%20Overview.pdf) outlines the Python objects of the Home Manager controller and how they interact with Domoticz, Homebridge and the three other controllers that comprise the overall system.



License
This project is licensed under the MIT License - see the LICENSE.md file for details
