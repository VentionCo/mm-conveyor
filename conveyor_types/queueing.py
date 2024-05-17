
from conveyor_types.base import Conveyor, ConveyorState
from conveyor_types.system import SystemState
from conveyor_types.definitions.ipc_mqtt_definitions import mqtt_messages

class QueueingConveyor(Conveyor):
    def __init__(self, system_state: SystemState, parentConveyor: Conveyor, index, **kwargs):
        super().__init__(system_state, index, **kwargs)
        self.initialize_box_sensor(kwargs)
        self.parentConveyor = parentConveyor
        self.conveyor_state = parentConveyor.conveyor_state

    def run(self):
        if self.parentConveyor.conveyor_state == ConveyorState.RUNNING:
            self.system_state.publish_conv_state(self.index, mqtt_messages['convRunning'])
            self.conveyor_state = self.parentConveyor.conveyor_state
            self.move_conveyor()
        else:
            if self.box_sensor.state.value:
                self.stop()

    def stop(self):
        self.system_state.publish_conv_state(self.index, mqtt_messages['convStopped'])
        self.conveyor_state = ConveyorState.STOPPING
        self.stop_conveyor()
