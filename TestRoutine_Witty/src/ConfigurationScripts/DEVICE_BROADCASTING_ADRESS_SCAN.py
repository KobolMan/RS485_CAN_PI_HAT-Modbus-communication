#!/usr/bin/python
# -*- coding:utf-8 -*-

import time
import logging
from hardware_control_singleBus import RS485Base

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeviceScanner:
    def __init__(self, port="/dev/ttySC0", baudrate=9600, txden_pin=27):
        self.rs485 = RS485Base(port, baudrate, txden_pin)
        
    def scan_devices(self, start_addr=1, end_addr=20):
        """Scan for devices in address range"""
        found_devices = []
        
        for addr in range(start_addr, end_addr + 1):
            logger.info(f"\nScanning address {addr}")
            
            # Function code 0x04 (Read Input Registers)
            command = [
                addr,           # Slave address
                0x04,          # Function code
                0x00, 0x00,    # Start register
                0x00, 0x01     # Number of registers
            ]
            
            # Add CRC
            crc = self.rs485.calculate_crc(command)
            command.extend([crc & 0xFF, (crc >> 8) & 0xFF])
            
            # Send command
            response = self.rs485.send_command(bytes(command))
            
            if response:
                found_devices.append(addr)
                
        return found_devices
        
    def close(self):
        """Close RS485 connection"""
        self.rs485.close()

def main():
    try:
        scanner = DeviceScanner()
        logger.info("Starting RS485 Modbus scan...")
        
        # Scan for devices
        found_devices = scanner.scan_devices()
        
        # Report results
        logger.info(f"\nFound devices at addresses: {found_devices}")
        
    except Exception as e:
        logger.error(f"Error during scan: {str(e)}")
    finally:
        if 'scanner' in locals():
            scanner.close()

if __name__ == "__main__":
    main()