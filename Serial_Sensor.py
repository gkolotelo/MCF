from serial import Serial
import serial
#import usb
import time
from serial.tools.list_ports import comports

CRLF = 0
CR = 1
LF = 2

def listPorts():
    return comports()

# def getAvailableIDs(baud_rate):
#     ports = listPorts()
#     ret_dict = {}
#     ids = []
#     string = ""
#     for i in ports:
#         conn = Serial(i, baud_rate, timeout=5, writeTimeout=5)
#         conn.write('I\r')
#         conn.flushInput()
#         conn.write('I\r')
#         if conn.inWaiting() != 0:
#             try:
#                 while char != '\r':
#                     if conn.inWaiting() == 0: return ""
#                     char = conn.read(1)
#                     string += char
#                 ids.append(string)
#                 string = ""
#                 conn.flushInput()
#     for i in ids:
#         ret_dict[i] = ports[ports.find(i)]
#.............................................


#ERROR NUMBERS:
#0: Could not connect
#1: Device not found
#2: Invalid Data Type
class SerialError(Exception):
    def __init__(self, arg='Serial Exception',sensor = '', port='', errno=0):
        self.args = arg
        self.errno = errno
        self.port = port
        self.sensor = sensor
    def __str__(self):
        return repr('Serial sensor exception @ ' + self.sensor + " on " + self.port)


class SerialSensor:
    def __init__(self, name, units, serial_port, wait_time, baud_rate=38400):
        self.__serial_port = serial_port
        self.__baud_rate = baud_rate
        self.__name = name
        self.__readings = 0.00
        self.__units = units
        self.__wait_time = wait_time
        self.__last_read_string = ""
        self.__enabled = True
        try: 
            self.__connection = Serial(serial_port, baud_rate, timeout=5, writeTimeout=5)#, parity=PARITY_NONE, stopbits=STOPBITS_ONE, bytesize=EIGHTBITS)
            self.__connection.write('\r')#Sometimes first commands are read as error, this prevents that
        except serial.SerialException, e:
            raise SerialError("Could not connect to serial device", self.__name, self.__serial_port, 0)
        except serial.SerialTimeoutException:
            raise SerialError("Timeout on device", self.__name, self.__serial_port, 0)
        time.sleep(0.3)#Wait for receive buffer to fill
        self.__connection.flushInput()
        self.__connection.flushInput()


    def send(self,command):
        if command[-1:] == '\n':
            command = command[:-1]
        if not command[-1:] == '\r':
            command+='\r'
        self.__connection.flushInput()
        try:
            self.__connection.write(command)
        except serial.SerialTimeoutException:
            raise SerialError("Timeout on device", self.__name, self.__serial_port, 0)

    def readRaw(self):
        try:
            string = ""
            char = ''
            while char != '\r':
                if self.__connection.inWaiting() == 0: return ""
                char = self.__connection.read(1)
                string += char
            return string
            #"old"#string = (__connection.read(__connection.inWaiting())) #read characters available in buffer  
        except:
            raise SerialError("Could not read sensor.", self.__name, self.__serial_port, 0)

    def readString(self, mode=CRLF):#Available modes CRLF, LF, CR
        self.__last_read_string = ""
        string = self.readRaw()
        string = string[:string.find('\r')]
        if mode == CR:
            string += '\r'
        elif mode == LF:
            string += '\n'
        else:
            string += '\r\n' # use CRLF as default
        self.__connection.flushInput()
        self.__last_read_string = string
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
        except serial.SerialException:
            pass
        self.__connection.close()
        del __connection
        time.sleep(0.7)
        try:
            self.__connection = Serial(self.__serial_port, self.__baud_rate, timeout=5, writeTimeout=5)
            time.sleep(0.3)
            self.__connection.write('\r')
            time.sleep(0.3)
        except serial.SerialException:
            return False
        except serial.SerialTimeoutException:
            return False
        return self.__connection.isOpen()

            
    def readValues(self):
        if self.check_connection() == False:
            raise SerialError("Could not connect to serial device", self.__name, self.__serial_port, 0)
        string = self.readString(CRLF)
        if string == "":return []
        val_list = string.replace(' ','').split(',')
        try:
            values = [ float(i) for i in val_list]
        except ValueError, e:
            raise SerialError("Ivalid data type", self.__name, self.__serial_port, 2)
        return values
        
    def readJSON(self):
        names = self.getName().replace(' ','').split(',')
        units = self.getUnits().replace(' ','').split(',')
        values = self.readValues()
        json_dict = {}
        if (len(values) > len(names)): x = len(names)
        elif (len(values) > len(units)): x = len(units)
        else: x = len(values)
        for i in range(x):
            json_dict.update({names[i]:{"value":values[i], "units":units[i]}})
        return json_dict

    def getName(self):
        return str(self.__name)

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
        return str(self.__last_read_string)

    def getJSONSettings(self, name, value):
        return {"name":self.getName(), "units":self.getUnits(), "wait_time":self.getWaitTime(), "baud_rate":self.getBaud(), name:value}

