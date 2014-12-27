SerialSensor 1.1
================

About
-----

The SerialSensor module is designed to facilitate the use of sensors that use serial communication.

SerialSensor is compatible with sensors that output numeric values, or numeric comma separated values (CSV), through a USB to Serial converter.

Currently, SerialSensor is only compatible with Linux/Unix based systems.

SerialSensor can represent the acquired data though JSON, numerical value lists or strings.

Requirements
------------

You will need the following packages:

python 2.7 or above
    
[pySerial](http://pyserial.sourceforge.net/)
    	

Installation
------------

Just have serialsensor.py in the same folder as the script being executed.




rpi_service 1.1
================

About
-----

rpi_service is a script developed to retrieve data from serial sensors and storing it on MongoDB databases. This script uses the SerialSensor Library.

The current version of 'rpi_service' supports web management and headless deployment using the tools provided in this repository.

Requirements
------------

The following packages are required:

SerialSensor 1.1

[PyMongo](http://api.mongodb.org/python/current/index.html)

web management:

[Flask](http://flask.pocoo.org/)

[PyMongo](http://api.mongodb.org/python/current/index.html)

Installation
------------

rpi_service.py, serialsensor.py and config.json(base config file) must be present in the same folder, and the web management server must be running for intialization.

By cloning this repository you may just execute:
	
	python rpi_service.py
	python web_management/server.py

Notes:
You must add DB server and authentication information to both server.py, for the web management interface, and config.json, for the 'rpi_service' script to properly connect to the database.

Demo for Raspberry Pi
---------------------

A demo kit is provided to be used on data collection boards.

The demo has been tested for the following configuration:
	
Raspberry Pi Model B

Arch Linux kernel 3.12.34 (provided)

Requirements
------------

Linux computer for image configuration.

MongoDB database set up.

Raspberry Pi board with internet connectivity

Included
--------

Included on the Demo kit are:

Documentation
'rpi_service' script and supporting files
Web management script and supporting files

Installation
------------

Download prebuild Arch Linux 3.12.34:
[ArchLinux_3.12.34](https://drive.google.com/file/d/0Bzu5DJ7GsPj5WG1rY1U2VHl6czA/view)
(The image does not contain the scripts, which will be added by the image utility, the image does, however, contain all supporting libraries needed.)

Use the provided image utility to copy and configure the image for deployment:

	utilities/image_utility.py

After board has been set up, and is powered up and connected to the internet you may initialize it's settings using the web management interface.

More details provided on "docs/Water Board Deployment Guide"





