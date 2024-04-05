"""
Definitions for the different types of conveyors
"""

from conveyor_types.definitions.conveyor_definitions import *
from helpers.thread_helpers import InterThreadBool
from helpers.timer_helper import Timer
from conveyor_types.system import SystemState
from conveyor_types.base import Conveyor, ConveyorState


class SimpleInfeedConveyor(Conveyor):

    def __init__(self, system_state: SystemState, parentConveyor: Conveyor, **kwargs):
        super().__init__(system_state, **kwargs)
        self.initialize_box_sensor(kwargs)
        self.parent_conveyor = parentConveyor

    def run(self):
        if not self.system_state.drives_are_ready and self.system_state.estop:
            self.system_state.publish_conv_state(1, 'stopped')
            self.conveyor_state = ConveyorState.INIT
            self.stop_conveyor()
        if self.parent_conveyor.conveyor_state == ConveyorState.RUNNING:
            self.move_conveyor()
            self.conveyor_state = ConveyorState.RUNNING
        if self.conveyor_state == ConveyorState.RUNNING:
            self.system_state.publish_conv_state(1, 'running')
            if self.get_box_sensor_state() and not self.parent_conveyor.conveyor_state == ConveyorState.RUNNING:
                self.stop()
                self.conveyor_state = ConveyorState.STOPPING
        elif self.conveyor_state == ConveyorState.STOPPING:
            self.stop_conveyor()
            self.conveyor_state = ConveyorState.INIT

    def stop(self):
        self.system_state.publish_conv_state(1, 'stopped')
        self.conveyor_state = ConveyorState.INIT
        self.stop_conveyor()


class SimplePickConveyor(Conveyor):
    def __init__(self, system_state: SystemState, **kwargs):
        super().__init__(system_state, **kwargs)
        self.initialize_box_sensor(kwargs)
        self.initialize_pusher(kwargs)
        self.box_detected = False

    def run(self):
        if not self.system_state.drives_are_ready and self.system_state.estop:
            self.system_state.publish_conv_state(2, 'stopped')
            self.conveyor_state = ConveyorState.INIT
            if self.pusher_present:
                self.pusher.pull_async()
        if self.conveyor_state == ConveyorState.INIT:
            if self.pusher_state("pushed"):
                self.conveyor_state = ConveyorState.RETRACT
            if self.pusher_state("pulled"):
                self.move_conveyor()
                self.conveyor_state = ConveyorState.RUNNING
        elif self.conveyor_state == ConveyorState.RUNNING:
            self.system_state.publish_conv_state(2, 'running')
            print('running')
            self.move_conveyor()
            if self.get_box_sensor_state():
                self.stop()
                self.conveyor_state = ConveyorState.STOPPING
        elif self.conveyor_state == ConveyorState.RETRACT:
            self.pusher.pull_async()
            if self.pusher_state("pulled"):
                self.pusher.idle_async()
                self.conveyor_state = ConveyorState.WAITING_FOR_PICK
        elif self.conveyor_state == ConveyorState.PUSHING:
            self.pusher.push_async()
            if self.pusher_state("pushed"):
                self.pusher.idle_async()
                self.conveyor_state = ConveyorState.RETRACT
        elif self.conveyor_state == ConveyorState.STOPPING:
            self.stop()
            self.conveyor_state = ConveyorState.PUSHING
        elif self.conveyor_state == ConveyorState.WAITING_FOR_PICK:
            if not self.get_box_sensor_state():
                self.conveyor_state = ConveyorState.RUNNING

    def stop(self):
        self.system_state.publish_conv_state(2, 'stopped')
        self.conveyor_state = ConveyorState.INIT
        self.stop_conveyor()
        if self.pusher_present:
            self.pusher.idle_async()





