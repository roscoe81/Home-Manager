# Home Manager
This is a Raspberry Pi based Home Automation Manager. Utilises mosquitto, Homebridge, Homebridge-mqtt, Domoticz and the projects contained in my other GitHub repositories to automate airconditioning, doorbell, lighting, power outlets, flood sensors, door sensors, window blinds and a garage door opener.

## System Overview
This overview shows the four Raspeberry Pi based controllers that comprise the system, the mqtt messages that allow them to communicate with each other and the end devices that they manage.

![alt text](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Home%20Automation%20Overview.pdf)

## Home Manager Functional Overview
This functional overview outlines the Python objects of the Home Manager controller and how they interact with Domoticz, Homebridge and the three other controllers that comprise the overall system.

![alt text](https://github.com/roscoe81/Home-Manager/blob/master/Documentation/Home%20Automation%20OOP%20Functional%20Overview.pdf)

License
This project is licensed under the MIT License - see the LICENSE.md file for details
