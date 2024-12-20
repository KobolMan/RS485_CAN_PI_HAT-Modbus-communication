#!/usr/bin/python
# -*- coding:utf-8 -*-

from hardware_control_singleBus import RS485Base, DACController
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        # Initialize RS485 communication
        rs485 = RS485Base(
            port="/dev/ttySC0",
            baudrate=9600,
            txden_pin=27
        )
        
        # Create DAC controller with default slave address (0x01)
        dac = DACController(rs485)
        
        # Set DAC channel 1 to 3000mV (3V)
        logger.info("Setting DAC1 to 0V...")
        dac.set_voltage(channel=1, voltage_mv=0)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
    finally:
        # Cleanup
        if 'rs485' in locals():
            rs485.close()

if __name__ == "__main__":
    main()