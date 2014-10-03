rpi_service.py
==============

About
-----

The included rpi_service.py was created to get data from Atlas Scientific and generic serial sensors, and store the data on a MongoDB database.

How it works
------------

The script requires some information such as server address, and database name, and information about the sensors, such as name, units, and so on. These settings will be stored in the ``config.json`` file on ``/root/RPi/``, this can be changed by altering the ``base_path`` variable. Logging data is stored in the same path on the ``log.log`` file.

The script will wait for an internet connection before proceeding. After connected, it'll check for an existing settings file, if found, it'll be used, if not, the user will be asked to enter the required information, and the file will be created. The script will then try to connect to the MongoDB database at the defined server and database, and will store data in a collection whose name is the same as the board's name. Each board name must be unique, or sensor data from different boards will be mixed. Information about the board, such as it's IP address will be stored in the database for administrative purposes. Existing serial ports will be scanned and matched to the configuration on file, if all sensors exist it'll proceed to initialize the sensors, if not, an error will be thrown. ``ctrl^c`` can also be pressed to override the automatic initialization, an the sensors can be entered manually, they will then be stored on the configuration file. Information about the sensors will then be displayed to the user, and sensor reading will start.

The script reads sensor once every ``sensor_reading_frequency`` seconds. This takes into account the time each sensor takes to make a reading. If ``sensor_reading_frequency`` is less than the total time all sensors take to make their readings, the reading frequency will be the smallest possible, and a warning will be given.

Error handling also occurs in the script. If the SerialSensor class throws an error, the error will be evaluated and the script will try to correct the error. If it's not possible to correct the error, the sensor will be disabled, and the other sensors will not be affected. If an unhandled exception happens, the script will halt.

Using the script
----------------

To use the script, you must have ``rpi_service.py`` and ``serialsensor.py`` in the same folder. Take note of the folder the script's in, and open ``rpi_service.py`` on a text editor, then change ``base_path`` to your folder's path, making sure it ends with a '*/* ' .

Connect the sensors to the host machine, and run the script as a superuser::

    user@host_machine:$ sudo ./rpi_service.py

If it's the first time the script is executed, it'll ask to create a configuration file::

    File not found, or nonexistent, press enter to create a new settings file (Enter)

Press Enter, and enter in the requested information::

    Enter board name: (Will be used to create a collection at the specified database, each board name must be unique)
    Enter database name: (Database being used to store sensor data)
    Enter server address or IP: (Server address. Can be an IP address or URL)
    Enter sensor reading frequency (seconds): (Interval in which the board will send readings to the database)

The entered information will be displayed, and it’ll try to connect to the server::

    Using settings:
    Board Name: ...
    ...
    
    Connecting to Mongo server...
    Connected to 'database'
    Added board info to server:...
    ...

    Listing available serial ports... (This may take a few seconds)
    Wait to use predefined sensors, press ctrl-c to manually enter sensors (will delete old sensors).

If it's the first time the script is executed, press ``ctrl^c`` to enter the sensors manually, since no sensor are stored in the configuration file::

    Available serial ports: (The available serial ports will be shown, as the example below)
    (0) /dev/ttyACM0
    (1) /dev/ttyUSB0
    (2) /dev/ttyUSB1
    (3) /dev/ttyUSB2

Information will be asked for each sensor to be added. Just enter the information (port number, sensor/measurements names, sensor/measurements units, time required for measurement)::
    
    Sensor #1
    Type a port number: (Type the index of the port you wish to use. e.g. '1', for '/dev/ttyUSB0' on the example above)
    Type the sensor's measurement name: (Can be one name, or CSV names of the measurements read by the sensor. e.g. 'Temperature,Humidity,CO2')
    Type the sensor's units: (Must match the number of measurements provided above. e.g. 'C,RH,ppm' for the example above)
    Type the time this sensor takes to return a measurement (in milliseconds): (The time, in *ms*, the sensor takes to make all readings)

    Sensor#2
    Type a port number: (Will be asked again, this time for the next sensor. If no more sensors will be added, just press enter)

    Continuing...

The sensor configuration will be stored in the configuration file, so the next time the script is run, the sensors will be initialized automatically.

Information about the sensors will be displayed, and sensor reading will start::

    Available sensors:
    Temperature,Humidity,CO2 @ /dev/ttyUSB0 units: C,RH,ppm waiting time: 400
    Data points to date: 0 (Number of data points stored on the database, if it's the first reading, 0 will be shown)

    Reading Started: (Sample provided below)


    1
    {"Temperature":{"value": 21.98, "units": "C"}, "Humidity":{"value": 38.4, "units": "RH"}, "CO2":{"value": 469, "units": "ppm"}}

    2
    {"Temperature":{"value": 21.86, "units": "C"}, "Humidity":{"value": 38.3, "units": "RH"}, "CO2":{"value": 467, "units": "ppm"}}


Now, every ``sensor_reading_frequency`` seconds, a JSON string will be sent to the database.

The script can be left running on the background by using ``screen`` as such::

    user@host_machine:$ screen 

This command will open screen, press enter to open a new screen terminal and run the script::

    user@host_machine(screen):$ sudo ./rpi_service.py

After everything is running as expected, just detach screen by pressing ``ctrl^a`` followed by ``d``, and the scrip will be now running in background.
To reattach the terminal just enter::

    user@host_machine:$ screen -r

More information about using screen can be found at .. __: http://www.gnu.org/software/screen/manual/screen.html

The log can also be used to check on the scripts status. You can check the log by going to the directory the config file and log file's in (defined by ``base_path``) and use ``cat`` as following::

    user@host_machine:$ cd path/to/log/file/
    user@host_machine:$ cat log.log


Details
-------

This section discusses some particularities about the script, which might be useful in understanding how it fully works, and figuring out what might've gone wrong.

    1. The way sensors are initialized automatically from the settings file require that the USB to serial converter be connected to the same USB port, and if a USB hub is used, it must also remain connected to the same USB port on the host machine, or else, different hardware will be assigned to different configurations, resulting in incorrect data being sent to the database. The reason for that is because the sysfs path to the USB to serial device is stored in the configuration file, and will be used, through an ``ls`` Linux/Unix command to discover the ``/dev/`` path to the USB device. This behavior was by design, since each time the host machine restarts different ``/dev/`` ports are assigned, whereas the sysfs path remains the same.

    2. If more than one script is to be run in the same host machine, the ``base_path``, currently, must be differ for each running script, or else, the same sensors will be read to the same database concurrently, and may cause invalid data being read from the serial buffer.

    3. This script has been tested for Arch Linux on the Raspberry Pi, and Ubuntu Linux. Automatic device initialization may not work if running this script on other operating systems. This is due to the fact that the sysfs path may vary for different Linux distributions.

    4. Udevadm is used to discover sysfs paths to each USB device, and so, if not installed, may result in unexpected behavior.

    5. This script uses authentication on the MongoDB database, through the ``admin`` database. If authentication on your database is handled differently, or if it is not implemented at all, line 126 of the code can be changed to fix this.

    6. The SerialSensor class is used in this script, and in order for it to work, PySerial is required. PyMongo is also required to connect to the database.

    7. In the provided script, the command issued to read from the serial sensors is ``"r\r"``. This may change for different types of sensors, and can be altered as needed. Also the commands ``"L1\r"`` and ``"E\r"`` are issued to turn on the LED debugging and disable continuous reading of the Atlas Scientific sensors.








