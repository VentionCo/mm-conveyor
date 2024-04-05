from conveyor_types.base import Conveyor, ConveyorState
from conveyor_types.system import SystemState
from transitions import Machine as MachineTransitions
from transitions.extensions import GraphMachine as MachineTransitions


class SimpleConveyor(Conveyor):
    def __init__(self, system_state: SystemState, index, **kwargs):
        super().__init__(system_state, **kwargs)
        self.initialize_box_sensor(kwargs)
        self.index = index

    def run(self):
        self.system_state.publish_conv_state(self.index, 'running')
        if not self.system_state.drives_are_ready or self.system_state.estop:
            self.conveyor_state = ConveyorState.INIT
            self.stop_conveyor()

        if self.get_box_sensor_state():
            self.stop()

        else:
            self.conveyor_state = ConveyorState.RUNNING
            self.move_conveyor()

    def stop(self):
        self.system_state.publish_conv_state(self.index, 'stopping')
        self.conveyor_state = ConveyorState.STOPPING
        self.stop_conveyor()


class SimpleFSMConveyor(Conveyor):

    def __init__(self, system_state: SystemState, index, **kwargs):
        super().__init__(system_state, **kwargs)
        self.index = index
        self.initialize_box_sensor(kwargs)

        self.states = ['stopped', 'running']
        self.machine = MachineTransitions(model=self, states=self.states, initial='stopped')
        self.machine.add_transition(trigger='start', source='stopped', dest='running', before='before_start',
                                    after='after_start')
        self.machine.add_transition(trigger='stop', source='running', dest='stopped', before='before_stop',
                                    after='after_stop')
        # self.setup_mqtt_box_detection_listener(self.sensor_topic, self.mqtt_event_handler)
        self.system_state.machine.on_mqtt_event(self.sensor_topic, self.mqtt_event_handler)
        self.machine.get_graph().draw('./conveyor_types/state_images/simple_conveyor_state_diagram.png', prog='dot')

    def before_start(self):
        print("Preparing to start conveyor.")
        if not self.system_state.drives_are_ready or self.system_state.estop:
            print("Drives are not ready or system is in estop state.")
            self.stop()

    def after_start(self):
        self.move_conveyor()
        print("Conveyor started.")

    def before_stop(self):
        print("Preparing to stop conveyor.")
        self.stop_conveyor()

    def after_stop(self):
        print("Conveyor stopped.")

    def mqtt_event_handler(self, topic, message):
        if topic == self.sensor_topic:
            if message == 'START':
                self.start()
            elif message == 'STOP':
                self.stop()






