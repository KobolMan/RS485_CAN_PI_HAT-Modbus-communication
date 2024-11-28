import time

import RPi.GPIO as GPIO

# Set up GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)

try:
    while True:
        button_state = GPIO.input(18)
        if button_state == GPIO.LOW:
            print("Button Pressed")
        else:
            print("Button Released")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("Exiting program")

finally:
    GPIO.cleanup()