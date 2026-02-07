#!/usr/bin/env python3
# 全ID自動pingテスト
import sys
import os

sdk_path = os.path.join(os.path.dirname(__file__), "stservo-env", "STServo_Python", "stservo-env")
if sdk_path not in sys.path:
    sys.path.append(sdk_path)
from scservo_sdk import *

BAUDRATE = 1000000
ID_RANGE = range(0, 16)  # 0～15までテスト
DEVICENAMES = ['/dev/ttyACM0', '/dev/ttyACM1']

sdk_path = os.path.join(os.path.dirname(__file__), "stservo-env", "STServo_Python", "stservo-env")
if sdk_path not in sys.path:
    sys.path.append(sdk_path)
from scservo_sdk import *

for DEVICENAME in DEVICENAMES:
    print(f"\n=== Testing port: {DEVICENAME} ===")
    portHandler = PortHandler(DEVICENAME)
    packetHandler = scscl(portHandler)

    if not portHandler.openPort():
        print(f"Failed to open the port: {DEVICENAME}")
        continue
    if not portHandler.setBaudRate(BAUDRATE):
        print(f"Failed to set baudrate: {BAUDRATE}")
        portHandler.closePort()
        continue

    found = False
    for sid in ID_RANGE:
        scs_model_number, scs_comm_result, scs_error = packetHandler.ping(sid)
        if scs_comm_result == COMM_SUCCESS:
            print(f"[ID:{sid}] ping succeeded. Model number: {scs_model_number}")
            found = True
        else:
            print(f"[ID:{sid}] ping failed.")
    portHandler.closePort()
    if not found:
        print("No servos responded in the tested ID range.")
