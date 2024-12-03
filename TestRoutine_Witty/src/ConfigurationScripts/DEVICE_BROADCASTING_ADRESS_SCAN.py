#!/usr/bin/python
import logging
from hardware_control import RS485Device
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Device type definitions
DEVICE_TYPES = {
    0x04: "Analog Input Module",
    0x06: "Analog Output Module"
}

def interpret_response(addr, func_code, response):
    """Interpret the response from a device"""
    if not response:
        return None
        
    logging.info(f"Response from 0x{addr:02X}: {' '.join([f'{b:02X}' for b in response])}")
    
    # Check if it's an exception response
    if response[1] & 0x80:
        logging.warning(f"Exception response from device 0x{addr:02X}: {response[2]}")
        return None
        
    # Try to identify device type
    if func_code == 0x03:  # Read Holding Registers
        if len(response) >= 5:
            device_type = response[3] << 8 | response[4]
            return DEVICE_TYPES.get(device_type, "Unknown device type")
    
    return "Unknown response format"

def scan_devices():
    dev = RS485Device()
    found_devices = {}
    
    # Test addresses 1-10
    for addr in range(1, 11):
        # Test different function codes
        function_codes = [
            (0x04, "Read Input Registers"),
            (0x03, "Read Holding Registers"),
            (0x06, "Write Single Register")
        ]
        
        for func_code, desc in function_codes:
            frame = [
                addr,
                func_code,
                0x00, 0x00,  # Starting address
                0x00, 0x01   # Number of registers/Value
            ]
            
            crc = dev.calculate_crc(frame)
            frame.extend([crc & 0xFF, (crc >> 8) & 0xFF])
            
            logging.info(f"Testing address 0x{addr:02X} with {desc} (0x{func_code:02X})")
            response = dev.send_command(addr, frame)
            
            if response:
                device_type = interpret_response(addr, func_code, response)
                if device_type:
                    found_devices[addr] = device_type
                time.sleep(0.2)
    
    # Summary
    if found_devices:
        logging.info("\nFound devices:")
        for addr, device_type in found_devices.items():
            logging.info(f"Address 0x{addr:02X}: {device_type}")
    else:
        logging.info("\nNo devices found")

if __name__ == "__main__":
    try:
        scan_devices()
    except KeyboardInterrupt:
        logging.info("Scan interrupted by user")
    except Exception as e:
        logging.error(f"Error during scan: {e}")
        raise