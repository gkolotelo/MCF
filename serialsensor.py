from serial import Serial, termios, SerialException
import serial
import time
from serial.tools.list_ports import comports
import traceback
import sys

SerialSensor_version = "1.1 Build 5"

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
        self.errno = errno
        self.port = port
        self.sensor = sensor
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
        self.read_command = read_command
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
        if not self.__connection.isOpen():
            raise SerialError("Could not connect to serial device -> Connection closed.", self.__name, self.__serial_port, 0, 'readRaw()', source_exc_info=sys.exc_info())
        try:
            self.__connection.flushInput()
        except termios.error:
            raise SerialError("Could not connect to serial device -> TERMIOS error.", self.__name, self.__serial_port, 0, 'send()', "flushInput() call", source_exc_info=sys.exc_info())
        command = str(command)  # Gets rid of unicode strings
        if command[-1:] != '\n' or command[-1:] != '\r':  # If line ending not defined, default to CR
            command += '\r'
        time.sleep(0.1)
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
        """readRaw() reads the serial buffer as ASCII characters up to a Carriage Return or Line Feed.
        If no characters are read, a SerialError (Error #3) is raised. If no EOL character
        is received, a SerialError (Error #6) is raised.
        String returned ends with CR or LF, but never CRLF.
        """
        if not self.__connection.isOpen():
            raise SerialError("Could not connect to serial device -> Connection closed.", self.__name, self.__serial_port, 0, 'readRaw()', source_exc_info=sys.exc_info())
        try:
            buff = self.__connection.inWaiting()
        except serial.SerialException, e:
            raise SerialError("Failed reading serial device -> SerialException.", self.__name, self.__serial_port, 0, 'readRaw()', "inWaiting() call " + e.message, source_exc_info=sys.exc_info())
        except termios.error:
            raise SerialError("Could not connect to serial device, TERMIOS error.", self.__name, self.__serial_port, 5, 'readRaw()', "inWaiting() call", source_exc_info=sys.exc_info())
        except IOError:
            raise SerialError("Could not connect to serial device, IOError.", self.__name, self.__serial_port, 5, 'readRaw()', "inWaiting() call", source_exc_info=sys.exc_info())
        except OSError:
            raise SerialError("Could not connect to serial device -> OSError.", self.__name, self.__serial_port, 5, 'readRaw()', "inWaiting() call", source_exc_info=sys.exc_info())
        except Exception, e:
            raise SerialError("Unhandled error.", self.__name, self.__serial_port, 0, 'readRaw()', "inWaiting() call, Error: " + str(e), source_exc_info=sys.exc_info())
        if buff == 0:
            raise SerialError("No data read -> No data on receive buffer.", self.__name, self.__serial_port, 3, 'readRaw()', source_exc_info=sys.exc_info())
        try:
            string = ""
            char = ''
            while char != '\r' and char != '\n':
                if self.__connection.inWaiting() == 0:
                    raise SerialError("Did not receive EOL character, assuming corrupted data.", self.__name, self.__serial_port, 6, 'readRaw()', 'Last character received: "' + char + '"', source_exc_info=sys.exc_info())
                time.sleep(0.01)
                char = self.__connection.read(1)
                time.sleep(0.01)
                string += char
            self.__last_read_string = string
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
        return string


#    def read_hex(self):
#        string = self.readRaw()

    def readString(self, mode=CRLF):  # Available modes CRLF, LF, CR
        string = self.readRaw()
        if string.find('\r') == -1:
            string = ""
        else:
            string = string[:string.find('\r')]
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
        string = self.readString(CRLF)[:-2]
        string = string.replace(' ', '')
        if len(string) == 0:
            return []
        val_list = string.split(',')
        try:
            values = [float(i) for i in val_list]
        except ValueError:
            raise SerialError("Invalid data type received -> Cannot convert to float.", self.__name, self.__serial_port, 2, 'readValues()', 'Invalid string: "' + self.__last_read_string + '"', source_exc_info=sys.exc_info())
        return values

    def readJSON(self):
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

    def read(self):
        # self.close()  # Make sure it's closed, so no errors are thrown
        # self.open()
        if self.read_command is None:
            raise SerialError("Invalid Data Type -> No read_command set, nothing to send.", self.__name, self.__serial_port, 2, 'read()', source_exc_info=sys.exc_info())
        if callable(self.read_command):
            self.send(self.read_command())
        else:
            self.send(self.read_command)
        time.sleep(self.getWaitTime()/1000)
        reading = self.readJSON()
        # self.close()
        return reading

    def getName(self):
        return str(self.__name)

    def open(self):
        try:
            self.__connection.open()
            time.sleep(0.1)
            self.__connection.flushInput()
            time.sleep(0.1)
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
        self.__connection.close()
        time.sleep(0.2)

    def isEnabled(self):
        return self.__enabled

    def enable(self, enable):
        self.__enabled = enable

    def getPort(self):
        return str(self.__serial_port)

    def getWaitTime(self):
        return float(self.__wait_time)

    def getBaud(self):
        return int(self.__baud_rate)

    def getUnits(self):
        return str(self.__units)

    def getLastString(self):
        return str(self.__last_read_string)

    def getJSONSettings(self, name, value):
        if name != "":
            return {"name": self.getName(), "units": self.getUnits(), "wait_time": self.getWaitTime(),
                    "baud_rate": self.getBaud(), name: value}
        else:
            return {"name": self.getName(), "units": self.getUnits(), "wait_time": self.getWaitTime(),
                    "baud_rate": self.getBaud()}
