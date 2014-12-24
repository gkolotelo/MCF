#!/usr/bin/python2
"""
CityFARM Image Preparation Utility

image_utility TARGET_DISK SOURCE_IMAGE [ADDITIONAL_FILES]...

Instructions:
    1.  Files needed:
        Have on the same folder the following files, which are necessary for the proper
        operation of the board, be it an Air Board, or Water Board.
        Only the following files will be copied. If you wish to have other files copied,
        append its filenames as arguments.

        Files needed:
            config.json
            rpi_service.py
            rpi_service.service
            rpi_sh.sh
            sensor_terminal.py
            serialsensor.py
            archlinux_cityfarm_image_3_12_34_ARCH.img (or other CityFARM linux image)

    2.  Hardware Needed:
        An 8Gb SD Card connected to the computer, and have its path noted, for instance:
            SD Card at /dev/sdb
        It is vital that you get the correct path, or else the utility will unmercifully
        erase all data on that path, with no possibility of recovery.
        To make sure you have the correct path, you may execute an 'ls' command before
        and after inserting the SD Card; the new path that appears will most likely be
        the SD Card.
        An example of something you might see is:

            ==> (No SD card):
            user$: ls /dev
            bus         loop1       sda2         stdout
            cdrom       pts         sda5         tty0
            cdrw        ram0        sdb          ttyUSB0
            dvd         sda         stderr
            dvdrw       sda1        stdin
            ==> (Insert SD card)
            user$: ls /dev
            bus         loop1       sda2         stderr
            cdrom       pts         sda5         stdin
            cdrw        ram0        sdb          stdout
            dvd         sda         sdb1  <--    tty0       Note that sdb1 and sdb2 appeared
            dvdrw       sda1        sdb2  <--    ttyUSB0    after inserting the SD card.

        So the path you're interested in is: /dev/sdb
        It's worth it to point out that the path we're interested in is the disk itself,
        /dev/sdb, not /dev/sdb1 or 2 which corresponds to a partition within de disk sdb.

    3.  Information needed:
        The server address (URL or IP Address) in hands, as well as the username and password
        of the database.

    4.
        If you have ALL the items above, you can proceed to burning your image
        into the SD Card. To do that, follow the instructions below:

        4.1 - On a terminal window, go to the directory containing the files needed on item 1,
        for instance:

            user$: cd ~/Documents/CityFARM/Sensor_Board
            user$: ls
            archlinux_cityfarm_image_3_12_34_ARCH.img        rpi_service.service
            config.json                                      rpi_sh.sh
            image_utility.py                                 sensor_terminal.py
            rpi_service.py                                   serialsensor.py

        4.2 - On the same terminal window, execute the Image Preparation Utility, if any additional
            files are to be added, add them as arguments, for instance:
            image_utility TARGET_DISK SOURCE_IMAGE [ADDITIONAL_FILES]...

                user$: ./image_utility.py /dev/sdb archlinux_cityfarm_image_3_12_34_ARCH.img

            Or with additional files:

                user$: ./image_utility.py /dev/sdb archlinux_cityfarm_image_3_12_34_ARCH.img whatever_file.txt

    5.  WAIT! This process may take as long as 15 minutes, so be patient. After the utility completes its job
        you may remove the SD card and stick it in the Raspberry Pi and boot it up.

"""

import sys
import subprocess
import os
import json

if (os.getuid() != 0):
    print "Must be run as superuser"
    sys.exit(0)

files = ['config.json',
         'rpi_service.py',
         'rpi_service.service',
         'rpi_sh.sh',
         'sensor_terminal.py',
         'serialsensor.py'
         ]

try:
    arg = str(sys.argv[1])
except:
    pass
if arg == "-h" or arg == "--help":
    print "No help here, open image_utility.py for instructions."
    sys.exit(0)

try:
    target_disk = sys.argv[1]
    if target_disk.find('dev') == -1:
        print "Invalid target disk."
        sys.exit(0)
except:
    print "No target disk set."
    sys.exit(0)
try:
    source_image = sys.argv[2]
    if source_image.find('.img') == -1:
        print "Invalid source image."
        sys.exit(0)
except:
    print "No source image set."
    sys.exit(0)

try:
    for additional_files in sys.argv[3:]:
        # Add additional files to files list.
        files.append(additional_files)
except:
    # No additional files
    pass

for file_ in files:
    try:
        subprocess.check_output("ls " + file_, shell=True)
    except:
        print "File: " + file_ + " not found, please have all the needed files placed in the current folder, then try again."
        sys.exit(0)

server = raw_input("Enter the database server URL or IP Address : ")
username = raw_input("Enter the database username: ")
password = raw_input("Enter the database password: ")


print "All files found."
print "Target Disk:  " + target_disk
print "Source Image: " + source_image

if raw_input("Press Enter to continue...") != '':
    print "Aborting"
    sys.exit(0)

print "\nMounting image...\n"
# arg in the format: fdisk -l source_image.img | grep Linux| awk '{print $2}'
# Finds Linux type partition on disk image, and returns starting sector
arg = "fdisk -l " + source_image + " | grep Linux | awk '{print $2}'"
number_of_sectors = subprocess.check_output(arg, shell=True)
# Finds the size of each sector
arg = "fdisk -l " + source_image + ' | grep "Sector size" | awk ' + "'{print $4}'"
sector_size = subprocess.check_output(arg, shell=True)

starting_size = str(int(number_of_sectors)*int(sector_size))

mount_point = "mount_point_" + source_image

# Mount disk on folder:
try:
    subprocess.check_output("umount " + mount_point, shell=True)
    subprocess.check_output("rmdir " + mount_point, shell=True)
except:
    pass
subprocess.check_output("mkdir " + mount_point, shell=True)
subprocess.check_output("mount -t auto -o loop,offset=" + starting_size + ' ' + source_image + ' ' + mount_point, shell=True)

print "Copying files:"

rpi_root_folder = mount_point + '/root/RPi/'

try:
    subprocess.check_output("rm -r " + rpi_root_folder, shell=True)
except:
    pass
subprocess.check_output("mkdir " + rpi_root_folder, shell=True)

for file_ in files:
    subprocess.check_output("cp " + file_ + ' ' + rpi_root_folder, shell=True)
    print "    " + file_

print "Setting permissions..."

for file_ in files:
    if file_.find('.py') != -1 or file_.find('.sh') != -1:
        subprocess.check_output("chmod +x " + rpi_root_folder + file_, shell=True)

print "Adding connection settings to config file."

with open(rpi_root_folder + 'config.json') as settings_file:
    settings = json.load(settings_file)
    # Change to new settings paradigm
    settings['settings']['username'] = username
    settings['settings']['password'] = password
    settings['settings']['server'] = server
fp = open(rpi_root_folder + 'config.json', 'w+')
fp.write(json.dumps(settings, indent=4))
fp.close()

print "\nUnmounting image.\n"

subprocess.check_output("umount " + mount_point, shell=True)
subprocess.check_output("rmdir " + mount_point, shell=True)

if raw_input("Image preparation finished, press Enter to continue...") != '':
    print "Aborting"
    sys.exit(0)

print "\nBurning image to SD Card at " + target_disk
print "Image burning may take as long as 15 minutes, please wait.\n\n"

try:
    # Note that bs=1M (capital M is being used)
    print subprocess.check_output("dd if=" + source_image + " of=" + target_disk + " bs=1M")
except KeyboardInterrupt:
    print "Aborted by user."
    sys.exit(0)

print "Process complete!"
