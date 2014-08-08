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
    logger.error("Must be run as superuser!")
    sys.exit(0)

sensors = []
count = 0
base_path = '/root/RPi/'
log_path  = base_path + 'log.log'
config_path = base_path + 'config.json'
#config_path = '/Users/gkolotelo/Documents/Programming/University/MIT/CityFARM/RPi/config.json'
reading_frequency = 0

#if (sys.argv != []): base_path = sys.argv[0]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler(log_path)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.info("\n\n\nStarted excecution:\n")

#Returns UNIX Epoch timestamp.
def now():
    return(datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds()

#Logs unhandled exceptions
def unhandled_exception_logger(type, value, traceback):
    logger.error("Uncaught unhandled exception")
    logger.error(type)
    logger.error(value)
    logger.error(traceback)
    sys.exit()

sys.excepthook = unhandled_exception_logger #Override sys.excepthook

#Initialization

#Waits for internet connection.
try:
    urllib2.urlopen('http://www.google.com', timeout=5)
    logger.info("Internet connection estabilished")
except urllib2.URLError:
    t = time.time()
    try:
        while (time.time() - t) < 30:
            try:
                urllib2.urlopen('http://www.google.com', timeout=5)
                break
            except urllib2.URLError:
                time.sleep(1)
    finally:
        del t 


#Get settings from config file
#Available settings:
#settings["settings"]["board_name", "db_name", "server", "sensor_reading_frequency"]
#settings["sensor"]["baud_rate", "wait_time", "name", "units", "port_number", "port", "path"]
try:
    settings = json.load(open(config_path))
    logger.info("Config file found")
except IOError, e:
    logger.error("Config file not found")
    raise

reading_frequency = float(settings["settings"]["sensor_reading_frequency"])

printout = "Using default settings:\n\n" + \
"Board Name: " + settings["settings"]["board_name"] + \
"\nMongo Server: " + settings["settings"]["server"] + \
"\nDB name: " + settings["settings"]["db_name"] + \
'\nFrequency (seconds): ' + str(settings["settings"]["sensor_reading_frequency"]) + \
"\nIP Address: " + socket.gethostbyname(socket.gethostname()) + \
"\nHostname: " + socket.gethostname() + "\n" 
logger.info(printout)
del printout

#Connect to Mongo Server:
try :
    client = pymongo.MongoClient(settings["settings"]["server"])
    client.admin.authenticate("admin","cityfarm")
    db = client[settings["settings"]["db_name"]]
    collection = db[settings["settings"]["board_name"]]
    logger.info(("Connected to " + collection.full_name))
except pymongo.errors.ConnectionFailure:
    printout = 'Could not connect to Mongo at: "' + settings["settings"]["server"] + '" on database "' + settings["settings"]["db_name"] + "." + settings["settings"]["board_name"] + '"'
    logger.error(printout)
    sys.exit(0)

#Register board on server, if already registered, update information about board
board_info = {"ip":socket.gethostbyname(socket.gethostname()), "hostname":socket.gethostname(), "sensor_reading_frequency":settings["settings"]["sensor_reading_frequency"], "server":settings["settings"]["server"], }
try:
    client["admin"]["boards"].update({"name":settings["settings"]["board_name"]}, board_info)
except:
    client["admin"]["boards"].insert(board_info)
logger.info("Added board info:")
logger.info(board_info)
del board_info

#Find and match serial ports:
available_ports = listPorts()
if len(available_ports) == 0:
    logger.error("No ports found.")
    sys.exit(0)
ports = []
syspaths = []
for i in available_ports:
    ports.append(i[0])#get only ttyUSBX values
    arg = 'udevadm info -q path -n ' + i[0]
    arg = subprocess.check_output(arg, shell=True)
    arg = '/sys' + arg[0:arg.index('tty')]
    syspaths.append(arg)#get sysfs bus info

for i in settings["sensors"]:
    if not i["path"] in syspaths:#If path stored in the settings file does not exist in syspaths throw error
        logger.error("Not all sensors are connected, check connections and try again, or manually enter sensors. Now exiting.")
        sys.exit(0) 
for i in settings["sensors"]:#Instantiate sensors defined in settings file
    arg = 'ls ' + i["path"] + ' |grep tty'
    port = '/dev/' + subprocess.check_output(arg, shell=True)[0:-1]#Remove \n, and add /dev/
    if(port == '/dev/tty'):#Ubuntu exception
        arg = 'ls ' + i["path"] + '/tty |grep tty'
        port = '/dev/' + subprocess.check_output(arg, shell=True)[0:-1]
    try:
        sensors.append(SerialSensor(i["name"], i["units"], port, i["wait_time"], i["baud_rate"]))#initialize sensors
    except SerialError, e:
        logger.error(e.args + e.sensor + e.port)
        raise

#cleanup unused variables
del port, i, settings, syspaths, ports, available_ports, arg

#Display sensors
logger.info("Available sensors:")
for i in sensors:
    logger.info((i.getName(), '@', i.getPort(), "units:", i.getUnits(), "waiting time:", i.getWaitTime()))
logger.info(("Data points to date: " + str(collection.count())))
logger.info("Reading Started")

#Send LED on and Disable continuous mode commands
try:
    for i in sensors:
        i.send('L1')
        i.send('E')
except SerialError, e:
    logger.error("Error sending initial commands")
    raise

#End of initialization
#Finally, start reading:
#Main Loop
while True:
    try:
        initial_time = time.time()
        JSON_readings = {}# clear dictionary that holds json formatted sensor readings
        for i in sensors:
            i.send('R')#Can throw exceptions 
            time.sleep((float(i.getWaitTime())/1000))
            reading = i.readJSON()#Can throw exceptions
            JSON_readings.update(reading)
        
        count += 1
        JSON_readings["date"] = now()
        collection.insert(JSON_readings)
        
        final_time = time.time()
        sleep = (reading_frequency - (final_time - initial_time))
        if sleep >= 0.0: time.sleep(sleep)
        else: logger.info("Running at " + str(final_time - initial_time) + " seconds per reading, more than defined reading frequency. Make necessary adjustments.")
    except SerialError, e:
        logger.error(("Serial error occured, trying to fix connection of " + e.sensor +' @ ' + e.port + ' errno ' + e.errno))
        if e.errno == 0:#Errno 0: Could not connect error, try to repair:
            logger.error(("Could not connect to sensor: " + e.sensor +' @ ' + e.port + ' errno ' + e.errno))
            for _ in xrange(3):
                if check_connection(True): #Try to repair connection
                    logger.info("Fixed")
                    break
            if not check_connection(True): #If unable, disable sensor, and move on
                i.enable(False)
                logger.error(("Disabled sensor: " + e.sensor +' @ ' + e.port + ' errno ' + e.errno))
                pass
        elif e.errno == 2:#Errno 2: Invalid data type error, try reading again:
            logger.error(("Invalid data type on sensor: " + e.sensor +' @ ' + e.port + ' errno ' + e.errno))
            for _ in xrange(3):
                try:
                    time.sleep(3)
                    i.readJSON()
                    break
                except:
                    pass
            try:
                i.readJSON()
                pass
            except:#Still having problems, remove sensor
                i.enable(False)
                logger.error(("Disabled sensor: " + e.sensor +' @ ' + e.port + ' errno ' + e.errno))
        else:
            logger.error("Unhandled error")
            raise
    except:
        logger.error("Unhandled Exception, non SerialError in main while loop")
        raise









