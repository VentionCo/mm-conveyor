from conveyor_types.base import Conveyor, ConveyorState
from conveyor_types.system import SystemState
from transitions import Machine as MachineTransitions
from helpers.thread_helpers import InterThreadBool
from helpers.timer_helper import Timer
from transitions.extensions import GraphMachine as MachineTransitions
from conveyor_types.ipc_mqtt_definitions import mqtt_messages, mqtt_topics, format_message


class TransferConveyor(Conveyor):
    def __init__(self, system_state: SystemState, parentConveyor: Conveyor, **kwargs):
        super().__init__(system_state, **kwargs)
        self.initialize_box_sensor(kwargs)
        self.initialize_pusher(kwargs)
        self.parentConveyor = parentConveyor
        self.conveyor_state = ConveyorState.INIT

    def run(self):
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
                    self.conveyor_state == ConveyorState.STOPPING and self.parentConveyor.conveyor_state == ConveyorState.RUNNING):
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
        self.stop_conveyor()


class TransferFSMConveyor(Conveyor):
    def __init__(self, system_state: SystemState, parentConveyor: Conveyor, **kwargs):
        super().__init__(system_state, **kwargs)
        self.parentConveyor = parentConveyor
        self.parent_topic = format_message(mqtt_topics['conveyor/state'], id_conv=parentConveyor.index)

        self.states = ['running', 'stopped', 'pushing', 'retracting', 'waiting']
        self.machine = MachineTransitions(model=self, states=self.states, initial='running')
        self.machine.add_transition(trigger='stop', source='running', dest='stopped', before='before_stop',
                                    after='after_stop')
        self.machine.add_transition(trigger='push', source='stopped', dest='pushing', before='before_push',
                                    after='after_push')
        self.machine.add_transition(trigger='retract', source='pushing', dest='retracting', before='before_retract',
                                    after='after_retract')
        self.machine.add_transition(trigger='wait', source='retracting', dest='waiting', before='before_wait',
                                    after='after_wait')
        self.machine.add_transition(trigger='start', source='waiting', dest='running', before='before_start',
                                    after='after_start')
        self.initialize_box_sensor(kwargs)
        self.initialize_pusher(kwargs)
        self.system_state.machine.on_mqtt_event(self.sensor_topic, self.mqtt_event_handler)
        self.system_state.machine.on_mqtt_event(self.parent_topic, self.mqtt_event_handler)
        self.machine.get_graph().draw('./conveyor_types/state_images/transfer_conveyor_state_diagram.png', prog='dot')

    def mqtt_event_handler(self, topic, message):
        if topic == self.sensor_topic:
            if message == mqtt_messages['sensorTrigger']:
                self.start()
            elif message == mqtt_messages['sensorUnTrigger']:
                if self.parentConveyor.state != 'running':
                    self.stop()
                else:
                    pass
        if topic == self.parent_topic:
            if message == mqtt_messages['parentRunning']:
                self.start()

    def before_start(self):
        print("Preparing to start follower conveyor.")

    def after_start(self):
        self.move_conveyor()
        print("Follower conveyor started.")

    def before_push(self):
        print("Preparing to push.")

    def after_push(self):
        self.pusher.push_async()
        print("Pushing box.")
        self.retract()

    def before_retract(self):
        print("Preparing to retract.")

    def after_retract(self):
        self.pusher.pull_async()
        print("Retracting pusher.")
        self.wait()

    def before_wait(self):
        print("Preparing to wait.")

    def after_wait(self):
        print("Waiting for box.")
        self.start()

    def before_stop(self):
        print("Preparing to stop follower conveyor.")

    def after_stop(self):
        self.stop_conveyor()
        print("Follower conveyor stopped.")
        self.push()
