#!/usr/bin/python
# -*- coding:utf-8 -*-

import logging
from hardware_control_singleBus import RS485Base
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RS485Scanner:
    def __init__(self, port="/dev/ttySC0", baudrate=9600, txden_pin=27):
        self.rs485 = RS485Base(port=port, baudrate=baudrate, txden_pin=txden_pin)
    
    def scan(self, start_addr=1, end_addr=10):
        """Scan RS485 bus for devices"""
        found_devices = []
        
        for addr in range(start_addr, end_addr + 1):
            logger.info(f"\nScanning address {addr}")
            
            # Build command - Function code 0x04 (Read Input Registers)
            command = [
                addr,           # Slave address
                0x04,          # Function code
                0x00, 0x00,    # Starting register
                0x00, 0x01     # Number of registers
            ]
            
            # Calculate and append CRC
            crc = self.rs485.calculate_crc(command)
            command.extend([crc & 0xFF, (crc >> 8) & 0xFF])
            
            # Send command and check response
            response = self.rs485.send_command(bytes(command))
            if response:
                found_devices.append(addr)
                logger.info(f"Device found at address {addr}")
        
        return found_devices
    
    def close(self):
        """Cleanup resources"""
        self.rs485.close()

def main():
    try:
        print("Starting RS485 Modbus scan...")
        scanner = RS485Scanner()
        
        # Scan addresses 1-10 (adjust range as needed)
        devices = scanner.scan(start_addr=0, end_addr=15)
        
        if devices:
            print("\nFound devices at addresses:", devices)
        else:
            print("\nNo devices found")
            
    except KeyboardInterrupt:
        print("\nScan interrupted by user")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        if 'scanner' in locals():
            scanner.close()

if __name__ == "__main__":
    main()