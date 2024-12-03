#!/usr/bin/python
# -*- coding:utf-8 -*-
import serial
import RPi.GPIO as GPIO
import time
import os
import sys
import logging
import hardware_control_singleBus

logging.basicConfig(level=logging.INFO)
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_2_CH_RS485_HAT import config

if __name__ == "__main__":
    try:
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        
        # Create hardware control instance
        hardware = hardware_control_singleBus(
            port="/dev/ttySC0",
            baudrate=9600,
            txden_pin=27,
            dac_slave_address=0x01,
            adc_slave_address=0x02
        )

        # Set DAC channels
        print("\nSetting DAC Channel 1 to 5V...")
        hardware.SetVoltage(channel=1, voltage_mv=5000)
        time.sleep(0.1)  # Small delay between operations
        
        print("\nSetting DAC Channel 2 to 3V...")
        hardware.SetVoltage(channel=2, voltage_mv=3000)
        time.sleep(0.1)

        # Read ADC channels
        print("\nReading ADC Channel 4 Voltage...")
        voltage_ch4 = hardware.ReadVoltage(channel=4)
        if voltage_ch4 is not None:
            print(f"ADC Channel 4 reading: {voltage_ch4:.3f}V")
        
        time.sleep(0.1)
        
        print("\nReading ADC Channel 5 Voltage...")
        voltage_ch5 = hardware.ReadVoltage(channel=5)
        if voltage_ch5 is not None:
            print(f"ADC Channel 5 reading: {voltage_ch5:.3f}V")

    except KeyboardInterrupt:
        print("\nProgram stopped by user.")
    except Exception as exc:
        print(f"An error occurred: {exc}")
        logging.exception("Detailed error information:")
    finally:
        # Close hardware
        if 'hardware' in locals():
            hardware.close()