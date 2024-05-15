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

from conveyor_types.system import SystemState
from conveyor_types.conveyors import ControlAllConveyor
from helpers.thread_helpers import InterThreadBool
from conveyor_configuration import get_conveyor_config, configure_conveyors, fake_box
from conveyor_types.definitions.ipc_mqtt_definitions import mqtt_messages
from machinelogic import Machine

# machine = Machine('http://192.168.7.2:3100', 'ws://192.168.7.2:9001')
machine = Machine()


def stop_conveyors():
    """Stop all conveyors gracefully."""
    global conveyors_list, program_run, CONVEYORS_ARE_RUNNING
    print("Stopping all conveyors...")
    program_run.set(False)
    conveyors_list.stop_all()
    CONVEYORS_ARE_RUNNING = False
    print("All conveyors stopped.")


def start_conveyors():
    """Start all conveyors with the current configuration."""
    global conveyors_list, program_run, CONVEYORS_ARE_RUNNING
    print("Starting all conveyors...")
    program_run.set(True)
    conveyors_list.run_all()
    CONVEYORS_ARE_RUNNING = True
    print("All conveyors running.")


def reconfigure_conveyors():
    global conveyors, conveyors_list
    print("Reconfiguring conveyors...")

    # Stop the conveyors before reconfiguring
    stop_conveyors()

    # Reconfigure conveyors
    configuration_data = get_conveyor_config()
    conveyors = configure_conveyors(configuration_data, system, robot_is_picking)
    conveyors_list = ControlAllConveyor(conveyors)

    # Start the conveyors with the new configuration
    start_conveyors()

    print("Conveyors reconfigured successfully.")


def on_restart_command(topic: str, payload: str):
    """This function is called when a message is received on the restart topic."""
    if payload.lower() == mqtt_messages['restart']:
        reconfigure_conveyors()


machine.on_mqtt_event('restart', on_restart_command)

system = SystemState(machine)

time.sleep(2)

configuration_data = get_conveyor_config()
robot_is_picking = InterThreadBool()
PARENT = None

conveyors = configure_conveyors(configuration_data, system, robot_is_picking)

for conveyor in conveyors:
    print(conveyor.conveyor_state)
    print(conveyor.system_state.estop)
    print(conveyor.system_state.drives_are_ready)

# Main conveyor loop program
conveyors_list = ControlAllConveyor(conveyors)

program_run = InterThreadBool()

END_PROGRAM = False
CONVEYORS_ARE_RUNNING = False
prev_time = time.perf_counter()
fake_box(system)
program_run.set(True)
try:
    system.subscribe_to_control_topics()

    print("System is now listening for MQTT control messages. Press CTRL+C to exit.")

    while not END_PROGRAM:

        if system.program_run:
            print("Program is running")
            program_run.set(True)
            conveyors_list.run_all()
            CONVEYORS_ARE_RUNNING = True
        if not system.program_run:
            print("Program is not running")
            program_run.set(False)
            conveyors_list.stop_all()

        time.sleep(0.1)
        sleep_time = 0.100 - (time.perf_counter() - prev_time)
        if sleep_time > 0:
            time.sleep(sleep_time)
        prev_time = time.perf_counter()

except KeyboardInterrupt:
    conveyors_list.stop_all()
    print("Keyboard Interrupt")
    END_PROGRAM = True
finally:
    # Ensure all conveyors are stopped on program exit
    conveyors_list.stop_all()
    print("Conveyors have been stopped. Program terminated.")