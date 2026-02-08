#!/usr/bin/env python
#
# *********     非同期移動の例      *********
#
#
# この例で利用可能なSCサーボモデル : プロトコルSCを使用するすべてのモデル
# この例はSCサーボ(SC15/SC09)とURTでテストされています
# この例はasyncioを使用して2つのサーボを同時に制御する方法を示します。
#

import sys
import os
import asyncio
import json

if os.name == 'nt':
    import msvcrt
    def getch():
        return msvcrt.getch().decode()
        
else:
    import sys, tty, termios
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    def getch():
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


# scservo_sdkのパスをimport直前で追加
import sys
import os
sdk_path = os.path.join(os.path.dirname(__file__), "stservo-env", "STServo_Python", "stservo-env")
if sdk_path not in sys.path:
    sys.path.append(sdk_path)
from scservo_sdk import *  # SCサーボSDKライブラリを使用

# JSONファイルからアーム設定を読み込み
try:
    with open('follower_arm.json', 'r') as f:
        follower_arm_config = json.load(f)
    with open('leader_arm.json', 'r') as f:
        leader_arm_config = json.load(f)
except FileNotFoundError as e:
    print(f"Error: {e}. Please make sure follower_arm.json and leader_arm.json are in the same directory.")
    sys.exit(1)


# デバイス設定
devices = {
    'follower': {
        'BAUDRATE': 1000000,
        'DEVICENAME': '/dev/ttyACM1',
        'SCS_MOVING_SPEED': 1000,
        'arm_config': follower_arm_config
    },
    'leader': {
        'BAUDRATE': 1000000,
        'DEVICENAME': '/dev/ttyACM0',
        'SCS_MOVING_SPEED': 1000,
        'arm_config': leader_arm_config
    }
}

async def move_and_wait(packet_handler, device_settings, scs_id, position):
    """
    サーボを特定の位置に移動し、移動が完了するまで待機します。
    タスクのキャンセルを適切に処理します。
    """
    try:
        speed = device_settings['SCS_MOVING_SPEED']
        loop = asyncio.get_event_loop()

        def write_pos_sync():
            return packet_handler.WritePos(scs_id, position, 0, speed)

        scs_comm_result, scs_error = await loop.run_in_executor(None, write_pos_sync)
        if scs_comm_result != COMM_SUCCESS:
            print(f"[ID:{scs_id:03d}] {packet_handler.getTxRxResult(scs_comm_result)}")
            return
        elif scs_error != 0:
            print(f"[ID:{scs_id:03d}] {packet_handler.getRxPacketError(scs_error)}")
            return

        print(f"[ID:{scs_id:03d}] Sent goal position {position}")
        moving = None
        while moving != 0:
            def read_sync():
                scs_present_position, scs_present_speed, scs_comm_result_p, scs_error_p = packet_handler.ReadPosSpeed(scs_id)
                moving, scs_comm_result_m, scs_error_m = packet_handler.ReadMoving(scs_id)
                return scs_present_position, scs_present_speed, scs_comm_result_p, scs_error_p, moving, scs_comm_result_m, scs_error_m

            scs_present_position, scs_present_speed, scs_comm_result_p, scs_error_p, moving, scs_comm_result_m, scs_error_m = await loop.run_in_executor(None, read_sync)
            
            if scs_comm_result_p != COMM_SUCCESS:
                print(f"ReadPosSpeed [ID:{scs_id:03d}]: {packet_handler.getTxRxResult(scs_comm_result_p)}")
            elif scs_error_p != 0:
                print(f"ReadPosSpeed [ID:{scs_id:03d}]: {packet_handler.getRxPacketError(scs_error_p)}")
            else:
                print(f"[ID:{scs_id:03d}] GoalPos:{position} PresPos:{scs_present_position} PresSpd:{scs_present_speed}")

            if scs_comm_result_m != COMM_SUCCESS:
                print(f"ReadMoving [ID:{scs_id:03d}]: {packet_handler.getTxRxResult(scs_comm_result_m)}")
            if scs_error_m != 0:
                print(f"ReadMoving [ID:{scs_id:03d}]: {packet_handler.getRxPacketError(scs_error_m)}")

            await asyncio.sleep(0.1)
        print(f"[ID:{scs_id:03d}] Move to {position} complete.")
    except asyncio.CancelledError:
        print(f"Movement of servo [ID:{scs_id:03d}] was cancelled (timeout).")

