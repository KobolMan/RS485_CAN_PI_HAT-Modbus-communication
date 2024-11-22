# main.py
import time
import logging
from hardware_control import RS485Device, AnalogOutput, AnalogInput

logging.basicConfig(level=logging.INFO)

# Constants for the thermistor
BETA = 3435  # Beta parameter
R0 = 10000  # Resistance at 25°C (10kΩ)
T0 = 298.15  # Reference temperature (25°C in Kelvin)
VIN = 3.3  # Input voltage to the voltage divider
RFIXED = 10000  # Fixed resistor value in the voltage divider (10kΩ)

def voltage_to_temp(voltage):
    """Convert voltage to temperature using the Beta parameter equation."""
    if voltage <= 0:
        return float('inf')  # Avoid division by zero
    
    # Calculate the thermistor resistance
    r_therm = RFIXED * (VIN / voltage - 1)
    
    # Calculate the temperature in Kelvin using the Beta parameter equation
    temp_k = 1 / (1 / T0 + 1 / BETA * math.log(r_therm / R0))
    
    # Convert temperature to Celsius
    temp_c = temp_k - 273.15
    
    return temp_c


def temp_test(analog_in):
    logging.info("Starting Temp Test")
    # Read temperature sensor voltage from ADC channel 1
    voltage = analog_in.read_voltage(1)
    # Convert voltage to temperature using the Beta parameter
    # Assuming a placeholder conversion function voltage_to_temp
    temperature = voltage_to_temp(voltage)
    logging.info(f"Temperature: {temperature:.2f}°C")
    if 20 <= temperature <= 30:
        logging.info("Temp Test Passed")
    else:
        logging.error("Temp Test Failed")

def voltage_sense_test(analog_out, analog_in):
    logging.info("Starting Voltage Sense Test")
    # Step 2.1
    analog_out.set_voltage(1, 5.0)  # DAC_1 ON
    time.sleep(1)
    voltage = analog_in.read_voltage(2)  # Check ADC_2
    logging.info(f"Voltage Sense (Step 2.1): {voltage:.2f}V")
    
    # Step 2.2
    analog_out.set_voltage(3, 5.0)  # DAC_3 ON
    time.sleep(1)
    voltage = analog_in.read_voltage(2)  # Check ADC_2
    logging.info(f"Voltage Sense (Step 2.2): {voltage:.2f}V")
    
    # Step 2.3
    analog_out.set_voltage(1, 0.0)  # DAC_1 OFF
    time.sleep(1)
    voltage = analog_in.read_voltage(2)  # Check ADC_2
    logging.info(f"Voltage Sense (Step 2.3): {voltage:.2f}V")
    if voltage == 0:
        logging.info("OVProtection Test Passed")
    else:
        logging.error("OVProtection Test Failed")

def oc_protection_test(analog_out, analog_in):
    logging.info("Starting OCProtection Test")
    analog_out.set_voltage(1, 5.0)  # DAC_1 ON
    analog_out.set_voltage(2, 5.0)  # DAC_2 ON
    time.sleep(1)
    current = analog_in.read_voltage(3)  # Check CUR_S (TP_3)
    logging.info(f"Current Sense: {current:.2f}A")
    if abs(current - 1.0) < 0.1:
        logging.info("OCProtection Test Passed")
    else:
        logging.error("OCProtection Test Failed")
    analog_out.set_voltage(2, 0.0)  # DAC_2 OFF

def v3v_test(analog_out, analog_in):
    logging.info("Starting 3V3 Test")
    analog_out.set_voltage(1, 5.0)  # DAC_1 ON
    time.sleep(1)
    voltage = analog_in.read_voltage(7)  # Check TP_13 (ADC_7)
    logging.info(f"3V3 Voltage: {voltage:.2f}V")
    if abs(voltage - 3.3) < 0.1:
        logging.info("3V3 Test Passed")
    else:
        logging.error("3V3 Test Failed")

def cc_test(analog_out, analog_in):
    logging.info("Starting CC Test")
    # CC1, CC2 on state test
    analog_out.set_voltage(4, 3.3)  # DAC_4 = 3.3V
    analog_out.set_voltage(5, 3.3)  # DAC_5 = 3.3V
    time.sleep(1)
    voltage_cc1 = analog_in.read_voltage(4)  # Check ADC_4
    voltage_cc2 = analog_in.read_voltage(5)  # Check ADC_5
    logging.info(f"CC1 Voltage: {voltage_cc1:.2f}V, CC2 Voltage: {voltage_cc2:.2f}V")
    if abs(voltage_cc1 - 3.3) < 0.1 and abs(voltage_cc2 - 3.3) < 0.1:
        logging.info("CC On State Test Passed")
    else:
        logging.error("CC On State Test Failed")
    
    # CC1, CC2 off state test
    analog_out.set_voltage(4, 0.5)  # DAC_4 = 0.5V
    analog_out.set_voltage(5, 0.5)  # DAC_5 = 0.5V
    time.sleep(1)
    voltage_cc1 = analog_in.read_voltage(4)  # Check ADC_4
    voltage_cc2 = analog_in.read_voltage(5)  # Check ADC_5
    logging.info(f"CC1 Voltage: {voltage_cc1:.2f}V, CC2 Voltage: {voltage_cc2:.2f}V")
    if voltage_cc1 == 0 and voltage_cc2 == 0:
        logging.info("CC Off State Test Passed")
    else:
        logging.error("CC Off State Test Failed")

def user_button_test(analog_in):
    logging.info("Starting User Button Test")
    button_state = analog_in.read_voltage(6)  # Check TP_9_FUNC_BTN (ADC_6)
    logging.info(f"User Button State: {button_state:.2f}")
    if button_state == 1:
        logging.info("User Button Test Passed")
    else:
        logging.error("User Button Test Failed")

def main():
    logging.info("Initializing RS485 devices...")
    
    output_board = RS485Device("/dev/ttySC0", txden_pin=27)
    input_board = RS485Device("/dev/ttySC1", txden_pin=22)
    
    analog_out = AnalogOutput(output_board)
    analog_in = AnalogInput(input_board)
    
    temp_test(analog_in)
    voltage_sense_test(analog_out, analog_in)
    oc_protection_test(analog_out, analog_in)
    v3v_test(analog_out, analog_in)
    cc_test(analog_out, analog_in)
    user_button_test(analog_in)

if __name__ == "__main__":
    main()

##To execute the scripts from Raspberry, remember to enable the venv using rs485 command on terminal.