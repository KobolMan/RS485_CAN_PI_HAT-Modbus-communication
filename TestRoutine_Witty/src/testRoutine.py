##To execute the scripts from Raspberry, remember to enable the venv using rs485 command on terminal.

#Changelog
##V1.0.0 - 2024-12-01 - Initial release
##implementing the new hardware_control_singleBus.py
##implementing the new testRoutine.py based on the hardware PCB board rev 1.4
##implementing the new EXT_BUTTON.py based on the hardware PCB board rev 1.4. The external button (connected to GPIO 18)
##is used to start the test sequence triggered as a callback function. 
#implementing the new I2C_Display.py based on the hardware PCB board rev 1.4. The I2C grove LCD display is used to show the test sequence status.


#The test sequence is composed of the following steps:
#1. Temperature Test: Read the temperature sensor (TP_1) and convert the voltage to temperature in Celsius.
#2. Voltage Sense Test: Check the voltage sense (ADC_2) in three steps:
#   2.1 Initial voltage sense check (should be below 0.1V)
#   2.2 CHG_EN voltage sense check (5V)
#   2.3 OV Protection check: Turn off DAC_1 (LDO, 12V output to VBUS_IN) and turn on DAC_6 (PS, 24V output to VBUS_IN). The voltage sense reading should be below 0.1V.
#3. OC Protection Test: Turn on DAC_2 (3V output to Q1 Mosfet that forces 120mA on R6 and R7) and reads the current sense (TP_3) to check if it matches.
#4. 3.3V Rail Test: Read the 3.3V rail voltage (TP_23) and check if it is in the range 3.2-3.5V.
#5. CC Test: Check the CC_1 and CC_2 voltage sense (ADC_4 and ADC_5) in two steps:
#   5.1 CC ON State Test: Turn on CC_1 and CC_2 (3.3V) and check if the voltage sense reading is in the range 3.2-3.5V.
#   5.2 CC OFF State Test: Turn off CC_1 and CC_2 (0.5V) and check if the voltage sense reading is below 0.1V.
#6. User Button Test: Read from user button voltage divider (TP_9_FUNC_BTN) and check if it is in acceptable range 3.0-3.5V.

#If all tests pass, the program will execute the flash-wittyc.sh script to flash the WittyC board. If any test fails, the program will stop the test sequence and display the failed test.



#!/usr/bin/python
# -*- coding:utf-8 -*-

import time
import math
import logging
import signal
import subprocess
import RPi.GPIO as GPIO
from hardware_control_singleBus import HardwareControl
from I2C_Display import GroveLCD

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants for ERT-J1VG103JA thermistor
BETA = 3435  
R0 = 10000   # 10kΩ at 25°C
T0 = 298.15  # 25°C in Kelvin
VIN = 3.3    
RFIXED = 10000


# Button GPIO pin
BUTTON_PIN = 18

# Flags to control program execution
running = True
test_in_progress = False


class TestDisplay:
    def __init__(self):
        self.lcd = GroveLCD()
        self.clear()
        self.show_ready()
    
    def clear(self):
        self.lcd.clear()
    
    def show_ready(self):
        self.lcd.write("WittyC Testboard", 0)
        self.lcd.write("Ready to test", 1)
    
    def show_test_status(self, test_name, status="Running"):
        self.lcd.clear()
        self.lcd.write(f"Test: {test_name}", 0)
        self.lcd.write(status, 1)
    
    def show_result(self, passed):
        self.lcd.clear()
        self.lcd.write("Test Complete:", 0)
        status = "PASSED" if passed else "FAILED"
        self.lcd.write(status, 1, start_col=16-len(status))

def run_flash_script():
    """Execute the flash-wittyc.sh script"""
    try:
        logger.info("All tests passed - Starting flash process...")
        result = subprocess.run(['./flash-wittyc.sh'], 
                              check=True,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True)
        logger.info("Flash completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Flash failed with error: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Failed to execute flash script: {str(e)}")
        return False
    
