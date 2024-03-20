''' This is the main program for the conveyor control system. 
It is responsible for creating the conveyor objects and running the main conveyor loop. 
The main conveyor loop is responsible for running the conveyors and stopping them
when the drives are not ready or the system is in an estop state.
The main conveyor loop also checks for the programRun flag and stops the conveyors if set to False.
The main conveyor loop also checks for the robotIsPicking flag and stops the conveyors 
if it is set to True. The main conveyor loop also checks for the
END_PROGRAM flag and stops the conveyors if it is set to True. 
The main conveyor loop also checks for the CONVEYORS_ARE_RUNNING flag and
stops the conveyors if it is set to False. 
'''

import time
from conveyor_definitions import *
from conveyors import SimpleInfeedConveyor, SimplePickConveyor, SystemState, ControlAllConveyor
from helpers import InterThreadBool, get_conveyor_config

system = SystemState()

"""
TODO:
REQUIREMENTS: 
- 1 MM
- I IO module
- 3 photo sensors (1 pick, 1 infeed start IS, 1 infeed stop)

Description of the infeed and pick conveyor: 
    the infeed conveyor starts rolling when IS is detected (infeed start sensor), this will also start the pick conveyor
    the pick will stop when the pick sensor is detected, 
    the infeed conveyor will stop when the infeed stop sensor is detected
"""


time.sleep(2)

configuration_data = get_conveyor_config()
conveyors = []
robot_is_picking = InterThreadBool()
PARENT = None

for key, conveyor_config in configuration_data[LIST_OF_ALL_CONVEYORS].items():
    if conveyor_config[ENABLE_CONVEYORS] != "True":
        continue

    conveyor_type = conveyor_config[TYPE]
    print(conveyor_type)
    print(conveyor_config)

    if conveyor_type == "SimplePickConveyor":
        pickInfeed = SimplePickConveyor(system, **conveyor_config)
        conveyors.append(pickInfeed)
        PARENT = pickInfeed
    elif conveyor_type == "SimpleInfeedConveyor":
        infeed_conveyor = SimpleInfeedConveyor(system, PARENT, **conveyor_config)
        conveyors.append(infeed_conveyor)

for conveyor in conveyors:
    print(conveyor.conveyor_state)
    print(conveyor.system_state.estop)
    print(conveyor.system_state.drives_are_ready)


## Main conveyor loop program


conveyors_list = ControlAllConveyor(conveyors)

program_run = InterThreadBool()

END_PROGRAM = False
CONVEYORS_ARE_RUNNING = False
prev_time = time.perf_counter()

program_run.set(True)
try:

    while not infeed_conveyor.get_start_sensor_state():
        print("Waiting for start sensor")
        time.sleep(1)

    while True:

        try:
            if program_run.get() and system.drives_are_ready :
                conveyors_list.run_all()
                CONVEYORS_ARE_RUNNING = True
            elif not system.drives_are_ready or system.estop:
                conveyors_list.stop_all()
                CONVEYORS_ARE_RUNNING = False
                program_run.set(False)
            else:
                program_run.set(True)

        except Exception as e:
            conveyors_list.stop_all()
            print(e)

        sleep_time = 0.100 - (time.perf_counter() - prev_time)
        if sleep_time > 0:
            time.sleep(sleep_time)
        prev_time = time.perf_counter()

except KeyboardInterrupt:
    conveyors_list.stop_all()
    print("Keyboard Interrupt")
    END_PROGRAM = True
