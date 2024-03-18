from enum import Enum
from machinelogic import Machine, ActuatorException, MachineException
from abc import ABC, abstractmethod
from conveyor_definitions import *
from helpers import InterThreadBool
from timer_helper import Timer

machine = Machine('http://192.168.7.2:3100', 'ws://192.168.7.2:9001')

class SystemState:
    def __init__(self):
        self._observers = []
        self.drives_are_ready = False
        self.estop = False
        self.subscribe_to_estop()
        self.subscribe_to_drive_readiness()

    def subscribe_to_estop(self):
        machine.on_mqtt_event('estop/status', self.estop_callback)

    def estop_callback(self, topic: str, payload: str):
        if payload.lower() == "true":
            self.estop = True
        elif payload.lower() == "false":
            self.estop = False
        else:
            print(f"Unexpected payload received in estopCallback: {payload}")

    def subscribe_to_drive_readiness(self):
        machine.on_mqtt_event('smartDrives/areReady', self.smart_drive_callback)

    def smart_drive_callback(self, topic: str, payload: str):
        if payload.lower() == "true":
            self.drives_are_ready = True
        elif payload.lower() == "false":
            self.drives_are_ready = False
        else:
            print(f"Unexpected payload received in smartDriveCallback: {payload}")

class ConveyorState(Enum):
    INIT = 0
    RUNNING = 1
    STOPPING = 2
    PUSHING = 3
    RETRACT = 4
    WAITING_FOR_PICK = 5
    STARTUP = 6
    PACING = 7
    QUEUEING = 8
    WAITING = 9

class Conveyor(ABC):
    def __init__(self, system_state: SystemState, **kwargs):
        self.system_state = system_state
     
        self.conveyor_state = ConveyorState.INIT
        self.initialize_actuator(kwargs)

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    def initialize_actuator(self, kwargs):
        self.actuator_name = kwargs.get(CONVEYOR_NAME)
        try: 
            self.actuator = machine.get_ac_motor(self.actuator_name)
            self.actuator_is_vfd = True
        except MachineException:
            print(f'Actuator {self.actuator_name} not found as ac motor')
            try:
                self.actuator = machine.get_actuator(self.actuator_name)
                self.set_actuator_params(kwargs)
                self.actuator_is_vfd = False
            except MachineException:
                raise Exception(f"Actuator {self.actuator_name} not found")

        
    def set_actuator_params(self, kwargs):
        axis_params = kwargs.get(AXIS_PARAMETERS, {})
        self.actuator_speed = axis_params.get(SPEED)
        self.actuator_acceleration = axis_params.get(ACCELERATION)
        self.actuator_deceleration = axis_params.get(DECCELERATION)
    
    def initialize_box_sensor(self, kwargs):
        sensor = kwargs.get(BOX_DETECTION_SENSOR_NAME)
        self.reverse_box_logic = kwargs.get(REVERSE_BOX_LOGIC).lower() == 'true'
        if sensor:
            self.box_sensor = machine.get_input(sensor)
        else:
            self.box_sensor = None

    def get_box_sensor_state(self):
        state = self.box_sensor.state.value
        if self.reverse_box_logic:
                return not state
        else:
            return state
    
    def initialize_accumulation_sensor(self, kwargs):
        sensor = kwargs.get(ACCUMULATION_SENSOR_NAME)
        self.reverse_accumulation_logic = kwargs.get(REVERSE_ACCUMULATION_LOGIC).lower() == 'true'
        if sensor:
            self.accumulation_sensor = machine.get_input(sensor)
        else:
            self.accumulation_sensor = None

    def get_accumulation_sensor_state(self):
        state = self.accumulation_sensor.state.value
        if self.reverse_accumulation_logic:
            return not state
        else:
            return state
        
    def initialize_pusher(self, kwargs):
        pusher_params = kwargs.get(PUSHER_CONFIG, {})
        self.pusher_present = pusher_params.get(PUSHER_PRESENT)
        if self.pusher_present == "True":
            self.pusher_present = True
            self.pusher = machine.get_pneumatic(pusher_params.get(PUSHER_NAME))
            self.pusher_extend_logic = pusher_params.get(PUSHER_EXTEND_LOGIC)
            self.pusher_retract_logic = pusher_params.get(PUSHER_RETRACT_LOGIC)
            self.pusher_extend_delay = pusher_params.get(EXTEND_DELAY_SEC)
            self.pusher_retract_delay = pusher_params.get(RETRACT_DELAY_SEC)
            self.pusher_sensor_present = pusher_params.get(SENSORS_PRESENT).lower() == "true"

    def pusher_state(self, desired_state):
        if self.pusher_sensor_present:
            if self.pusher.state == desired_state:
                return True
            else:
                return False
        else:
            return False

    def initialize_stopper(self, kwargs):
        self.stopper_config = kwargs.get(STOPPER_CONFIG, {})
        self.stopper_present = self.stopper_config.get(STOPPER_PRESENT)
        if self.stopper_present == "True":
            self.stopper_present = True
            self.stopper = machine.get_pneumatic(self.stopper_config.get(STOPPER_NAME))
            self.stopper_extend_logic = self.stopper_config.get(STOPPER_EXTEND_LOGIC)
            self.stopper_retract_logic = self.stopper_config.get(STOPPER_RETRACT_LOGIC)
            self.stopper_extend_delay = self.stopper_config.get(EXTEND_DELAY_SEC)
            self.stopper_retract_delay = self.stopper_config.get(RETRACT_DELAY_SEC)
            self.stopper_sensor_present = self.stopper_config.get(SENSORS_PRESENT)
            if self.stopper_sensor_present == "True":
                self.stopper_sensor = machine.get_input(self.stopper_config.get(STOPPER_SENSOR_NAME))
                self.stopper_sensor_state = self.stopper_sensor.state.value

    def stopper_state(self, desired_state):
        if self.stopper_present:
            if self.stopper_sensor_state == desired_state:
                return True
            else:
                return False
        else:
            return False
        
    def move_conveyor(self):
        if self.actuator_is_vfd:
            self.actuator.move_forward()
        else:
            self.actuator.move_continuous_async(self.actuator_speed, self.actuator_acceleration)
    
    def stop_conveyor(self):
        if self.actuator_is_vfd:
            self.actuator.stop()
        else:
            self.actuator.stop(self.actuator_deceleration)

    def set_conveyor_state_to_init(self):
        self.conveyor_state = ConveyorState.INIT

    def get_status(self):
        return self.conveyor_state
    
