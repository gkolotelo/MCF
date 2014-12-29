rpi_service.py
==============

About
-----

The included rpi_service.py was created to get data from Atlas Scientific and other generic serial sensors, and store the data on a MongoDB database.

How it works
------------

The script requires some information, such as server address, username, password, database name and collection, and information about the sensors, such as name, units, and so on are stored in the config file. These settings will be stored in the ``config.json`` file, as a json dictionary. The defult location of the script and supporting files is ``/root/RPi/`` or ``/root/RPi_Air/`` (in the case of an Air Board), which are the default paths when using ``image_utility.py``. The current and last logs are stored in the same path on the ``log.log`` file, while older logs are stored in ``old_log.log``.

The script will wait for an internet connection before proceeding. After connected, it'll get server, username and password information from the settings file, used to connect to the settings database. If the board has never been initialized, that is, no sensor information or DB information has been configured, the board will show up as ``Uninitialized_board`` in the web management interface and will wait for settings to be updated, once they are, the board will start acquiring data. If the board has already been initialized in the server, the settings stored in the database will be fetched and save to the settings file. If the board has already been initialized, but it is being introduced into a new server, the settings stored in the settings file will be uploaded to the settings database and the board will resume operation, with no need of initialization.

The status of the board ('Running' or 'Stopped') can be checked through the status lights in the selection page, or by selecting a board and vieweing the status on the information area.

The information area also provides the hostname, IP address, software version, ID and last settings change date, as well as access to the log file.

The sensors are associated to a specific USB port, so in order for the correct data to be associated to the correct sensor, the sensors must not be switched to other USB ports. If all sensors specified in the config file are not present when the script is started execution will fail.

The script reads each sensor once every ``sensor_reading_frequency`` seconds, as defined in the web management interface. If ``sensor_reading_frequency`` is less than the total time all sensors take to make their readings, the reading frequency will be the smallest possible, and a warning will be given in the log.

Error handling also occurs within the script. If the SerialSensor class throws an error, the error will be handled and the script will try to correct the error. If it's not possible to correct the error, the script may be reloaded, the board rebooted or execution will stop.

Using and configuring the script
--------------------------------

To start the script simply execute it:

    ``./rpi_service.py``

The rest of the configuration is done in the web management interface. To start the interface, simply start the interfaces server:

    ``web_management/server.py``

On the web management interface, selecting the board to be configured the following settings will be available:

General settings:
-   DB Username
-   DB Password
-   Description
-   DB Name
-   Collection Name
-   Hostname
-   Sensors Location
-   Server Address
-   Sensor Reading Frequency

Sensor settings:
-   Measurement Units
-   Measurement Names
-   Baud Rate
-   Waiting Time
-   Read Command [9]
-   Sysfs path or /dev/ttyUSBx path

All settings must be set in order to be saved.

Measurement Units and Names can be as follows::

Single measurement example:
        
    Names:  Temperature
    Units:  C

Multiple measurements example:

    Names:  Temperature,Humidity,CO2
    Units:  C,RH,ppm

Waiting Time: The time it takes for the sensor to respond after a reading command.
Read Command: The ASCII string the sensor takes as input to reply with a measurement.
Sysfs path or /dev/ttyUSBx path: When first initialized it is suggested that the /dev/ttyUSBx path corresponding to the sensor being set be used, since it is more human readable, however after settings are saved the system will replace this path with a sysfs path.

If all information provided is correct, the script will start outputting data:

Example output after initialization::

    Started execution:
    
    
    Connection estabilished
    
    Connected to server_address
    
    Version:                  1.1 Build 9
    Status:                   Running
    Description:              Sample Description
    Location:                 Sample Location
    Hostname:                 sample_hostname
    IP Address:               boards IP address
    ID:                       549d2592ece389050f909eaf
    Last updated settings:    01/31/15 12:00:00PM
    
    Using settings:
    
    Server:                   server_address
    DB name:                  db_name
    Collection name:          collection_name
    Frequency (seconds):      10
    
    Available sensors:
    Temperature,Humidity,CO2 @ /dev/ttyUSB0 , Units: C,RH,ppm , Waiting time: 1100.0ms
    Data points to date: data_points_on_collection_to_date
    Reading Started...

    1
    {"Temperature":{"value": 21.98, "units": "C"}, "Humidity":{"value": 38.4, "units": "RH"}, "CO2":{"value": 469, "units": "ppm"}}

    2
    {"Temperature":{"value": 21.86, "units": "C"}, "Humidity":{"value": 38.3, "units": "RH"}, "CO2":{"value": 467, "units": "ppm"}}


Now, every ``sensor_reading_frequency`` seconds, a JSON string will be sent to the database.

The script can be left running on the background by using ``screen`` as such::

    user$ screen 

This command will open screen, press enter to open a new screen terminal and run the script::

    user$ sudo ./rpi_service.py

After everything is running as expected, just detach screen by pressing ``ctrl^a`` followed by ``d``, and the scrip will be now running in background.
To reattach the terminal just enter::

    user$ screen -r

More information about using screen can be found at .. __: http://www.gnu.org/software/screen/manual/screen.html

If using a prebuilt linux image from CityFARM with the dedicated image utility, the script will be executed automatically upon booting, and so, headless deployment of boards is possible.

The log can also be used to check on the scripts status, which is available on the web management interface. 


Details
-------

This section discusses some particularities about the script, which might be useful in understanding how it fully works, and figuring out what might've gone wrong.

    1. The way sensors are initialized automatically from the settings file require that the USB to serial converters be kept connected to the same USB ports, and if a USB hub is used, it must also remain connected to the same USB ports on the host machine, or else, different hardware will be assigned to different configurations, resulting in incorrect data being sent to the database or a halting of the script. The reason for that is because the sysfs path to the USB to serial device is stored in the configuration file and will be used, with the help of an ``ls`` command, to discover the ``/dev/`` path to the USB device. This behavior is by design, since each time the host machine restarts, different ``/dev/`` ports are assigned, whereas the sysfs path remains the same.

    2. This script has been tested for Arch Linux on the Raspberry Pi, and Ubuntu Linux. Automatic device initialization may not work if running this script on other operating systems. This is due to the fact that the sysfs path may vary for different Linux distributions.

    3. Udevadm is used to discover sysfs paths to each USB device, and so, if not installed, may result in unexpected behavior.

    4. This script uses authentication on the MongoDB database through the ``admin`` database, and board settings and logs are also stored in the ``admin`` database, on the ``boards`` and ``log`` collection respectively. If authentication on your database is handled differently, function ``mongoConnect()`` may be changed to fix this.

    5. The SerialSensor class is used in this script, and in order for it to work, PySerial is required. PyMongo is also required to connect to the database.

    6. Note that a CR line ending is assume by default. If no line ending if provided along with "Read Command" on the web interface settings, CR will be used.








