
from conveyor_types.base import Conveyor, ConveyorState
from conveyor_types.system import SystemState
from conveyor_types.definitions.ipc_mqtt_definitions import mqtt_messages


class TransferConveyor(Conveyor):
    def __init__(self, system_state: SystemState, parentConveyor: Conveyor, index, **kwargs):
        super().__init__(system_state, index, **kwargs)
        self.initialize_box_sensor(kwargs)
        self.initialize_pusher(kwargs)
        self.parentConveyor = parentConveyor
        self.conveyor_state = ConveyorState.INIT

    def run(self):
        self.system_state.publish_conv_state(self.index, self.conveyor_state.name)
        if not self.system_state.drives_are_ready and not self.system_state.estop:
            self.conveyor_state = ConveyorState.INIT
            if self.pusher_present:
                self.pusher.pull_async()

        if self.conveyor_state == ConveyorState.INIT:
            if self.pusher_state("pushed"):
                self.pusher.pull_async()
            if self.system_state.drives_are_ready:
                self.move_conveyor()
                self.conveyor_state = ConveyorState.RUNNING

        elif self.conveyor_state == ConveyorState.RUNNING:
            if self.box_sensor.state.value:
                self.stop()

        elif self.conveyor_state == ConveyorState.STOPPING:
            if self.pusher_present and (
                    self.conveyor_state == ConveyorState.STOPPING and
                    self.parentConveyor.conveyor_state == ConveyorState.RUNNING):
                self.conveyor_state = ConveyorState.PUSHING
            elif not self.pusher_present:
                self.conveyor_state = ConveyorState.WAITING
            if not self.box_sensor.state.value:
                self.move_conveyor()
                self.conveyor_state = ConveyorState.RUNNING

        elif self.conveyor_state == ConveyorState.PUSHING:
            self.pusher.push_async()
            if self.pusher_state("pushed"):
                self.pusher.idle_async()
                self.conveyor_state = ConveyorState.RETRACT

        elif self.conveyor_state == ConveyorState.RETRACT:
            self.pusher.pull_async()
            if self.pusher_state("pulled"):
                self.pusher.idle_async()
                self.conveyor_state = ConveyorState.WAITING

        elif self.conveyor_state == ConveyorState.WAITING:
            if not self.box_sensor.state.value:
                self.move_conveyor()
                self.conveyor_state = ConveyorState.RUNNING

    def stop(self):
        self.conveyor_state = ConveyorState.STOPPING
        self.system_state.publish_conv_state(self.index, self.conveyor_state.name)
        self.stop_conveyor()
