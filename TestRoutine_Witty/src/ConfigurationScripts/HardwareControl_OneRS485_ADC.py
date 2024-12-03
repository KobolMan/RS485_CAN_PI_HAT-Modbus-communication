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
        
    def send_command(self, command):
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

class AnalogInput:
    def __init__(self, device, slave_address=0x02):
        self.device = device
        self.slave_address = slave_address

    def set_data_type(self, channel, data_type):
        """Set the data type for the specified channel."""
        # Register address starts from 0x1000
        register_address = 0x1000 + (channel - 1)
        high_addr = (register_address >> 8) & 0xFF
        low_addr = register_address & 0xFF

        high_data = (data_type >> 8) & 0xFF
        low_data = data_type & 0xFF

        command = [self.slave_address, 0x06, high_addr, low_addr, high_data, low_data]
        crc = calculate_crc(command)
        command.extend([crc & 0xFF, (crc >> 8) & 0xFF])
        command_bytes = bytes(command)

        response = self.device.send_command(command_bytes)
        # Check response if needed
        return response

    def read_voltage(self, channel):
        """Read voltage from the specified channel."""
        # Read input register starting at channel address
        register_address = channel - 1  # Channels are 0-indexed in registers
        high_addr = (register_address >> 8) & 0xFF
        low_addr = register_address & 0xFF

        command = [
            self.slave_address, 0x04, high_addr, low_addr, 0x00, 0x01
        ]  # Read 1 register
        crc = calculate_crc(command)
        command.extend([crc & 0xFF, (crc >> 8) & 0xFF])
        command_bytes = bytes(command)

        response = self.device.send_command(command_bytes)

        if response and len(response) >= 7:
            if response[0] == self.slave_address and response[1] == 0x04:
                byte_count = response[2]
                if byte_count == 2:
                    high_data = response[3]
                    low_data = response[4]
                    value = (high_data << 8) | low_data

                    # Convert value to voltage based on data type
                    # Assuming data type is 0x0000: 0~5V range, output in mV
                    voltage_mv = value  # Value represents mV in this data type
                    voltage = voltage_mv / 1000.0
                    print(f"Channel {channel} Voltage: {voltage:.3f} V")
                    return voltage
                else:
                    print("Unexpected byte count in response")
            else:
                print("Invalid response or incorrect slave address/function code")
        else:
            print("No valid response or insufficient data received")
        return None

try:
    print("Initializing RS485 device...")

    device = RS485Device("/dev/ttySC0", txden_pin=27)

    analog_in = AnalogInput(device, slave_address=0x02)  # Adjust slave_address if necessary

    # Set data type for channel 1 to 0~5V (data type code 0x0000)
    print("\nSetting data type for Channel 1 to 0~5V...")
    analog_in.set_data_type(channel=1, data_type=0x0000)

    # Read voltage from channel 1
    print("\nReading voltage from Channel 1:")
    voltage = analog_in.read_voltage(channel=1)

except KeyboardInterrupt:
    print("\nProgram stopped by user")
except Exception as exc:
    print(f"An error occurred: {exc}")
finally:
    device.close()
    GPIO.cleanup()