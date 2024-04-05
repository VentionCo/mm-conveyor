from conveyors import (SimpleInfeedConveyor, SimplePickConveyor,
                        InfeedConveyor, AccumulatingConveyor, DoublePickInfeedConveyor,
                       QueueingConveyor, SystemState)
from conveyor_types.conveyor_definitions import *
from conveyor_types.simple import SimpleConveyor, SimpleFSMConveyor
from conveyor_types.pick import PickFSMConveyor
from conveyor_types.follower import FollowerFSMConveyor
from conveyor_types.queueing import QueueingFSMConveyor
import json
import os


def get_conveyor_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    conveyor_configuration_path = os.path.join(parent_dir, "configured_conveyors.json")

    with open(conveyor_configuration_path) as f:
        configuration_data = json.load(f)

    return configuration_data


def configure_conveyors(configuration_data, system, robot_is_picking):
    parent = None
    conveyors = []
    index = 1
    for key, conveyor_config in configuration_data[LIST_OF_ALL_CONVEYORS].items():
        if conveyor_config[ENABLE_CONVEYORS] != "True":
            continue
        print(conveyor_config)

        conveyor_type = conveyor_config[TYPE]

        if conveyor_type == "InfeedConveyor":
            infeed_conveyor = InfeedConveyor(system, robot_is_picking, **conveyor_config)
            conveyors.append(infeed_conveyor)
        elif conveyor_type == "SimpleConveyor":
            simple_conveyor = SimpleFSMConveyor(system, index, **conveyor_config)
            conveyors.append(simple_conveyor)
        elif conveyor_type == "PickConveyor":
            pick_conveyor = PickFSMConveyor(system, robot_is_picking, index, **conveyor_config)
            parent = pick_conveyor
            conveyors.append(pick_conveyor)
        # elif conveyor_type == "AccumulatingConveyor":
        #     accumulating_conveyor = AccumulatingConveyor(system, robot_is_picking, **conveyor_config)
        #     conveyors.append(accumulating_conveyor)
        # elif conveyor_type == "DoublePickInfeedConveyor":
        #     double_pick_infeed_conveyor = DoublePickInfeedConveyor(system, **conveyor_config)
        #     conveyors.append(double_pick_infeed_conveyor)
        elif conveyor_type == "FollowerConveyor":
            if parent is None:
                raise ValueError("Parent conveyor not defined for follower conveyor.")
            else:
                follower_conveyor = FollowerFSMConveyor(system, parent, **conveyor_config)
                conveyors.append(follower_conveyor)
        elif conveyor_type == "QueueingConveyor":
            queueing_conveyor = QueueingFSMConveyor(system, parent, **conveyor_config)
            conveyors.append(queueing_conveyor)
        index = index + 1
    return conveyors


def fake_box(system: SystemState):
    system.machine.publish_mqtt_event('estop/status', "False")
    system.machine.publish_mqtt_event('smartDrives/areReady', "True")