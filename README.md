UTILIZED HARDWARE: 
1 - https://www.waveshare.com/modbus-rtu-analog-output-8ch.htm
2 - https://www.waveshare.com/modbus-rtu-analog-input-8ch.htm
3 - https://www.waveshare.com/product/rs485-can-hat-b.htm

##To execute the scripts from Raspberry, remember to enable the venv using rs485 command on terminal.
```
This project contains a set of scripts to perform hardware tests on the WittyC board using a Raspberry Pi 4b with an RS485 CAN HAT. The tests involve driving external peripherals (ADC & DAC via RS485) and verifying that the hardware components match the specifications.

## Project Structure


hardware_control_singleBus.py

: Contains classes for interacting with the RS485 devices, including 

RS485Device

, 

AnalogOutput

, and 

AnalogInput

.
- 

testRoutine.py

: Main script that performs the hardware tests.
- `lib/`: Directory containing additional libraries required for the RS485 CAN HAT.

## Test Routine

The test routine involves several steps to check that the hardware components are functioning correctly. The steps are as follows:

1. **Temperature Test (TP_1 on WittyC HW, B8 schematic)**
    - Check that the temperature is within an acceptable range.
    - The MPN of the temperature sensor is ERT-J1VG103JA. The Beta parameter is used to convert voltage to temperature and check that it is within a reasonable working range (around 25°C).

2. **Voltage Sense (TP_2 on WittyC HW, B7 schematic)**
    - **Step 2.1**: Turn on DAC_1 and check the voltage sense on ADC_2.
    - **Step 2.2**: Turn on DAC_1 and DAC_3, and check the voltage sense on ADC_2.
    - **Step 2.3**: Test the over-voltage protection circuit by turning off DAC_1 and checking that the voltage sense on ADC_2 is 0.

3. **Over-Current Protection (OCProtection)**
    - Turn on DAC_1 and DAC_2.
    - Check the current sense (CUR_S) on TP_3, which should be close to 1A.
    - Turn off DAC_2.

4. **3.3V Test**
    - Turn on DAC_1 and check the voltage on TP_13 (ADC_7), which should be 3.3V.

5. **CC Test**
    - **CC1, CC2 On State Test**: Set DAC_4 and DAC_5 to 3.3V and check that ADC_4 and ADC_5 are 3.3V.
    - **CC1, CC2 Off State Test**: Set DAC_4 and DAC_5 to 0.5V and check that ADC_4 and ADC_5 are 0V.

6. **User Button Test**
    - Check the state of the user button on TP_9_FUNC_BTN (ADC_6), which should be 1.

## Usage

### Prerequisites

- Raspberry Pi 4b
- RS485 CAN HAT
- WittyC board
- Python 3.x
- Required Python libraries: `RPi.GPIO`, `serial`, 

logging



### Setup

1. Clone the repository to your Raspberry Pi.
2. Navigate to the project directory.
3. Ensure the RS485 CAN HAT is properly connected to the Raspberry Pi.
4. Install the required Python libraries if not already installed:
    ```bash
    pip install RPi.GPIO pyserial
    ```

### Running the Tests

1. Enable the virtual environment (if applicable):
    ```bash
    source rs485_env/bin/activate
    ```
2. Run the test routine script:
    ```bash
    sudo python testRoutine.py
    ```

### Example Output

The script will log the progress and results of each test step. Example output:
```
INFO:root:Initializing RS485 devices...
INFO:root:Starting Temp Test
INFO:root:

Temperature

: 25.00°C
INFO:root:Temp Test Passed
INFO:root:Starting Voltage Sense Test
INFO:root:Setting output voltage to 5.0V on DAC channel 1
INFO:root:Voltage Sense (Step 2.1): 5.00V
INFO:root:Setting output voltage to 5.0V on DAC channel 3
INFO:root:Voltage Sense (Step 2.2): 5.00V
INFO:root:Setting output voltage to 0.0V on DAC channel 1
INFO:root:Voltage Sense (Step 2.3): 0.00V
INFO:root:OVProtection Test Passed
...
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments

- Special thanks to the developers of the RS485 CAN HAT library.
- Thanks to the WittyC hardware team for their support and documentation.

---

This README provides a comprehensive overview of the project, including the test routine steps, usage instructions, and example output.

KobolMan: Let's update the description including the other scripts as side description. Let's modify the name of the peripherals. The RS485 is a Waveshare RS485_CAN_PiHAT, the DAC is a Waveshare 8CH Analog Output (B), the ADC is a Waveshare 8CH Analog Input (B).


GitHub Copilot: Sure! Here is the updated README with the additional details and modified peripheral names:

