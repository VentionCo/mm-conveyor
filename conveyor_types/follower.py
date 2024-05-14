
from conveyor_types.base import Conveyor, ConveyorState
from conveyor_types.system import SystemState


class FollowerConveyor(Conveyor):
    def __init__(self, system_state: SystemState, parentConveyor: Conveyor, **kwargs):
        super().__init__(system_state, **kwargs)

        self.initialize_actuator(kwargs)
        self.parentConveyor = parentConveyor
        self.conveyor_state = parentConveyor.conveyor_state

    def run(self):
        if self.parentConveyor.conveyor_state == ConveyorState.RUNNING:
            self.conveyor_state = self.parentConveyor.conveyor_state
            self.move_conveyor()
        else:
            self.stop()

    def stop(self):
        self.conveyor_state = ConveyorState.STOPPING
        self.stop_conveyor()
