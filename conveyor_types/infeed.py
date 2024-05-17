
from conveyor_types.base import Conveyor, ConveyorState
from conveyor_types.system import SystemState
from helpers.thread_helpers import InterThreadBool
from helpers.timer_helper import Timer
from conveyor_types.definitions.ipc_mqtt_definitions import mqtt_messages


class InfeedConveyor(Conveyor):
    def __init__(self, system_state: SystemState, robot_is_picking: InterThreadBool, index, **kwargs):
        super().__init__(system_state, index, **kwargs)

        self.initialize_box_sensor(kwargs)
        self.initialize_pusher(kwargs)

        self.robot_is_picking = robot_is_picking
        self.restart_conveyor_timer = Timer(self.pusher_retract_delay)
        self.not_moving = True

    def run(self):
        self.system_state.publish_conv_state(self.index, self.conveyor_state.name)
        if not self.system_state.drives_are_ready and self.system_state.estop:
            self.conveyor_state = ConveyorState.INIT
            if self.pusher_present:
                self.pusher.pull_async()
        if self.conveyor_state == ConveyorState.INIT:
            if self.pusher_state("pushed"):
                self.pusher.pull_async()
                self.conveyor_state = ConveyorState.RETRACT
            if self.pusher_state("pulled"):
                self.move_conveyor()
                self.not_moving = False
                self.conveyor_state = ConveyorState.RUNNING

        if self.conveyor_state == ConveyorState.RUNNING:
            if self.pusher_present:
                self.pusher.idle_async()
            if self.get_box_sensor_state():
                self.stop()
                self.not_moving = True
                self.conveyor_state = ConveyorState.STOPPING

        elif self.conveyor_state == ConveyorState.STOPPING:
            self.not_moving = True
            if self.pusher_present:
                self.conveyor_state = ConveyorState.PUSHING
            else:
                self.conveyor_state = ConveyorState.WAITING_FOR_PICK

        elif self.conveyor_state == ConveyorState.PUSHING:
            self.not_moving = True
            self.pusher.push_async()
            if self.pusher_state("pushed"):
                self.pusher.idle_async()
                self.conveyor_state = ConveyorState.RETRACT

        elif self.conveyor_state == ConveyorState.RETRACT:
            self.not_moving = True
            self.pusher.pull_async()
            if self.pusher_state("pulled"):
                self.pusher.idle_async()
                self.conveyor_state = ConveyorState.WAITING_FOR_PICK

        elif self.conveyor_state == ConveyorState.WAITING_FOR_PICK:
            self.not_moving = True
            if (not self.get_box_sensor_state() and not self.robot_is_picking.get() and
                    not self.restart_conveyor_timer.started):
                self.restart_conveyor_timer.start()
            if self.restart_conveyor_timer.done():
                self.restart_conveyor_timer.stop()
                self.move_conveyor()
                self.conveyor_state = ConveyorState.RUNNING

    def stop(self):
        self.system_state.publish_conv_state(self.index, self.conveyor_state.name)
        self.conveyor_state = ConveyorState.INIT
        self.stop_conveyor()
        self.restart_conveyor_timer.stop()
        if self.pusher_present:
            self.pusher.idle_async()
