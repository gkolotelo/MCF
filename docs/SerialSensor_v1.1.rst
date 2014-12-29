Using the SerialSensor v1.1 Module
==================================

Content within the module
-------------------------

============ ===========
Content        Description
------------ -----------
SerialSensor Used to interact with sensors via a serial port.
SerialError  Passes information from sensors that raised an exception.
listPorts()  Lists available serial ports on the host machine.
============ ===========


Importing the module
--------------------

The SerialSensor class can be imported by itself, however sensor information is passed through SerialError when exceptions occur, so it is suggested that it be imported as well. listPorts can be imported if the available serial ports are not known.

>>> from serialsensor import SerialSensor, SerialError, listPorts


Using SerialSensor
------------------

Following is an example that instantiates one sensor on ``/dev/ttyUSB0``, and prints the received data in the different available formats::

    from serialsensor import SerialSensor, SerialError

    # Instatiating a Temperature sensor located on '/dev/ttyUSB0', whose measurement is given in degrees 
    # Celsius, each measurement takes 400 milliseconds, and the Baud rate of the sensor is 38400 b/s.
    # The reading command, in this case, is 'r\r', where the sensor responds with data after 400ms.

        sensor = SerialSensor('Temperature', 'C', '/dev/ttyUSB0', 400, 38400, 'r')  # Note that CR line ending is assumed by default.

    # Print information about sensor:

        print "Reading from", sensor.getName(), "sensor:"

    # There are two ways to acquire data:
    # 1. Issue a reading command. In this case, the sensor outputs a reading 400ms after the 'r\r' command.

        sensor.send('r\r')  # Alternatively you may use just sensor.send('r'), since CR line ending is assumed by default.

    # Wait for the required time. Since the Wait Time is given in ms, it converted to s dividing by 1000

        time.sleep(sensor.getWaitTime()/1000)

    # Make readings:
    # Sensor data as read, converted to CRLF line break:
    
        read_string = sensor.readString(CRLF)

    # Sensor data in floating point values:
    
        read_value = sensor.readValues()

    # Sensor data in JSON dictionary format, containing the sensor's name, unit and measurement:
    
        read_json = sensor.readJSON()

    # Print measurements:

        print "String:", read_string
        print "Value:", read_value
        print "JSON:", read_json

    # 2. Read JSON directly, using read() function.
    # Sends read command, waits for required time, returns JSON dictionary.

        print "Read Function Output:", sensor.read()

Sample output::

    Reading from Temperature sensor:
    String: 21.98\r\n
    Value: 21.98
    JSON: {"Temperature":{"value":21.98, "units":"C"}}
    Read Function Output: {"Temperature":{"value":21.98, "units":"C"}}


The SerialSensor class can also handle sensors that send CSV values, just instatiate the sensor accordingly, for example:

Sensor instantiation::

    # Separate name and units by commas
    sensor = SerialSensor('Temp_C,Temp_F,Temp_F', 'C,F,K', '/dev/ttyUSB0', 400, 38400, 'r')

Sample output::

    Sensor output: 21.98,71.56,295.13\r
    String: 21.98,71.56,295.13\r\n
    Value: [21.98,71.56,295.13]
    JSON: {"Temp_C":{"value":21.98, "units":"C"}, "Temp_F":{"value":71.56, "units":"F"}, "Temp_K":{"value":295.13, "units":"K"}}
    Read Function Output: {"Temp_C":{"value":21.98, "units":"C"}, "Temp_F":{"value":71.56, "units":"F"}, "Temp_K":{"value":295.13, "units":"K"}}


SerialError
-----------

In case of an exception, errors are thrown either by serial connection errors or invalid data types, SerialSensor can throw these exceptions:

=================== ============ ===========
Exception           Error number Description
------------------- ------------ -----------
Could not connect   0            Could not connect to the serial port during write, read or ancillary operations.
Device not found    1            Port defined could not be foud. Sensor may have been disconnected.
Invalid Data Type   2            Value received from sensor is of non numeric data type, and cannot be converted.
No data read        3            No data present on buffer. May occur if trying to read and no data has been sent.
I/O Error           5            Termios, IOError or OSError errors cause this exception to be thrown. Usually when serial conn. is not working.
Did not receive EOL 6            Exception thrown if string received does not have a line ending character. Assumes data is invalid.
=================== ============ ===========

When thrown, SerialError errors contain the following arguments:

================= ===========
Argument          Description
----------------- -----------
args              (tuple) Descriptor
sensor            (str)   Sensor name as defined during initialization
port              (str)   Port the sensor's connected to
errno             (int)   Error number
function          (str)   Name of the function that raised the exception
msg               (str)   Arbitrary message. Provides further details specific to certain circumstances.
source_exc_info   (type, value, traceback) When available provides the source exeption information that has cause the error.
================= ===========


Method details
--------------

SerialSensor(name, units, serial_port, wait_time, baud_rate=9600, read_command=None, bytesize=8, parity='N', stopbits=1, timeout=5, writeTimeout=5)

``send(command)``: Sends the ``command`` string to the sensor. CR line breaks are assumed if no line ending is provided. Explicitly define the line ending if using one other that CR.

``readRaw()``: Returns the raw string as read from the sensor until the first line ending character. If no line ending character is received, error 6 is thrown.


``readString(mode=CRLF)``: Returns the raw string with a default line ending, set by ``mode``


``readValues()``: Returns a list of numerical values, which correspond to the values read by the sensor. If the string cannot be converted to numerical values, error 2 is thrown.


``readJSON()``: Returns the JSON dictionary with names units and values of the measurements read from the sensor.


``read()``: Executes 3 methods in sequence, first calls ``send(read_command)``, where 'read_command' is the string or function set during initialization; then waits for ``wait_time`` through getWaitTime() amount of time; finally returns the JSON dictionary through ``readJSON()``


``open()``: Opens the serial port. Raises an exception if the port cannot be opened.


``close()``: Closes the serial port.


``getName()``: Returns the ``name`` string.


``isEnabled()`` Returns wether the ``enabled`` flag is True or False


``enable(enable)`` Sets the ``enabled`` flag to the value in the argument.


``getPort()``: Returns the ``port`` string.


``getWaitTime()``: Returns the ``wait_time`` integer.


``getBaud()``: Returns the ``baud_rate`` integer.


``getUnits()``: Returns the ``units`` string.


``getLastString()``: Returns the last raw string read from ``readRaw()``.


``getJSONSettings(_key="", _value="")``: Returns a JSON dictionary with 5 (optionally 6) keys: ``name``, ``units``, ``baud_rate``, ``wait_time``, ``read_command``, and if provided ``_key``.
