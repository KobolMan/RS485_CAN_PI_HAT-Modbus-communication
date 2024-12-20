import time
import signal
import RPi.GPIO as GPIO

# Button GPIO pin
BUTTON_PIN = 18

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Flag to control program execution
running = True

def button_callback(channel):
    """Callback function that runs when button state changes"""
    if GPIO.input(BUTTON_PIN) == GPIO.LOW:
        print("Button Pressed")
    else:
        print("Button Released")

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    global running
    print("\nExiting program")
    running = False

try:
    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Add event detection for both rising and falling edges
    GPIO.add_event_detect(BUTTON_PIN, GPIO.BOTH, 
                         callback=button_callback, 
                         bouncetime=200)  # 200ms debounce
    
    print("Monitoring button events. Press Ctrl+C to exit")
    
    # Keep program running
    while running:
        time.sleep(0.1)

finally:
    # Clean up
    GPIO.remove_event_detect(BUTTON_PIN)
    GPIO.cleanup()