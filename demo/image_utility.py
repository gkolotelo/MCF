#!/usr/bin/python2
"""
CityFARM Image Preparation Utility

image_utility [--water] [--air] [--no-burn] [--no-unmount] SOURCE_IMAGE [TARGET_DISK]

Options:
    --air
            Indicates that the image being created is that of an Air Board. By enabling this option,
            you must explicitly enable the '--water' option if you wish to have both Air and Water Board
            files copied to the image file. That is, by selecting this option only the Air Board files will
            be copied, unless the '--water' is explicitly enabled.

    --water
            Default. If '--air' is not enabled, Water Board files will be copied by default.

    --no-burn
            If enabled, the custom image will be created, but not burned to the TRAGET_DISK, that is,
            TARGET_DISK is not used, and need not be defined, since the 'dd' command will not be executed.

    --only-burn
            If enabled does the opposite of --no-burn. The custom image will not be created (It is assumed
            that it has already been created and the user just wishes to burn the SOURCE_IMAGE to the
            TARGET_DISK). Both SOURCE_IMAGE and TARGET_DISK must be defined. All other options are ignored.
            'dd' command used for reference: "dd if=SOURCE_IMAGE of=TARGET_DISK bs=1M"

    --no-unmount
            If enabled the SOURCE_IMAGE will no be unmounted after copying the files, so the user may access
            and copy custom files to the mounted SOURCE_IMAGE.
            '--no-burn' will be enabled by default.
            '--no-unmount' has priority over '--only-burn'




Instructions:
    1.  Files needed:
        Have on the same folder the following files, which are necessary for the proper
        operation of the board, be it an Air Board, or Water Board.
        Only the following files will be copied.

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

# Flags

water = True
air = False
no_burn = False
do_mount = True
no_unmount = False

water_folder = './RPi/'
water_files = ['config.json',
               'rpi_service.py',
               'rpi_service.service',
               'rpi_sh.sh',
               'sensor_terminal.py',
               'serialsensor.py'
               ]

air_folder = './RPi_Air/'
air_files = ['config.json',
             'rpi_service.py',
             'rpi_service_air.service',
             'rpi_sh.sh',
             'sensor_terminal.py',
             'serialsensor.py'
             ]

try:
    args = sys.argv[1:]
except:
    pass
if str(args).find("--help") != -1:
    print "No help here, open image_utility.py for instructions."
    sys.exit(0)
if str(args).find("--air") != -1:
    air = True
    water = False
if str(args).find("--water") != -1:
    water = True
if str(args).find("--only-burn") != -1:
    do_mount = False
    air = False
    water = False
    no_unmount = False
if str(args).find("--no-burn") != -1:
    if any("/dev/" in s for s in args):
        print "--no-burn enabled. Do not set TARGET_DISK"
        sys.exit(0)
    no_burn = True
if str(args).find("--no-unmount") != -1:
    if any("/dev/" in s for s in args):
        print "--no-unmount enabled. Do not set TARGET_DISK"
        sys.exit(0)
    do_mount = True
    no_unmount = True
    no_burn = True

if no_burn is False:
    if not any("/dev/" in s for s in args):
        print "TARGET_DISK not set or invalid TARGET_DISK."
        #sys.exit(0)



def main():
    if no_burn:
        # No TARGET_DISK defined, SOURCE_IMAGE is last arg.
        source_image = args[len(args)-1]
    else:
        # If TARGET_DISK define, SOURCE_IMAGE is second last arg.
        source_image = args[len(args)-2]
        target_disk = args[len(args)-1]
        if target_disk.find('/dev/') == -1:
            print "TARGET_DISK not set or invalid TARGET_DISK."
            #sys.exit(0)
        print "Target Disk:  " + target_disk
    if source_image.find('.img') == -1:
            print "SOURCE_IMAGE not set or inavlid SOURCE_IMAGE."
            sys.exit(0)
    print "Source Image: " + source_image

    if do_mount:

        if air:
            checkAllFilesPresentForCopy(air_files, air_folder)
        if water:
            checkAllFilesPresentForCopy(water_files, water_folder)

        if raw_input("Press Enter to continue...") != '':
            print "Aborting"
            sys.exit(0)

        try:
            mount_point = mount(source_image)
        except:
            print "Could not mount SOURCE_IMAGE."
            sys.exit(0)

        server = raw_input("Enter the database server URL or IP Address : ")
        username = raw_input("Enter the database username: ")
        password = raw_input("Enter the database password: ")

        if air:
            rpi_air_root_folder = mount_point + '/root/RPi_Air/'
            config_file_air = rpi_air_root_folder + 'config.json'

            copy(air_folder, air_files, rpi_air_root_folder)
            setPermissions(air_files, rpi_air_root_folder)
            setConfigfile(config_file_air, server, username, password)
        if water:
            rpi_root_folder = mount_point + '/root/RPi/'
            config_file_water = rpi_root_folder + 'config.json'

            copy(water_folder, water_files, rpi_root_folder)
            setPermissions(water_files, rpi_root_folder)
            setConfigfile(config_file_water, server, username, password)
        if no_unmount:
            print "Image creation succesful."
            print "Source image mounted on: " + mount_point
            sys.exit(0)
        unmount(mount_point)

    if no_burn:
        print "Image preparation succesful."
        sys.exit(0)

    if raw_input("Press Enter to continue burning image to disk...") != '':
        print "Aborting"

    burn(source_image, target_disk)

    if no_burn:
        print "Process completed succesfully!"
    else:
        print "Process completed succesfully! You may now remove the SD Card."
    sys.exit(0)


def copy(source_folder, file_list, target_folder):
    print "Copying files to: '" + target_folder + "'"

    try:
        subprocess.check_output("rm -r " + target_folder, shell=True)
    except:
        pass
    subprocess.check_output("mkdir " + target_folder, shell=True)

    for file_ in file_list:
        subprocess.check_output("cp " + source_folder + file_ + ' ' + target_folder, shell=True)
        print "    " + file_


def setPermissions(file_list, target_folder):
    print "Setting permissions on: '" + target_folder + "'"

    for file_ in file_list:
        if file_.find('.py') != -1 or file_.find('.sh') != -1:
            subprocess.check_output("chmod +x " + target_folder + file_, shell=True)


def setConfigfile(config_file_json, server, username, password):
    print "Adding connection settings to config file."

    with open(config_file_json) as settings_file:
        settings = json.loads(settings_file.read())

    settings['settings']['value']['username']['value'] = username
    settings['settings']['value']['password']['value'] = password
    settings['settings']['value']['server']['value'] = server

    fp = open(config_file_json, 'w+')
    fp.writelines(json.dumps(settings, indent=4))
    fp.close()


def mount(source_image):
    print "Mounting image..."
    # arg in the format: fdisk -l source_image.img | grep Linux| awk '{print $2}'
    # Finds Linux type partition on disk image, and returns starting sector
    arg = "fdisk -l " + source_image + " | grep Linux | awk '{print $2}'"
    number_of_sectors = subprocess.check_output(arg, shell=True)
    # Finds the size of each sector
    arg = "fdisk -l " + source_image + ' | grep "Sector size" | awk ' + "'{print $4}'"
    sector_size = subprocess.check_output(arg, shell=True)

    starting_size = str(int(number_of_sectors)*int(sector_size))

    mount_point = "mount_point_" + source_image

    # Mount disk to mount_point:
    try:
        subprocess.check_output("umount " + mount_point, shell=True)
    except:
        pass
    try:
        subprocess.check_output("rmdir " + mount_point, shell=True)
    except:
        pass
    subprocess.check_output("mkdir " + mount_point, shell=True)
    subprocess.check_output("mount -t auto -o loop,offset=" + starting_size + ' ' + source_image + ' ' + mount_point, shell=True)

    print "Mounting succesful"

    return mount_point


def unmount(mount_point):
    print "Unmounting image."

    subprocess.check_output("umount " + mount_point, shell=True)
    subprocess.check_output("rmdir " + mount_point, shell=True)


def burn(source_image, target_disk):
    print "Unmounting disk partitions (ignore errors)."
    try:
        subprocess.check_output("umount -f " + target_disk + '*', shell=True)
    except:
        pass
    print "Burning image to SD Card at " + target_disk
    print "Image burning may take as long as 15 minutes, please wait."
    print "Running: " + "dd if=" + source_image + " of=" + target_disk + " bs=1M"
    try:
        print subprocess.check_output("dd if=" + source_image + " of=" + target_disk + " bs=1M", shell=True)
    except KeyboardInterrupt:
        print "Aborted by user."
        sys.exit(0)
    try:
        subprocess.check_output("umount -f " + target_disk + '*', shell=True)
    except:
        pass


def checkAllFilesPresentForCopy(file_list, folder):
    for file_ in file_list:
        try:
            subprocess.check_output("ls " + folder + file_, shell=True)
        except:
            print "File: '" + folder + file_ + "'' not found, please have all the needed files placed in the '" + folder + "' folder, then try again."
            sys.exit(0)
    print "All files found on: '" + folder + "'"


if __name__ == '__main__':
    main()

