SerialSensor 0.7
================

About
-----

The SerialSensor module is designed to facilitate the use of sensors that use serial communication.

SerialSensor is compatible with sensors that output numeric values, or numeric comma separated values (CSV), through a serial to USB converter. The values must end with a CR or CRLF line break.

Currently, SerialSensor is only compatible with Linux/Unix.

SerialSensor can output JSON, numerical value lists and strings of the read values.

Requirements
------------

You will first need to install the following packages:
    python 2.7 or above
    
    At least one of the supported libraries (libusb 1.0, libusb 0.1 or OpenUSB)
    
    PyUSB 1.0

Installation
------------

Just copy serialsensor.py to the same folder as the script being executed.




