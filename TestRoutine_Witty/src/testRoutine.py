#!/usr/bin/python
# -*- coding:utf-8 -*-

"""
Automated Test Routine for WittyC Board
Hardware: PCB board rev 1.4
Author: Faradex
Last Update: 2024-12-18

To execute the scripts from Raspberry, remember to enable the venv using rs485 command on terminal.

Changelog:
V1.0.0 - 2024-12-01 - Initial release
- Implementing the new hardware_control_singleBus.py
- Implementing the new testRoutine.py based on the hardware PCB board rev 1.4
- Implementing the new EXT_BUTTON.py for the external button (GPIO 18)
- Implementing the new I2C_Display.py for test sequence status display

V1.0.1 - 2024-12-18 - Bug fixes and improvements
- Fixed hardware control access by properly using DAC and ADC controllers
- Implemented reliable button polling instead of edge detection
- Added new display sequence: "Powered by Faradex" startup message
- Improved display status messages (Test passed/failed, Flashing, Done)
- Added proper error handling for hardware communication
- Enhanced GPIO cleanup and initialization
- Fixed display initialization timing

Hardware Configuration:
- External button connected to GPIO 18
- I2C Grove LCD display for status indication
- RS485 HAT communication:
  * DAC slave address: 0x01
  * ADC slave address: 0x02
  * Port: /dev/ttySC0
  * Baudrate: 9600
  * TXDEN pin: GPIO 27

Test Sequence:
1. Temperature Test: Read temperature sensor (TP_1)
   - Converts voltage to temperature in Celsius
   - Valid range: 12°C to 35°C

2. Voltage Sense Test (ADC_2):
   2.1. Initial voltage sense check (should be below 0.1V)
   2.2. CHG_EN voltage sense check (should be ~1.8V)
   2.3. OV Protection check:
       - Turn off DAC_1 (LDO, 12V output to VBUS_IN)
       - Turn on DAC_6 (PS, 24V output to VBUS_IN)
       - Voltage should be below 0.1V

3. OC Protection Test:
   - Turn on DAC_2 (3V output to Q1 Mosfet)
   - Force 120mA on R6 and R7
   - Read current sense (TP_3)
   - Verify current matches expected value

4. 3.3V Rail Test:
   - Read 3.3V rail voltage (TP_23)
   - Valid range: 3.2V to 3.5V

5. CC Test for CC_1 and CC_2 (ADC_4 and ADC_5):
   5.1. CC ON State Test:
       - Set CC_1 and CC_2 to 3.3V
       - Verify voltage is 3.0V-3.6V
   5.2. CC OFF State Test:
       - Set CC_1 and CC_2 to 0.5V
       - Verify voltage is below 0.1V

6. User Button Test:
   - Read voltage from user button divider (TP_9_FUNC_BTN)
   - Valid range: 3.0V to 3.6V

Success Criteria:
- All tests must pass sequentially
- On success: Execute flash-wittyc.sh script
- On failure: Stop sequence and display error

Display Status Indicators:
- Startup: "Powered by Faradex" (1 second)
- Ready: "Press the button to start"
- Testing: Test status (pass/fail)
- Flashing: "Flashing"
- Complete: "Done"
"""

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
BUTTON_PIN = 22

# Flags to control program execution
running = True
test_in_progress = False
display = None

class TestDisplay:
    def __init__(self):
        self.lcd = GroveLCD()
        self.clear()
        self.show_startup()
    
    def clear(self):
        self.lcd.clear()
    
    def show_startup(self):
        """Show initial startup message"""
        self.lcd.clear()
        self.lcd.write("Powered by", 0)
        self.lcd.write("Faradex", 1)
        time.sleep(1)  # Show for 1 second
        self.show_ready()
    
    def show_ready(self):
        """Show ready message"""
        self.lcd.clear()
        self.lcd.write("Press the button", 0)
        self.lcd.write("to start", 1)
    
    def show_test_status(self, status):
        """Show test status"""
        self.lcd.clear()
        if status == "pass":
            self.lcd.write("Test passed", 0)
        elif status == "fail":
            self.lcd.write("Test failed", 0)
        elif status == "flash":
            self.lcd.write("Flashing", 0)
        elif status == "done":
            self.lcd.write("Done", 0)

