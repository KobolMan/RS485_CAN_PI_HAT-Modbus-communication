#!/usr/bin/python
# -*- coding: utf-8 -*-

import serial
import RPi.GPIO as GPIO
import time
import os
import sys
import logging
from typing import Optional, Union, List

logging.basicConfig(level=logging.INFO)
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

logger = logging.getLogger(__name__)

class RS485Base:
    def __init__(self, port: str = "/dev/ttySC0", baudrate: int = 9600, txden_pin: int = 27):
        self.port = port
        self.baudrate = baudrate
        self.txden_pin = txden_pin
        self._setup_gpio()
        self._setup_serial()
        
    def _setup_gpio(self) -> None:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.txden_pin, GPIO.OUT)
        GPIO.output(self.txden_pin, GPIO.HIGH)
        
    def _setup_serial(self) -> None:
        try:
            from waveshare_2_CH_RS485_HAT import config
            self.ser = config.config(dev=self.port, Baudrate=self.baudrate).serial
            logger.info(f"Initialized RS485 device on {self.port} with baudrate {self.baudrate}")
        except Exception as e:
            logger.error(f"Failed to initialize serial communication: {e}")
            raise

    def send_command(self, command: bytes) -> Optional[bytearray]:
        try:
            GPIO.output(self.txden_pin, GPIO.LOW)
            time.sleep(0.01)
            
            self.ser.write(command)
            logger.debug(f"Sent: {' '.join(f'{b:02X}' for b in command)}")
            
            time.sleep(0.01)
            GPIO.output(self.txden_pin, GPIO.HIGH)
            time.sleep(0.05)
            
            response = bytearray()
            timeout = time.time() + 0.1
            
            while time.time() < timeout:
                if self.ser.in_waiting:
                    response.extend(self.ser.read(self.ser.in_waiting))
                    break
                time.sleep(0.005)
            
            if response:
                logger.debug(f"Received: {' '.join(f'{b:02X}' for b in response)}")
                return response
            
            logger.warning("No response received")
            return None
            
        except Exception as e:
            logger.error(f"Error in send_command: {e}")
            return None

    @staticmethod
    def calculate_crc(data: List[int]) -> int:
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

    def close(self) -> None:
        self.ser.close()
        GPIO.cleanup()
        logger.info("Closed RS485 device")

class DACController:
    def __init__(self, rs485: RS485Base, slave_address: int = 0x01):
        self.rs485 = rs485
        self.slave_address = slave_address
    
    def set_voltage(self, channel: int, voltage_mv: int) -> Optional[bytearray]:
        if not 1 <= channel <= 8:
            logger.error(f"Invalid DAC channel: {channel}")
            return None
            
        voltage_hex = voltage_mv & 0xFFFF
        high_byte = (voltage_hex >> 8) & 0xFF
        low_byte = voltage_hex & 0xFF
        
        register_address = channel - 1
        high_addr = (register_address >> 8) & 0xFF
        low_addr = register_address & 0xFF
        
        command = [
            self.slave_address,
            0x06,
            high_addr,
            low_addr,
            high_byte,
            low_byte
        ]
        
        crc = self.rs485.calculate_crc(command)
        command.extend([crc & 0xFF, (crc >> 8) & 0xFF])
        
        response = self.rs485.send_command(bytes(command))
        
        if self._validate_dac_response(response, channel, voltage_mv):
            return response
        return None
        
    def _validate_dac_response(self, response: Optional[bytearray], 
                             channel: int, voltage_mv: int) -> bool:
        if response and len(response) >= 8:
            if response[0] == self.slave_address and response[1] == 0x06:
                logger.info(f"Set DAC Channel {channel} to {voltage_mv/1000.0:.3f}V")
                return True
        return False

class ADCController:
    def __init__(self, rs485: RS485Base, slave_address: int = 0x02):
        self.rs485 = rs485
        self.slave_address = slave_address
        self._initialize_channels()
    
    def _initialize_channels(self) -> None:
        self.set_data_type(channel=1, data_type=0x0000)
    
    def set_data_type(self, channel: int, data_type: int) -> Optional[bytearray]:
        register_address = 0x1000 + (channel - 1)
        high_addr = (register_address >> 8) & 0xFF
        low_addr = register_address & 0xFF
        
        high_data = (data_type >> 8) & 0xFF
        low_data = data_type & 0xFF
        
        command = [self.slave_address, 0x06, high_addr, low_addr, high_data, low_data]
        crc = self.rs485.calculate_crc(command)
        command.extend([crc & 0xFF, (crc >> 8) & 0xFF])
        
        return self.rs485.send_command(bytes(command))
    
    def read_voltage(self, channel: int) -> Optional[float]:
        register_address = channel - 1
        high_addr = (register_address >> 8) & 0xFF
        low_addr = register_address & 0xFF
        
        command = [
            self.slave_address,
            0x04,
            high_addr,
            low_addr,
            0x00,
            0x01
        ]
        
        crc = self.rs485.calculate_crc(command)
        command.extend([crc & 0xFF, (crc >> 8) & 0xFF])
        
        response = self.rs485.send_command(bytes(command))
        return self._process_adc_response(response, channel)
    
    def _process_adc_response(self, response: Optional[bytearray], 
                            channel: int) -> Optional[float]:
        if response and len(response) >= 7:
            if response[0] == self.slave_address and response[1] == 0x04:
                if response[2] == 2:
                    value = (response[3] << 8) | response[4]
                    voltage = value / 1000.0
                    logger.info(f"ADC Channel {channel} Voltage: {voltage:.3f}V")
                    return voltage
        return None

class HardwareControl:
    def __init__(self, port: str = "/dev/ttySC0", baudrate: int = 9600, 
                 txden_pin: int = 27):
        self.rs485 = RS485Base(port=port, baudrate=baudrate, txden_pin=txden_pin)
        self.dac = DACController(rs485=self.rs485, slave_address=0x01)
        self.adc = ADCController(rs485=self.rs485, slave_address=0x02)
    
    def close(self) -> None:
        self.rs485.close()

def main():
    try:
        hardware = HardwareControl()
        
        print("\nSetting voltages on DAC channels...")
        hardware.dac.set_voltage(channel=1, voltage_mv=5000)  # 5V
        hardware.dac.set_voltage(channel=2, voltage_mv=3000)  # 3V
        
        print("\nReading voltages from ADC channels...")
        hardware.adc.read_voltage(channel=1)
        hardware.adc.read_voltage(channel=2)
        
    except KeyboardInterrupt:
        print("\nProgram stopped by user")
    except Exception as exc:
        logger.error(f"An error occurred: {exc}", exc_info=True)
    finally:
        if 'hardware' in locals():
            hardware.close()

if __name__ == "__main__":
    main()

#This script offers an HL for the RS485 HAT, which can be used to control the DAC and ADC channels when connected to a single RS485 bus. Note: DAC slave addrs = 0x01, ADC slave addrs = 0x02