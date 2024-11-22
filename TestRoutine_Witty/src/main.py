# main.py
import time
import logging
from hardware_control import RS485Device, AnalogOutput, AnalogInput

logging.basicConfig(level=logging.INFO)

def perform_tests(analog_out, analog_in):
    try:
        # Example test sequence
        voltages = [1.0, 2.0, 3.0, 4.0, 5.0]
        dac_channels = [0]  # Test only DAC channel 0
        adc_channels = [1]  # Test only ADC channel 0
        
        for dac_channel in dac_channels:
            for voltage in voltages:
                logging.info(f"Setting output voltage to {voltage}V on DAC channel {dac_channel}")
                analog_out.set_voltage(dac_channel, voltage)
                time.sleep(1)
                
                for adc_channel in adc_channels:
                    read_voltage = analog_in.read_voltage(adc_channel)
                    logging.info(f"Read input voltage from ADC channel {adc_channel}: {read_voltage:.3f}V")
                    time.sleep(1)
    except Exception as e:
        logging.error(f"Error during tests: {e}")

def main():
    logging.info("Initializing RS485 devices...")
    
    output_board = RS485Device("/dev/ttySC0", txden_pin=27)
    input_board = RS485Device("/dev/ttySC1", txden_pin=22)
    
    analog_out = AnalogOutput(output_board)
    analog_in = AnalogInput(input_board)
    
    perform_tests(analog_out, analog_in)

if __name__ == "__main__":
    main()

##This script has been simplified to demonstrate the basic structure of a test routine script.
##To execute the scripts from Raspberry, remember to enable the venv using rs485 command on terminal.