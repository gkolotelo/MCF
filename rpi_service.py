#!/usr/bin/python2
"""
Sensor Reader Script


Attributes:
    sensors: List to hold the sensor objects.
    count: Variable to hold number of entries sent to DB.
    version: Version number

"""
from serial import termios
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
from serialsensor import *

if (os.getuid() != 0):
    print "Must be run as superuser"
    sys.exit(0)

version = "0.8 Build 7"

sensors = []
count = 0
base_path = '/root/RPi/'
log_path = base_path + 'log.log'
config_path = base_path + 'config.json'
sensor_reading_frequency = 0

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler(log_path)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.info("\n\n\nStarted excecution:\n")


def now():
    # Returns UNIX Epoch timestamp.
    return(datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds()


def unhandled_exception_logger(type, value, traceback):
    # Logs unhandled exceptions
    logger.error("Uncaught unhandled exception")
    logger.error(type)
    logger.error(value)
    logger.error(traceback)
    print "Check errors in log"
    sys.exit()

sys.excepthook = unhandled_exception_logger  # Override sys.excepthook

# Initialization
print version
logger.info(version)

# Waits for internet connection.
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

# Get settings from config file, if nonexistent, create one
# Available settings:
# settings["settings"]["board_name", "db_name", "server", "sensor_reading_frequency"]
# settings["sensor"]["baud_rate", "wait_time", "name", "units", "port_number", "port", "path"]
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
            settings["settings"]["db_name"] = raw_input("Enter database name: ")
            settings["settings"]["server"] = raw_input("Enter server address or IP: ")
            settings["settings"]["sensor_reading_frequency"] = raw_input("Enter sensor reading frequency (seconds): ")
            settings["sensor"] = {}
            fp.write(json.dumps(settings, indent=4))
            fp.close()
            print "Done!"
            logger.info("Config file created")
        except IOError, e:
            print "Could not create file"
            logger.exception("Config file not found")
            raise
    else:
        logger.exception("Config file not accessible, unhandled exception")
        raise
sensor_reading_frequency = float(settings["settings"]["sensor_reading_frequency"])

printout = "Using settings:\n\n" + \
           "Board Name: " + settings["settings"]["board_name"] + \
           "\nMongo Server: " + settings["settings"]["server"] + \
           "\nDB name: " + settings["settings"]["db_name"] + \
           '\nFrequency (seconds): ' + str(settings["settings"]["sensor_reading_frequency"]) + \
           "\nIP Address: " + socket.gethostbyname(socket.gethostname()) + \
           "\nHostname: " + socket.gethostname() + "\n"
print printout
logger.info(printout)
del printout

# Connect to Mongo Server:
print "Connecting to Mongo server..."
try:
    client = pymongo.MongoClient(settings["settings"]["server"])
    client.admin.authenticate(settings["settings"]["username"], settings["settings"]["password"])
    db = client[settings["settings"]["db_name"]]
    collection = db[settings["settings"]["board_name"]]
    print "Connected to ", collection.full_name
    logger.info(("Connected to " + collection.full_name))
except pymongo.errors.ConnectionFailure:
    printout = 'Could not connect to Mongo at: "' + settings["settings"]["server"] + '" on database "' + \
               settings["settings"]["db_name"] + "." + settings["settings"]["board_name"] + '"'
    print printout
    logger.error(printout)
    sys.exit(0)

# Register board on server, if already registered, update information about board
board_info = {"ip": socket.gethostbyname(socket.gethostname()), "hostname": socket.gethostname(),
              "sensor_reading_frequency": settings["settings"]["sensor_reading_frequency"],
              "server": settings["settings"]["server"], "board_name": settings["settings"]["board_name"],
              "db_name": settings["settings"]["db_name"]}
try:
    client["admin"]["boards"].update({"board_name": settings["settings"]["board_name"],
                                      "db_name": settings["settings"]["db_name"]}, board_info)
except:
    client["admin"]["boards"].insert(board_info)
print "Added board info to server:"
print board_info
logger.info("Added board info to server:")
logger.info(board_info)
del board_info

# Find and match serial ports:
print "\nListing available serial ports... (This may take a few seconds)"
logger.info("Listing available serial ports")
available_ports = listPorts()
if len(available_ports) == 0:
    print "Error: No ports found."
    logger.error("No ports found.")
    sys.exit(0)
ports = []
syspaths = []
for i in available_ports:
    ports.append(i[0])  # get only ttyUSBX values
    arg = 'udevadm info -q path -n ' + i[0]
    arg = subprocess.check_output(arg, shell=True)
    arg = '/sys' + arg[0:arg.index('tty')]
    syspaths.append(arg)  # get sysfs bus info

print "Wait to use predefined sensors, press ctrl-c to manually enter sensors (will delete old sensors)."
try:
    for i in xrange(1, 6):  # timer waiting for user input
        print (6-i)
        time.sleep(1)
        sys.stdout.write('\r')
    print "Using sensors on config file..."
    logger.info("Using sensors on config file")

    for i in settings["sensors"]:
        if not i["path"] in syspaths:
            # If path stored in the settings file does not exist in syspaths throw error
            print "Not all sensors are connected, check connections and try again,\
                  or manually enter sensors. Now exiting."
            logger.error("Not all sensors are connected, check connections and try \
                         again, or manually enter sensors. Now exiting.")
            sys.exit(0)
    for i in settings["sensors"]:  # Instantiate sensors defined in settings file
        arg = 'ls ' + i["path"] + ' |grep tty'
        port = '/dev/' + subprocess.check_output(arg, shell=True)[0:-1]  # Remove \n, and add /dev/
        if(port == '/dev/tty'):  # Ubuntu exception
            arg = 'ls ' + i["path"] + '/tty |grep tty'
            port = '/dev/' + subprocess.check_output(arg, shell=True)[0:-1]
        try:
            # initialize sensors:
            sensors.append(SerialSensor(i["name"], i["units"], port, i["wait_time"], i["baud_rate"], read_command=lambda: 'R'))
        except SerialError, e:
            print e.args, e.sensor, e.port
            raise
    del port, i

except KeyboardInterrupt:  # Catch manual override
    print '\nAvailable serial ports:'
    for i in ports:
        print "({})".format(ports.index(i)), i

    # Input example:
    print "Several sensors can be entered, just enter the asked information\
          (4 per sensor) for each sensor. When done, just press enter"
    print "More than one measurement can be made by each sensor, just enter comma\
          separated names for measurements and units (without spaces)"
    print "Example: \n", "0 \nMeas_1,Meas_2", "\nmg/L,PPM", "\n1000", "\n[Enter]"

    i = 1
    while True:
        print "\nSensor #" + str(i)
        number = raw_input("Type a port number:")
        if (number == ''):
            print "Continuing..."
            break
        name = raw_input("Type the sensor's measurement name:")
        units = raw_input("Type the sensor's units:")
        wait = raw_input("Type the time this sensor takes to return a measurement (in milliseconds):")
        # initialize sensors:
        sensors.append(SerialSensor(name, units, available_ports[int(number)][0], int(wait), baud_rate=38400, read_command=lambda: 'R'))
        i = i+1
    # Store settings in file
    settings["sensors"] = []
    for i in sensors:
        try:
            settings["sensors"].append(i.getJSONSettings('path', syspaths[ports.index(i.getPort())]))
            # Sysfs bus info added to JSON string
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
        logger.exception("Cannot open config file")
        raise
    del number, name, units, wait, fp
# cleanup unused variable
del settings, syspaths, ports, available_ports, arg

# Display sensors
print "\nAvailable sensors:"
logger.info("Available sensors:")
for i in sensors:
    print i.getName(), '@', i.getPort(), "units:", i.getUnits(), "waiting time:", i.getWaitTime()
    logger.info((i.getName(), '@', i.getPort(), "units:", i.getUnits(), "waiting time:", i.getWaitTime()))
print "Data points to date: ", collection.count()
logger.info(("Data points to date: " + str(collection.count())))
print "\nReading Started:\n\n"
logger.info("Reading Started")

# Send LED on and Disable continuous mode commands
# try:
#     for i in sensors:
#         i.send('L1')
#         i.send('E')
# except:
#     print e.args, e.sensor, e.port
#     logger.error("Unhandled Exception")
#     raise

# End of initialization
# Finally, start reading:
# Main Loop
while True:
    try:
        initial_time = time.time()
        JSON_readings = {}  # clear dictionary for nex reading
        for i in sensors:
            if i.isEnabled():
                # i.send('R')  # Can throw exceptions
                # time.sleep((float(i.getWaitTime())/1000))
                # reading = i.readJSON()  # Can throw exceptions
                reading = i.read()  # New
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
        sleep = (sensor_reading_frequency - (final_time - initial_time))
        if sleep >= 0.0:
            time.sleep(sleep)
        else:
            print "Running at " + str(final_time - initial_time) + " seconds per reading, \
                  more than defined reading frequency. Make necessary adjustments."

    except SerialError, e:
        if e.errno == 0:  # Errno 0: Could not connect error, try to repair:
            print e
            logger.error(e)
            if i.check_connection(False):  # Try again
                print "Fixed, no repair"
                logger.info("Fixed, no repair")
            else:
                for _ in xrange(3):
                    if i.check_connection(True):  # Try to repair connection
                        print "Fixed, repaired"
                        logger.info("Fixed, fixed repaired")
                        break
                if not i.check_connection(True):  # If unable to repair, disable sensor, and move on
                    i.enable(False)
                    print "Disabled sensor: " + e.sensor + ' @ ' + e.port
                    logger.error(("Disabled sensor: " + e.sensor +
                                  ' @ ' + e.port + ' errno ' + str(e.errno)))
        elif e.errno == 2:  # Errno 2: Invalid data type error, try reading again:
            print e
            logger.error(e)
            for _ in xrange(5):
                try:
                    time.sleep(2)
                    i.send('R')
                    time.sleep((float(i.getWaitTime())/1000) + 1)
                    i.readRaw()
                    break
                except SerialError, e:
                    pass
            try:
                i.send('R')
                time.sleep((float(i.getWaitTime())/1000) + 1)
                i.readRaw()
            except SerialError, e:  # Still having problems, remove sensor
                i.enable(False)
                print "Disabled sensor: " + e.sensor + ' @ ' + e.port + ' errno ' + str(e.errno)
                logger.error(("Disabled sensor: " + e.sensor + ' @ ' + e.port + ' errno ' + str(e.errno)))
        elif e.errno == 3:
            print e
            logger.error(e)
        else:
            print "SerialError occured, unhandled error on sensor: " + e.sensor + ' @ ' + e.port + ' errno ' + str(e.errno)
            logger.exception("SerialError occured, unhandled error on sensor: " + e.sensor + ' @ ' + e.port + ' errno ' + str(e.errno))
            raise

    except pymongo.errors.AutoReconnect, e:
        logger.error("Connection to database @ " + settings["settings"]["server"] + " Lost, trying to reconnect every 30 seconds up to 500 times")
        print "Connection lost"
        timeout = 500
        i = 0
        while i <= timeout:
            try:
                client.database_names()  # try to reconnect
                logger.info("Connection restabilished. Continuing...")
                print "Connection restabilished. Continuing..."
                i = timeout
            except pymongo.errors.AutoReconnect, e:
                if i == timeout:
                    print "Connection could not be restabilished"
                    logger.exception("Connection to database could not be restabilished. Now exiting...")
                    raise
                    sys.exit(0)  # Just in case raise doesn't raise
                time.sleep(30)
            i += 1

    except termios.error, e:
        print "Termios error occured: " + str(e) + ' ' + e.message + 'on' + i.getName()
        logger.error(("Termios error occured: " + str(e) + ' ' + e.message))
        for _ in xrange(3):
            if i.check_connection(True):  # Try to repair connection
                print "Fixed"
                logger.info("Fixed")
                break
        if not i.check_connection(True):  # If unable, disable sensor, and move on
            i.enable(False)
            print "Disabled sensor: " + i.getName() + ' @ ' + i.getPort()
            logger.error(("Disabled sensor: " + i.getName() + ' @ ' + i.getPort()))
            pass

    except KeyboardInterrupt, e:
        print "Manual quit"
        logger.error("Manual quit")
        sys.exit(0)

    except:
        print "Unhandled Exception, non SerialError in main while loop"
        logger.exception("Unhandled Exception, non SerialError in main while loop")
        raise
