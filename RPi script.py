from serial import Serial
from serial.tools.list_ports import comports
import datetime
from pymongo import MongoClient
import sys
import time

#Settings:
db_name = 'test'
board_name = 'Hydro_Water_Sensors'
mongo_server = '192.168.1.3'#18.85.58.53'
sensor_reading_frequency = 5 #sensor reading frequency in seconds
#Comment line below to enable port picker, or set default port in code
default_serial_port = '/dev/ttyUSB0'

print "Using default settings:\nBoard Name: " + board_name +  "\nMongo Server: " + mongo_server + "\nDB name: " + db_name + '\n'


try:
    default_serial_port
    print "Using default serial port :", default_serial_port
except:
    print "No serial port is predefined"

    available_ports = comports()
    
    if len(available_ports) == 0:
        print "No COM ports found. Aborting..."
        sys.exit()
    else:
        i = 0
        for ports in comports():
            print "({})".format(i), ports[0]
            i += 1
        res = raw_input("Choose a port number:")
        port = comports()[int(res)][0]
        print "Opening port: ", port
  
#Open serial port    
try:
    DO_serial = Serial(port, 38400, timeout=5)

except:
    print "Error opening serial port, try again"
    sys.exit(0)

#Connect to MongoDB Server
print "Conecting to Mongo server"
try :
    client = MongoClient(mongo_server)
    db = client[db_name]
    collection = db[board_name]
    print "Connected to ", collection.full_name
except:
    print 'Could not connect to Mongo at: "' + mongo_server + '" on database "' + db_name + "." + board_name + '"'
    sys.exit(0)



# ser.flushInput() #flush corrupted data, if there's any
# for line in ser:
#     print line
#     line = line[0:-2] # Remove trailing /r/n
#     line = line.rsplit(',')
#     num_sensors = len(line)/3
#     data = [line[3*i:3*i+3] for i in range(num_sensors)]
#     data = {point[0]:{"value":float(point[1]), "units":point[2]} for point in data}
#     data["date"] = datetime.datetime.now()
#     collection.insert(data)
#     print data
#     print '\n'

#Initialization sequences
#DO
DO_serial.write('E\r') #Disable auto-reading
DO_serial.write('L1\r') #Turn on debugging LED's

# #ORP
# ORP_serial.write('E\r') #Disable auto-reading
# ORP_serial.write('L1\r') #Turn on debugging LED's

# #EC
# EC_serial.write('E\r') #Disable auto-reading
# EC_serial.write('L,1\r') #Turn on debugging LED's

# #PH
# PH_serial.write('E\r') #Disable auto-reading
# PH_serial.write('L1\r') #Turn on debugging LED's

# #Flow
# Flow_serial.write('E\r') #Disable auto-reading
# Flow_serial.write('L1\r') #Turn on debugging LED's

# #Temp
# Temp_serial.write('E\r') #Disable auto-reading



name = []
read = []
units = []


while True:
    #check serial ports and db connection every loop
    time1 = time.time()#used to guarantee stable frequency
    if not client.alive():
        print "DB connection lost, trying to reconnect..."
        try :
            client = MongoClient(mongo_server)
            db = client[db_name]
            collection = db[board_name]
            print "Reconnected to ", collection.full_name
        except:
            print 'Could not connect to Mongo at: "' + mongo_server + '" on database "' + db_name + "." + board_name + '"'
            sys.exit(0)


    #Evaluate if all serial ports are open, if not try to reconnect
    if not DO_serial.isOpen():
        try:    
            DO_serial.open()
        except:
            print "Could not establish connection to DO sensor"
            sys.exit(0)

    # if not ORP_serial.isOpen():
        # try:    
            # ORP_serial.open()
        # except:
            # print "Could not establish connection to ORP sensor"
            # sys.exit(0)
 
    # if not EC_serial.isOpen():
        # try:    
            # EC_serial.open()
        # except:
            # print "Could not establish connection to EC sensor"
            # sys.exit(0)

    # if not PH_serial.isOpen():
        # try:    
            # PH_serial.open()
        # except:
            # print "Could not establish connection to PH sensor"
            # sys.exit(0)

    # if not Temp_serial.isOpen():
        # try:    
            # Temp_serial.open()
        # except:
            # print "Could not establish connection to PH sensor"
            # sys.exit(0)

    # if not Temp_serial.isOpen():
        # try:    
            # Temp_serial.open()
        # except:
            # print "Could not establish connection to Temperature sensor"
            # sys.exit(0)

    #Execute readings
    #DO
    name.append("DO")
    units.append("Mg/L")
    DO_serial.flushInput() #flush corrupted data, if there's any
    DO_serial.write('R\r') #send Read command
    readval = (DO_serial.read(DO_serial.inWaiting())) #read characters available in buffer
    read.append(readval[:readval.find('\r')])
    
    # #ORP
    # name.append("ORP")
    # units.append("N/A")
    # ORP_serial.flushInput() #flush corrupted data, if there's any
    # ORP_serial.write('R\r') #send Read command
    # readval = (ORP_serial.read(ORPs_serial.inWaiting())) #read characters available in buffer
    # read.append(readval[:readval.find('\r')])
    
    # #EC
    # name.append("EC")
    # units.append("N/A")
    # EC_serial.flushInput() #flush corrupted dssata, if there's any
    # EC_serial.write('R\r') #send Read command
    # readval = (EC_serial.read(EC_serial.inWaiting())) #read characters available in buffer
    # read.append(readval[:readval.find('\r')])

    # #PH
    # name.append("PH")
    # units.append("N/A")
    # PH_serial.flushInput() #flush corrupted data, if there's any
    # PH_serial.write('R\r') #send Read command
    # readval = (PH_serial.read(PH_serial.inWaiting())) #read characters available in buffer
    # read.append(readval[:readval.find('\r')])
    
    # #Flow
    # name.append("Flow")
    # units.append("N/A")
    # Flow_serial.flushInput() #flush corrupted dssata, if there's any
    # Flow_serial.write('R\r') #send Read command
    # readval = (Flow_serial.read(Flow_serial.inWaiting())) #read characters available in buffer
    # read.append(readval[:readval.find('\r')])
    
    # #Temp
    # name.append("Temperature")
    # units.append("C")
    # Temp_serial.flushInput() #flush corrupted data, if there's any
    # Temp_serial.write('R\r') #send Read command
    # readval = (Temp_serial.read(Temp_serial.inWaiting())) #read characters available in buffer
    # read.append(readval[:readval.find('\r')])

    data = {name[i]:{"value":read[i], "units":units[i]} for i in range(len(name))}
    collection.insert(data)
    print data
    name = []
    read = []
    units = []

    time.sleep(sensor_reading_frequency - (time.time() - time1))












