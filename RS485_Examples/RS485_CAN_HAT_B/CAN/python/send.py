import os
import can

# Bring down the interface if it's already up
os.system('sudo ip link set can0 down')

# Set up the CAN interface
os.system('sudo ip link set can0 up type can bitrate 1000000')
os.system('sudo ifconfig can0 txqueuelen 65536')

# Initialize the CAN bus
can0 = can.interface.Bus(channel='can0', bustype='socketcan')

# Create and send a CAN message
msg = can.Message(arbitration_id=0x123, data=[0, 1, 2, 3, 4, 5, 6, 7], is_extended_id=False)
can0.send(msg)

# Bring down the CAN interface
os.system('sudo ip link set can0 down')

#sudo apt install python3-can
#run the script with sudo