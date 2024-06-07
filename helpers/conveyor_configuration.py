
from conveyor_types.system import SystemState
from conveyor_types.simple import SimpleConveyor
from conveyor_types.infeed import InfeedConveyor
from conveyor_types.accumulating import AccumulatingConveyor
from conveyor_types.double_pick_infeed import DoublePickInfeedConveyor
from conveyor_types.follower import FollowerConveyor
from conveyor_types.queueing import QueueingConveyor
from conveyor_types.transfer import TransferConveyor
from conveyor_types.custom import CustomConveyor
from conveyor_types.definitions.conveyor_definitions import *
import json
import os


def get_conveyor_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    conveyor_configuration_path = os.path.join(script_dir, '..', 'configurations', 'configured_conveyors.json')
    with open(conveyor_configuration_path) as f:
        configuration_data = json.load(f)
    return configuration_data


def configure_conveyors(configuration_data, system, robot_is_picking):
    parent = None
    conveyors = []
    index = 1
    for key, conveyor_config in configuration_data[LIST_OF_ALL_CONVEYORS].items():
        print(conveyor_config)

        conveyor_type = conveyor_config[TYPE]

        if conveyor_type == "SimpleConveyor":
            simple_conveyor = SimpleConveyor(system, index, **conveyor_config)
            parent = simple_conveyor
            conveyors.append(simple_conveyor)
        elif conveyor_type == "InfeedConveyor":
            infeed_conveyor = InfeedConveyor(system, robot_is_picking, index, **conveyor_config)
            parent = infeed_conveyor
            conveyors.append(infeed_conveyor)
        elif conveyor_type == "AccumulatingConveyor":
            accumulating_conveyor = AccumulatingConveyor(system, robot_is_picking, index, **conveyor_config)
            parent = accumulating_conveyor
            conveyors.append(accumulating_conveyor)
        elif conveyor_type == "DoublePickInfeedConveyor":
            double_pick_infeed_conveyor = DoublePickInfeedConveyor(system, index, **conveyor_config)
            parent = double_pick_infeed_conveyor
            conveyors.append(double_pick_infeed_conveyor)
        elif conveyor_type == "FollowerConveyor":
            follower_conveyor = FollowerConveyor(system, parent, index, **conveyor_config)
            conveyors.append(follower_conveyor)
        elif conveyor_type == "QueueingConveyor":
            queueing_conveyor = QueueingConveyor(system, parent, index, **conveyor_config)
            conveyors.append(queueing_conveyor)
        elif conveyor_type == "TransferConveyor":
            transfer_conveyor = TransferConveyor(system, parent, index, **conveyor_config)
            conveyors.append(transfer_conveyor)
        elif conveyor_type == "CustomConveyor":
            custom_conveyor = CustomConveyor(system, robot_is_picking, index, **conveyor_config)
            conveyors.append(custom_conveyor)
        index = index + 1
    return conveyors


def fake_box(system: SystemState):
    system.machine.publish_mqtt_event('estop/status', "False")
    system.machine.publish_mqtt_event('smartDrives/areReady', "True")