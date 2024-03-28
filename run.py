#!/usr/local/bin/python3
import RPi.GPIO as GPIO
import pygame
import random

import glob
import os
import shutil

localdir = "files/"
extensions = ["aif", "aiff", "m4a", "m4b", "mp3", "ogg", "wav"]
last_played = None

sensor1_led = 1 # red
sensor2_led = 2 # red
sound1_led = 3 # green
sound2_led = 4 # green
usb_led = [5,6,7] # rgb

# GPIO.setmode(GPIO.BOARD)
sensor_pins = [11, 12]
led_pins = [sensor1_led, sensor2_led, sound1_led, sound2_led, usb_led]

for pin in led_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, True)

pygame.mixer.init()
PLAYBACK_FINISHED = pygame.USEREVENT + 1
pygame.mixer.music.set_endevent(PLAYBACK_FINISHED)


def play(filename):
    global last_played
    last_played = filename
    try:
        # just in case
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        # load and play
        GPIO.output(sound1_led, True)
        pygame.mixer.music.load(last_played)
        pygame.mixer.music.play(0)
    except pygame.error:
        GPIO.output(sound1_led, False)
        print("errrr")

def trigger():
    if pygame.mixer.music.get_busy():
        # TODO briefly fire red LED
        return
    files = [f for ext in extensions for f in glob.glob(f"{localdir}/*.{ext}")]
    play(random.choice(list(filter(lambda n: n != last_played, files))))

for pin in led_pins:
    GPIO.output(pin, False)

for pin in sensor_pins:
    GPIO.setup(pin, GPIO.IN)
    GPIO.add_event_detect(pin, GPIO.RISING, callback=trigger, bouncetime=200)

try:
    while True:
        trigger()
        # TODO check /Volumes and copy files over
        usb = glob.glob("/media/pi/*")
        for dir in usb:
            # os.path.ismount("/media/pi/..."))
            if os.access(dir, os.R_OK):
                print(dir)
                files = [f for ext in extensions for f in glob.glob(f"{dir}/*.{ext}")]
                for file in files:
                    GPIO.output(usb_pin, True)
                    print(file)
                    target = f"{localdir}/{file}"
                    # 1. check for size/checksum difference
                    if os.file.exists(target) and os.path.getsize(file) == os.path.getsize(target):
                        pygame.time.wait(50)
                        GPIO.output(usb_pin, False)
                        continue
                    # 2. load() to check if valid
                    # 3. copy file
                    shutil.copyfile(file, target)
                    GPIO.output(usb_pin, False)
                    # 4. start play()
                    play(target)
#            os.system("sudo eject /dev/sdb1")
#            os.system(f"sudo umount {dir}")
        for event in pygame.event.get():
            if event.type == PLAYBACK_FINISHED:
                GPIO.output(sound1_led, False)
        pygame.time.wait(1000) # TODO check if wait blocks the trigger event from firing?
finally:
    GPIO.cleanup()

