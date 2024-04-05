""" This is the main program for the conveyor control system.
It is responsible for creating the conveyor objects and running the main conveyor loop. 
The main conveyor loop is responsible for running the conveyors and stopping them
when the drives are not ready or the system is in an estop state.
The main conveyor loop also checks for the programRun flag and stops the conveyors if set to False.
The main conveyor loop also checks for the robotIsPicking flag and stops the conveyors 
if it is set to True. The main conveyor loop also checks for the
END_PROGRAM flag and stops the conveyors if it is set to True. 
The main conveyor loop also checks for the CONVEYORS_ARE_RUNNING flag and
stops the conveyors if it is set to False. 
"""

import time

# from conveyors import (SystemState, ControlAllConveyor)
from conveyor_types.system import SystemState
from helpers.thread_helpers import InterThreadBool
from helpers.conveyor_configuration import get_conveyor_config, configure_conveyors, fake_box


from machinelogic import Machine

# machine = Machine('http://192.168.7.2:3100', 'ws://192.168.7.2:9001')
machine = Machine()

system = SystemState(machine)

time.sleep(2)

configuration_data = get_conveyor_config()
robot_is_picking = InterThreadBool()
conveyors = configure_conveyors(configuration_data, system, robot_is_picking)
print(conveyors)

for conveyor in conveyors:
    print(conveyor.conveyor_state)
    print(conveyor.system_state.estop)
    print(conveyor.system_state.drives_are_ready)


# Main conveyor loop program
# conveyors_list = ControlAllConveyor(conveyors)

program_run = InterThreadBool()

END_PROGRAM = False
CONVEYORS_ARE_RUNNING = False
prev_time = time.perf_counter()
fake_box(system)
program_run.set(True)
while True:
    time.sleep(1)
# try:
#     system.subscribe_to_control_topics()
#
#     print("System is now listening for MQTT control messages. Press CTRL+C to exit.")
#
#     while not END_PROGRAM:
#
#         if system.program_run:
#             print("Program is running")
#             program_run.set(True)
#             conveyors_list.run_all()
#             CONVEYORS_ARE_RUNNING = True
#         if not system.program_run:
#             print("Program is not running")
#             program_run.set(False)
#             conveyors_list.stop_all()
#
#         time.sleep(0.1)
#         sleep_time = 0.100 - (time.perf_counter() - prev_time)
#         if sleep_time > 0:
#             time.sleep(sleep_time)
#         prev_time = time.perf_counter()
#
# except KeyboardInterrupt:
#     conveyors_list.stop_all()
#     print("Keyboard Interrupt")
#     END_PROGRAM = True
# finally:
#     # Ensure all conveyors are stopped on program exit
#     conveyors_list.stop_all()
#     print("Conveyors have been stopped. Program terminated.")