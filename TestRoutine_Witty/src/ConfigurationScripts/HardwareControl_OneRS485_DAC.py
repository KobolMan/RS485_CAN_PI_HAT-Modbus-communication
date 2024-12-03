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
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.txden, GPIO.OUT)
            GPIO.output(self.txden, GPIO.HIGH)
        
    def send_command(self, hex_list):
        command = bytes(hex_list)
        if hasattr(self, 'txden'):
            GPIO.output(self.txden, GPIO.LOW)
        time.sleep(0.01)
        
        self.ser.serial.write(command)
        print(f"{self.ser.dev} Sent:", ' '.join([f'{b:02X}' for b in command]))
        
        time.sleep(0.05)
        
        if hasattr(self, 'txden'):
            GPIO.output(self.txden, GPIO.HIGH)
        time.sleep(0.05)
        
        response = bytearray()
        timeout = time.time() + 0.1  # 100ms timeout
        while time.time() < timeout:
            if self.ser.serial.in_waiting:
                response.extend(self.ser.serial.read(self.ser.serial.in_waiting))
                break
            time.sleep(0.005)
        
        if response:
            print(f"{self.ser.dev} Received:", ' '.join([f'{b:02X}' for b in response]))
            return response
        else:
            print(f"{self.ser.dev} No response received.")
        return None

    def close(self):
        self.ser.serial.close()

class AnalogOutput:
    def __init__(self, device):
        self.device = device
        
    def set_voltage(self, channel, voltage_mv):
        """Set voltage in millivolts on specified channel"""
        voltage_hex = voltage_mv & 0xFFFF
        high_byte = (voltage_hex >> 8) & 0xFF
        low_byte = voltage_hex & 0xFF
        
        # Determine the register address based on the channel
        if channel == 1:
            register_address = [0x00, 0x00]  # Register 0x0000 for CH1
        elif channel == 2:
            register_address = [0x00, 0x01]  # Register 0x0001 for CH2
        else:
            print("Invalid channel")
            return None
        
        # Build the command
        command = [0x01, 0x06] + register_address + [high_byte, low_byte]
        crc = self.calculate_crc(command)
        command.extend([crc & 0xFF, (crc >> 8) & 0xFF])

        response = self.device.send_command(command)
        return response

    @staticmethod
    def calculate_crc(data):
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

try:
    print("Initializing RS485 device...")
    
    device = RS485Device("/dev/ttySC0", txden_pin=27)
    
    analog_out = AnalogOutput(device)
    
    # Set CH1 to 1V
    print("\nSetting CH1 to 1V...")
    if analog_out.set_voltage(1, 1000):
        print("CH1 set to 1V successfully")
    
    # Set CH2 to 5V
    print("\nSetting CH2 to 5V...")
    if analog_out.set_voltage(2, 5000):
        print("CH2 set to 5V successfully")
    
except KeyboardInterrupt:
    print("\nProgram stopped by user")
except Exception as exc:
    print(f"An error occurred: {exc}")
finally:
    device.close()
    GPIO.cleanup()

##03/12/2024 This script succesfully sets DAC output voltage to 1V and 5V on CH1 and CH2 respectively, considering a connection of ADC and DAC on same RS485 peripheral.