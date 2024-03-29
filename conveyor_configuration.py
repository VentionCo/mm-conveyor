from conveyors import (SimpleInfeedConveyor, SimplePickConveyor,
                       SimpleConveyor, InfeedConveyor, AccumulatingConveyor, DoublePickInfeedConveyor,
                       FollowerConveyor, QueueingConveyor, SystemState)
from conveyor_definitions import *
import json


def get_conveyor_config():
    conveyor_configuration_path = "configured_conveyors.json"
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

        if conveyor_type == "SimplePickConveyor":
            pick_infeed = SimplePickConveyor(system, **conveyor_config)
            conveyors.append(pick_infeed)
            parent = pick_infeed
        elif conveyor_type == "SimpleInfeedConveyor":
            infeed_conveyor = SimpleInfeedConveyor(system, parent, **conveyor_config)
            conveyors.append(infeed_conveyor)
        elif conveyor_type == "SimpleConveyor":
            simple_conveyor = SimpleConveyor(system, index, **conveyor_config)
            conveyors.append(simple_conveyor)
        elif conveyor_type == "InfeedConveyor":
            infeed_conveyor = InfeedConveyor(system, robot_is_picking, **conveyor_config)
            conveyors.append(infeed_conveyor)
        elif conveyor_type == "AccumulatingConveyor":
            accumulating_conveyor = AccumulatingConveyor(system, robot_is_picking, **conveyor_config)
            conveyors.append(accumulating_conveyor)
        elif conveyor_type == "DoublePickInfeedConveyor":
            double_pick_infeed_conveyor = DoublePickInfeedConveyor(system, **conveyor_config)
            conveyors.append(double_pick_infeed_conveyor)
        elif conveyor_type == "FollowerConveyor":
            follower_conveyor = FollowerConveyor(system, parent, **conveyor_config)
            conveyors.append(follower_conveyor)
        elif conveyor_type == "QueueingConveyor":
            queueing_conveyor = QueueingConveyor(system, parent, **conveyor_config)
            conveyors.append(queueing_conveyor)
        index = index + 1
    return conveyors


def fake_box(system: SystemState):
    system.machine.publish_mqtt_event('estop/status', "False")
    system.machine.publish_mqtt_event('smartDrives/areReady', "True")