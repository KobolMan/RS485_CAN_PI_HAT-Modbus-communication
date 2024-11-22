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
        else:
            print(f"{self.ser.dev} No response")
            return None

    def read_device_id(self):
        """Read device address command"""
        cmd = [0x00, 0x03, 0x40, 0x00, 0x00, 0x01, 0x90, 0x1B]
        return self.send_command(cmd)

try:
    print("Initializing RS485 devices...")
    
    # Initialize both devices
    output_board = RS485Device("/dev/ttySC0", txden_pin=27)  # TXDEN_1
    input_board = RS485Device("/dev/ttySC1", txden_pin=22)   # TXDEN_2
    
    # First, let's read both device IDs
    print("\nReading Output Board ID (ttySC0):")
    output_id = output_board.read_device_id()
    
    print("\nReading Input Board ID (ttySC1):")
    input_id = input_board.read_device_id()
    
    if output_id and input_id:
        print("\nBoth devices responded!")
        print("Ready to proceed with voltage setting and reading.")
        input("Press Enter to continue with next steps...")
    else:
        print("\nWarning: One or both devices not responding properly.")
        print("Please check connections and try again.")

except KeyboardInterrupt:
    print("\nProgram stopped by user")
except Exception as exc:
    print(str(exc))
finally:
    GPIO.cleanup()

#This script is used to test the communication between the Raspberry Pi and the RS485 devices. It initializes two RS485 devices connected to the Raspberry Pi via serial ports and sends a command to read the device ID of each device. The response from each device is then displayed on the console. This script can be used to verify the communication setup and troubleshoot any issues with the RS485 devices.