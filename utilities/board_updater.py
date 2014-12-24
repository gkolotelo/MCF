# Board updater

import datetime
import sys
import paramiko

# Boards:
boards = []  # <-- Add board addresses here

try:
    filename = str(sys.argv[1])
except:
    print "No files to copy!"
    sys.exit(0)
if filename == "-h" or filename == "--help":
    print "No help!"
    sys.exit(0)

print "Confirm boards to be updated (Information on file): "
for i in boards:
    print i
print "Confirm files to be updated: "
for i in sys.argv[1:]:
    print i
res = raw_input("If the information above is correct, press enter to continue...")
if res != "":
    sys.exit(0)

username = raw_input("Enter username: ")
password = raw_input("Enter password: ")
foldername = raw_input("Enter foldername or leave blank for default: RPi_")
now = datetime.datetime.now()
if foldername == "":
    foldername = "RPi_" + str(now.month) + '_' + str(now.day) + '_' + str(now.year) +\
                 '_' + str(now.hour) + '_' + str(now.minute) + '_' + str(now.second)
else:
    foldername = "RPi_" + foldername

print "\nProceeding with updates...\n\n\n"

for board in boards:
    print "Now updating " + board
    print "Connecting by SSH..."
    client = paramiko.client.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(board, username=username, password=password)
    print "Connected"
    print "Creating backup of current files on new folder: " + foldername
    _, stdout, stderr = client.exec_command('cp -r RPi/ ' + foldername)
    if len(stderr.readlines()) != 0:
        print stderr.readlines()
        print "Error copying files!"
        continue
    print "Done!"
    print "Uploading, and overwriting, new files:"
    sftp = client.open_sftp()
    for argument in sys.argv[1:]:
        info = sftp.put(argument, '/root/RPi/' + argument.split('/')[-1])
        print "     Transfered " + argument.split('/')[-1] + ", " + str(info.st_size) + "bytes"
    client.close()
    print "Finished updating board " + board
