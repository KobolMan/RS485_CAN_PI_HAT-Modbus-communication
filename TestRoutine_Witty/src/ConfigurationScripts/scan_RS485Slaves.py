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

class RS485Scanner:
    def __init__(self, port="/dev/ttySC0", baudrate=9600, txden_pin=27):
        self.txden_pin = txden_pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.txden_pin, GPIO.OUT)
        GPIO.output(self.txden_pin, GPIO.HIGH)

        self.ser = config.config(dev=port, Baudrate=baudrate).serial

    def scan(self, start_addr=1, end_addr=247):
        found_devices = []
        for addr in range(start_addr, end_addr + 1):
            print(f"\nScanning address {addr}")
            command = [addr, 0x04, 0x00, 0x00, 0x00, 0x01]  # Function code 0x04 (Read Input Registers)
            crc = calculate_crc(command)
            command.extend([crc & 0xFF, (crc >> 8) & 0xFF])

            if self.send_command(bytes(command)):
                found_devices.append(addr)
        return found_devices

    def send_command(self, command):
        GPIO.output(self.txden_pin, GPIO.LOW)  # Enable transmitter
        time.sleep(0.01)
        self.ser.write(command)
        print("Sent:", ' '.join(f'{b:02X}' for b in command))
        time.sleep(0.01)

        GPIO.output(self.txden_pin, GPIO.HIGH)  # Disable transmitter
        time.sleep(0.05)

        response = bytearray()
        timeout = time.time() + 0.1  # 100ms timeout
        while time.time() < timeout:
            if self.ser.in_waiting:
                response.extend(self.ser.read(self.ser.in_waiting))
                break
            time.sleep(0.005)

        if response:
            print("Received:", ' '.join(f'{b:02X}' for b in response))
            return True
        else:
            print("No response from address.")
            return False

    def close(self):
        self.ser.close()
        GPIO.cleanup()

if __name__ == "__main__":
    try:
        print("Starting RS485 Modbus scan...")
        scanner = RS485Scanner(port="/dev/ttySC0", baudrate=9600, txden_pin=27)
        devices = scanner.scan(start_addr=1, end_addr=10)  # Adjust the range as needed
        print("\nFound devices at addresses:", devices)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        scanner.close()