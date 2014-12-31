#!/usr/bin/python2
"""
Sensor Reader Script

Script to retrieve data from serial sensors and storing onto MongoDB databases.
Support for web management, and headless deployment.

Script also used to demonstrate SerialSensor Library.


Attributes:
    version (str): Version number.
    counter (int): Variable to hold number of entries sent to DB.
    hostname (str): Board's hostname.
    ip_address (str): Board's IP Address.
    base_path (str): Current working directory (where log and config files are located)
    log_path (str): Path to the log file, appended to old_log_path, then cleared.
    old_log_path (str): Path to the old log file, where current logs are appended to.
    config_path (str): Path to the config file.
    client (MongoClient): DB Client object.

"""

from serial import termios
import datetime
import socket
from bson import json_util
from bson.objectid import ObjectId
import sys
import time
import urllib2
import subprocess
import traceback
import pymongo
from pymongo import errors
import logging
import os
from serialsensor import *


# Global Variables:
# Version number
version = "1.1 Build 10"
# Variable to count the number of data points sent
counter = 0
# Board's hostname
hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)
# base_path is the script directory, where log.log and config.json must be present
base_path = os.path.dirname(os.path.realpath(__file__)) + '/'
log_path = base_path + 'log.log'
old_log_path = base_path + 'old_log.log'
config_path = base_path + 'config.json'
# DB Client
client = None
# Settings
settings = None


# Initializes logger
def initialize_logger(log_path, old_log_path):
    # Try to find current log, if found, append to old_log
    try:
        with open(log_path, 'r+') as curr_log:
            log = curr_log.read()
            if log.count('Started execution:') >= 2:  # If there's only 1 or less logs, do nothing
                l1st = log.rfind('Started execution:')  # 1st log log[last occurence of 'Started exec...':EOF]
                with open(old_log_path, 'a+') as old_log:
                    old_log.writelines(log[:l1st])  # Append everything up to the 1st log
                f = open(log_path, 'w+')
                f.writelines(log[l1st:])
                f.close
            del log
    except:
        pass
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_path)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


# Initialize logger
logger = initialize_logger(log_path, old_log_path)

# Check if superuser
if (os.getuid() != 0):
    logger.error("Must be run as superuser!")
    sys.exit(0)


# Override sys.excepthook to log unhandled exceptions (unhandled_exception_logger defined at the end)
def unhandled_exception_logger(_type, _value, _traceback):
    # Logs unhandled exceptions
    try:
        settings['status']['value'] = "Exception"
        saveSettingsToDB(settings, client, settings['_id'])
        uploadLog(client, log_path, settings['_id'])
    except:
        logger.exception("Error uploading log and settings:")
    logger.error("Uncaught unhandled exception: ", exc_info=(_type, _value, _traceback))
    print "Check errors in log"
    sys.exit(0)

sys.excepthook = unhandled_exception_logger

# Function definitions:


def quit():
    try:
        settings['status']['value'] = "Stopped"
    except:
        pass
    try:
        saveSettingsToDB(settings, client, settings['_id'])
        uploadLog(client, log_path, settings['_id'])
    except:
        try:
            logger.exception("Error uploading log and settings:")
        except:
            pass
    sys.exit(0)


