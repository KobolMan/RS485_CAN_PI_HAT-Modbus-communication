# hardware_control.py
import serial
import RPi.GPIO as GPIO
import time
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_2_CH_RS485_HAT import config

class RS485Device:
    def __init__(self, port, baudrate=9600, txden_pin=None):
        self.ser = config.config(dev=port, Baudrate=baudrate)
        if txden_pin is not None:
            self.txden = txden_pin
            GPIO.setup(self.txden, GPIO.OUT)
            GPIO.output(self.txden, GPIO.HIGH)
    
    def send_command(self, hex_list):
        command = bytes(hex_list)
        if hasattr(self, 'txden'):
            GPIO.output(self.txden, GPIO.LOW)
        time.sleep(0.1)
        
        self.ser.serial.write(command)
        print(f"{self.ser.dev} Sent:", ' '.join([f'{b:02X}' for b in hex_list]))
        
        time.sleep(0.2)
        
        if hasattr(self, 'txden'):
            GPIO.output(self.txden, GPIO.HIGH)
        time.sleep(0.1)
        
        if self.ser.serial.in_waiting:
            response = self.ser.serial.read(self.ser.serial.in_waiting)
            print(f"{self.ser.dev} Received:", ' '.join([f'{b:02X}' for b in response]))
            return response
        return None

class AnalogOutput:
    def __init__(self, device):
        self.device = device
    
    def set_voltage(self, channel, voltage):
        try:
            address = 0x01
            function_code = 0x06
            register_address = 0x0000 + channel  # Adjusted for DAC channels
            value = int(voltage * 1000)
            frame = [
                address,
                function_code,
                (register_address >> 8) & 0xFF,
                register_address & 0xFF,
                (value >> 8) & 0xFF,
                value & 0xFF
            ]
            crc = self.calculate_crc(frame)
            frame.append(crc & 0xFF)
            frame.append((crc >> 8) & 0xFF)
            response = self.device.send_command(frame)
            if response and response[1] & 0x80:
                logging.error(f"Failed to set voltage: Exception code {response[2]}")
            return True
        except Exception as e:
            logging.error(f"Failed to set voltage: {e}")
            return False

    @staticmethod
    def calculate_crc(data):
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

class AnalogInput:
    def __init__(self, device):
        self.device = device
    
    def read_voltage(self, channel):
        try:
            address = 0x01
            function_code = 0x04
            register_address = 0x0000 + channel  # Adjusted for ADC channels
            frame = [
                address,
                function_code,
                (register_address >> 8) & 0xFF,
                register_address & 0xFF,
                0x00, 0x01  # Number of registers to read
            ]
            crc = self.calculate_crc(frame)
            frame.append(crc & 0xFF)
            frame.append((crc >> 8) & 0xFF)
            response = self.device.send_command(frame)
            
            if response and len(response) >= 5:
                value = (response[3] << 8) | response[4]
                voltage = value / 1000.0  # Adjusted to match the expected voltage range
                print(f"Input Voltage: {voltage:.3f}V")
                return voltage
            return None
        except Exception as e:
            logging.error(f"Failed to read voltage: {e}")
            return None

    @staticmethod
    def calculate_crc(data):
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc