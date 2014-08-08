#!/usr/bin/python2
"""
Sensor Reader Script


Attributes:
    sensors: List to hold the sensor objects.
    count: Variable to hold number of entries sent to DB.

"""

import datetime
import socket
import json
import sys
import time
import urllib2
import subprocess
import pymongo
import logging
import os
from Serial_Sensor import *

if (os.getuid() != 0):
    print "Must be run as superuser"
    sys.exit(0)

sensors = []
count = 0
base_path = '/root/RPi/'
log_path  = base_path + 'log.log'
config_path = base_path + 'config.json'
#config_path = '/Users/gkolotelo/Documents/Programming/University/MIT/CityFARM/RPi/config.json'

#Initialization

#Get settings from config file, if nonexistent, create one
#Available settings:
#settings["settings"]["board_name", "db_name", "server", "sensor_reading_frequency"]
#settings["sensor"]["baud_rate", "wait_time", "name", "units", "port_number", "port", "path"]
try:
    open(config_path)
    if(raw_input("Config file already present, continuing will delete it. Press enter to continue.") != ""): sys.exit(0) 
except IOError, e:
    pass

fp = open(config_path, 'w+')
settings = json.load(fp)
settings["settings"]["server"] = raw_input("Enter server address or (http://cityfarm.media.mit.edu): ")
settings["settings"]["username"] = raw_input("Enter db username: ")
settings["settings"]["password"] = raw_input("Enter db password: ")
#fetch dbs and board names:
#Connect to Mongo Server:
try :
    client = pymongo.MongoClient(settings["settings"]["server"])
    client.admin.authenticate(settings["settings"]["username"],settings["settings"]["password"])
    db_list = client.database_names()
    print "Available databases:"
    for i in db_list:
        if db_list.index(i) < (len(db_list)-1): print(" ├── " + str(i))
        else: print (" └── " + str(i)) 
except pymongo.errors.ConnectionFailure:
    print 'Could not connect to Mongo at: "' + settings["settings"]["server"] + '" with username "' + settings["settings"]["username"] + '"'
    print "Server address or authentication may be wrong, if not, you can continue."

settings["settings"]["db_name"] = raw_input("Enter database name (you can enter one from the list above, or enter a new one): ")
#db_list = client.admin.boards.find()
#for i in db_list:
#    if db_list.index(i) < (len(db_list)-1): print("    ├── " + str(i))
#    else: print ("    └── " + str(i)) 
settings["settings"]["board_name"] = raw_input("Enter board name: ")

settings["settings"]["sensor_reading_frequency"] = raw_input("Enter sensor reading frequency (seconds): ")
settings["sensor"] = {}
fp.write(json.dumps(settings, indent=4))
fp.close()
print "Saved! Now register the sensors."

#Find serial ports:
print "\nListing available serial ports..."
available_ports = listPorts()
if len(available_ports) == 0:
    print "Error: No ports found."
    sys.exit(0)
ports = []
syspaths = []
for i in available_ports:
    ports.append(i[0])#get only ttyUSBX values
    arg = 'udevadm info -q path -n ' + i[0]
    arg = subprocess.check_output(arg, shell=True)
    arg = '/sys' + arg[0:arg.index('tty')]
    syspaths.append(arg)#get sysfs bus info

print '\nAvailable serial ports:'
for i in ports:
    print "({})".format(ports.index(i)), i

#Input example:
print "Several sensors can be entered, just enter the asked information (4 per sensor) for each sensor. When done, just press enter"
print "More than one measurement can be made by each sensor, just enter comma separated names for measurements and units (without spaces)"
print "Example: \n", "0 \nMeas_1,Meas_2", "\nmg/L,PPM", "\n1000", "\n[Enter]\n"

while True:
    number = raw_input("Type a port number:")
    if (number == ''):
        print "Continuing..."
        break
    name = raw_input("Type the sensor's measurement name:")
    units = raw_input("Type the sensor's units:")
    wait = raw_input("Type the maximum time this sensor takes to return a measurement (in milliseconds):")
    sensors.append(SerialSensor(name, units, available_ports[int(number)][0], int(wait)))#initialize sensors
#Store settings in file
settings["sensors"] = []
for i in sensors:
    try:
        settings["sensors"].append(i.getJSONSettings('path', syspaths[ports.index(i.getPort())]))#Sysfs bus info added to JSON string
    except SerialError, e:
        print e.args, e.sensor, e.port
        raise
try:
    fp = open(config_path, 'w+')
    fp.write(json.dumps(settings, indent=4))
    fp.close()
    print "Saved"
except IOError:
    print "Cannot open settings file."
    raise


#Display sensors
print "\nAvailable sensors:"
logger.info("Available sensors:")
for i in sensors: 
    print i.getName(), '@', i.getPort(), "units:", i.getUnits(), "waiting time:", i.getWaitTime()
    logger.info((i.getName(), '@', i.getPort(), "units:", i.getUnits(), "waiting time:", i.getWaitTime()))
print "Data points to date: ", collection.count()
logger.info(("Data points to date: " + str(collection.count())))
print "\nReading Started:\n\n"
logger.info("Reading Started")


                

        


