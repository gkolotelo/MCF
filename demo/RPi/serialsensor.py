from serial import Serial, termios, SerialException
import serial
import time
from serial.tools.list_ports import comports
import traceback
import sys

SerialSensor_version = "1.1 Build 8"

CRLF = 0
CR = 1
LF = 2


def listPorts():
    return comports()

# ERROR NUMBERS:
# #0: Could not connect
# #1: Device not found
# #2: Invalid Data Type
# #3: No data read
# #5: I/O error
# #6: Did not receive EOL character, assuming corrupted data. (/r or /n or /r/n)


class SerialError(Exception):
    def __init__(self,
                 arg='Unknown SerialError',
                 sensor='N/D',
                 port='N/D',
                 errno=None,
                 function="",
                 msg='',
                 source_exc_info=None):
        self.args = (arg,)
        self.sensor = sensor
        self.port = port
        self.errno = errno
        self.function = function
        self.msg = msg
        self.source_exc_info = source_exc_info

    def __str__(self):
        if self.msg == '':
            return repr('SerialSensor Error: ' + self.args[0] + ' Sensor: "' + self.sensor +
                        '" @ "' + self.port + '", Errno ' + str(self.errno) + ", Method: " + self.function)
        else:
            return repr('SerialSensor Error: ' + self.args[0] + ' Sensor: "' + self.sensor + '" @ "' + self.port
                        + '", Errno ' + str(self.errno) + ", Method: " + self.function + ", Message:" + self.msg)

    def SourceTraceback(self):
        if self.source_exc_info is None:
            return None
        exc = traceback.format_exception(self.source_exc_info[0], self.source_exc_info[1], self.source_exc_info[2])
        text = ''
        for i in exc:
            text += i.replace("'", '"')
        return text


class SerialSensor:
    def __init__(self, name, units, serial_port, wait_time,
                 baud_rate=9600,
                 read_command=None,
                 bytesize=8,
                 parity='N',
                 stopbits=1,
                 timeout=5,
                 writeTimeout=5
                 ):
        """
        Instatiates a sensor.

        Notes:
            - The default baudrate is 9600bps


        Required Arguments:
            name (str): Name of the sensor/measurements (e.g. 'Temperature,Humidity').
            units (str): Units of the sensor/measurements (e.g. 'C,RH').
            serial_port (str): Serial port of the sensor (e.g. /dev/ttyUSBx).
            wait_time (int): Time to wait for response (in milliseconds).
            read_command (object or str): Function returning a string, or string, to be sent to sensor, if
            none defined read() method cannot be used. (e.g. lambda: 'R', or 'R').

        Optional Arguments:
            baud_rate (int): Baud rate of sensor (Default 9600).
            bytesize (int): Default 8
            parity (str): Default 'N'
            stopbits (int): Default 1
            timeout (int): Default 5 seconds
            writeTimeout (int): Default 5 seconds

        Exceptions:
            Handles SerialException, SerialTimeoutException, TERMIOS errors, I.OError and OSError, and returns
            SerialErrors #0 (Cannot connect to device) or #5 (I/O Error).

            If an Unknown exception is raised, SerialError #0 is raised.
        """
        self.__serial_port = serial_port
        self.__baud_rate = baud_rate
        self.__name = name.replace(' ', '')
        self.__readings = 0.00
        self.__units = units.replace(' ', '')
        self.__wait_time = wait_time
        self.__last_read_string = ""
        self.__enabled = True
        self.__timeout = timeout
        self.__writeTimeout = writeTimeout
        self.__parity = parity
        self.__stopbits = stopbits
        self.__bytesize = bytesize
        self.__read_command = read_command
        try:
            self.__connection = Serial(serial_port, baud_rate, bytesize=bytesize, parity=parity,
                                       stopbits=stopbits, timeout=timeout, writeTimeout=writeTimeout)
            self.__connection.write('\r')  # Sometimes first commands are read as error, this prevents that

        except serial.SerialException, e:
            raise SerialError("Could not connect to serial device during initialization.", self.__name, self.__serial_port, 0, 'SerialSensor()', e.message, source_exc_info=sys.exc_info())
        except termios.error:
            raise SerialError("Could not connect to serial device -> TERMIOS error during initialization.", self.__name, self.__serial_port, 5, 'SerialSensor()', source_exc_info=sys.exc_info())
        except IOError, e:
            raise SerialError("Could not connect to serial device -> IOError during initialization.", self.__name, self.__serial_port, 5, 'SerialSensor()', source_exc_info=sys.exc_info())
        except OSError, e:
            raise SerialError("Could not connect to serial device -> OSError during initialization.", self.__name, self.__serial_port, 5, 'SerialSensor()', source_exc_info=sys.exc_info())
        except Exception, e:
            raise SerialError("Unhandled error during initialization.", self.__name, self.__serial_port, 0, 'SerialSensor()', "Error: " + str(e), source_exc_info=sys.exc_info())
        except:
            raise SerialError("Unknown exception during initialization.", self.__name, self.__serial_port, 0, 'SerialSensor()', source_exc_info=sys.exc_info())
        time.sleep(0.3)  # Wait for receive buffer to fill
        self.__connection.flushInput()
        self.__connection.flushInput()
        time.sleep(0.1)

