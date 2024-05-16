from conveyor_types.base import Conveyor, ConveyorState
from conveyor_types.system import SystemState


class SimpleConveyor(Conveyor):
    def __init__(self, system_state: SystemState, index, **kwargs):
        super().__init__(system_state, index, **kwargs)
        self.initialize_box_sensor(kwargs)

    def run(self):
        if not self.system_state.drives_are_ready or self.system_state.estop:
            self.conveyor_state = ConveyorState.INIT
            self.stop_conveyor()

        if self.get_box_sensor_state():
            self.stop()

        else:
            self.conveyor_state = ConveyorState.RUNNING
            self.move_conveyor()

    def stop(self):
        self.conveyor_state = ConveyorState.STOPPING
        self.stop_conveyor()
