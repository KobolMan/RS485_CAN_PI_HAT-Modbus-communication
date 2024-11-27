from smbus2 import SMBus
import time

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
    
    def write(self, text, line=0):
        if line == 0:
            self.send_command(0x80)
        else:
            self.send_command(0xC0)
        
        for char in text:
            self.send_data(char)

# Example usage
if __name__ == "__main__":
    lcd = GroveLCD()
    lcd.clear()
    lcd.write("Hello World!", 0)
    lcd.write("Line 2 Test", 1)