#!/usr/bin/python
# -*- coding:utf-8 -*-

#region Header Information
"""
Automated Test Routine for WittyC Board
Hardware: PCB board rev 1.4
Author: Faradex
Last Update: 2024-12-20

To execute the scripts from Raspberry, remember to enable the venv using the `rs485` command on the terminal.
"""
#endregion

#region Changelog
"""
V1.0.0 - 2024-12-01 - Initial release
- Implemented hardware_control_singleBus.py
- Added testRoutine.py for hardware PCB board rev 1.4
- Added EXT_BUTTON.py for the external button (GPIO 18)
- Added I2C_Display.py for test sequence status display

V1.0.1 - 2024-12-18 - Bug fixes and improvements
- Fixed hardware control access by properly using DAC and ADC controllers
- Changed CC test order (executed after flashing for CC working state) 
- Implemented reliable button polling instead of edge detection
- Added a new display sequence: "Powered by Faradex" startup message
- Improved display status messages (Test passed/failed, Flashing, Done)
- Added proper error handling for hardware communication
- Enhanced GPIO cleanup and initialization
- Fixed display initialization timing

V1.0.2 - 2024-12-20 - Structural optimization and parallelization
- Introduced `basic_tests_parallel` for concurrent execution of temperature, 3.3V rail, button, and initial voltage sense checks
- Refactored CC Test into ON/OFF sequence for improved timing execution
- Improved timing measurements with `TimingLogger` for phase-wise performance tracking
- Added detailed logs for each test phase
- Optimized flash and erase script execution for reduced delay
- Streamlined power cycle logic for consistent hardware initialization
- Enhanced test sequence control to handle failures gracefully

Hardware Configuration:
- External button connected to GPIO 18
- I2C Grove LCD display for status indication
- RS485 HAT communication:
  * DAC slave address: 0x01
  * ADC slave address: 0x02
  * Port: /dev/ttySC0
  * Baudrate: 9600
  * TXDEN pin: GPIO 27
"""
#endregion

#region Test Sequence
"""
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
   5.1. CC OFF State Test:
       - Set CC_1 and CC_2 to 0.5V
       - Verify voltage is below 0.25V
   5.2. CC ON State Test:
       - Set CC_1 and CC_2 to 3.3V
       - Verify voltage is 2.5V-3.6V

6. User Button Test:
   - Read voltage from user button divider (TP_9_FUNC_BTN)
   - Valid range: 2.6V to 3.6V

Success Criteria:
- All tests must pass sequentially
- On success: Execute flash-wittyc.sh script
- On failure: Stop sequence and display error
"""
#endregion

#region Display Status Indicators
"""
Display Status Indicators:
- Startup: "Powered by Faradex" (1 second)
- Ready: "Press the button to start"
- Testing: Test status (pass/fail)
- Flashing: "Flashing"
- Complete: "Done"
"""
#endregion

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
        time.sleep(0.1)  # Kept small delay after clearing for display stability
    
    def show_startup(self):
        """Show initial startup message"""
        self.clear()
        self.lcd.write("Powered by", 0)
        self.lcd.write("Faradex", 1)
        time.sleep(1)  # Show for 1 second
        self.show_ready()
    
    def show_ready(self):
        """Show ready message"""
        self.clear()
        self.lcd.write("Press the button", 0)
        self.lcd.write("to start", 1)
    
    def blink_success(self):
        """Blink success message 3 times"""
        for _ in range(3):
            self.clear()
            time.sleep(0.3)  # Off time
            self.lcd.write("Test complete", 0)
            self.lcd.write("All passed!", 1)
            time.sleep(0.5)  # On time
        # Leave message on after blinking
        self.lcd.write("Test complete", 0)
        self.lcd.write("All passed!", 1)
    
    def show_test_status(self, status):
        """Show test status with better visibility"""
        self.clear()
        if status == "pass":
            self.lcd.write("Test passed", 0)
            self.lcd.write("Flashing...", 1)
        elif status == "fail":
            self.lcd.write("Test failed!", 0)
            self.lcd.write("Check logs", 1)
        elif status == "flash":
            self.lcd.write("Flashing", 0)
            self.lcd.write("Please wait...", 1)
        elif status == "done":
            self.blink_success()  # Use blinking effect for success
        elif status == "erasing":
            self.lcd.write("Erasing flash", 0)
            self.lcd.write("Please wait...", 1)
        elif status == "testing":
            self.lcd.write("Testing", 0)
            self.lcd.write("Please wait...", 1)

class TimingLogger:
    def __init__(self):
        self.start_time = None
        self.phase_start = None
        self.phases = {}
    
    def start(self):
        """Start the overall timing"""
        self.start_time = time.time()
        self.phase_start = self.start_time
    
    def log_phase(self, phase_name):
        """Log the duration of a phase"""
        now = time.time()
        duration = now - self.phase_start
        self.phases[phase_name] = duration
        self.phase_start = now
        logger.info(f"Phase '{phase_name}' took {duration:.2f} seconds")
    
    def summary(self):
        """Print timing summary"""
        total_time = time.time() - self.start_time
        logger.info("\nTiming Summary:")
        logger.info("-" * 40)
        for phase, duration in self.phases.items():
            logger.info(f"{phase:<30} {duration:>6.2f}s")
        logger.info("-" * 40)
        logger.info(f"{'Total':<30} {total_time:>6.2f}s")