class DoublePickInfeedConveyor(Conveyor):

    def __init__(self, system_state: SystemState, robot_is_picking: InterThreadBool = InterThreadBool(), **kwargs):
        super().__init__(system_state, **kwargs)
        self.pacingTimer = None
        self.sustainTimer = None
        self.startup_timer = None
        self.initialize_timers(**kwargs)
        self.initialize_box_sensor(kwargs)
        self.initialize_accumulation_sensor(kwargs)
        self.initialize_pusher(kwargs)
        self.initialize_stopper(kwargs)

        self.restart_conveyor_timer = Timer(kwargs.get(RESTART_TIME))
        self.boxes_to_queue = 2
        self.box_was_picked = False
        self.robot_is_picking = robot_is_picking

    def initialize_timers(self, **kwargs):
        self.startup_timer = Timer(kwargs.get(STARTUP_TIME))
        self.sustainTimer = Timer(kwargs.get(SUSTAIN_TIME))
        self.pacingTimer = Timer(kwargs.get(PACING_TIME))

    def run(self):
        if not self.system_state.drives_are_ready and not self.system_state.estop:
            self.conveyor_state = ConveyorState.INIT
            if self.pusher_present:
                self.pusher.pull_async()
            if self.stopper_present:
                self.stopper.pull_async()

        if self.conveyor_state == ConveyorState.INIT:
            if self.pusher_state("pulled"):
                self.pusher.pull_async()
            if self.stopper_state("pushed"):
                self.stopper.push_async()

            if self.system_state.drives_are_ready and self.pusher_state("pulled"):
                if not self.startup_timer.started:
                    self.startup_timer.start()
                self.boxes_to_queue = 2
                self.conveyor_state = ConveyorState.STARTUP

        elif self.conveyor_state == ConveyorState.STARTUP:
            if self.startup_timer.done() or (self.get_box_sensor_state() and self.get_accumulation_sensor_state()):
                self.startup_timer.stop()
                if self.get_box_sensor_state():
                    self.boxes_to_queue -= 1
                if self.get_accumulation_sensor_state():
                    self.boxes_to_queue -= 1
                if self.boxes_to_queue < 0:
                    print("ERROR: More boxes detected than expected")
                    raise Exception("ERROR: More boxes detected than expected")
                if self.boxes_to_queue > 0:
                    self.stopper.idle_async()
                    print("[Startup] Boxes to queue: " + str(self.boxes_to_queue))
                    self.conveyor_state = ConveyorState.QUEUEING

        elif self.conveyor_state == ConveyorState.QUEUEING:
            self.stopper.pull_async()
            if self.stopper_sensor_present and self.stopper_sensor.state.value:
                self.boxes_to_queue -= 1
            if self.boxes_to_queue == 0:
                self.stopper.idle_async()
                self.move_conveyor()
                self.conveyor_state = ConveyorState.RUNNING

        elif self.conveyor_state == ConveyorState.RUNNING:
            self.stopper.push_async()
            if self.get_box_sensor_state() and self.get_accumulation_sensor_state() and not self.sustainTimer.started:
                self.sustainTimer.start()
            if self.sustainTimer.done():
                self.sustainTimer.stop()
                self.stop_conveyor()
                self.conveyor_state = ConveyorState.PUSHING

        elif self.conveyor_state == ConveyorState.PUSHING:
            if not self.pusher_present:
                self.conveyor_state = ConveyorState.WAITING_FOR_PICK
            else:
                self.pusher.push_async()
                if self.pusher_state("pushed"):
                    self.pusher.idle_async()
                    self.conveyor_state = ConveyorState.RETRACT

        elif self.conveyor_state == ConveyorState.RETRACT:
            self.pusher.pull_async()
            if self.pusher_state("pulled"):
                self.pusher.idle_async()
                self.box_was_picked = False
                self.conveyor_state = ConveyorState.WAITING_FOR_PICK

        elif self.conveyor_state == ConveyorState.WAITING_FOR_PICK:
            if not self.get_box_sensor_state() or not self.get_accumulation_sensor_state():
                self.box_was_picked = True
            if self.box_was_picked and not self.robot_is_picking.get() and not self.restart_conveyor_timer.started:
                self.restart_conveyor_timer.start()
            if self.restart_conveyor_timer.done():
                self.restart_conveyor_timer.stop()
                self.boxes_to_queue = 2
                if self.get_box_sensor_state():
                    self.boxes_to_queue -= 1
                if self.get_accumulation_sensor_state():
                    self.boxes_to_queue -= 1
                self.move_conveyor()
                if self.pacingTimer.started:
                    self.pacingTimer.start()
                self.conveyor_state = ConveyorState.PACING

        elif self.conveyor_state == ConveyorState.PACING:
            if self.pacingTimer.done():
                self.pacingTimer.stop()
                if self.boxes_to_queue > 0:
                    self.stopper.idle_async()
                print("[Pacing] Boxes to queue: " + str(self.boxes_to_queue))
                self.conveyor_state = ConveyorState.QUEUEING

    def stop(self):
        self.conveyor_state = ConveyorState.INIT
        self.stop_conveyor()
        self.restart_conveyor_timer.stop()
        self.startup_timer.stop()
        self.sustainTimer.stop()
        self.pacingTimer.stop()

        if self.pusher_present:
            self.pusher.idle_async()
        if self.stopper_present:
            self.stopper.push_async()


class ControlAllConveyor:
    """
    ControlAllConveyor class is used to control all the conveyors.
    It is used to control the behavior of all the conveyors in the system.
    Attributes:
        list_of_conveyors: A list of all the conveyors in the system.
    Methods:
        run_all: A method that is used to run all the conveyors.
        stop_all: A method that is used to stop all the conveyors.
        set_init_state: A method that is used to set the state of all the conveyors to INIT.
    """

    def __init__(self, list_of_conveyors: list):
        self.list_of_conveyors = list_of_conveyors

    def run_all(self):
        """
        A method that is used to run all the conveyors.
        """
        for conveyor in self.list_of_conveyors:
            conveyor.run()

    def stop_all(self):
        """
        A method that is used to stop all the conveyors.
        """
        for conveyor in self.list_of_conveyors:
            conveyor.stop()

    def set_init_state(self):
        """
        A method that is used to set the state of all the conveyors to INIT.
        """
        for conveyor in self.list_of_conveyors:
            conveyor.set_conveyor_state_to_init()
