#!/usr/bin/python
# -*- coding:utf-8 -*-

"""
Automated Test Routine for WittyC Board
Hardware: PCB board rev 1.4
Author: Faradex
Last Update: 2024-12-18

To execute the scripts from Raspberry, remember to enable the venv using rs485 command on terminal.
"""

import time
import math
import logging
import signal
import subprocess
import RPi.GPIO as GPIO
from hardware_control_singleBus_optimized import HardwareControl
from I2C_Display import GroveLCD

logging.basicConfig(
    level=logging.DEBUG,
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
    
    # Read all voltages in sequence with bypass_cache to ensure fresh readings
    temp_voltage = hw_control.adc.read_voltage(1, bypass_cache=True)    # TP_1
    v3v_voltage = hw_control.adc.read_voltage(7, bypass_cache=True)     # TP_23
    button_voltage = hw_control.adc.read_voltage(6, bypass_cache=True)  # TP_9_FUNC_BTN
    vsense_voltage = hw_control.adc.read_voltage(2, bypass_cache=True)  # ADC_2 (Initial voltage sense)
    
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
    logger.debug("Setting DAC_3 (CHG_EN) to 3300mV")
    hw_control.dac.set_voltage(3, 3300)  # DAC_3 ON (CHG_EN) 
    time.sleep(0.5)
    voltage = hw_control.adc.read_voltage(2, bypass_cache=True)  # ADC_2
    logger.debug(f"ADC_2 reading after CHG_EN ON: {voltage:.3f}V")
    
    if voltage is None or not (1.6 <= voltage <= 1.9):
        logger.error("Step 2.2 Failed")
        return False
    logger.info(f"Voltage Sense (2.2): {voltage:.2f}V - PASS")
    
    # Step 2.3: OV Protection test
    logger.info("Step 2.3: OV Protection check")
    
    # Turn off LDO (DAC_1)
    logger.debug("Turning off DAC_1 (LDO)")
    resp1 = hw_control.dac.set_voltage(1, 0)
    logger.debug(f"DAC_1 OFF response: {resp1}")
    
    # Verify LDO is off
    time.sleep(0.1)
    voltage_check = hw_control.adc.read_voltage(2, bypass_cache=True)
    logger.debug(f"Voltage after LDO OFF: {voltage_check:.3f}V")
    
    # Turn on PS (DAC_7)
    logger.debug("Turning on DAC_7 (PS)")
    resp2 = hw_control.dac.set_voltage(7, 3300)
    logger.debug(f"DAC_7 ON response: {resp2}")
    
    # Wait for voltage to settle
    time.sleep(0.5)
    voltage = hw_control.adc.read_voltage(2, bypass_cache=True)
    logger.debug(f"Final voltage reading: {voltage:.3f}V")
    
    if voltage is None or voltage > 0.1:
        logger.error(f"Step 2.3 Failed - Voltage {voltage:.3f}V is above 0.1V threshold")
        return False
    logger.info(f"OV Protection voltage: {voltage:.3f}V - PASS")
    
    # Restore normal state - do each operation separately for debugging
    logger.debug("Restoring normal state")
    hw_control.dac.set_voltage(7, 0)     # DAC_7 OFF (PS)
    time.sleep(0.1)
    hw_control.dac.set_voltage(1, 3300)  # DAC_1 ON (LDO)
    
    # Verify restore
    time.sleep(0.1)
    final_voltage = hw_control.adc.read_voltage(2, bypass_cache=True)
    logger.debug(f"Final state voltage: {final_voltage:.3f}V")
    
    return True

def oc_protection_test(hw_control):
    """Step 3: OC Protection Test"""
    logger.info("Step 3: OC Protection Test")
    
    hw_control.dac.set_voltage(2, 3300)  # DAC_2 ON (MOSFET)
    time.sleep(0.3)  # Quick check
    voltage = hw_control.adc.read_voltage(3, bypass_cache=True)  # TP_3 (CUR_S)
    hw_control.dac.set_voltage(2, 0)     # DAC_2 OFF (MOSFET)
    current = (voltage)/(0.01*50)
    
    if current is None or not (0.12 <= current <= 0.15):
        logger.error(f"Current sense: {current:.2f}A - FAIL")
        return False
    logger.info(f"Current sense: {current:.2f}A - PASS")
    return True

def cc_test(hw_control):
    """Original CC Test implementation with debug logging"""
    logger.info("Step 5: CC Test")
    
    # Verify power is stable before CC test
    vdd_voltage = hw_control.adc.read_voltage(7)  # 3.3V rail
    logger.debug(f"3.3V rail before CC test: {vdd_voltage:.3f}V")
    
    # CC ON state test - use individual commands like original
    logger.debug("Setting CC1 and CC2 to 3.3V")
    hw_control.dac.set_voltage(4, 3300)  # Individual command
    hw_control.dac.set_voltage(5, 3300)  # Individual command
    time.sleep(0.3)  # Keep minimum stable delay
    
    # Read both CC voltages - use cache like original
    cc2_voltage = hw_control.adc.read_voltage(4)  
    cc1_voltage = hw_control.adc.read_voltage(5)
    logger.debug(f"CC1 voltage: {cc1_voltage:.3f}V")
    logger.debug(f"CC2 voltage: {cc2_voltage:.3f}V")
    
    if cc1_voltage is None or cc2_voltage is None or \
       not (2.5 <= cc1_voltage <= 3.6) or not (2.5 <= cc2_voltage <= 3.6):
        logger.error(f"CC ON State Test Failed - Voltages out of range")
        logger.error(f"CC1: {cc1_voltage:.3f}V (expected 2.5V-3.6V)")
        logger.error(f"CC2: {cc2_voltage:.3f}V (expected 2.5V-3.6V)")
        return False
    
    logger.info("CC ON State Test Passed")
    
    # CC OFF state test - use individual commands like original
    logger.debug("Setting CC1 and CC2 to 0.5V")
    hw_control.dac.set_voltage(4, 500)  # Individual command
    hw_control.dac.set_voltage(5, 500)  # Individual command
    time.sleep(0.4)  # Keep discharge delay
    
    cc2_voltage = hw_control.adc.read_voltage(4)  # Use cache
    cc1_voltage = hw_control.adc.read_voltage(5)  # Use cache
    logger.debug(f"CC1 OFF voltage: {cc1_voltage:.3f}V")
    logger.debug(f"CC2 OFF voltage: {cc2_voltage:.3f}V")
    
    if cc1_voltage > 0.1 or cc2_voltage > 0.1:
        logger.error(f"CC OFF State Test Failed - Voltages above threshold")
        logger.error(f"CC1: {cc1_voltage:.3f}V (expected <= 0.1V)")
        logger.error(f"CC2: {cc2_voltage:.3f}V (expected <= 0.1V)")
        return False
        
    logger.info("CC OFF State Test Passed")
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
            time.sleep(0.3)
            hw_control.dac.set_voltage(1, 3000)
            time.sleep(0.3)
            
            if not cc_test(hw_control):
                display.show_test_status("fail")
                all_tests_passed = False
            else:
                display.show_test_status("done")
            timing.log_phase("CC Test")
    
    finally:
        hw_control.dac.set_voltage(1, 0)
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
            
            # Initialize hardware without config
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