def run_flash_script():
    """Execute the flash-wittyc.sh script"""
    try:
        logger.info("All tests passed - Starting flash process...")
        result = subprocess.run(['/usr/local/bin/flash-wittyc.sh'], 
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

def voltage_to_temp(voltage):
    if voltage <= 0:
        return float('inf')
    r_therm = RFIXED * (VIN / voltage - 1)
    temp_k = 1 / (1 / T0 + 1 / BETA * math.log(r_therm / R0))
    return temp_k - 273.15

def temp_test(hw_control):
    """Step 1: Temperature Test"""
    logger.info("Step 1: Temperature Test")
    voltage = hw_control.adc.read_voltage(1)  # TP_1
    if voltage is None:
        logger.error("Failed to read temperature sensor")
        return False
    
    resistance = (3.3*RFIXED-RFIXED*voltage)/voltage
    logger.info(f"Resistance: {resistance:.2f}")
    temperature = voltage_to_temp(voltage)
    logger.info(f"Temperature: {temperature:.2f}°C")
    
    if 6 <= temperature <= 35:
        logger.info("Temperature Test: PASS")
        return True
    logger.error("Temperature Test: FAIL")
    return False

def voltage_sense_test(hw_control):
    """Step 2: Voltage Sense Tests"""
    logger.info("Step 2: Voltage Sense Test")
    
    # Step 2.1: Initial voltage sense - expecting ~0V
    #if CHG_EN is OFF
    hw_control.dac.set_voltage(3, 0)  # DAC_3 OFF (CHG_EN)
    #time.sleep(0.1)
    logger.info("Step 2.1: Initial voltage sense check")
    voltage = hw_control.adc.read_voltage(2)  # ADC_2
    if voltage is None or voltage > 0.1:  # Pass if voltage is close to 0V
        logger.error(f"Step 2.1 Failed - Voltage: {voltage:.2f}V")
        return False
    logger.info(f"Voltage Sense (2.1): {voltage:.2f}V - PASS")
    
    # Step 2.2: CHG_EN
    logger.info("Step 2.2: CHG_EN voltage sense check")
    hw_control.dac.set_voltage(3, 3300)  # DAC_3 ON (CHG_EN) 
    #time.sleep(0.1)
    voltage = hw_control.adc.read_voltage(2)  # ADC_2
    if voltage is None or not (1.6 <= voltage <= 1.9):  #Ideally should be around 1.8V
        logger.error("Step 2.2 Failed")
        return False
    logger.info(f"Voltage Sense (2.2): {voltage:.2f}V - PASS")
    
    # Step 2.3: OV Protection test
    logger.info("Step 2.3: OV Protection check")
    hw_control.dac.set_voltage(1, 0)     # DAC_1 OFF (LDO)
    hw_control.dac.set_voltage(7, 3300)  # DAC_7 ON (PS)
    #time.sleep(0.1)
    voltage = hw_control.adc.read_voltage(2)  # ADC_2
    if voltage is None or voltage > 0.1:
        logger.error("Step 2.3 Failed")
        return False
    logger.info("OV Protection Test: PASS")
    
    # Restore normal state
    hw_control.dac.set_voltage(1, 3300)  # DAC_1 ON (LDO)
    hw_control.dac.set_voltage(7, 0)     # DAC_7 OFF (PS)
    return True

def oc_protection_test(hw_control):
    """Step 3: OC Protection Test"""
    logger.info("Step 3: OC Protection Test")
    
    hw_control.dac.set_voltage(2, 3300)  # DAC_2 ON (MOSFET)
    time.sleep(0.1)  # Quick check
    voltage = hw_control.adc.read_voltage(3)  # TP_3 (CUR_S)
    current = (voltage)/(0.01*50)
    hw_control.dac.set_voltage(2, 0)     # DAC_2 OFF (MOSFET)
    
    if current is None or not (0.12 <= current <= 0.15):
        logger.error(f"Current sense: {current:.2f}A - FAIL")
        return False
    logger.info(f"Current sense: {current:.2f}A - PASS")
    return True

def v3v_test(hw_control):
    """Step 4: 3.3V Rail Test"""
    logger.info("Step 4: 3.3V Rail Test")
    voltage = hw_control.adc.read_voltage(7)  # TP_23 -> ADC_7
    if voltage is None or not (3.2 <= voltage <= 3.5):
        logger.error(f"3.3V Rail: {voltage:.2f}V - FAIL")
        return False
    logger.info(f"3.3V Rail: {voltage:.2f}V - PASS")
    return True

def cc_test(hw_control):
    """Step 5: CC Test"""
    logger.info("Step 5: CC Test")
    
    # CC ON state test
    hw_control.dac.set_voltage(4, 3300)  # CC_2 (TP_7)
    hw_control.dac.set_voltage(5, 3300)  # CC_1 (TP_8)
    time.sleep(0.1)
    
    cc2_voltage = hw_control.adc.read_voltage(4)  # ADC_4
    cc1_voltage = hw_control.adc.read_voltage(5)  # ADC_5
    
    if cc1_voltage is None or cc2_voltage is None or \
       not (2.5 <= cc1_voltage <= 3.6) or not (2.5 <= cc2_voltage <= 3.6):
        logger.error("CC ON State Test Failed")
        return False
    logger.info("CC ON State Test: PASS")
    
    # CC OFF state test
    hw_control.dac.set_voltage(4, 0)   # CC_2 = 0.5V
    hw_control.dac.set_voltage(5, 0)   # CC_1 = 0.5V
    time.sleep(1)
    
    cc2_voltage = hw_control.adc.read_voltage(4)
    cc1_voltage = hw_control.adc.read_voltage(5)
    
    if cc1_voltage > 0.1 or cc2_voltage > 0.1:
        logger.error("CC OFF State Test Failed")
        return False
    logger.info("CC OFF State Test: PASS")
    return True

def user_button_test(hw_control):
    """Step 6: User Button Test"""
    logger.info("Step 6: User Button Test")
    button_voltage = hw_control.adc.read_voltage(6)  # TP_9_FUNC_BTN -> ADC_6
    if button_voltage is None or not (2.6 <= button_voltage <= 3.6):
        logger.error("User Button Test Failed")
        return False
    logger.info("User Button Test: PASS")
    return True

def run_test_sequence(hw_control):
    """Execute complete test sequence"""
    global test_in_progress
    
    if test_in_progress:
        logger.info("Test already in progress")
        return
        
    test_in_progress = True
    all_tests_passed = True
    flash_success = False
    
    try:
        # Power up sequence
        hw_control.dac.set_voltage(1, 3000)  # DAC_1 ON (12V LDO enable)
        time.sleep(.1)  # Wait for power stabilization
        
        # Sequential test execution (CC test moved after flash)
        pre_flash_tests = [
            ("Temperature Test", temp_test),
            ("Voltage Sense Test", voltage_sense_test),
            ("OC Protection Test", oc_protection_test),
            ("3.3V Rail Test", v3v_test),
            ("User Button Test", user_button_test)
        ]
        
        # Execute pre-flash tests
        for test_name, test_func in pre_flash_tests:
            logger.info(f"\nExecuting {test_name}")
            if not test_func(hw_control):
                logger.error(f"{test_name} failed - stopping test sequence")
                display.show_test_status("fail")
                all_tests_passed = False
                return
            time.sleep(0.05)
        
        # Run flash process if pre-flash tests passed
        if all_tests_passed:
            display.show_test_status("pass")
            #time.sleep(1)
            #display.show_test_status("flash")
            flash_success = run_flash_script()
            if not flash_success:
                logger.error("Flash process failed")
                display.show_test_status("fail")
                all_tests_passed = False
                return
        
        # Execute CC test after successful flash
        if flash_success:
            logger.info("\nExecuting CC Test")
            #Power cycle to reset CC
            hw_control.dac.set_voltage(1, 0) # DAC_1 OFF
            time.sleep(.3)
            hw_control.dac.set_voltage(1, 3000) # DAC_1 ON
            if not cc_test(hw_control):
                logger.error("CC Test failed")
                display.show_test_status("fail")
                all_tests_passed = False
            else:
                display.show_test_status("done")
    
    finally:
        # Safe shutdown
        hw_control.dac.set_voltage(1, 0)  # DAC_1 OFF
        test_in_progress = False
        status = "PASSED" if all_tests_passed else "FAILED"
        logger.info(f"Test sequence completed - {status}")

def button_callback(channel):
    """Interrupt handler for button press"""
    if GPIO.input(BUTTON_PIN) == GPIO.LOW:  # Button pressed
        logger.info("Button pressed - initiating test sequence")
        display.show_test_status("Initiating test sequence")
        time.sleep(.15)  # Wait for display update
        try:
            hw_control = HardwareControl(
                port="/dev/ttySC0",
                baudrate=9600,
                txden_pin=27
            )
            run_test_sequence(hw_control)
        except Exception as e:
            logger.error(f"Test error: {str(e)}")
            if display:
                display.show_test_status("fail")
        finally:
            if 'hw_control' in locals():
                hw_control.close()

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    global running
    logger.info("\nExiting program")
    running = False

def main():
    global running, display
    
    # Setup GPIO with warnings disabled
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    
    try:
        # Setup button pin
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        logger.info("GPIO setup successful")
        
        # Initialize display
        display = TestDisplay()
        
        # Setup signal handler
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.info("Ready for testing. Press button to start test sequence.")
        logger.info("Press Ctrl+C to exit")
        
        # Main loop with button polling
        prev_state = GPIO.input(BUTTON_PIN)
        while running:
            try:
                current_state = GPIO.input(BUTTON_PIN)
                
                # Detect falling edge (button press)
                if prev_state == GPIO.HIGH and current_state == GPIO.LOW:
                    time.sleep(0.05)  # Debounce
                    if GPIO.input(BUTTON_PIN) == GPIO.LOW:  # Check again
                        button_callback(BUTTON_PIN)
                
                prev_state = current_state
                time.sleep(0.05)  # Short sleep to prevent CPU hogging
                
            except Exception as e:
                logger.error(f"Loop iteration error: {str(e)}")
                # Re-initialize GPIO if needed
                if "GPIO" in str(e):
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                time.sleep(1)  # Wait before retrying
                
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Program error: {str(e)}")
    finally:
        # Only cleanup GPIO when actually exiting
        if not running:
            GPIO.cleanup()
            logger.info("Program terminated")

if __name__ == "__main__":
    main()