#    def send_hex(self, command):
#        self.__connection.flushInput()
#        time.sleep(0.1)
#        try:
#            self.__connection.write(command)
#        except serial.SerialTimeoutException:
#            raise SerialError("Timeout on device", self.__name, self.__serial_port, 0, source_exc_info=sys.exc_info())

    def send(self, command):
        """
        Sends through the serial connection the string 'command' and returns nothing.

        If no line ending (CR, LF or CRLF) is provided, the CR line ending ('\r') is appended to 'command' by default.

        Args:
            command (str): ASCII string to be sent through the serial connection.

        Exceptions:
            Handles SerialException, SerialTimeoutException, TERMIOS errors, IOError and OSError, and returns
            SerialErrors #0 (Cannot connect to device) or #5 (I/O Error).
        """
        if not self.__connection.isOpen():
            raise SerialError("Could not connect to serial device -> Connection closed.", self.__name, self.__serial_port, 0, 'send()', source_exc_info=sys.exc_info())
        try:
            self.__connection.flushInput()
            time.sleep(0.15)
        except termios.error:
            raise SerialError("Could not connect to serial device -> TERMIOS error.", self.__name, self.__serial_port, 0, 'send()', "flushInput() call", source_exc_info=sys.exc_info())
        command = str(command)  # Gets rid of unicode strings
        if command[-1:] != '\n' or command[-1:] != '\r':  # If line ending not defined, default to CR
            command += '\r'
        try:
            self.__connection.write(command)
        except serial.SerialTimeoutException:
            raise SerialError("Timeout on device", self.__name, self.__serial_port, 0, 'send()', "write() call", source_exc_info=sys.exc_info())
        except serial.SerialException, e:
            raise SerialError("Could not connect to serial device -> SerialException.", self.__name, self.__serial_port, 0, 'send()', "write() call " + e.message, source_exc_info=sys.exc_info())
        except termios.error:
            raise SerialError("Could not connect to serial device, TERMIOS error.", self.__name, self.__serial_port, 5, 'send()', "write() call", source_exc_info=sys.exc_info())
        except IOError:
            raise SerialError("Could not connect to serial device -> IOError.", self.__name, self.__serial_port, 5, 'send()', "write() call", source_exc_info=sys.exc_info())
        except OSError:
            raise SerialError("Could not connect to serial device -> OSError.", self.__name, self.__serial_port, 5, 'send()', "write() call", source_exc_info=sys.exc_info())

    def readRaw(self):
        """
        Reads all the available serial buffer as ASCII characters and returns it.

        Exceptions:
            Handles SerialException, SerialTimeoutException, TERMIOS errors, IOError and OSError, and returns
            SerialErrors #0 (Cannot connect to device) or #5 (I/O Error).

        If an Unknown exception is raised, SerialError #0 is raised.
        """
        string = ''
        if not self.__connection.isOpen():
            raise SerialError("Could not connect to serial device -> Connection closed.", self.__name, self.__serial_port, 0, 'readRaw()', source_exc_info=sys.exc_info())
        try:
            string = self.__connection.read(self.__connection.inWaiting())
            self.__last_read_string = string
            return string
        except serial.SerialTimeoutException:
            raise SerialError("Timeout on device -> SerialTimeoutException.", self.__name, self.__serial_port, 0, 'readRaw()', source_exc_info=sys.exc_info())
        except serial.SerialException, e:
            raise SerialError("Failed reading serial device -> SerialException.", self.__name, self.__serial_port, 0, 'readRaw()', e.message, source_exc_info=sys.exc_info())
        except termios.error:
            raise SerialError("Could not connect to serial device -> TERMIOS error.", self.__name, self.__serial_port, 5, 'readRaw()', source_exc_info=sys.exc_info())
        except IOError:
            raise SerialError("Could not connect to serial device -> IOError.", self.__name, self.__serial_port, 5, 'readRaw()', source_exc_info=sys.exc_info())
        except OSError:
            raise SerialError("Could not connect to serial device -> OSError.", self.__name, self.__serial_port, 5, 'readRaw()', source_exc_info=sys.exc_info())
        except Exception, e:
            raise SerialError("Unhandled error.", self.__name, self.__serial_port, 0, 'readRaw()', "Error: " + str(e), source_exc_info=sys.exc_info())


    #def readRaw_old(self):
    #    """readRaw() reads the serial buffer as ASCII characters up to a Carriage Return or Line Feed.
    #    If no characters are read, a SerialError (Error #3) is raised. If no EOL character
    #    is received, a SerialError (Error #6) is raised.
    #    String returned ends with CR or LF, but never CRLF.
    #    """
    #    if not self.__connection.isOpen():
    #        raise SerialError("Could not connect to serial device -> Connection closed.", self.__name, self.__serial_port, 0, 'readRaw()', source_exc_info=sys.exc_info())
    #    try:
    #        buff = self.__connection.inWaiting()
    #    except serial.SerialException, e:
    #        raise SerialError("Failed reading serial device -> SerialException.", self.__name, self.__serial_port, 0, 'readRaw()', "inWaiting() call " + e.message, source_exc_info=sys.exc_info())
    #    except termios.error:
    #        raise SerialError("Could not connect to serial device, TERMIOS error.", self.__name, self.__serial_port, 5, 'readRaw()', "inWaiting() call", source_exc_info=sys.exc_info())
    #    except IOError:
    #        raise SerialError("Could not connect to serial device, IOError.", self.__name, self.__serial_port, 5, 'readRaw()', "inWaiting() call", source_exc_info=sys.exc_info())
    #    except OSError:
    #        raise SerialError("Could not connect to serial device -> OSError.", self.__name, self.__serial_port, 5, 'readRaw()', "inWaiting() call", source_exc_info=sys.exc_info())
    #    except Exception, e:
    #        raise SerialError("Unhandled error.", self.__name, self.__serial_port, 0, 'readRaw()', "inWaiting() call, Error: " + str(e), source_exc_info=sys.exc_info())
    #    if buff == 0:
    #        raise SerialError("No data read -> No data on receive buffer.", self.__name, self.__serial_port, 3, 'readRaw()', source_exc_info=sys.exc_info())
    #    try:
    #        string = ""
    #        char = ''
    #        while char != '\r' and char != '\n':
    #            if self.__connection.inWaiting() == 0:
    #                raise SerialError("Did not receive EOL character, assuming corrupted data.", self.__name, self.__serial_port, 6, 'readRaw()', 'Last character received: "' + char + '"', source_exc_info=sys.exc_info())
    #            time.sleep(0.01)
    #            char = self.__connection.read(1)
    #            time.sleep(0.01)
    #            string += char
    #        self.__last_read_string = string
    #    except serial.SerialTimeoutException:
    #        raise SerialError("Timeout on device -> SerialTimeoutException.", self.__name, self.__serial_port, 0, 'readRaw()', source_exc_info=sys.exc_info())
    #    except serial.SerialException, e:
    #        raise SerialError("Failed reading serial device -> SerialException.", self.__name, self.__serial_port, 0, 'readRaw()', e.message, source_exc_info=sys.exc_info())
    #    except termios.error:
    #        raise SerialError("Could not connect to serial device -> TERMIOS error.", self.__name, self.__serial_port, 5, 'readRaw()', source_exc_info=sys.exc_info())
    #    except IOError:
    #        raise SerialError("Could not connect to serial device -> IOError.", self.__name, self.__serial_port, 5, 'readRaw()', source_exc_info=sys.exc_info())
    #    except OSError:
    #        raise SerialError("Could not connect to serial device -> OSError.", self.__name, self.__serial_port, 5, 'readRaw()', source_exc_info=sys.exc_info())
    #    except Exception, e:
    #        raise SerialError("Unhandled error.", self.__name, self.__serial_port, 0, 'readRaw()', "Error: " + str(e), source_exc_info=sys.exc_info())
    #    return string


