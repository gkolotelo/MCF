from serial import Serial, termios
import serial
import time
from serial.tools.list_ports import comports

# version = "0.8 Build 3"

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
# #5: Termios I/O error (used for repair)
# #6: Did not receive EOL character, assuming corrupted data. (/r or /n or /r/n)


class SerialError(Exception):
    def __init__(self, arg='Unknown SerialError', sensor='N/D', port='N/D', errno=None, msg=''):  # Changed errno=0
        self.args = (arg,)
        self.errno = errno
        self.port = port
        self.sensor = sensor
        self.msg = msg

    def __str__(self):
        return repr('SerialSensor Error: ' + self.args[0] + ' Sensor: "' + self.sensor +
                    '" @ "' + self.port + '" errno ' + str(self.errno) + self.msg)


class SerialSensor:
    def __init__(self, name, units, serial_port, wait_time,
                 baud_rate=38400, read_command=None, bytesize=8,
                 parity='N', stopbits=1, timeout=5, writeTimeout=5):
        """ Instatiates a sensor

        Required Arguments:
        name -- Name of the sensor/measurements (e.g. 'Temperature,Humidity').
        units -- Units of the sensor/measurements (e.g. 'C,RH').
        serial_port -- Serial port of the sensor (e.g. /dev/ttyUSBX).
        wait_time -- Time to wait for response (in milliseconds).
        read_command -- Function returning one string to be sent to sensor, if\
        none defined read() method cannot be used. (e.g. lambda: 'R').

        Optional Arguments:
        baud_rate -- Baud rate of sensor (default 38400).
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
        except serial.SerialException:
            raise SerialError("Could not connect to serial device", self.__name, self.__serial_port, 0)
        except serial.SerialTimeoutException:
            raise SerialError("Timeout on device", self.__name, self.__serial_port, 0)
        time.sleep(0.3)  # Wait for receive buffer to fill
        self.__connection.flushInput()
        self.__connection.flushInput()
        time.sleep(0.1)

    def send_hex(self, command):
        self.__connection.flushInput()
        time.sleep(0.1)
        try:
            self.__connection.write(command)
        except serial.SerialTimeoutException:
            raise SerialError("Timeout on device", self.__name, self.__serial_port, 0)

    def send(self, command):
        self.__connection.flushInput()
        if command[-1:] == '\n':
            command = command[:-1]
        if not command[-1:] == '\r':
            command += '\r'
        time.sleep(0.1)
        try:
            self.__connection.write(command)
        except serial.SerialTimeoutException:
            raise SerialError("Timeout on device", self.__name, self.__serial_port, 0, "serialsensor.send()")

    def readRaw(self):
        """readRaw() reads the serial buffer as ASCII characters up to a carriage return.
        If no character are read, a SerialError (Error #3) is raised.
        """
        if not self.__connection.isOpen():
            raise SerialError("Could not connect to serial device -> Connection closed.", self.__name, self.__serial_port, 0, 'readRaw()')
        try:
            buff = self.__connection.inWaiting()
        except:
            raise SerialError("Failed reading serial device.", self.__name, self.__serial_port, 0, 'readRaw()')
        if buff == 0:
            raise SerialError("No data read -> No data on receive buffer.", self.__name, self.__serial_port, 3, 'readRaw()')
        try:
            string = ""
            char = ''
            while char != '\r' and char != '\n':
                if self.__connection.inWaiting() == 0:
                    raise SerialError("Did not receive EOL character, assuming corrupted data.", self.__name,
                                      self.__serial_port, 6, ('Last character received: "' + char + '"' + 'readRaw()'))
                time.sleep(0.01)
                char = self.__connection.read(1)
                time.sleep(0.01)
                string += char
            self.__last_read_string = string
        except serial.SerialTimeoutException:
            raise SerialError("Timeout on device", self.__name, self.__serial_port, 0, 'readRaw()')
        except serial.SerialException:
            raise SerialError("Failed reading serial device.", self.__name, self.__serial_port, 0, 'readRaw()')
        return string

    def read_hex(self):
        string = self.readRaw()

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

    def check_connection(self, repair=False):
        result = self.__connection.isOpen()
        if not repair:
            return result
        if result:
            return result
        try:
            self.__connection.open()
            time.sleep(0.3)
            if self.__connection.isOpen():
                return True
        except:
            pass
        self.__connection.close()
        time.sleep(0.7)
        try:
            self.__connection = Serial(self.__serial_port, self.__baud_rate, self.__bytesize, self.__parity,
                                       self.__stopbits, self.__timeout, self.__writeTimeout)
            time.sleep(0.3)
            self.__connection.write('\r')
            time.sleep(0.3)
        except serial.SerialException:
            return False
        except serial.SerialTimeoutException:
            return False
        except termios.error:
            return False
        except OSError:
            return False
        return self.__connection.isOpen()

    def repair_connection(self, errno):
        if errno == 0:
            result = self.__connection.isOpen()
            # Simply try again
            if result:
                return result
        elif errno == 1:
            pass
        elif errno == 2:
            pass
        elif errno == 3:
            pass
        elif errno == 5:
            pass



    def readValues(self):
        string = self.readString(CRLF)[:-2]
        string = string.replace(' ', '')
        if len(string) == 0:
            return []
        val_list = string.split(',')
        try:
            values = [float(i) for i in val_list]
        except ValueError:
            raise SerialError("Invalid data type", self.__name, self.__serial_port, 2, ('Invalid string: "' + self.__last_read_string + '"'))
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
        #self.close()  # Make sure it's closed, so no errors are thrown
        #self.open()
        self.send(self.read_command())
        time.sleep(self.getWaitTime()/1000)
        reading = self.readJSON()
        #self.close()
        return reading

    def getName(self):
        return str(self.__name)

    def open(self):
        try:
            self.__connection.open()
            time.sleep(0.05)
        except:
            raise SerialError("Could not connect to serial device", self.__name, self.__serial_port, 0)

    def close(self):
        self.__connection.close()

    def isEnabled(self):
        return self.__enabled

    def enable(self, enable):
        self.__enabled = enable

    def getPort(self):
        return str(self.__serial_port)

    def getWaitTime(self):
        return self.__wait_time

    def getBaud(self):
        return self.__baud_rate

    def getUnits(self):
        return str(self.__units)

    def getLastString(self):
        return self.__last_read_string

    def getJSONSettings(self, name, value):
        return {"name": self.getName(), "units": self.getUnits(), "wait_time": self.getWaitTime(),
                "baud_rate": self.getBaud(), name: value}
