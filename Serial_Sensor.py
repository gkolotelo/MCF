from serial import Serial
from serial.tools.list_ports import comports

CRLF = 0
CR = 1
LF = 2

class SerialSensor:
	def __init__(self, name, serial_port, baud_rate=38400):
		self.__serial_port = serial_port
		self.__baud_rate = baud_rate
		self.__name = name
		self.__readings = 0.00
		self.__units = 'N/A'
		self.su__connection = Serial(serial_port, baud_rate, timeout=5, writeTimeout=5)#, parity=PARITY_NONE, stopbits=STOPBITS_ONE, bytesize=EIGHTBITS)


	def send(self,command):
		if command[-1:] == '\n':
			command = command[:-1]
		if not command[-1:] == '\r':
			command+='\r'
		return self.__connection.write(command)#Returns number of written characters

	def readRaw(self, mode=CRLF):#Available modes CRLF, LF, CR
		string = ""
		try:
			if self.__connection.inWaiting() == 0: return ""
			while char != '\r':
				char = __connection.read(1, timeout=5)
				string += char
			#"old"#string = (__connection.read(__connection.inWaiting())) #read characters available in buffer	
		except:
			return "error: Could not read sensor: " + __name
		string = string[:string.find('\r')]
		if mode == CR:
			string += '\r'
		elif mode == LF:
			string += '\n'
		else:
			string += '\r\n' # use CRLF as default
		return string

	def check_connection(self, repair=False):
		result = self.__connection.isOpen()
		if not repair:
			return result
		if result:
			return result
		try:
			self.__connection.open()
			return self.__connection.isOpen()
		except:
			return self.__connection.isOpen()
			
	def read(self):
		string = readRaw(CRLF)

		#more to implement

	def getName(self):
		return self.__name

	def getUnits(self):
		return self.__units

	#def getEntry(self):
	#	return {__name:{"value":float()}} give more thought
