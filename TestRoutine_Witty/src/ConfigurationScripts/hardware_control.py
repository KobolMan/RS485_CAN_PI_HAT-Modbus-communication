#!/usr/bin/python
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
    def __init__(self, port="/dev/ttySC0", baudrate=9600, txden_pin=27):
        self.ser = config.config(dev=port, Baudrate=baudrate)
        self.txden = txden_pin
        GPIO.setup(self.txden, GPIO.OUT)
        GPIO.output(self.txden, GPIO.HIGH)
    
    def send_command(self, hex_list):
        command = bytes(hex_list)
        GPIO.output(self.txden, GPIO.LOW)
        time.sleep(0.1)
        
        self.ser.serial.write(command)
        logging.debug(f"Sent: {' '.join([f'{b:02X}' for b in hex_list])}")
        
        time.sleep(0.2)
        GPIO.output(self.txden, GPIO.HIGH)
        time.sleep(0.1)
        
        if self.ser.serial.in_waiting:
            response = self.ser.serial.read(self.ser.serial.in_waiting)
            logging.debug(f"Received: {' '.join([f'{b:02X}' for b in response])}")
            return response
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

class AnalogOutput:
    def __init__(self, device, device_addr):
        self.device = device
        self.device_addr = device_addr
    
    def set_voltage(self, channel, voltage):
        try:
            function_code = 0x06
            register_address = channel
            value = int(voltage * 1000)
            
            frame = [
                self.device_addr,
                function_code,
                (register_address >> 8) & 0xFF,
                register_address & 0xFF,
                (value >> 8) & 0xFF,
                value & 0xFF
            ]
            
            crc = self.device.calculate_crc(frame)
            frame.extend([crc & 0xFF, (crc >> 8) & 0xFF])
            
            response = self.device.send_command(frame)
            if not response:
                logging.error(f"No response from device 0x{self.device_addr:02X}")
                return False
                
            if response[1] & 0x80:
                logging.error(f"Device 0x{self.device_addr:02X} reported error: {response[2]}")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Failed to set voltage on device 0x{self.device_addr:02X}: {e}")
            return False

class AnalogInput:
    def __init__(self, device, device_addr):
        self.device = device
        self.device_addr = device_addr
    
    def read_voltage(self, channel):
        try:
            function_code = 0x03  # Using Read Holding Registers
            register_address = channel
            
            frame = [
                self.device_addr,
                function_code,
                (register_address >> 8) & 0xFF,
                register_address & 0xFF,
                0x00,
                0x01
            ]
            
            crc = self.device.calculate_crc(frame)
            frame.extend([crc & 0xFF, (crc >> 8) & 0xFF])
            
            response = self.device.send_command(frame)
            if not response:
                logging.error(f"No response from device 0x{self.device_addr:02X}")
                return None
                
            if response[1] & 0x80:
                logging.error(f"Device 0x{self.device_addr:02X} reported error: {response[2]}")
                return None
                
            if len(response) >= 5:
                value = (response[3] << 8) | response[4]
                voltage = value / 1000.0
                return voltage
                
            logging.error(f"Invalid response length from device 0x{self.device_addr:02X}")
            return None
            
        except Exception as e:
            logging.error(f"Failed to read voltage from device 0x{self.device_addr:02X}: {e}")
            return None