def now():
    # Returns UNIX Epoch timestamp.
    return(datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds()


def initialize(path, hostname, version):
    """
    Initialization routine.
    Initializes DB Client, and retrieves settings from DB and File for comparison.
    If no settings are found on DB, file settings are pushed to DB, else, settings are pulled from DB
    and saved to file.

    Notes:
        - File config is essentially used to push settings/sensor settings pattern to DB, and insert
        already initialized settings to a new DB.
        - The 'client' returned is a global variable (used to upload logs if outside main()).
        - Exits script if cannot retrieve settings from DB after just inserting them.

    Args:
        path (str): Path to config file.
        hostname (str): Board's hostname.
        version (str): Board's version string (defined in the beginning)

    Returns:
        (settings, client) tuple. With the settings file to be used, and the DB client
    """
    file_settings = getSettingsFromFile(path)  # Get username, password and server
    for j in xrange(3*60*60/15):  # 720 trials
        try:
            client = mongoConnect(file_settings['settings']['value']['server']['value'],
                                  username=file_settings['settings']['value']['username']['value'],
                                  password=file_settings['settings']['value']['password']['value']
                                  )
            break
        except:
            if j >= 3*60*60/15 - 1:
                output("Could not connect to DB.", logger.error)
                sys.exit(0)  # Don't bother with quit(), no connection anyway
            else:
                output("Trying again in 15 seconds.", logger.error)
            time.sleep(15)

    try:
        Id = file_settings['_id']
    except KeyError:
        Id = None  # Using None as Id, No ID found on config file
    settings = getSettingsFromDB(client, Id)
    if settings is None or settings['changes']['date'] == "":
        # No settings on server, or never saved, so
        # board is new, or server is new, either way, push settings on file to DB
        try:
            file_settings.pop('_id')  # Remove _id, in case settings_file already has one
        except KeyError:
            pass
        if file_settings['changes']['date'] == "":
            # No 'date' -> Uninitialized board, wait for settings to be updated
            output("Server and Board uninitialized, adding initial info...")
            file_settings['version']['value'] = version
            file_settings['status']['value'] = "Uninitialized, waiting for update..."
            file_settings['settings']['value']['hostname']['value'] = hostname
            file_settings['ip']['value'] = ip_address
            Id = saveSettingsToDB(file_settings, client, None)  # Creates new entry and gets _id
            db_settings = getSettingsFromDB(client, Id)
            if db_settings is None:
                output("Problem Saving/Retrieving settings during initialization.", logger.error)
                quit()
            saveSettingsToFile(db_settings, config_path)
            output("Waiting for settings to be updated on the website, execution will resume once settings are updated...")
            new_settings = checkUpdates(db_settings, client, Id, config_path)
            while new_settings is None:
                time.sleep(10)
                new_settings = checkUpdates(db_settings, client, Id, config_path)
            settings = new_settings
            settings['status']['value'] = "Initialized"
            saveSettingsToDB(settings, client, settings['_id'])
            saveSettingsToFile(settings, path)

        else:
            output("Board has already been initialized, however server has not, saving settings on file to server...")
            Id = saveSettingsToDB(file_settings, client, None)
            settings = getSettingsFromDB(client, Id)  # get new _id
            saveSettingsToFile(settings, config_path)

    settings['version']['value'] = version
    settings['settings']['value']['hostname']['value'] = hostname
    settings['ip']['value'] = ip_address
    settings['status']['value'] = "Running"
    saveSettingsToFile(settings, path)
    saveSettingsToDB(settings, client, settings['_id'])

    # Check and update hostname:
    if settings['settings']['value']['hostname']['value'] != hostname:
        subprocess.check_output("hostnamectl set-hostname " + settings['settings']['value']['hostname']['value'], shell=True)
        output("New hostname set to: " + settings['settings']['value']['hostname']['value'] + "  Rebooting board.")
        os.system("systemctl reboot")
        sys.exit(0)

    output("\nUsing settings from DB\n")
    uploadLog(client, log_path, settings['_id'])

    return settings, client


def mongoConnect(server, username="", password=""):
    """
    Connects and authenticates to the server if username provided.

    Notes:
        Authentication uses the 'admin' database.

    Args:
        server (str): Server's URL or IP Address
        username (str): DB Server's username. If provided, authentication will be used.
        password (str): DB Server's password.

    Returns:
        DB Client (MongoClient).
    """
    try:
        client = pymongo.MongoClient(server)
        if len(username.strip()) > 0:
            client.admin.authenticate(username, password)
        output("Connected to " + client.host, logger.info)
        return client
    except pymongo.errors.ConnectionFailure:
        output("Configuration error, please check settings. Exiting.", logger.error)
        sys.exit(0)  # Don't bother with quit(), no connection anyway
    except pymongo.errors.ConnectionFailure:
        output('Could not connect to MongoDB at: "' + server + '"', logger.error)
        raise


def insertData(data, client, settings):
    """
    Inserts data point to DB and Collection defined in settings.

    Args:
        data(JSON serializable dict): Data point.
        client (MongoClient): MongoDB Client object
        settings (dict): Current settings dictionary.
    """
    client[settings['settings']['value']['db_name']['value']][settings['settings']['value']['collection_name']['value']].insert(data)


# # Parse json file into simple dictionary
# def parseSettings(settings_json):
#     # settings has:
#     # status
#     # settings {}
#     # changes
#     # sensors []
#     # ip
#     # version
#     if settings_json is None:
#         return None
#     settings = {}
#     for key in settings_json.keys():
#         # Only keep values
#         if isinstance(settings_json[key]['value'], dict):
#             settings[key] = parseSettings(settings_json[key]['value'])
#         elif isinstance(settings_json[key]['value'], list):
#             for i in settings_json[key]['value']:
#                 settings.setdefault(key, []).append(parseSettings(i))
#         else:
#             settings[key] = settings_json[key]['value']
#     return settings


def checkUpdates(current_settings, client, Id, path):
    """
    Checks settings on DB for updates, and updates file and running settings.

    Notes:
        Settings are retrieved/uploaded to the 'admin' database on the 'boards' collection by default.

    Args:
        current_settings (dict): current settings dictionary
        client (MongoClient): MongoDB Client object
        Id (str or ObjectId): Board Id, corresponding to settings/log entry Id on database
        path (str): Path to config file

    Returns:
        settings dictionary if new settings are found on DB
        None if no new settings are found on DB (conpared to current settings by date)
        False if it was not possible to retrieve settings from DB

    """
    db_settings = getSettingsFromDB(client, Id)
    if db_settings is None:
        # Could not retrieve settings from db, deleted?
        output("Problem retrieving settings from DB. Board may have been deleted from server", logger.error)
        return False
    try:
        curr_date = time.strptime(current_settings['changes']['date'], "%m/%d/%y %I:%M:%S%p")
    except:
        curr_date = 0
    try:
        db_date = time.strptime(db_settings['changes']['date'], "%m/%d/%y %I:%M:%S%p")
    except:
        db_date = 0
    if curr_date < db_date:
        output("New settings found on DB, updating...", logger.info)
        saveSettingsToFile(db_settings, path)
        # updateSettings(db_settings)  # settings is now equal to db_setings
        output("New settings updated.", logger.info)
        return db_settings
    return None


def uploadLog(client, log_path, Id):
    """
    Uploads the current log to the database.

    Notes:
        Log is uploaded to the 'admin' database on the 'log' collection by default.

    Args:
        client (MongoClient): MongoDB Client object
        log_path (str): Path to log file
        Id (str or ObjectId): Board Id, corresponding to settings/log entry Id on database

    """
    # Uploads only current log
    try:
        with open(log_path) as log_file:
            text = log_file.read()
            if not client['admin']['log'].update({'_id': ObjectId(Id)},
                                                 {'_id': ObjectId(Id), 'contents': text}
                                                 )['updatedExisting']:
                client['admin']['log'].insert({'_id': ObjectId(Id), 'contents': text})
    except:
        output("Error uploading log, ignoring...", logger.error)


def saveSettingsToFile(settings, path):
    """
    Saves the settings disctionary to the config file.

    Args:
        settings (dict): Current settings dictionary.
        path (str): Path to config file.

    """
    try:
        with open(path, 'w') as open_path:
            open_path.writelines(json_util.dumps(settings, indent=4))
    except:
        output("Cannot write to file. Continuing without saving...", logger.error)


def saveSettingsToDB(settings, client, Id):
    """
    Saves the settings file to the database, given an Id.

    Notes:
        Settings and Log are saved to the 'admin' database on the 'boards' collection by default.

    Args:
        settings (dict): Settings dictionary to be saved.
        client (MongoClient): MongoDB Client object.
        Id (str or ObjectId): Board Id, corresponding to settings entry Id on database.

    Returns:
        Id, if not already present on the database, inserting a new entry.
        None, if error while saving.
    """
    if settings is None:
        return None
    try:
        if Id is None:
            # New Board
            return client['admin']['boards'].insert(settings)  # return _id
        if not client['admin']['boards'].update({'_id': ObjectId(Id)}, settings)['updatedExisting']:
            # Id not found, create new entry
            return client['admin']['boards'].insert(settings)  # return _id
    except pymongo.errors.OperationFailure:
        output("Error saving settings to DB", logger.error)
        return None


def getSettingsFromFile(path):
    """
    Gets settings disctionary from config file.

    Args:
        path (str): Path to config file.

    Returns:
        Settings dictionary, if found.

    Exceptions:
        IOError, if file not found.
    """
    try:
        with open(path) as open_path:
            settings_json = json_util.loads(open_path.read())
            return settings_json
    except IOError, e:
        if e.errno == 2:  # File not found
            output("Config file not found. Now exiting...")
            quit()
        else:
            output("Unknown error while opening config file.")
            raise
            quit()


def getSettingsFromDB(client, Id):
    """
    Gets settings disctionary from DB given an Id.

    Notes:
        - Settings and Log are retrieved to the 'admin' database on the 'boards' collection by default.
        - Assumes client has already been authenticated to, if needed.

    Args:
        client (MongoClient): MongoDB Client object.
        Id (str or ObjectId): Board Id, corresponding to settings entry Id on database.

    Returns:
        Settings dictionary, if found.
        None, if not found, if 'Id' is None, or error.
    """
    try:
        if Id is None:
            return None
        return client['admin']['boards'].find_one({'_id': ObjectId(Id)})
    except pymongo.errors.OperationFailure:
        output("Error getting settings to DB", logger.error)
        return None


def waitForInternet(wait):
    """
    Wait for internet connection for a given amount of time.

    Notes:
        Exits after timeout.

    Args:
        wait (int): Time to keep waiting for internet connection.
    """
    try:
            urllib2.urlopen('http://74.125.228.100', timeout=5)  # Google
            output("Internet connection estabilished\n", logger.info)
    except urllib2.URLError:
        t = 0
        output("Waiting up to: " + str(wait) + " seconds for connection...", logger.info)
        while t < wait:
            try:
                urllib2.urlopen('http://74.125.228.100', timeout=5)  # change this to connect to server (if on intranet)
                output("Internet connection estabilished after: " + str(t) + " seconds.", logger.info)
                return
            except urllib2.URLError:
                time.sleep(10)
            t += 15
        output("No Internet connection, exiting...", logger.info)
        quit()


def output(message, log_func=None, verbose=True):
    """
    Outputs the message to stdio and/or log.

    Args:
        message (str): Message to be displayed.
        log_func(logging object, optional): If provided, message is printed on logger provided (l.info/l.error).
        verbose (bool, Default: False): If True, prints message to stdio.
    """
    if verbose:
        print message
    if log_func is not None:
        log_func(message)


def matchSerialPorts(settings, client, path):
    """
    Matches the available tty ports in the '/dev/' path to the paths in the settings file. If all
    paths from the settings file cannot be matched, exit.
    If any of the paths is using the '/dev/ttyUSBx' format, find sysfs path, and save to DB/File.

    Notes:
        - Replaces '/dev/ttyUSBx' paths for sysfs paths, and saves to DB/File.
        - No need for 'Id' arg, since settings dictionary is provided.


    Args:
        settings (dict): Settings dictionary to be used for matching. Paths can be of sysfs or '/dev/ttyUSBx' type.
        client (MongoClient): MongoDB Client object.
        path (str): Path to config file.
    """
    available_ports = listPorts()
    update = False
    if len(available_ports) == 0:
        output("No ports found. Now exiting.", logger.error)
        quit()
    ports = []
    syspaths = []
    for i in available_ports:
        ports.append(i[0])  # get only ttyUSBx values
        syspaths.append(getSysPathFromTTY(i[0]))
    for i in settings['sensors']['value']:
        if i['path']['value'].strip().find('/dev/') == 0:  # If starts with /dev/ must be /dev/ttyUSBx
            settings['sensors']['value'][settings['sensors']['value'].index(i)]['path']['value'] = getSysPathFromTTY(i['path']['value'])
            update = True
        if i['path']['value'] not in syspaths:
            # Check if path in the settings file doesn't exist in sysfs (syspaths)
            output("Not all sensors are connected. Now exiting. Check connections and try again:", logger.error)
            output("Sensor: " + i['path']['value'], logger.error)
            quit()
    if update:
        #  Add syspaths to config file, and push to server:
        output("Updated syspaths", logger.info)
        saveSettingsToFile(settings, path)
        saveSettingsToDB(settings, client, settings['_id'])


def getTTYFromPath(path):
    """
    Returns the '/dev/ttyUSBx' given either a sysfs path string or a '/dev/ttyUSBx' string.

    Notes:
        If given a '/dev/ttyUSBx' string, the function simply returns 'path'

    Args:
        path (str): sysfs or /dev path to USB device.

    Returns:
        str: returns a properly formatted '/dev/ttyUSBx' path
    """
    path = path.strip()
    if path.find('/dev/') == 0:  # If starts with /dev/ must be /dev/ttyUSBx
        return path
    arg = 'ls ' + path + ' |grep tty'  # Build arg string: ls /sys/path/... |grep tty
    port = '/dev/' + subprocess.check_output(arg, shell=True)[0:-1]  # Remove \n, and prepend /dev/
    if(port == '/dev/tty'):  # Ubuntu/Debian exception, handle 'tty' subfolder
            arg = 'ls ' + path + '/tty |grep tty'
            port = '/dev/' + subprocess.check_output(arg, shell=True)[0:-1]
    return port.strip()


def getSysPathFromTTY(TTY):
    """
    Returns the sysfs path given a '/dev/ttyUSBx' path string.

    Args:
        path (str): /dev path to USB device.

    Returns:
        str: returns a properly formatted sysfs path
    """
    TTY = TTY.strip()
    arg = 'udevadm info -q path -n ' + TTY  # String to be executed: udevadm info -q path -n /dev/ttyUSBx
    res = subprocess.check_output(arg, shell=True)  # Returns sysfs path
    path = '/sys' + res[0:res.index('tty')]  # prepend /sys and remove tty folder
    return path.strip()


def instantiateSensors(sensors_list):
    """
    Creates and returns a list of properly initialized sensors given a list of standard sensor
    configuration data.

    Args:
        sensors_list (list): List containing multiple sensor configuration data (dictionary), like such:

            [sensor_1, sensor_2, ...]

            Where sensor_n is a standard format sensor configuration dictionary:
            sensor_n = {
                "path": {
                    "title": "Sysfs path or ttyUSBX port (System will convert to sysfs path)",
                    "type": "string",
                    "value": ""
                },
                "baud_rate": {
                    "title": "Baud Rate",
                    "type": "integer",
                    "value": 0
                },
                "name": {
                    "title": "Measurement Names (comma separated)",
                    "type": "string",
                    "value": ""
                },
                "wait_time": {
                    "title": "Waiting time between measurements (milliseconds)",
                    "type": "integer",
                    "value": 0
                },
                "units": {
                    "title": "Measurement Units (comma separated)",
                    "type": "string",
                    "value": ""
                }
            }

        Note that sensor_n['path']['value'] may be either a sysfs path or a /dev/ttyUSBx path, such as:

            sensor_n['path']['value'] = '/sys/devices/platform/...''
        or
            sensor_n['path']['value'] = '/dev/ttyUSB0'

    Returns:
        list: List containing initialized sensors (instances of SerialSensor):
    """
    sensors = []
    for i in sensors_list:  # Instantiate sensors defined in settings file
        port = getTTYFromPath(i['path']['value'])
        try:
            # initialize sensors:
            sensors.append(SerialSensor(i['name']['value'],
                                        i['units']['value'],
                                        port,
                                        i['wait_time']['value'],
                                        i['baud_rate']['value'],
                                        read_command=i['read_command']['value']
                                        ))
        except SerialError, e:
            output('Could not initialize sensor "' + i['name']['value'] + '"', logger.error)
            raise
    return sensors


def main():
    global counter
    global client
    global settings

    # initialization routine, and get new settings and DB client
    settings, client = initialize(config_path, hostname, version)

    try:
        # log settings
        printout = '\nVersion:                  ' + version + \
                   '\nStatus:                   ' + settings['status']['value'] + \
                   '\nDescription:              ' + settings['settings']['value']['description']['value'] + \
                   '\nLocation:                 ' + settings['settings']['value']['location']['value'] + \
                   '\nHostname:                 ' + hostname + \
                   '\nIP Address:               ' + ip_address + \
                   '\nID:                       ' + str(settings['_id']) + \
                   '\nLast updated settings:    ' + settings['changes']['date'] + \
                   '\n\nUsing settings:\n' + \
                   '\nServer:                   ' + settings['settings']['value']['server']['value'] + \
                   '\nDB name:                  ' + settings['settings']['value']['db_name']['value'] + \
                   '\nCollection name:          ' + settings['settings']['value']['collection_name']['value'] + \
                   '\nFrequency (seconds):      ' + settings['settings']['value']['sensor_reading_frequency']['value'] + '\n'
        output(printout, logger.info)
        del printout

        try:
            # Find and match serial ports:
            matchSerialPorts(settings, client, config_path)
            # If all sensors from settings found, continue:
            sensors = instantiateSensors(settings['sensors']['value'])
        except:
            output("Rebooting board...", logger.error)
            uploadLog(client, log_path, settings['_id'])
            os.system("systemctl reboot")
            sys.exit(0)

        # Display initialized sensors
        output("Available sensors:", logger.info)
        for i in sensors:
            output(i.getName() + ' @ ' + i.getPort() + " , Units: " +
                   i.getUnits() + " , Waiting time: " + str(i.getWaitTime()) + 'ms', logger.info)

        output("Data points to date: " +
               str(client[settings['settings']['value']['db_name']['value']]
                   [settings['settings']['value']['collection_name']['value']].count()), logger.info)

        output("Reading Started...", logger.info)
    finally:
        uploadLog(client, log_path, settings['_id'])

    # End of initialization
    # Start reading:
    # Main Loop

    while True:

        new_settings = checkUpdates(settings, client, settings['_id'], config_path)

        uploadLog(client, log_path, settings['_id'])

        if new_settings is not None:
            if new_settings is False:
                # Settings has been deleted from server
                quit()
            return

        try:
            initial_time = time.time()
            JSON_readings = {}  # clear dictionary for nex reading
            for i in sensors:
                if i.isEnabled():
                    reading = i.read()
                    JSON_readings.update(reading)
            if JSON_readings == {} and counter > 2:
                # If all sensors are disabled
                output("No data being sent, exiting.", logger.error)
                quit()
            counter += 1
            JSON_readings['date'] = now()
            insertData(JSON_readings, client, settings)
            print counter
            print JSON_readings
            print '\n'
            final_time = time.time()
            sleep = (float(settings['settings']['value']['sensor_reading_frequency']['value']) - (final_time - initial_time))
            if sleep >= 0.0:
                time.sleep(sleep)
            else:
                output("Running at " + str(final_time - initial_time) + " seconds per reading, \
                      more than defined reading frequency. Make necessary adjustments.", logger.info)

        except SerialError, e:
            output("\n\n", logger.error)
            output(e, logger.error)
            output("The previous error was due to the following exception:", logger.error)
            output(e.SourceTraceback(), logger.error)
            for j in xrange(3):
                try:
                    i.close()
                    i.open()
                    i.send('\r\n')
                    i.read()
                    break
                except SerialError, e:
                    output("SerialError Exception occured during #" + str(j) + " trial:", logger.error)
                    output(e.SourceTraceback(), logger.error)
                    time.sleep(0.4)
                except:
                    output("Unknown Exception occured during #" + str(j) + " trial:", logger.error)
                    output(traceback.format_exc(), logger.error)
                    time.sleep(0.4)
            if j >= 2:  # If exhausted trials
                try:
                    i.close()
                    i.open()
                    i.read()
                except SerialError, e:
                    output("Exhausted maximum number of trials:", logger.error)
                    output(e.SourceTraceback(), logger.error)
                    if e.errno == 5:
                        try:
                            ports_still_same = i.getPort() == getTTYFromPath(getSysPathFromTTY(i.getPort()))
                        except:
                            ports_still_same = False
                        if not ports_still_same:
                            output("\n\nReloading sensors due to exception in: " + e.sensor + ' @ ' + e.port + ' errno ' + str(e.errno) + "\n\n", logger.error)
                            output(e.SourceTraceback(), logger.error)
                            uploadLog(client, log_path, settings['_id'])
                            return
                        else:
                            output("Rebooting board, due to fault in: " + e.sensor + ' @ ' + e.port + ' errno ' + str(e.errno), logger.error)
                            output(e.SourceTraceback(), logger.error)
                            uploadLog(client, log_path, settings['_id'])
                            os.system("systemctl reboot")
                            sys.exit(0)
                    if e.errno == 0 or e.errno == 3:
                        output("\n\nReloading sensors due to exception in: " + e.sensor + ' @ ' + e.port + ' errno ' + str(e.errno) + "\n\n", logger.error)
                        output(e.SourceTraceback(), logger.error)
                        uploadLog(client, log_path, settings['_id'])
                        return

                    output("Fault in: " + e.sensor + ' @ ' + e.port + ' errno ' + str(e.errno), logger.error)
                    output("Error cannot be fixed by reloading or rebooting. Check Board!", logger.error)
                    output(e.SourceTraceback(), logger.error)
                    quit()
                except:
                    output("Rebooting board due to non SerialError fault in: " + e.sensor + ' @ ' + e.port + ', Errno ' + str(e.errno), logger.error)
                    output(traceback.format_exc(), logger.error)
                    uploadLog(client, log_path, settings['_id'])
                    os.system("systemctl reboot")
                    sys.exit(0)

        except pymongo.errors.AutoReconnect, e:
            output("Connection to database Lost, trying to reconnect every 30 seconds up to 500 times", logger.error)
            timeout = 500
            j = 0
            while j <= timeout:
                try:
                    client.database_names()  # try to reconnect
                    output("Connection restabilished. Continuing...", logger.info)
                    j = timeout
                except pymongo.errors.AutoReconnect, e:
                    if j == timeout:
                        output("Connection to database could not be restabilished. Now exiting...", logger.exception)
                        quit()
                    time.sleep(30)
                j += 1

        except KeyboardInterrupt, e:
            output("Manual quit", logger.error)
            quit()

        except:
            output("Rebooting board due to non Unhandled Exception in main while loop", logger.error)
            output(traceback.format_exc(), logger.error)
            uploadLog(client, log_path, settings['_id'])
            os.system("systemctl reboot")
            sys.exit(0)

        finally:
            uploadLog(client, log_path, settings['_id'])


if __name__ == '__main__':
    output("\n\nStarted execution:\n\n", logger.info)
    # Waits for internet connection (up to 3600 seconds), exits if not found.
    waitForInternet(60*60*5)
    while True:
        main()