async def main():
    # 追従させるサーボIDリスト
    # 全サーボIDで追従
    """
    サーボを初期化し、移動デモを実行するメイン関数。
    """
    loop = asyncio.get_event_loop()
    portHandlers = {}
    packetHandlers = {}
    
    for name, settings in devices.items():
        portHandler = PortHandler(settings['DEVICENAME'])
        if portHandler.openPort():
            print(f"Succeeded to open the port for {name}")
            if portHandler.setBaudRate(settings['BAUDRATE']):
                print(f"Succeeded to change the baudrate for {name}")
                portHandlers[name] = portHandler
                packetHandlers[name] = scscl(portHandler)
            else:
                print(f"Failed to change the baudrate for {name}. Press any key to quit.")
                getch()
        else:
            print(f"Failed to open the port for {name}. Press any key to quit.")
            getch()

    if len(packetHandlers) == 0:
        print("No devices were initialized. Terminating.")
        return

    # サーボIDによるルックアップテーブルを作成
    follower_servos_by_id = {servo['id']: servo for servo in devices['follower']['arm_config'].values()}
    leader_servos_by_id = {servo['id']: servo for servo in devices['leader']['arm_config'].values()}

    # すべてのサーボのトルクを有効化

    print("Enabling torque for leader servos and disabling for follower servos...")
    # リーダーのみトルクON
    if 'leader' in packetHandlers:
        for scs_id in leader_servos_by_id.keys():
            result, error = packetHandlers['leader'].write1ByteTxRx(scs_id, SCSCL_TORQUE_ENABLE, 1)
            if result != COMM_SUCCESS:
                print(f"Failed to enable torque for leader servo {scs_id}: {packetHandlers['leader'].getTxRxResult(result)}")
            elif error != 0:
                print(f"Error enabling torque for leader servo {scs_id}: {packetHandlers['leader'].getRxPacketError(error)}")
            else:
                print(f"Successfully enabled torque for leader servo {scs_id}")

    # フォロワーはトルクOFF（フリー）
    if 'follower' in packetHandlers:
        for scs_id in follower_servos_by_id.keys():
            result, error = packetHandlers['follower'].write1ByteTxRx(scs_id, SCSCL_TORQUE_ENABLE, 0)
            if result != COMM_SUCCESS:
                print(f"Failed to disable torque for follower servo {scs_id}: {packetHandlers['follower'].getTxRxResult(result)}")
            elif error != 0:
                print(f"Error disabling torque for follower servo {scs_id}: {packetHandlers['follower'].getRxPacketError(error)}")
            else:
                print(f"Successfully disabled torque for follower servo {scs_id}")

    # デモループの状態
    position_index = 0
    servo_cycle_index = 0
    
    follower_settings = devices['follower']
    leader_settings = devices.get('leader')

    import time
    while True:
        for current_scs_id in follower_servos_by_id.keys():
            follower_position = None
            if 'follower' in packetHandlers:
                def read_follower_pos():
                    pos, _, comm_result, err = packetHandlers['follower'].ReadPosSpeed(current_scs_id)
                    if comm_result == COMM_SUCCESS and err == 0:
                        return pos
                    else:
                        print(f"Failed to read follower servo {current_scs_id} position.")
                        return None
                follower_position = await loop.run_in_executor(None, read_follower_pos)

            if follower_position is not None and 'leader' in packetHandlers and current_scs_id in leader_servos_by_id:
                await move_and_wait(packetHandlers['leader'], leader_settings, current_scs_id, follower_position)
        await asyncio.sleep(0.01)

    # 最後にトルクを無効化
    print("Disabling torque for all servos...")
    for handler, ids in all_servos:
        for scs_id in ids:
            handler.write1ByteTxRx(scs_id, SCSCL_TORQUE_ENABLE, 0)

    # ポートを閉じる
    for portHandler in portHandlers.values():
        portHandler.closePort()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program terminated by user.")