class InfeedConveyor(Conveyor):
    def __init__(self, system_state: SystemState, parentConveyor: Conveyor, robot_is_picking: InterThreadBool = InterThreadBool(),  **kwargs):
        super().__init__(system_state, **kwargs)

        self.initialize_box_sensor(kwargs)
        self.initialize_pusher(kwargs)
        
        self.parentConveyor = parentConveyor

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



class PickInfeedConveyor(Conveyor):

    def __init__(self, system_state: SystemState, **kwargs):
        super().__init__(system_state, **kwargs)
        self.initialize_timers(**kwargs)
        self.initialize_box_sensor(kwargs)
        self.initialize_pusher(kwargs)

        self.restart_conveyor_timer = Timer(kwargs.get(RESTART_TIME))
        self.boxes_to_queue = 2 
        self.box_was_picked = False

    def initialize_timers(self, **kwargs):
        self.startup_timer = Timer(kwargs.get(STARTUP_TIME))
        self.sustainTimer = Timer(kwargs.get(SUSTAIN_TIME))
        self.pacingTimer = Timer(kwargs.get(PACING_TIME))

    def run(self):
        if not self.system_state.drives_are_ready and not self.system_state.estop:
            self.conveyor_state = ConveyorState.INIT
            if self.pusher_present:
                self.pusher.pull_async()
            if self.stopper_present:
                self.stopper.pull_async()

        if self.conveyor_state == ConveyorState.INIT:
            if self.pusher_state("pulled"):
                self.pusher.pull_async()
            if self.stopper_state("pushed"):
                self.stopper.push_async()
            
            if self.drives_are_ready and self.pusher_state("pulled"):
                if not self.startup_timer.started:
                    self.startup_timer.start()
                self.boxes_to_queue = 2
                self.conveyor_state = ConveyorState.STARTUP

        elif self.conveyor_state == ConveyorState.STARTUP:
            if self.startup_timer.done() or (self.get_box_sensor_state() and self.get_accumulation_sensor_state()):
                self.startup_timer.stop()
                if self.box_sensor_state:
                    self.boxes_to_queue -= 1
                if self.get_accumulation_sensor_state():
                    self.boxes_to_queue -= 1
                if self.boxes_to_queue < 0:
                    print("ERROR: More boxes detected than expected")
                    raise Exception("ERROR: More boxes detected than expected")
                if self.boxes_to_queue > 0:
                    self.stopper.idle_async()
                    print("[Startup] Boxes to queue: " + str(self.boxes_to_queue))
                    self.conveyor_state = ConveyorState.QUEUEING

        elif self.conveyor_state == ConveyorState.QUEUEING:
            self.stopper.pull_async()
            if self.stopper_sensor_present and self.stopper_sensor_state:
                self.boxes_to_queue -= 1
            if self.boxes_to_queue == 0:
                self.stopper.idle_async()
                self.move_conveyor()
                self.conveyor_state = ConveyorState.RUNNING

        elif self.conveyor_state == ConveyorState.RUNNING:
            self.stopper.push_async()
            if self.box_sensor_state and self.get_accumulation_sensor_state() and not self.sustainTimer.started:
                self.sustainTimer.start()
            if self.sustainTimer.done():
                self.sustainTimer.stop()
                self.stop_conveyor()
                self.conveyor_state = ConveyorState.PUSHING
        
        elif self.conveyor_state == ConveyorState.PUSHING:
            if not self.pusher_present:
                self.conveyor_state = ConveyorState.WAITING_FOR_PICK
            else:
                self.pusher.push_async()
                if self.pusher_state("pushed"):
                    self.pusher.idle_async()
                    self.conveyor_state = ConveyorState.RETRACT
        
        elif self.conveyor_state == ConveyorState.RETRACT:
            self.pusher.pull_async()
            if self.pusher_state("pulled"):
                self.pusher.idle_async()
                self.box_was_picked = False
                self.conveyor_state = ConveyorState.WAITING_FOR_PICK
                
        elif self.conveyor_state == ConveyorState.WAITING_FOR_PICK:
            if not self.box_sensor_state or not self.get_accumulation_sensor_state():
                self.box_was_picked = True
            if self.box_was_picked and not self.robot_is_picking.get() and not self.restart_conveyor_timer.started:
                self.restart_conveyor_timer.start()
            if self.restart_conveyor_timer.done():
                self.restart_conveyor_timer.stop()
                self.boxes_to_queue = 2
                if self.box_sensor_state:
                    self.boxes_to_queue -= 1
                if self.get_accumulation_sensor_state():
                    self.boxes_to_queue -= 1
                self.move_conveyor()
                if self.pacingTimer.started:
                    self.pacingTimer.start()
                self.conveyor_state = ConveyorState.PACING

        elif self.conveyor_state == ConveyorState.PACING:
            if self.pacingTimer.done():
                self.pacingTimer.stop()
                if self.boxes_to_queue > 0:
                    self.stopper.idle_async()
                print("[Pacing] Boxes to queue: " + str(self.boxes_to_queue))
                self.conveyor_state = ConveyorState.QUEUEING

    def stop(self):
        self.conveyor_state = ConveyorState.INIT
        self.stop_conveyor()
        self.restart_conveyor_timer.stop()
        self.startup_timer.stop()
        self.sustainTimer.stop()
        self.pacingTimer.stop()

        if self.pusher_present:
            self.pusher.idle_async()
        if self.stopper_present:
            self.stopper.push_async()

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

class TransferConveyor(Conveyor):
    def __init__(self, system_state: SystemState, parentConveyor: InfeedConveyor, **kwargs):
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
            if self.pusher_present and (self.conveyor_state == ConveyorState.STOPPING and self.parentConveyor.conveyor_state == ConveyorState.RUNNING):
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

class ControlAllConveyor:

    def __init__(self, list_of_conveyors: list):
        self.list_of_conveyors = list_of_conveyors

    def run_all(self):
        for conveyor in self.list_of_conveyors:
            conveyor.run()

    def stop_all(self):
        for conveyor in self.list_of_conveyors:
            conveyor.stop()

    def set_init_state(self):
        for conveyor in self.list_of_conveyors:
            conveyor.set_conveyor_state_to_init()