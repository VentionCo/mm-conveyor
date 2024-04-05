from conveyor_types.system import SystemState
from conveyor_types.base import Conveyor, ConveyorState
from helpers.thread_helpers import InterThreadBool
from helpers.timer_helper import Timer
from transitions import Machine as MachineTransitions
from transitions.extensions import GraphMachine as MachineTransitions
from conveyor_types.definitions.ipc_mqtt_definitions import mqtt_messages, mqtt_topics


class InfeedConveyor(Conveyor):
    def __init__(self, system_state: SystemState, robot_is_picking: InterThreadBool = InterThreadBool(), **kwargs):
        super().__init__(system_state, **kwargs)

        self.initialize_box_sensor(kwargs)
        self.initialize_pusher(kwargs)

        self.robot_is_picking = robot_is_picking
        self.restart_conveyor_timer = Timer(self.pusher_retract_delay)
        self.not_moving = True

    def run(self):
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
            if not self.get_box_sensor_state() and not self.robot_is_picking.get() and not self.restart_conveyor_timer.started:
                self.restart_conveyor_timer.start()
            if self.restart_conveyor_timer.done():
                self.restart_conveyor_timer.stop()
                self.move_conveyor()
                self.conveyor_state = ConveyorState.RUNNING

    def stop(self):
        self.conveyor_state = ConveyorState.INIT
        self.stop_conveyor()
        self.restart_conveyor_timer.stop()
        if self.pusher_present:
            self.pusher.idle_async()


class InfeedFSMConveyor(Conveyor):
    def __init__(self, system_state: SystemState, index, robot_is_picking: InterThreadBool = InterThreadBool(),
                 **kwargs):
        super().__init__(system_state, **kwargs)
        self.index = index
        self.robot_is_picking = robot_is_picking
        self.initialize_box_sensor(kwargs)
        self.initialize_pusher(kwargs)
        self.states = ['stopped', 'running', 'pushing', 'retracting', 'waiting_for_pick']
        self.machine = MachineTransitions(model=self, states=self.states, initial='running')
        self.machine.add_transition(trigger='start', source='stopped', dest='running', before='before_start',
                                    after='after_start')
        self.machine.add_transition(trigger='stop', source='running', dest='stopped', before='before_stop',
                                    after='after_stop')
        self.machine.add_transition(trigger='push', source='stopped', dest='pushing', before='before_push',
                                    after='after_push')
        self.machine.add_transition(trigger='retract', source='pushing', dest='retracting', before='before_retract',
                                    after='after_retract')
        self.machine.add_transition(trigger='wait_for_robot_pick', source='retracting', dest='waiting_for_pick',
                                    before='before_wait_for_robot_pick', after='after_wait_for_robot_pick')
        self.machine.add_transition(trigger='resume_after_pick', source='waiting_for_pick', dest='running',
                                    before='before_resume_after_pick', after='after_resume_after_pick')

        self.system_state.machine.on_mqtt_event(self.sensor_topic, self.mqtt_event_handler)
        self.system_state.machine.on_mqtt_event(mqtt_topics['robotPick'], self.mqtt_event_handler)

        self.machine.get_graph().draw('./conveyor_types/state_images/infeed_conveyor_state_diagram.png', prog='dot')

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