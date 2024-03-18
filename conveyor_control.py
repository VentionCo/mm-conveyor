from ast import In
from conveyor_definitions import *
from conveyors import InfeedConveyor, PickInfeedConveyor, SystemState, ControlAllConveyor
import time
from helpers import *

system = SystemState()

time.sleep(2)

configuration_data = get_conveyor_config()
conveyors = []
robot_is_picking = InterThreadBool()
parent = None 

for key, conveyor_config in configuration_data[LIST_OF_ALL_CONVEYORS].items():
    if conveyor_config[ENABLE_CONVEYORS] != "True":
        continue

    conveyor_type = conveyor_config[TYPE]
    print(conveyor_type)
    print(conveyor_config)

    if conveyor_type == "PickInfeedConveyor":
        pickInfeed = PickInfeedConveyor(system, **conveyor_config)
        conveyors.append(pickInfeed)
        parent = pickInfeed
    elif conveyor_type == "InfeedConveyor":
        infeed_conveyor = InfeedConveyor(system, parent, robot_is_picking, **conveyor_config)
        conveyors.append(infeed_conveyor)
    
for conveyor in conveyors:
    print(conveyor.conveyor_state)
    print(conveyor.system_state.estop)
    print(conveyor.system_state.drives_are_ready)


## Main conveyor loop program


conveyors_list = ControlAllConveyor(conveyors)

programRun = InterThreadBool()
robotIsPicking = InterThreadBool()

endProgram = False
conveyors_are_running = False
prev_time = time.perf_counter()

programRun.set(True)
try:

    while True:

        try:
            if programRun.get() and system.drives_are_ready :
                conveyors_list.run_all()
                conveyors_are_running = True
            elif (not system.drives_are_ready or system.estop):
                conveyors_list.stop_all()
                conveyors_are_running = False
                programRun.set(False)
            else:
                programRun.set(True)
    
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
    pass