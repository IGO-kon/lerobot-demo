#!/usr/bin/env python
#
# *********     Async Move Example      *********
#
#
# Available SC Servo model on this example : All models using Protocol SC
# This example is tested with a SC Servo(SC15/SC09), and an URT
# This example demonstrates controlling two servos concurrently using asyncio.
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

sys.path.append("stservo-env")
from scservo_sdk import *                      # Uses SC Servo SDK library

# Load arm configurations from JSON files
try:
    with open('follower_arm.json', 'r') as f:
        follower_arm_config = json.load(f)
    with open('leader_arm.json', 'r') as f:
        leader_arm_config = json.load(f)
except FileNotFoundError as e:
    print(f"Error: {e}. Please make sure follower_arm.json and leader_arm.json are in the same directory.")
    sys.exit(1)


# Device settings
devices = {
    'follower': {
        'BAUDRATE': 1000000,
        'DEVICENAME': '/dev/ttyACM0',
        'SCS_MOVING_SPEED': 1000,
        'arm_config': follower_arm_config
    },
    'leader': {
        'BAUDRATE': 1000000,
        'DEVICENAME': '/dev/ttyACM1',
        'SCS_MOVING_SPEED': 1000,
        'arm_config': leader_arm_config
    }
}

async def move_and_wait(packet_handler, device_settings, scs_id, position):
    """
    Moves a servo to a specific position and waits for the move to complete.
    Handles task cancellation gracefully.
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
    """
    Main function to initialize servos and run the movement demo.
    """
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

    # Create a lookup table for servos by ID
    follower_servos_by_id = {servo['id']: servo for servo in devices['follower']['arm_config'].values()}
    leader_servos_by_id = {servo['id']: servo for servo in devices['leader']['arm_config'].values()}

    # Enable torque for all servos
    print("Enabling torque for all servos...")
    all_servos = []
    if 'follower' in packetHandlers:
        all_servos.append((packetHandlers['follower'], follower_servos_by_id.keys()))
    if 'leader' in packetHandlers:
        all_servos.append((packetHandlers['leader'], leader_servos_by_id.keys()))

    for handler, ids in all_servos:
        for scs_id in ids:
            result, error = handler.write1ByteTxRx(scs_id, SCSCL_TORQUE_ENABLE, 1)
            if result != COMM_SUCCESS:
                print(f"Failed to enable torque for servo {scs_id}: {handler.getTxRxResult(result)}")
            elif error != 0:
                print(f"Error enabling torque for servo {scs_id}: {handler.getRxPacketError(error)}")
            else:
                print(f"Successfully enabled torque for servo {scs_id}")

    # State for the demo loop
    position_index = 0
    servo_cycle_index = 0
    
    follower_settings = devices['follower']
    leader_settings = devices.get('leader')

    # Define which servos to move
    MOVING_SERVO_IDS = [1, 4, 5, 6]
    movement_delta = 100  # How far to move from the midpoint

    loop = asyncio.get_event_loop()
    
    while True:
        print("Press any key to continue! (or press ESC to quit!)")
        char = await loop.run_in_executor(None, getch)
        if char == chr(0x1b):
            break

        # Determine which servo to move in this cycle
        current_scs_id = MOVING_SERVO_IDS[servo_cycle_index]
        print(f"--- Activating Servo ID: {current_scs_id} ---")

        tasks = []

        # Prepare follower task
        if 'follower' in packetHandlers:
            servo_config = follower_servos_by_id.get(current_scs_id)
            if servo_config:
                mid_point = (servo_config['range_min'] + servo_config['range_max']) // 2
                pos1 = max(servo_config['range_min'], mid_point - movement_delta)
                pos2 = min(servo_config['range_max'], mid_point + movement_delta)
                goal_position = [pos1, pos2][position_index]
                tasks.append(asyncio.create_task(move_and_wait(packetHandlers['follower'], follower_settings, current_scs_id, goal_position)))

        # Prepare leader task
        if 'leader' in packetHandlers:
            servo_config = leader_servos_by_id.get(current_scs_id)
            if servo_config:
                mid_point = (servo_config['range_min'] + servo_config['range_max']) // 2
                pos1 = max(servo_config['range_min'], mid_point - movement_delta)
                pos2 = min(servo_config['range_max'], mid_point + movement_delta)
                # Move opposite to follower
                goal_position = [pos1, pos2][position_index]
                tasks.append(asyncio.create_task(move_and_wait(packetHandlers['leader'], leader_settings, current_scs_id, goal_position)))

        if tasks:
            done, pending = await asyncio.wait(tasks, timeout=5.0)

            if pending:
                print(f"Warning: {len(pending)} movement tasks timed out and were cancelled.")
                for task in pending:
                    task.cancel()

        # Update state for the next iteration
        position_index = 1 - position_index
        if position_index == 0: # A full back-and-forth cycle is complete
            servo_cycle_index = (servo_cycle_index + 1) % len(MOVING_SERVO_IDS)

    # Disable torque at the end
    print("Disabling torque for all servos...")
    for handler, ids in all_servos:
        for scs_id in ids:
            handler.write1ByteTxRx(scs_id, SCSCL_TORQUE_ENABLE, 0)

    # Close ports
    for portHandler in portHandlers.values():
        portHandler.closePort()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program terminated by user.")
