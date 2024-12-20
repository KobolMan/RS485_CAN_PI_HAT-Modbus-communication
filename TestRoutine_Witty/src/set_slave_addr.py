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

def calculate_crc(data):
    crc = 0xFFFF
    for pos in data:
        crc ^= pos
        for _ in range(8):
            if (crc & 1) != 0:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc

class RS485Device:
    def __init__(self, port="/dev/ttySC0", baudrate=9600, txden_pin=27):
        self.txden_pin = txden_pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.txden_pin, GPIO.OUT)
        GPIO.output(self.txden_pin, GPIO.HIGH)

        self.ser = config.config(dev=port, Baudrate=baudrate).serial

    def send_command(self, command):
        GPIO.output(self.txden_pin, GPIO.LOW)  # Enable transmitter
        time.sleep(0.01)
        self.ser.write(command)
        print("Sent:", ' '.join(f'{b:02X}' for b in command))
        time.sleep(0.01)

        GPIO.output(self.txden_pin, GPIO.HIGH)  # Disable transmitter
        time.sleep(0.05)

        # Devices do not respond to broadcast commands; no need to read response
        return True

    def close(self):
        self.ser.close()
        GPIO.cleanup()

if __name__ == "__main__":
    try:
        print("Setting ADC device address to 0x02...")
        device = RS485Device(port="/dev/ttySC0", baudrate=9600, txden_pin=27)

        # Broadcast address is 0x00
        broadcast_address = 0x00

        # Modbus function code 0x06 (Write Single Register)
        function_code = 0x06

        # Register address for setting device address is 0x4000
        register_address = 0x4000
        register_hi = (register_address >> 8) & 0xFF
        register_lo = register_address & 0xFF

        # New device address to set (0x02)
        new_device_address = 0x0001
        data_hi = (new_device_address >> 8) & 0xFF
        data_lo = new_device_address & 0xFF

        # Construct the command
        command = [
            broadcast_address,
            function_code,
            register_hi,
            register_lo,
            data_hi,
            data_lo
        ]

        # Calculate CRC
        crc = calculate_crc(command)
        crc_lo = crc & 0xFF
        crc_hi = (crc >> 8) & 0xFF
        command.extend([crc_lo, crc_hi])

        # Convert to bytes
        command_bytes = bytes(command)

        # Send the command
        device.send_command(command_bytes)

        print("\nADC device address has been set to 0x02 (Modbus ID 2).")
        print("Please reconnect the DAC device to the RS485 bus.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        device.close()

##This script was succesfully used to set the ADC device address to 0x02 (Modbus ID 2) on the RS485 bus. The DAC device was then reconnected to the bus. Note, we're broadcasting the message so the DAC needs to be disconnected.