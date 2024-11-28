import RPi.GPIO as GPIO
import time
from smbus2 import SMBus

class GroveLCD:
    def __init__(self, bus_number=1, lcd_addr=0x3e):
        self.bus = SMBus(bus_number)
        self.lcd_addr = lcd_addr
        self.initialize()
    
    def send_command(self, cmd):
        self.bus.write_byte_data(self.lcd_addr, 0x80, cmd)
        time.sleep(0.0001)
    
    def send_data(self, data):
        self.bus.write_byte_data(self.lcd_addr, 0x40, ord(data))
        time.sleep(0.0001)
    
    def initialize(self):
        # Initialize display
        self.send_command(0x38) # 8bit, 2 line, 5x8 dots
        self.send_command(0x0C) # Display ON, cursor OFF
        self.send_command(0x01) # Clear display
        time.sleep(0.002)
        self.send_command(0x06) # Entry mode set
    
    def clear(self):
        self.send_command(0x01)
        time.sleep(0.002)
    
    def write(self, text, line=0, start_col=0):
        if line == 0:
            self.send_command(0x80 + start_col)
        else:
            self.send_command(0xC0 + start_col)
        
        for char in text:
            self.send_data(char)

# GPIO setup for EXT_BUTTON
EXT_BUTTON_PIN = 18  # Change to the correct GPIO pin number
GPIO.setmode(GPIO.BCM)
GPIO.setup(EXT_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def main():
    lcd = GroveLCD()
    lcd.clear()
    lcd.write("Witty C ", 0)
    lcd.write("TestBoard", 1)
    time.sleep(2)
    lcd.clear()
    lcd.write("Powered by", 0)
    lcd.write("Faradex SRL", 1)
    time.sleep(2)
    lcd.clear()
    lcd.write("Press button", 0)
    lcd.write("to start", 1)
    
    try:
        while True:
            button_state = GPIO.input(EXT_BUTTON_PIN)
            if button_state == GPIO.LOW:
                lcd.clear()
                lcd.write("Testing Started", 0)
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()

#This script succesfully demostrates the combination of the external button and the LCD display.