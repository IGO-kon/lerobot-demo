#!/usr/bin/env python
#
# *********     Ping Example      *********
#
# SCサーボの単体応答テスト用

import sys
import os

# Linux用: /dev/ttyACM0 などに書き換えてください
DEVICENAME = '/dev/ttyACM0'
BAUDRATE = 1000000
SCS_ID = 1  # テストしたいサーボID

# SDKパスを追加
sdk_path = os.path.join(os.path.dirname(__file__), "stservo-env", "STServo_Python", "stservo-env")
if sdk_path not in sys.path:
    sys.path.append(sdk_path)
from scservo_sdk import *

# ポート初期化
portHandler = PortHandler(DEVICENAME)
packetHandler = scscl(portHandler)

if portHandler.openPort():
    print(f"Succeeded to open the port: {DEVICENAME}")
else:
    print(f"Failed to open the port: {DEVICENAME}")
    sys.exit(1)

if portHandler.setBaudRate(BAUDRATE):
    print(f"Succeeded to set baudrate: {BAUDRATE}")
else:
    print(f"Failed to set baudrate: {BAUDRATE}")
    sys.exit(1)

# Ping
scs_model_number, scs_comm_result, scs_error = packetHandler.ping(SCS_ID)
if scs_comm_result != COMM_SUCCESS:
    print(f"[ID:{SCS_ID}] ping failed: {packetHandler.getTxRxResult(scs_comm_result)}")
else:
    print(f"[ID:{SCS_ID}] ping succeeded. Model number: {scs_model_number}")
if scs_error != 0:
    print(f"[ID:{SCS_ID}] error: {packetHandler.getRxPacketError(scs_error)}")

portHandler.closePort()
