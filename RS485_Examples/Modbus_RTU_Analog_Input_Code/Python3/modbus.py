#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import time
import serial
import modbus_tk
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu


PORT="/dev/ttyUSB0"
master = modbus_rtu.RtuMaster(serial.Serial(port=PORT,baudrate=9600, bytesize=8, parity='N', stopbits=1, xonxoff=0))
master.set_timeout(5.0)
master.set_verbose(True)

red = []
alarm = ""
try:
    master.set_timeout(5.0)
    master.set_verbose(True)
    while True:
        #Read Input Registers Funtion:04H station:01H  address:00 length:08
        red = master.execute(1, cst.READ_INPUT_REGISTERS, 0x00, 0x08)
        print(red)
        time.sleep(1)

except Exception as exc:
    print(str(exc))