# Create global timing logger
timing = TimingLogger()

def basic_tests_parallel(hw_control):
    """Execute Temperature, 3.3V, Button tests and Initial Voltage Sense in parallel"""
    logger.info("Starting basic tests (Temperature, 3.3V Rail, User Button, Initial Voltage Sense)")
    
    # First ensure CHG_EN is off for initial voltage sense
    hw_control.dac.set_voltage(3, 0)  # DAC_3 OFF (CHG_EN)
    time.sleep(0.1)  # Brief delay for CHG_EN to settle
    
    # Read all voltages in sequence
    temp_voltage = hw_control.adc.read_voltage(1)    # TP_1
    v3v_voltage = hw_control.adc.read_voltage(7)     # TP_23
    button_voltage = hw_control.adc.read_voltage(6)  # TP_9_FUNC_BTN
    vsense_voltage = hw_control.adc.read_voltage(2)  # ADC_2 (Initial voltage sense)
    
    # Process temperature test
    if temp_voltage is None:
        logger.error("Failed to read temperature sensor")
        return False
    
    resistance = (3.3*RFIXED-RFIXED*temp_voltage)/temp_voltage
    temperature = voltage_to_temp(temp_voltage)
    logger.info(f"Temperature Test - Resistance: {resistance:.2f}, Temperature: {temperature:.2f}°C")
    
    if not (6 <= temperature <= 35):
        logger.error("Temperature Test: FAIL")
        return False
    logger.info("Temperature Test: PASS")
    
    # Process 3.3V rail test
    if v3v_voltage is None or not (3.2 <= v3v_voltage <= 3.5):
        logger.error(f"3.3V Rail: {v3v_voltage:.2f}V - FAIL")
        return False
    logger.info(f"3.3V Rail: {v3v_voltage:.2f}V - PASS")
    
    # Process button test
    if button_voltage is None or not (2.6 <= button_voltage <= 3.6):
        logger.error("User Button Test Failed")
        return False
    logger.info("User Button Test: PASS")
    
    # Process initial voltage sense check
    if vsense_voltage is None or vsense_voltage > 0.1:
        logger.error(f"Initial Voltage Sense: {vsense_voltage:.2f}V - FAIL")
        return False
    logger.info(f"Initial Voltage Sense: {vsense_voltage:.2f}V - PASS")
    
    return True

def voltage_sense_test(hw_control):
    """Step 2: Voltage Sense Tests (remaining steps)"""
    logger.info("Step 2: Voltage Sense Test (continuing)")
    
    # Step 2.2: CHG_EN (initial state already checked in parallel tests)
    logger.info("Step 2.2: CHG_EN voltage sense check")
    hw_control.dac.set_voltage(3, 3300)  # DAC_3 ON (CHG_EN) 
    time.sleep(0.5)
    voltage = hw_control.adc.read_voltage(2)  # ADC_2
    if voltage is None or not (1.6 <= voltage <= 1.9):  #Ideally should be around 1.8V
        logger.error("Step 2.2 Failed")
        return False
    logger.info(f"Voltage Sense (2.2): {voltage:.2f}V - PASS")
    
    # Step 2.3: OV Protection test
    logger.info("Step 2.3: OV Protection check")
    hw_control.dac.set_voltage(1, 0)     # DAC_1 OFF (LDO)
    hw_control.dac.set_voltage(7, 3300)  # DAC_7 ON (PS)
    time.sleep(0.5)
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
    time.sleep(0.3)  # Quick check
    voltage = hw_control.adc.read_voltage(3)  # TP_3 (CUR_S)
    hw_control.dac.set_voltage(2, 0)     # DAC_2 OFF (MOSFET)
    current = (voltage)/(0.01*50)
    
    
    if current is None or not (0.12 <= current <= 0.15):
        logger.error(f"Current sense: {current:.2f}A - FAIL")
        return False
    logger.info(f"Current sense: {current:.2f}A - PASS")
    return True

def cc_test(hw_control):
    """Optimized CC Test with OFF state first"""
    logger.info("Step 5: CC Test")
    
    # CC OFF state test first (DACs are already at 0V)
    logger.info("CC OFF State Test")
    cc2_voltage = hw_control.adc.read_voltage(4)
    cc1_voltage = hw_control.adc.read_voltage(5)
    
    if cc1_voltage > 0.25 or cc2_voltage > 0.25: #passed from .2 to .25 due to new OFF ON structure
        logger.error("CC OFF State Test Failed")
        logger.error(f"CC1: {cc1_voltage:.3f}V, CC2: {cc2_voltage:.3f}V")
        return False
    logger.info("CC OFF State Test: PASS")
    
    # CC ON state test
    logger.info("CC ON State Test")
    hw_control.dac.set_voltage(4, 3300)  # CC_2 = 3.3V
    hw_control.dac.set_voltage(5, 3300)  # CC_1 = 3.3V
    time.sleep(0.3)  # Keep minimum stable delay
    
    cc2_voltage = hw_control.adc.read_voltage(4)
    cc1_voltage = hw_control.adc.read_voltage(5)
    
    if cc1_voltage is None or cc2_voltage is None or \
       not (2.5 <= cc1_voltage <= 3.6) or not (2.5 <= cc2_voltage <= 3.6):
        logger.error("CC ON State Test Failed")
        logger.error(f"CC1: {cc1_voltage:.3f}V, CC2: {cc2_voltage:.3f}V")
        return False
    logger.info("CC ON State Test: PASS")
    
    return True

def run_test_sequence(hw_control):
    """Execute complete test sequence with timing measurements"""
    global test_in_progress
    
    if test_in_progress:
        return
        
    test_in_progress = True
    all_tests_passed = True
    flash_success = False
    
    try:
        # Start timing
        timing.start()
        
        # Power up sequence
        hw_control.dac.set_voltage(1, 3000)
        time.sleep(0.03)
        
        # Execute parallel basic tests
        logger.info("\nExecuting parallel basic tests")
        if not basic_tests_parallel(hw_control):
            logger.error("Basic tests failed - stopping test sequence")
            display.show_test_status("fail")
            all_tests_passed = False
            return
        timing.log_phase("Parallel Basic Tests")
        
        # Execute voltage sense test
        logger.info("\nExecuting Voltage Sense Test")
        if not voltage_sense_test(hw_control):
            logger.error("Voltage Sense Test failed - stopping test sequence")
            display.show_test_status("fail")
            all_tests_passed = False
            return
        timing.log_phase("Voltage Sense Test")
        
        # Execute OC protection test
        logger.info("\nExecuting OC Protection Test")
        if not oc_protection_test(hw_control):
            logger.error("OC Protection Test failed - stopping test sequence")
            display.show_test_status("fail")
            all_tests_passed = False
            return
        timing.log_phase("OC Protection Test")
        
        if all_tests_passed:
            display.show_test_status("pass")
            flash_success = run_flash_script()
            timing.log_phase("Flash Programming")
            if not flash_success:
                display.show_test_status("fail")
                all_tests_passed = False
                return
        
        if flash_success:
            logger.info("\nExecuting CC Test")
            # Power cycle
            hw_control.dac.set_voltage(1, 0)
            time.sleep(0.1)
            hw_control.dac.set_voltage(1, 3000)
            time.sleep(0.05)
            
            if not cc_test(hw_control):
                display.show_test_status("fail")
                all_tests_passed = False
            else:
                display.show_test_status("done")
            timing.log_phase("CC Test")
    
    finally:
        hw_control.dac.set_voltage(1, 0)
        hw_control.dac.set_voltage(4, 500)  # Turn off CC1 
        hw_control.dac.set_voltage(5, 500)  # Turn on CC2 
        test_in_progress = False
        if all_tests_passed:
            timing.summary()

def run_erase_script(hw_control):
    """Execute the flash erase script"""
    try:
        logger.info("Starting flash erase process...")
        display.show_test_status("erasing")
        
        # Power up STM32 - reduced delay
        logger.info("Powering up STM32...")
        hw_control.dac.set_voltage(1, 3000)  # Turn on DAC1 (12V LDO enable)
        time.sleep(0.2)  # Reduced from 0.5s to 0.2s
        
        # Run erase script
        result = subprocess.run(['/usr/local/bin/erase-wittyc.sh'], 
                              check=True,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True)
        
        if result.returncode == 0:
            logger.info("Flash erase completed successfully")
            return True
        else:
            logger.error(f"Flash erase failed with error: {result.stderr}")
            return False
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Flash erase failed with error: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Failed to execute erase script: {str(e)}")
        return False

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

def button_callback(channel):
    """Interrupt handler for button press with timing"""
    if GPIO.input(BUTTON_PIN) == GPIO.LOW:  # Button pressed
        logger.info("Button pressed - initiating test sequence")
        display.lcd.clear()
        display.lcd.write("Testing...", 0)
        time.sleep(0.2)
        
        try:
            timing.start()  # Start overall timing
            
            # Initialize hardware
            hw_control = HardwareControl(
                port="/dev/ttySC0",
                baudrate=9600,
                txden_pin=27
            )
            timing.log_phase("Hardware Initialization")
            
            # Run erase script
            if not run_erase_script(hw_control):
                logger.error("Flash erase failed - stopping test sequence")
                display.show_test_status("fail")
                return
            timing.log_phase("Flash Erase")
            
            # Update display
            display.lcd.clear()
            display.lcd.write("Testing...", 0)
            time.sleep(0.2)
            
            # Run test sequence
            run_test_sequence(hw_control)
            
        except Exception as e:
            logger.error(f"Test error: {str(e)}")
            if display:
                display.clear()
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