import os
import can

os.system('sudo ip link set can0 up type can bitrate 1000000')
os.system('sudo ifconfig can0 txqueuelen 65536')

can0 = can.interface.Bus(channel = 'can0', bustype = 'socketcan')# socketcan_native

#msg = can.Message(arbitration_id=0x123, data=[0, 1, 2, 3, 4, 5, 6, 7], is_extended_id=False)
msg = can0.recv(10.0)
print (msg)
if msg is None:
    print('Timeout occurred, no message.')

os.system('sudo ip link set can0 down')

#sudo apt install python3-can
#run the script with sudo