#    def read_hex(self):
#        string = self.readRaw()

    def readString(self, mode=CRLF):  # Available modes CRLF, LF, CR
        """
        Calls readRaw() and conditions the string befor returning.
        If the string is empty, a SerialError (Error #3) is raised.
        If no EOL character is received, a SerialError (Error #6) is raised.
        EOL from original string gets replaced by EOL set in the mode option.

        Args:
            mode (int): Line ending mode:
                    0: CRLF
                    1: CR
                    2: LF

        Exceptions:
            Does not handle any exceptions.
            Throws SerialError #3 if string received from readRaw() has zero lenght.
            Throws SerialError #6 if no line ending character has been received, assumes that data has is corrupted.
        """
        string = self.readRaw()
        if len(string.replace('\r', '').replace('\n', '')) == 0:
            raise SerialError("No data read -> No data on receive buffer.", self.__name, self.__serial_port, 3, 'readString()')
        cr = string.find('\r')
        lf = string.find('\n')
        if cr != -1:
            string = string[:cr]
        elif lf != -1:
            string = string[:lf]
        else:
            raise SerialError("Did not receive EOL character, assuming corrupted data.", self.__name, self.__serial_port, 6, 'readString()', 'String received: "' + string + '"', source_exc_info=sys.exc_info())
        if mode == CR:
            string += '\r'
        elif mode == LF:
            string += '\n'
        else:
            string += '\r\n'  # use CRLF as default
        return string

