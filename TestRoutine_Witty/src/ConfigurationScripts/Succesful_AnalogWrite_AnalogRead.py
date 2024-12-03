#!/usr/bin/python
# -*- coding:utf-8 -*-
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
    
    def set_voltage(self, voltage_mv):
        """Set voltage in millivolts"""
        voltage_hex = voltage_mv & 0xFFFF
        high_byte = (voltage_hex >> 8) & 0xFF
        low_byte = voltage_hex & 0xFF
        
        command = [0x01, 0x06, 0x00, 0x00, high_byte, low_byte]
        crc = self.calculate_crc(command)
        command.extend([crc & 0xFF, (crc >> 8) & 0xFF])
        
        return self.device.send_command(command)
    
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
    
    def read_voltage(self):
        """Read voltage from channel 1"""
        # Read single channel command
        command = [0x01, 0x03, 0x00, 0x00, 0x00, 0x01, 0x84, 0x0A]
        response = self.device.send_command(command)
        
        if response and len(response) >= 5:
            value = (response[3] << 8) | response[4]
            voltage = value / 10000.0  # Convert to volts
            #Formula from datasheet Voltage = Scale Code * 3300/4095/Operational Amplifier Ratio
            #voltage = value * 3300/4095/10/32.4
            print(f"Input Voltage: {voltage:.3f}V")
            return voltage
        return None

try:
    print("Initializing RS485 devices...")
    
    # Initialize devices
    output_board = RS485Device("/dev/ttySC0", txden_pin=27)
    input_board = RS485Device("/dev/ttySC1", txden_pin=22)
    
    # Create control objects
    analog_out = AnalogOutput(output_board)
    analog_in = AnalogInput(input_board)
    
    # Set output to 5V
    print("\nSetting output to 5V...")
    if analog_out.set_voltage(5000):  # 5000mV = 5V
        print("Output voltage set successfully")
    
    # Continuous monitoring loop
    print("\nStarting continuous monitoring...")
    print("Press Ctrl+C to stop")
    
    while True:
        # Read input voltage
        input_voltage = analog_in.read_voltage()
        
        # Optional: verify output voltage is still set
        time.sleep(1)  # Wait 1 second between readings

except KeyboardInterrupt:
    print("\nProgram stopped by user")
except Exception as exc:
    print(str(exc))
finally:
    GPIO.cleanup()

#This script succesfully sets the output voltage to 5V and reads the input voltage from the analog input channel.