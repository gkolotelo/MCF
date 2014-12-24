#!/usr/bin/python2
"""
Sensor Reader Script


Attributes:
    sensors: List to hold the sensor objects.
    count: Variable to hold number of entries sent to DB.

"""


import sys
import os
import select
from serialsensor import *

if (os.getuid() != 0):
    print "Must be run as superuser"
    sys.exit(0)

sensors = []
#Initialization



#Find and match serial ports:
print "\nListing available serial ports..."
available_ports = listPorts()
if len(available_ports) == 0:
    print "Error: No ports found."
    sys.exit(0)



print '\nAvailable serial ports:'
for i in available_ports:
    print "({})".format(available_ports.index(i)), i

#Input example:
print "Several sensors can be entered, just enter the asked information (4 per sensor) for each sensor. When done, just press enter"

while True:
    number = raw_input("Type a port number:")
    if (number == ''):
        print "Continuing..."
        break
    sensors.append(SerialSensor("", "", available_ports[int(number)][0], 0, 9600))#initialize sensors

while True:
    print "Type sensor number, and press enter to enter commands to that sensor. When done press ctrl-c to be done with that sensor"
    print "press enter to exit"
    print "\nAvailable sensors:"
    for i in sensors: 
        print "({})".format(sensors.index(i)), i.getName(), '@', i.getPort(), "units:", i.getUnits()
    try:
        sensor = raw_input("Enter asensor number: ")
        if sensor == "":sys.exit(0)
        while True:
            while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                line = sys.stdin.readline()
                if line:
                    sensors[int(sensor)].send(line)
            try:
                print sensors[int(sensor)].readRaw()
            except SerialError, e:
                if e.errno != 3:
                    raise

    except KeyboardInterrupt:
        pass





                

        


