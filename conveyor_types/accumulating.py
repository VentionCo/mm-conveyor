
from conveyor_types.base import Conveyor, ConveyorState
from conveyor_types.system import SystemState
from helpers.thread_helpers import InterThreadBool
from helpers.timer_helper import Timer
from conveyor_types.definitions.conveyor_definitions import *
from transitions import Machine as MachineTransitions
from transitions.extensions import GraphMachine as MachineTransitions
from conveyor_types.definitions.ipc_mqtt_definitions import mqtt_messages, mqtt_topics, format_message


class AccumulatingConveyor(Conveyor):
    def __init__(self, system_state: SystemState, robot_is_picking: InterThreadBool = InterThreadBool(), **kwargs):
        super().__init__(system_state, **kwargs)

        self.initialize_pusher(kwargs)

        self.initialize_box_sensor(kwargs)
        self.initialize_accumulation_sensor(kwargs)

        self.box_was_picked = False
        self.is_first_box_ready_for_pick = False
        self.restart_conveyor_timer = Timer(kwargs.get(RESTART_TIME))
        self.accumulationConveyorTimer = Timer(kwargs.get(ACCUMULATION_TIME))

        self.robot_is_picking = robot_is_picking

    def run(self):
        if not self.system_state.drives_are_ready and self.system_state.estop:
            self.conveyor_state = ConveyorState.INIT
            if self.pusher_present:
                self.pusher.pull_async()

        if self.conveyor_state == ConveyorState.INIT:
            self.is_first_box_ready_for_pick = False
            if self.pusher_state("pushed"):
                self.pusher.pull_async()
            if self.pusher_state("pulled"):
                self.move_conveyor()
                self.conveyor_state = ConveyorState.RUNNING

        if self.conveyor_state == ConveyorState.RUNNING:
            if self.get_box_sensor_state() and self.get_accumulation_sensor_state():
                if self.accumulationConveyorTimer.paused:
                    self.accumulationConveyorTimer.unpause()
                elif not self.accumulationConveyorTimer.started:
                    self.accumulationConveyorTimer.start()
            else:
                self.accumulationConveyorTimer.pause()

            if self.pusher_present and self.get_box_sensor_state() and not self.is_first_box_ready_for_pick:
                self.stop_conveyor()
                self.accumulationConveyorTimer.pause()
                self.conveyor_state = ConveyorState.PUSHING
            elif self.accumulationConveyorTimer.done():
                self.stop_conveyor()
                self.accumulationConveyorTimer.stop()
                self.conveyor_state = ConveyorState.STOPPING

        elif self.conveyor_state == ConveyorState.PUSHING:
            self.pusher.push_async()
            if self.pusher_state("pushed"):
                self.pusher.idle_async()
                self.conveyor_state = ConveyorState.RETRACT

        elif self.conveyor_state == ConveyorState.RETRACT:
            self.pusher.pull_async()
            self.is_first_box_ready_for_pick = True
            if self.pusher_state("pulled"):
                self.pusher.idle_async()
                self.move_conveyor()
                self.conveyor_state = ConveyorState.RUNNING

        elif self.conveyor_state == ConveyorState.STOPPING:
            if self.pusher_state("pushed"):
                self.pusher.pull_async()
            if self.pusher_state("pulled"):
                self.pusher.idle_async()
                self.box_was_picked = False
                self.conveyor_state = ConveyorState.WAITING_FOR_PICK

        elif self.conveyor_state == ConveyorState.WAITING_FOR_PICK:
            self.is_first_box_ready_for_pick = False
            if not self.get_box_sensor_state():
                self.box_was_picked = True
            if self.box_was_picked and not self.robot_is_picking.get() and not self.restart_conveyor_timer.started:
                self.restart_conveyor_timer.start()
            if self.restart_conveyor_timer.done():
                self.restart_conveyor_timer.stop()
                self.move_conveyor()
                self.conveyor_state = ConveyorState.RUNNING

        if self.robot_is_picking.get():
            if self.conveyor_state == ConveyorState.RUNNING and self.is_first_box_ready_for_pick:
                self.stop_conveyor()
                self.conveyor_state = ConveyorState.STOPPING

    def stop(self):
        self.conveyor_state = ConveyorState.INIT
        self.stop_conveyor()
        self.restart_conveyor_timer.stop()
        self.accumulationConveyorTimer.stop()
        if self.pusher_present:
            self.pusher.idle_async()


class AccumulatingFSMConveyor(Conveyor):
    def __init__(self, system_state: SystemState, index, robot_is_picking: InterThreadBool = InterThreadBool(), **kwargs):
        super().__init__(system_state, **kwargs)
        self.index = index
        self.robot_is_picking = robot_is_picking
        self.restart_conveyor_timer = Timer(kwargs.get(RESTART_TIME))
        self.accumulationConveyorTimer = Timer(kwargs.get(ACCUMULATION_TIME))
        self.initialize_box_sensor(kwargs)
        self.initialize_accumulation_sensor(kwargs)
        self.initialize_pusher(kwargs)
        self.system_state.machine.on_mqtt_event(self.sensor_topic, self.mqtt_event_handler)
        self.system_state.machine.on_mqtt_event(self.accumulation_topic, self.mqtt_event_handler)

        self.states = ['running', 'stopped', 'accumulating']
        self.machine = MachineTransitions(model=self, states=self.states, initial='stopped')
        self.machine.add_transition('detect_product', 'stopped', 'accumulating', after='start_accumulation')
        self.machine.add_transition('accumulation_complete', 'accumulating', 'stopped')
        self.machine.add_transition('manual_stop', '*', 'stopped', before='before_stop')

        self.machine.get_graph().draw('./conveyor_types/state_images/accumulation_conveyor_state_diagram.png', prog='dot')

    def mqtt_event_handler(self, topic, message):
        if topic == self.sensor_topic or topic == self.accumulation_topic:
            if message == 'sensorTrigger':
                self.accumulating()
            elif message == 'sensorUnTrigger':
                self.start()