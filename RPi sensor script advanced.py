import datetime
from serial.tools.list_ports import comports
from pymongo import MongoClient
import sys
import time
from Serial_Sensor import SerialSensor

sensors = []# array to hold the sensor objects

#Settings:
db_name = 'test'
board_name = 'Hydro_Water_Sensors'
mongo_server = '192.168.1.3'#18.85.58.53'
sensor_reading_frequency = 5 #sensor reading frequency in seconds

print "Using default settings:\nBoard Name: " + board_name +  "\nMongo Server: " + mongo_server + "\nDB name: " + db_name + '\n'

available_ports = comports()

if len(available_ports) == 0:
	print "No COM ports found. Aborting..."
	sys.exit()
else:
	i = 0
	for ports in comports():
		print "({})".format(i), ports[0]
		i += 1

print "You can make several selections, just type the number of the port, press enter, type the name of the sensor, press enter, and repeat. When you're done, just press enter"
print "example \n", "0 \nSensor 1 \n[Enter]"

while True:
	number = raw_input("Type a port number:")
	if (number == ''):
		print "Continuing..."
		break
	name = raw_input("Type the sensor name:")
	sensors.append(SerialSensor(name,comports()[int(number)][0]))

print "Available sensors:"
for i in sensors: print i.getName()







































