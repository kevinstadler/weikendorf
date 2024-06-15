#!/usr/bin/python
import RPi.GPIO as GPIO
from gpiozero import PWMLED

import pygame
import random

import glob
import os
import shutil

import json
import logging
import configparser

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.DEBUG)

logger = logging.getLogger("file")
logger.setLevel(logging.INFO)
handler = logging.FileHandler('files/log.txt')
handler.setFormatter(logging.Formatter("%(asctime)s,%(levelname)s,%(message)s", "%Y-%m-%d %H:%M:%S"))
logger.addHandler(handler)

logger.info("script,start")

#counts = json.load(open("counts.json"))

localdir = "/home/pi/files"
extensions = ["aif", "aiff", "m4a", "m4b", "mp3", "ogg", "wav"]
last_played = None

GPIO.setmode(GPIO.BCM)
sensor_pin = 23

sensor_led = PWMLED(4) # red
sound_led = PWMLED(10) # green
usb_led = PWMLED(5) # blue

def sensorled(pin):
    sensor_led.value = GPIO.input(pin)

GPIO.setup(sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.add_event_detect(sensor_pin, GPIO.BOTH, callback=sensorled)#, bouncetime=500)

leds = [sensor_led, sound_led, usb_led]

def dim(led):
    led.value = .02

for led in leds:
    dim(led)
 
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.mixer.pre_init(frequency=48000, buffer=2048)
pygame.mixer.init()

config = configparser.ConfigParser()

def play(filename, wait = False):
    global last_played
    logging.info("playing %s", filename)
    last_played = filename
    sound_led.pulse(.1, .1)
    snd = pygame.mixer.Sound(last_played)
    snd.play()
    sound_led.pulse()
    if last_played.startswith(localdir):
        name = os.path.basename(filename)
#        if name in counts.keys():
#            counts[name] = counts[name] + 1
#        else:
#            counts[name] = 1
    if wait:
        logging.debug("waiting %f seconds", snd.get_length())
        pygame.time.wait(round(1000 * snd.get_length()))
        logging.debug("still playing: " + str(pygame.mixer.get_busy()))
        dim(sound_led)

    return snd

def playrandom():
    k = int(config['weikendorf']['soundfiles_pro_gruppe'])
    breaktime = int(config['weikendorf']['pause_nach_soundfile'])
    for i in range(k):
        try:
            files = [f for ext in extensions for f in glob.glob(f"{localdir}/*.{ext}")]
            if len(files) == 0:
                logging.warning("no files to play")
                break
            elif len(files) > 1:
                files = list(filter(lambda n: n != last_played, files))
            target = random.choice(files)
#            targets = random.sample(list(filter(lambda n: n != last_played, files)), k=int(config['weikendorf']['soundfiles_pro_gruppe']))
            logger.info(f"play,{os.path.basename(target)}")
            play(target, True)
            pygame.time.wait(1000 * breaktime)
            if len(files) == 1:
                break
        except pygame.error:
            logging.warn("playback error, deleting file")
            logger.info(f"error,{target}")
            os.remove(target)

for led in leds:
    led.off()

try:
    justActive = True
    while True:
        # check disks and copy files over
        disks = glob.glob("/dev/sda[0-9]*")
        if len(disks):
            usb_led.value = .3
            logging.info(f"Mounting {len(disks)} USB partitions")
            if os.path.ismount("/mnt"):
                logging.warning("/mnt still mounted, dismounting")
                os.system(f"sudo umount /mnt")
            for disk in disks:
                logging.info("  - " + disk)
                usb_led.blink(1.5, 1, 1, 0, 1, False)
                logger.info(f"usbmnt,{disk}")
                os.system(f"sudo mount {disk} /mnt")
                files = [f for ext in extensions for f in glob.glob(f"/mnt/*.{ext}")]
                #i = 0
                for file in files:
                    #i = i + 1
                    #usb_led.blink(.5, .5, 0, 0, i, False)
                    usb_led.on()
                    pygame.time.wait(500)
                    base = os.path.basename(file)
                    logging.info("    - %s (%i)", base, os.path.getsize(file))
                    target = f"{localdir}/{base}"
                    # 1. check for size/checksum difference
                    if not os.path.isfile(target) or os.path.getsize(file) != os.path.getsize(target):
                        # 2. try playing back from USB to check if the file is valid/playable
                        try:
                            logger.info(f"usbtry,{base}")
                            play(file).stop()
                            # 3. copy file
                            logging.info(f"      - copying ({round(os.path.getsize(file) / (1024*1024), 1)}MB)")
                            usb_led.pulse(.1, .1)
                            logger.info(f"usbcpy,{base}")
                            shutil.copyfile(file, target)
                            usb_led.on()
                            # 4. start play() and leave for at least 5 seconds
                            snd = play(target)
                            logging.info("playing for 5s")
                            logger.info(f"peek,{base}")
                            pygame.time.wait(5000) # TODO less than 5 if short sound
                            snd.stop()
                            sound_led.off()

                        except pygame.error:
                            sound_led.off()
                            logging.info(f"      - file seems to be damaged/invalid, skipping")
                            logger.warn(f"tryfail,{base}")
                            sensor_led.blink(1, 0, 0, 0, 1, False)
                            sensor_led.off()
                    else:
                        logger.info(f"usbskp,{base}")
                        logging.info("      - already exists, skipping")
                        sound_led.blink(.1, .3, 0, 0, 2, False)

                    usb_led.off()
                    pygame.time.wait(500)

                if os.path.isfile("/mnt/config.txt"):
                    logger.info("cnfg,copy")
                    shutil.copyfile("/mnt/config.txt", f"{localdir}/config.txt")

                logging.debug("Unmounting " + disk)
                usb_led.blink(2, 2, 0, 1, 1, False)
                os.system(f"sudo umount /mnt")
            # umount /mnt -> /dev/sda1 still exists!
            # eject /dev/sda -> /dev/sda1 disappears
            os.system("sudo eject /dev/sda")
            logging.debug("Unmounted")

        on = GPIO.input(sensor_pin)
        if on:
            logger.info("trigger,re" if justActive else "trigger,new")
            config.read('files/config.txt')

            playrandom()

            # 5 second pause / break
            breaktime = int(config['weikendorf']['pause_nach_gruppe'])
            sound_led.blink(.1, .9, 0, 0, breaktime, False)
            logging.debug("reentering loop")
            sound_led.off()
        justActive = on
        pygame.time.wait(500)
        if usb_led.value == 0:
            dim(usb_led)
        else:
            usb_led.off()
        #usb_led.blink(.1, .9, n=1)
finally:
    logger.info("script,shutdown")
#    with open("counts.json", "w") as outfile:
#        json.dump(counts, outfile)
    GPIO.cleanup(sensor_pin)