def run_test_sequence(hw_control):
    """Execute complete test sequence"""
    global test_in_progress
    
    if test_in_progress:
        logger.info("Test already in progress")
        return
        
    test_in_progress = True
    all_tests_passed = True
    
    try:
        # Power up sequence
        hw_control.SetVoltage(1, 5000)  # DAC_1 ON (12V LDO enable)
        time.sleep(.1)  # Wait for power stabilization
        
        # Sequential test execution
        tests = [
            ("Temperature Test", temp_test),
            ("Voltage Sense Test", voltage_sense_test),
            ("OC Protection Test", oc_protection_test),
            ("3.3V Rail Test", v3v_test),
            ("CC Test", cc_test),
            ("User Button Test", user_button_test)
        ]
        
        for test_name, test_func in tests:
            logger.info(f"\nExecuting {test_name}")
            if not test_func(hw_control):
                logger.error(f"{test_name} failed - stopping test sequence")
                all_tests_passed = False
                break
            time.sleep(0.05)
        
        # Run flash script if all tests passed
        if all_tests_passed:
            if not run_flash_script():
                logger.error("Flash process failed")
                all_tests_passed = False
    
    finally:
        # Safe shutdown
        hw_control.SetVoltage(1, 0)  # DAC_1 OFF
        test_in_progress = False
        status = "PASSED" if all_tests_passed else "FAILED"
        logger.info(f"Test sequence completed - {status}")

def button_callback(channel):
    """Interrupt handler for button press"""
    if GPIO.input(BUTTON_PIN) == GPIO.LOW:  # Button pressed
        logger.info("Button pressed - initiating test sequence")
        try:
            hw_control = HardwareControl(
                port="/dev/ttySC0",
                baudrate=9600,
                txden_pin=27
            )
            run_test_sequence(hw_control)
        except Exception as e:
            logger.error(f"Test error: {str(e)}")
        finally:
            if 'hw_control' in locals():
                hw_control.close()

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    global running
    logger.info("\nExiting program")
    running = False


def voltage_to_temp(voltage):
    if voltage <= 0:
        return float('inf')
    r_therm = RFIXED * (VIN / voltage - 1)
    temp_k = 1 / (1 / T0 + 1 / BETA * math.log(r_therm / R0))
    return temp_k - 273.15

def temp_test(hw_control):
    """Step 1: Temperature Test"""
    logger.info("Step 1: Temperature Test")
    voltage = hw_control.ReadVoltage(1)  # TP_1
    if voltage is None:
        logger.error("Failed to read temperature sensor")
        return False
    
    temperature = voltage_to_temp(voltage)
    logger.info(f"Temperature: {temperature:.2f}°C")
    
    if 12 <= temperature <= 35:
        logger.info("Temperature Test: PASS")
        return True
    logger.error("Temperature Test: FAIL")
    return False

def voltage_sense_test(hw_control):
    """Step 2: Voltage Sense Tests"""
    logger.info("Step 2: Voltage Sense Test")
    
    # Step 2.1: Initial voltage sense - expecting ~0V
    logger.info("Step 2.1: Initial voltage sense check")
    voltage = hw_control.ReadVoltage(2)  # ADC_2
    if voltage is None or voltage > 0.1:  # Pass if voltage is close to 0V
        logger.error(f"Step 2.1 Failed - Voltage: {voltage:.2f}V")
        return False
    logger.info(f"Voltage Sense (2.1): {voltage:.2f}V - PASS")
    
    # Step 2.2: CHG_EN
    logger.info("Step 2.2: CHG_EN voltage sense check")
    hw_control.SetVoltage(3, 3300)  # DAC_3 ON (CHG_EN) 
    time.sleep(0.5)
    voltage = hw_control.ReadVoltage(2)  # ADC_2
    if voltage is None or not (1.7 <= voltage <= 1.9):  #Ideally should be around 1.8V
        logger.error("Step 2.2 Failed")
        return False
    logger.info(f"Voltage Sense (2.2): {voltage:.2f}V - PASS")
    
    # Step 2.3: OV Protection test
    logger.info("Step 2.3: OV Protection check")
    hw_control.SetVoltage(1, 0)     # DAC_1 OFF (LDO)
    hw_control.SetVoltage(6, 3300)  # DAC_6 ON (PS)
    time.sleep(0.5)
    voltage = hw_control.ReadVoltage(2)  # ADC_2
    if voltage is None or voltage > 0.1:
        logger.error("Step 2.3 Failed")
        return False
    logger.info("OV Protection Test: PASS")
    
    # Restore normal state
    hw_control.SetVoltage(1, 3300)  # DAC_1 ON (LDO)
    hw_control.SetVoltage(6, 0)     # DAC_6 OFF (PS)
    return True