#    def check_connection(self, repair=False):
#        result = self.__connection.isOpen()
#        if not repair:
#            return result
#        if result:
#            return result
#        try:
#            self.__connection.open()
#            time.sleep(0.3)
#            if self.__connection.isOpen():
#                return True
#        except:
#            pass
#        self.__connection.close()
#        time.sleep(0.7)
#        try:
#            self.__connection = Serial(self.__serial_port, self.__baud_rate, self.__bytesize, self.__parity,
#                                       self.__stopbits, self.__timeout, self.__writeTimeout)
#            time.sleep(0.3)
#            self.__connection.write('\r')
#            time.sleep(0.3)
#        except serial.SerialException:
#            return False
#        except serial.SerialTimeoutException:
#            return False
#        except termios.error:
#            return False
#        except OSError:
#            return False
#        return self.__connection.isOpen()
#
#    def repair_connection(self, errno):
#        if errno == 0:
#            result = self.__connection.isOpen()
#            # Simply try again
#            if result:
#                return result
#        elif errno == 1:
#            pass
#        elif errno == 2:
#            pass
#        elif errno == 3:
#            pass
#        elif errno == 5:
#            pass

    def readValues(self):
        """
        Returns a float or a list of floats representing the numeric values in the string returned from readString().

        Exceptions:
            If there is a ValueError, readValues raises a SerialError #2 (Invalid Data Type).
        """
        string = self.readString(CRLF)[:-2]
        string = string.replace(' ', '')
        if len(string) == 0:
            return []
        val_list = string.split(',')
        try:
            values = [float(i) for i in val_list]
        except ValueError:
            raise SerialError("Invalid data type received -> Cannot convert to float.",
                              self.__name, self.__serial_port,
                              2,
                              'readValues()',
                              'Invalid string: "' + string + '"' + ', Original raw string: "' + self.__last_read_string + '"',
                              source_exc_info=sys.exc_info()
                              )
        return values

    def readJSON(self):
        """
        Returns a JSON dictionary with the measurements taken:

            {'name1': {'units':'u1', 'value': '1.0'}, 'name2': {'units':'u3', 'value': '2.0'}, ...}

        The "names" and "units" are single measurement names/units or comma separated names/units, like so:

            names = "pH"  ;  units = "N/A"
        or
            names = "Temperature,Humidity,CO2"  ;  units = "C,RH,ppm"

        And so, the number of comma separated names and units must be the same, so as to create the
        corresponding pairs of name/unit/value, if the provided comma separated names and units are
        not paired, readJSON() will pair the smallest number of either names or units provided.
        Likewise, if the number of values available from readValues is smaller than the number of
        either names or units provided, the measurements will be paired for only the available values.

        Note that this can cause incorrect measurement values to be associated to names and units if
        these have not been initialized properly and/or in the same order as the values are read from the
        sensor, for example:

            Sensor output:  "25.3,36.6,443"
            measurements: Temperature in Celsius followed by Humidity in RH followed by CO2 in ppm.

            values = [25.3, 36.6, 443]
            names = "Temperature,Humidity,CO2"
            units = "C,RH,ppm"

            Final JSON dictionary:

                {
                "Temperature": {"value": 25.3, "units": "C"},
                "Humidity": {"value": 36.6, "units": "RH"},
                "CO2": {"value": 443, "units": "ppm"}
                }

            Note that names and units form their respective pairs in the same order as the values are read
            from the sensor, as well as there are the same number of names, units and values available to
            be paired, in this example, 3.
        """
        names = self.getName().split(',')
        units = self.getUnits().split(',')
        values = self.readValues()
        json_dict = {}
        if (len(values) > len(names)):
            x = len(names)
        elif (len(values) > len(units)):
            x = len(units)
        else:
            x = len(values)
        for i in range(x):
            json_dict.update({names[i]: {"value": values[i], "units": units[i]}})
        return json_dict

    def read(self, forced_command=None):
        """
        Executes 3 commands in sequence:
            1. Sends read_command to the serial device
            2. Waits for wait_time milliseconds.
            3. Reads and returns JSON dictionary of values, names and units.

        Note that read_command must have been defined when the sensor was initialized.

        Args:
            forced_command (str or function): If set, forces read() to use the provided command in place of
            the default read_command set when initialized.

        Exceptions:
            Raises SerialError #2 if read_command has not been defined when initialized.

        """
        if forced_command is None:
            command = self.__read_command
        else:
            command = forced_command
        if command is None:
            raise SerialError("Invalid Data Type -> No read_command set, nothing to send.", self.__name, self.__serial_port, 2, 'read()', source_exc_info=sys.exc_info())
        if callable(command):
            self.send(command())
        else:
            self.send(command)
        time.sleep(self.getWaitTime()/1000)
        reading = self.readJSON()
        # self.close()
        return reading

    def open(self):
        """
        Opens the serial connection.

        Exceptions:
            Handles SerialException, SerialTimeoutException, TERMIOS errors, IOError and OSError, and returns
            SerialErrors #0 (Cannot connect to device) or #5 (I/O Error).

            If an Unknown exception is raised, SerialError #0 is raised.
        """
        try:
            self.__connection.open()
            time.sleep(0.4)
            self.__connection.flushInput()
            time.sleep(0.4)
        except serial.SerialTimeoutException:
            raise SerialError("Timeout on device -> SerialTimeoutException.", self.__name, self.__serial_port, 0, 'open()', source_exc_info=sys.exc_info())
        except SerialException, e:
            raise SerialError("Could not connect to serial device -> SerialException.", self.__name, self.__serial_port, 0, 'open()', e.message, source_exc_info=sys.exc_info())
        except termios.error:
            raise SerialError("Could not connect to serial device -> TERMIOS error.", self.__name, self.__serial_port, 5, 'open()', source_exc_info=sys.exc_info())
        except IOError:
            raise SerialError("Could not connect to serial device -> IOError.", self.__name, self.__serial_port, 5, 'open()', source_exc_info=sys.exc_info())
        except OSError:
            raise SerialError("Could not connect to serial device -> OSError.", self.__name, self.__serial_port, 5, 'open()', source_exc_info=sys.exc_info())
        except Exception, e:
            raise SerialError("Unhandled error.", self.__name, self.__serial_port, 0, 'open()', "Error: " + str(e), source_exc_info=sys.exc_info())
        except:
            raise SerialError("Unknown exception.", self.__name, self.__serial_port, 0, 'open()', source_exc_info=sys.exc_info())

    def close(self):
        """
        Closes the serial connection.
        """
        self.__connection.close()
        time.sleep(0.2)

    def isEnabled(self):
        """
        Returns True if the 'enabled' flag is True, returns False otherwise.
        """
        return self.__enabled

    def enable(self, enable):
        """
        Sets the 'enabled' flag.

        Args:
            enable (bool): Boolean value to which the 'enabled' flag will be set.
        """
        self.__enabled = enable

    def getName(self):
        """
        Returns string corresponding to the name of the sensor as defined during initialization.
        """
        return str(self.__name)

    def getPort(self):
        """
        Returns string corresponding to the port of the sensor as defined during initialization.
        """
        return str(self.__serial_port)

    def getWaitTime(self):
        """
        Returns numeric value corresponding to the wait_time of the sensor as defined during initialization.
        """
        return float(self.__wait_time)

    def getReadCommand(self):
        """
        Returns string or function or None type (default) corresponding to the read_command of the sensor
        as defined during initialization.
        """
        return self.__read_command

    def getBaud(self):
        """
        Returns numeric value corresponding to the baud_rate of the sensor as defined during initialization.
        """
        return int(self.__baud_rate)

    def getUnits(self):
        """
        Returns string corresponding to the units of the sensor as defined during initialization.
        """
        return str(self.__units)

    def getLastString(self):
        """
        Returns string corresponding to the last string read by readRaw().
        """
        return str(self.__last_read_string)

    def getJSONSettings(self, _key="", _value=""):
        """
        Returns JSON dictionary with all of the arguments set during initialization.

        Args:
            _key (str) and _value (any): If set, this custom key/value entry will be included in the
            dictionary that will be returned.
        """
        if _key != "":
            return {"name": self.getName(), "units": self.getUnits(), "wait_time": self.getWaitTime(),
                    "baud_rate": self.getBaud(), "read_command": self.__read_command, _key: _value}
        else:
            return {"name": self.getName(), "units": self.getUnits(), "wait_time": self.getWaitTime(),
                    "baud_rate": self.getBaud(), "read_command": self.__read_command}
