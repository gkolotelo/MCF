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
reading_frequency = 0

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
    print "Check errors in log"
    sys.exit()

sys.excepthook = unhandled_exception_logger #Override sys.excepthook

#Initialization

#Waits for internet connection.
try:
    print "Waiting up to 30 seconds for internet connection, press ctrl-c to skip."
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
except KeyboardInterrupt:
    pass

#Get settings from config file, if nonexistent, create one
#Available settings:
#settings["settings"]["board_name", "db_name", "server", "sensor_reading_frequency"]
#settings["sensor"]["baud_rate", "wait_time", "name", "units", "port_number", "port", "path"]
try:
    settings = json.load(open(config_path))
    logger.info("Config file found")
except IOError, e:
    if e.errno == 2:
        if not raw_input("File not found, or nonexistent, press enter to create a new settings file (Enter)") == "": raise
        try:
            fp = open(config_path, 'w+')
            settings = json.load(fp)
            settings["settings"]["board_name"] = raw_input("Enter board name: ")
            settings["settings"]["db_name"] = raw_input("Enter database name (main_system or germinator: ")
            settings["settings"]["server"] = raw_input("Enter server address or (http://cityfarm.media.mit.edu): ")
            settings["settings"]["sensor_reading_frequency"] = raw_input("Enter sensor reading frequency (seconds): ")
            settings["sensor"] = {}
            fp.write(json.dumps(settings, indent=4))
            fp.close()
            print "Done!"
            logger.info("Config file created")
        except IOError, e: 
            print "Could not create file"
            logger.error("Config file not found")
            raise
    else: 
        logger.error("Config file not accessible, unhandled exception")
        raise
reading_frequency = float(settings["settings"]["sensor_reading_frequency"])

printout = "Using default settings:\n\n" + \
"Board Name: " + settings["settings"]["board_name"] + \
"\nMongo Server: " + settings["settings"]["server"] + \
"\nDB name: " + settings["settings"]["db_name"] + \
'\nFrequency (seconds): ' + str(settings["settings"]["sensor_reading_frequency"]) + \
"\nIP Address: " + socket.gethostbyname(socket.gethostname()) + \
"\nHostname: " + socket.gethostname() + "\n" 
print printout
logger.info(printout)
del printout

#Connect to Mongo Server:
print "Conecting to Mongo server..."
try :
    client = pymongo.MongoClient(settings["settings"]["server"])
    client.admin.authenticate(settings["settings"]["username"],settings["settings"]["password"])
    db = client[settings["settings"]["db_name"]]
    collection = db[settings["settings"]["board_name"]]
    print "Connected to ", collection.full_name
    logger.info(("Connected to " + collection.full_name))
except pymongo.errors.ConnectionFailure:
    printout = 'Could not connect to Mongo at: "' + settings["settings"]["server"] + '" on database "' + settings["settings"]["db_name"] + "." + settings["settings"]["board_name"] + '"'
    print printout
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
print "\nListing available serial ports..."
available_ports = listPorts()
if len(available_ports) == 0:
    print "Error: No ports found."
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

print "Wait to use predefined sensors, press ctrl-c to manually enter sensors (will delete old sensors)."
try: 
    for i in xrange(1,6):#timer waiting for user input
        print (6-i)
        time.sleep(1)
        sys.stdout.write('\r')
    print "Using sensors on config file..."
    logger.info("Using sensors on config file")

    for i in settings["sensors"]:
        if not i["path"] in syspaths:#If path stored in the settings file does not exist in syspaths throw error
            print "Not all sensors are connected, check connections and try again, or manually enter sensors. Now exiting."
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
            print e.args, e.sensor, e.port
            raise
    del port, i

except KeyboardInterrupt:#Catch manual override
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
        logger.info("Added sensor to config file")
    except IOError:
        print "Cannot open settings file."
        logger.error("Cannot open config file")
        raise
    del number, name, units, wait, fp, i
#cleanup unused variable
del settings, syspaths, ports, available_ports, arg

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

#Send LED on and Disable continuous mode commands
try:
    for i in sensors:
        i.send('L1')
        i.send('E')
except:
    print e.args, e.sensor, e.port
    logger.error("Unhandled Exception")
    raise

#End of initialization
#Finally, start reading:
#Main Loop
while True:
    try:
        initial_time = time.time()
        JSON_readings = {} # clear dictionary for nex reading
        for i in sensors:
            if i.isEnabled():
                i.send('R') #Can throw exceptions 
                time.sleep((float(i.getWaitTime())/1000))
                reading = i.readJSON() #Can throw exceptions
                JSON_readings.update(reading)
        if JSON_readings == {} and count > 2:
            print "No data being sent, exiting."
            logger.error("No data being sent, exiting.")
            sys.exit(0)
        count += 1
        JSON_readings["date"] = now()
        collection.insert(JSON_readings)
        print count
        print JSON_readings
        print '\n'
        
        final_time = time.time()
        sleep = (reading_frequency - (final_time - initial_time))
        if sleep >= 0.0: time.sleep(sleep)
        else: print "Running at " + str(final_time - initial_time) + " seconds per reading, more than defined reading frequency. Make necessary adjustments."
    except SerialError, e:
        print "Serial error occured, trying to fix connection of " + e.sensor +' @ ' + e.port + ' errno ' + str(e.errno)
        logger.error(("Serial error occured, trying to fix connection of " + e.sensor +' @ ' + e.port + ' errno ' + str(e.errno)))
        if e.errno == 0:#Errno 0: Could not connect error, try to repair:
            print "Could not connect to sensor: " + e.sensor +' @ ' + e.port + ' errno ' + str(e.errno)
            logger.error(("Could not connect to sensor: " + e.sensor +' @ ' + e.port + ' errno ' + str(e.errno)))
            for _ in xrange(3):
                if check_connection(True): #Try to repair connection
                    print "Fixed"
                    logger.info("Fixed")
                    break
            if not check_connection(True): #If unable, disable sensor, and move on
                i.enable(False)
                print "Disabled sensor: " + e.sensor + ' @ ' + e.port
                logger.error(("Disabled sensor: " + e.sensor +' @ ' + e.port + ' errno ' + str(e.errno)))
                pass
        elif e.errno == 2:#Errno 2: Invalid data type error, try reading again:
            print "Invalid data type on sensor: " + e.sensor +' @ ' + e.port + ' errno ' + str(e.errno) + ' value read: ' + "'" + e.msg + "'"
            logger.error(("Invalid data type on sensor: " + e.sensor +' @ ' + e.port + ' errno ' + str(e.errno) + ' value read: ' + e.msg))
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
                print "Disabled sensor: " + e.sensor +' @ ' + e.port + ' errno ' + str(e.errno)
                logger.error(("Disabled sensor: " + e.sensor +' @ ' + e.port + ' errno ' + str(e.errno)))
        else:
            print "Unhandled error"
            logger.error("Unhandled error")
            raise
    except:
        print "Unhandled Exception, non SerialError in main while loop"
        logger.error("Unhandled Exception, non SerialError in main while loop")
        raise