def oc_protection_test(hw_control):
    """Step 3: OC Protection Test"""
    logger.info("Step 3: OC Protection Test")
    
    hw_control.SetVoltage(2,3300)  # DAC_2 ON (MOSFET)
    time.sleep(0.1)  # Quick check
    current = hw_control.ReadVoltage(3)  # TP_3 (CUR_S)
    hw_control.SetVoltage(2, 0)     # DAC_2 OFF (MOSFET)
    
    if current is None or abs(current - 1.0) > 0.1:
        logger.error(f"Current sense: {current:.2f}A - FAIL")
        return False
    logger.info(f"Current sense: {current:.2f}A - PASS")
    return True

def v3v_test(hw_control):
    """Step 4: 3.3V Rail Test"""
    logger.info("Step 4: 3.3V Rail Test")
    voltage = hw_control.ReadVoltage(7)  # TP_13 -> ADC_7
    if voltage is None or not (3.2 <= voltage <= 3.5):
        logger.error(f"3.3V Rail: {voltage:.2f}V - FAIL")
        return False
    logger.info(f"3.3V Rail: {voltage:.2f}V - PASS")
    return True

def cc_test(hw_control):
    """Step 5: CC Test"""
    logger.info("Step 5: CC Test")
    
    # CC ON state test
    hw_control.SetVoltage(4, 3300)  # CC_2 (TP_7)
    hw_control.SetVoltage(5, 3300)  # CC_1 (TP_8)
    time.sleep(0.5)
    
    cc2_voltage = hw_control.ReadVoltage(4)  # ADC_4
    cc1_voltage = hw_control.ReadVoltage(5)  # ADC_5
    
    if cc1_voltage is None or cc2_voltage is None or \
       not (3.0 <= cc1_voltage <= 3.6) or not (3.0 <= cc2_voltage <= 3.6):
        logger.error("CC ON State Test Failed")
        return False
    logger.info("CC ON State Test: PASS")
    
    # CC OFF state test
    hw_control.SetVoltage(4, 500)   # CC_2 = 0.5V
    hw_control.SetVoltage(5, 500)   # CC_1 = 0.5V
    time.sleep(0.5)
    
    cc2_voltage = hw_control.ReadVoltage(4)
    cc1_voltage = hw_control.ReadVoltage(5)
    
    if cc1_voltage > 0.1 or cc2_voltage > 0.1:
        logger.error("CC OFF State Test Failed")
        return False
    logger.info("CC OFF State Test: PASS")
    return True

def user_button_test(hw_control):
    """Step 6: User Button Test"""
    logger.info("Step 6: User Button Test")
    button_voltage = hw_control.ReadVoltage(6)  # TP_9_FUNC_BTN -> ADC_6
    if button_voltage is None or not (3.0 <= button_voltage <= 3.6):
        logger.error("User Button Test Failed")
        return False
    logger.info("User Button Test: PASS")
    return True

def main():
    try:
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Setup interrupt
        GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, 
                            callback=button_callback, 
                            bouncetime=200)
        
        # Setup signal handler
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.info("Ready for testing. Press button to start test sequence.")
        logger.info("Press Ctrl+C to exit")
        
        # Keep program running
        while running:
            time.sleep(0.1)
            
    except Exception as e:
        logger.error(f"Program error: {str(e)}")
    finally:
        GPIO.cleanup()
        logger.info("Program terminated")

if __name__ == "__main__":
    main()






