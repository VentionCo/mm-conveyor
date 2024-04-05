from conveyor_types.base import Conveyor, ConveyorState
from conveyor_types.system import SystemState
from transitions import Machine as MachineTransitions
from transitions.extensions import GraphMachine as MachineTransitions
import time
import threading


class QueueingConveyor(Conveyor):
    def __init__(self, system_state: SystemState, parentConveyor: Conveyor, **kwargs):
        super().__init__(system_state, **kwargs)
        self.initialize_box_sensor(kwargs)
        self.parentConveyor = parentConveyor
        self.conveyor_state = parentConveyor.conveyor_state

    def run(self):
        if self.parentConveyor.conveyor_state == ConveyorState.RUNNING:
            self.conveyor_state = self.parentConveyor.conveyor_state
            self.move_conveyor()
        else:
            if self.box_sensor.state.value:
                self.stop()

    def stop(self):
        self.conveyor_state = ConveyorState.STOPPING
        self.stop_conveyor()


class QueueingFSMConveyor(Conveyor):
    def __init__(self, system_state: SystemState, parentConveyor: Conveyor, **kwargs):
        super().__init__(system_state, **kwargs)
        self.parentConveyor = parentConveyor

        self.parent_topic = f'conveyors/{self.parentConveyor.index}/state'

        self.states = ['running', 'stopped']
        self.machine = MachineTransitions(model=self, states=self.states, initial='stopped')
        self.machine.add_transition(trigger='start', source='stopped', dest='running', before='before_start',
                                    after='after_start')
        self.machine.add_transition(trigger='stop', source='running', dest='stopped', before='before_stop',
                                    after='after_stop')
        self.initialize_box_sensor(kwargs)
        self.system_state.machine.on_mqtt_event(self.sensor_topic, self.mqtt_event_handler)
        self.system_state.machine.on_mqtt_event(self.parent_topic, self.parent_state_handler)
        # self.system_state.machine.on_mqtt_event(self.parent_topic, self.mqtt_event_handler)
        self.machine.get_graph().draw('./conveyor_types/state_images/queueing_conveyor_state_diagram.png', prog='dot')

    def parent_state_handler(self, topic, message):
        if message == 'running':
            self.start()

    def mqtt_event_handler(self, topic, message):
        if message == 'START':
            self.start()
        elif message == 'STOP':
            if self.parentConveyor.state != 'running':
                self.stop()
            else:
                pass

    def before_start(self):
        print("Preparing to start follower conveyor.")

    def after_start(self):
        self.move_conveyor()
        print("Follower conveyor started.")

    def before_stop(self):
        print("Preparing to stop follower conveyor.")

    def after_stop(self):
        self.stop_conveyor()
        print("Follower conveyor stopped.")