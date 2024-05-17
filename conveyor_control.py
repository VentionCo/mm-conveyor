import logging
import threading
import time

from machinelogic import Machine

from configurations.restart_control import write_to_json
from conveyor_types.conveyors import ControlAllConveyor
from conveyor_types.definitions.ipc_mqtt_definitions import mqtt_topics
from conveyor_types.system import SystemState
from helpers.conveyor_configuration import get_conveyor_config, configure_conveyors, fake_box
from helpers.thread_helpers import InterThreadBool

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("conveyor_system.log"),
                        logging.StreamHandler()
                    ])

machine = Machine()
system = SystemState(machine)

configuration_data = get_conveyor_config()
robot_is_picking = InterThreadBool()
program_run = InterThreadBool()
END_PROGRAM = False

control_flag = InterThreadBool(True)
thread_stop_flag = threading.Event()
conveyor_thread = None


def start_conveyor_thread():
    global conveyor_thread
    thread_stop_flag.clear()
    control_flag.set(True)
    program_run.set(True)

    conveyor_thread = threading.Thread(target=conveyor_loop, daemon=True)
    conveyor_thread.start()
    logging.info("Conveyor thread started")


def stop_conveyor_thread():
    global conveyor_thread
    if conveyor_thread is not None:
        thread_stop_flag.set()
        conveyor_thread.join()
        conveyor_thread = None
        logging.info("Conveyor thread stopped")


def on_restart_command(topic: str, message: str):
    logging.info(f"Received restart command on topic {topic} with message {message}")

    stop_conveyor_thread()
    logging.info("Conveyors stopped")
    time.sleep(1)
    logging.info("Restarting with new configuration")

    # Write new configuration
    write_to_json(message)
    new_configuration_data = get_conveyor_config()
    new_conveyors = configure_conveyors(new_configuration_data, system, robot_is_picking)
    conveyors_list.update_conveyors(new_conveyors)

    # Start a new conveyor thread
    start_conveyor_thread()


def conveyor_loop():
    while not thread_stop_flag.is_set():
        if control_flag.get() and program_run.get() and system.program_run:
            conveyors_list.run_all()
            logging.debug('running')
        elif not system.program_run:
            conveyors_list.stop_all()
            logging.debug('stopped')
        time.sleep(1)  # Avoid busy waiting


# Register MQTT event
logging.info("Registering MQTT event for topic 'conveyors/configured'")
machine.on_mqtt_event(mqtt_topics['restart'], on_restart_command)
system.subscribe_to_control_topics()

# Configure conveyors and start controlling them
conveyors = configure_conveyors(configuration_data, system, robot_is_picking)
conveyors_list = ControlAllConveyor(conveyors)

fake_box(system)

# Start the conveyor loop in a separate thread
start_conveyor_thread()

try:
    while True:
        time.sleep(10)
except KeyboardInterrupt:
    logging.info("Keyboard Interrupt received, stopping conveyors...")
    END_PROGRAM = True
finally:
    stop_conveyor_thread()
    conveyors_list.stop_all()
    logging.info("Conveyors have been stopped. Program terminated.")
