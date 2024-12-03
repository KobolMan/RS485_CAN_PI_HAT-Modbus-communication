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

# Initialize RS485 port
ser = config.config(dev = "/dev/ttySC0", Baudrate = 9600)

# GPIO setup
TXDEN_1 = 27
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(TXDEN_1, GPIO.OUT)

def send_hex_command(hex_list):
    command = bytes(hex_list)
    GPIO.output(TXDEN_1, GPIO.LOW)
    time.sleep(0.1)
    
    ser.serial.write(command)
    print("Sent hex:", ' '.join([f'{b:02X}' for b in hex_list]))
    
    time.sleep(0.2)
    
    GPIO.output(TXDEN_1, GPIO.HIGH)
    time.sleep(0.1)
    
    if ser.serial.in_waiting:
        response = ser.serial.read(ser.serial.in_waiting)
        print("Received:", ' '.join([f'{b:02X}' for b in response]))
        return response
    else:
        print("No response")
        return None

def set_voltage(voltage_mv):
    """Set voltage in millivolts"""
    # Convert voltage to hex bytes
    voltage_hex = voltage_mv & 0xFFFF
    high_byte = (voltage_hex >> 8) & 0xFF
    low_byte = voltage_hex & 0xFF
    
    # Calculate CRC for the command
    command = [0x01, 0x06, 0x00, 0x00, high_byte, low_byte]
    crc = 0xFFFF
    for byte in command:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    
    command.append(crc & 0xFF)
    command.append((crc >> 8) & 0xFF)
    
    return send_hex_command(command)

def read_voltage():
    """Read current voltage setting"""
    read_cmd = [0x01, 0x03, 0x00, 0x00, 0x00, 0x01, 0x84, 0x0A]
    response = send_hex_command(read_cmd)
    if response and len(response) >= 4:
        voltage_mv = (response[3] << 8) | response[4]
        print(f"Current voltage: {voltage_mv}mV ({voltage_mv/1000.0:.2f}V)")
        return voltage_mv
    return None

try:
    print("Starting voltage ramp test...")
    
    # Test voltages (in millivolts)
    voltages = [1000, 2000, 3000, 4000, 5000]  # 1V to 5V
    
    for voltage in voltages:
        print(f"\nSetting voltage to {voltage/1000.0:.1f}V")
        if set_voltage(voltage):
            time.sleep(0.5)
            read_voltage()
            input(f"Press Enter to try next voltage (or Ctrl+C to exit)...")

except KeyboardInterrupt:
    print("\nProgram stopped by user")
except Exception as exc:
    print(str(exc))
finally:
    GPIO.output(TXDEN_1, GPIO.HIGH)
    GPIO.cleanup()

#22/11/2024 
#This script succesfully communicates with the Analog Output module. 
#Sends a command to set the voltage output to 1V, 2V, 3V, 4V, and 5V. 
#Then reads the current voltage setting and displays it. 
#Then waits for the user to press Enter before trying the next voltage setting.
#Stops when the user presses Ctrl+C.