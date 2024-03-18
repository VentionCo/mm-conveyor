'''
Definitions for the conveyors
'''
from enum import Enum
from abc import ABC, abstractmethod
from machinelogic import Machine, MachineException
from conveyor_definitions import *
from helpers import InterThreadBool
from timer_helper import Timer

machine = Machine('http://192.168.7.2:3100', 'ws://192.168.7.2:9001')

class SystemState:
    ''' 
    SystemState class is used to keep track of the state of the system.
    It is used to keep track of the state of the drives and the state of the estop.
    Attributes:
        _observers: A list of observers that are subscribed to the estop and smartDrives/areReady topics on the mqtt broker.
        drives_are_ready: A boolean that is used to keep track of the state of the drives. It is set to True when the drives are ready and False when the drives are not ready.
        estop: A boolean that is used to keep track of the state of the estop. It is set to True when the estop is active and False when the estop is not active.
    Methods:
        subscribe_to_estop: Subscribes to the estop/status topic on the mqtt broker. When a message is received on this topic, the estop_callback function is called.
        estop_callback: This function is called when a message is received on the estop/status topic. It sets the estop variable to the value of the payload.
        subscribe_to_drive_readiness: Subscribes to the smartDrives/areReady topic on the mqtt broker. When a message is received on this topic, the smart_drive_callback function is called.
        smart_drive_callback: This function is called when a message is received on the smartDrives/areReady topic. It sets the drives_are_ready variable to the value of the payload.
    '''
    def __init__(self):
        ''' Constructor for the SystemState class. It initializes the _observers list and sets the drives_are_ready and estop variables to False. It also subscribes to the estop and smartDrives/areReady topics on the mqtt broker.'''
        self._observers = []
        self.drives_are_ready = False
        self.estop = False
        self.subscribe_to_estop()
        self.subscribe_to_drive_readiness()

    def subscribe_to_estop(self):
        ''' Subscribes to the estop/status topic on the mqtt broker. When a message is received on this topic, the estop_callback function is called.'''
        machine.on_mqtt_event('estop/status', self.estop_callback)

    def estop_callback(self, topic: str, payload: str):
        ''' This function is called when a message is received on the estop/status topic. It sets the estop variable to the value of the payload.'''
        if payload.lower() == "true":
            self.estop = True
        elif payload.lower() == "false":
            self.estop = False
        else:
            print(f"Unexpected payload received in estopCallback: {payload}")

    def subscribe_to_drive_readiness(self):
        ''' Subscribes to the smartDrives/areReady topic on the mqtt broker. When a message is received on this topic, the smart_drive_callback function is called.'''
        machine.on_mqtt_event('smartDrives/areReady', self.smart_drive_callback)

    def smart_drive_callback(self, topic: str, payload: str):
        ''' This function is called when a message is received on the smartDrives/areReady topic. It sets the drives_are_ready variable to the value of the payload.'''
        if payload.lower() == "true":
            self.drives_are_ready = True
        elif payload.lower() == "false":
            self.drives_are_ready = False
        else:
            print(f"Unexpected payload received in smartDriveCallback: {payload}")

class ConveyorState(Enum):
    '''
    Conveyor State is an enum that is used to keep track of the state of the conveyor. 
    It is used to keep track of the state of the conveyor and 
    to determine what the conveyor should do next.
    '''
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
    ''' Base class for all conveyors. 
    It is an abstract class that is used to define the methods that all conveyors should have. 
    It also has some helper methods that are used by all conveyors.
    Attributes:
        system_state: A SystemState object that is used to keep track of the state of the system.
        conveyor_state: A ConveyorState object used to keep track of the state of the conveyor.
        actuator_name: A string used to keep track of the name of the actuator used by conveyor.
        actuator: A machine object that is used to control the actuator.
        actuator_is_vfd: A boolean used to keep track of whether the actuator is a vfd or not.
        actuator_speed: A float that is used to keep track of the speed of the actuator.
        actuator_acceleration: A float used to keep track of the acceleration of the actuator.
        actuator_deceleration: A float used to keep track of the deceleration of the actuator.
        box_sensor: A machine object that is used to keep track of the box sensor.
        reverse_box_logic: A boolean used to keep track of whether the box sensor logic is reverse.
        accumulation_sensor: A machine object that is used to keep track of the accumulation sensor.
        reverse_accumulation_logic: A boolean to track of whether the accumulation sensor logic.
        pusher_present: A boolean used to keep track of whether the pusher is present or not.
        pusher: A machine object that is used to control the pusher.
        pusher_extend_logic: A string to keep track of the logic for extending the pusher.
        pusher_retract_logic: A string used to keep track of the logic for retracting the pusher.
        pusher_extend_delay: A float used to keep track of the delay for extending the pusher.
        pusher_retract_delay: A float used to keep track of the delay for retracting the pusher.
        pusher_sensor_present: A boolean used to track of whether the pusher sensor is present.
        stopper_present: A boolean used to keep track of whether the stopper is present or not.
        stopper: A machine object that is used to control the stopper.
        stopper_extend_logic: A string used to keep track of the logic for extending the stopper.
        stopper_retract_logic: A string that is used to keep
        track of the logic for retracting the stopper.
        stopper_extend_delay: A float used to keep track of the delay for extending the stopper.
        stopper_retract_delay: A float used to keep track of the delay for retracting the stopper.
        stopper_sensor_present: A boolean used to track of whether the stopper sensor is present.
    Methods:
        run: An abstract method to define the behavior of the conveyor when it is running.
        stop: An abstract method used to define the behavior of the conveyor when it is stopped.
        initialize_actuator: A method that is used to initialize the actuator.
        set_actuator_params: A method that is used to set the parameters of the actuator.
        initialize_box_sensor: A method that is used to initialize the box sensor.
        get_box_sensor_state: A method that is used to get the state of the box sensor.
        initialize_accumulation_sensor: A method that is used to initialize the accumulation sensor.
        get_accumulation_sensor_state: A method to get the state of the accumulation sensor.
        initialize_pusher: A method that is used to initialize the pusher.
        pusher_state: A method that is used to get the state of the pusher.
        initialize_stopper: A method that is used to initialize the stopper.
        stopper_state: A method that is used to get the state of the stopper.
        move_conveyor: A method that is used to move the conveyor.
        stop_conveyor: A method that is used to stop the conveyor.
        set_conveyor_state_to_init: A method that is used to set the conveyor state to INIT.
        get_status: A method that is used to get the status of the conveyor.

    '''
    def __init__(self, system_state: SystemState, **kwargs):
        ''' Constructor for the Conveyor class. It initializes the system_state 
        and sets the conveyor_state to INIT.
        It also calls the initialize_actuator method.'''
        self.system_state = system_state
        self.conveyor_state = ConveyorState.INIT
        self.actuator_speed = 0
        self.actuator_acceleration = 0
        self.actuator_deceleration = 0
        self.reverse_box_logic = False
        self.box_sensor = None
        self.reverse_accumulation_logic = False
        self.accumulation_sensor = None
        self.pusher_present = False
        self.pusher = None
        self.pusher_extend_logic = None
        self.pusher_retract_logic = None
        self.pusher_extend_delay = 0
        self.pusher_retract_delay = 0
        self.pusher_sensor_present = False
        self.stopper_present = False
        self.stopper = None
        self.stopper_extend_logic = None
        self.stopper_retract_logic = None
        self.stopper_extend_delay = 0
        self.stopper_retract_delay = 0
        self.stopper_sensor_present = False
        self.restart_conveyor_timer = None
        self.stopper_sensor = None
        self.actuator_is_vfd = False
        self.stopper_config = {}
        self.initialize_actuator(kwargs)

    @abstractmethod
    def run(self):
        ''' 
        An abstract method that is used to define 
        the behavior of the conveyor when it is running.
        '''

    @abstractmethod
    def stop(self):
        '''
        An abstract method that is used to define 
        the behavior of the conveyor when it is stopped.
        '''

    def initialize_actuator(self, kwargs):
        ''' 
        A method that is used to initialize the actuator.
        It takes a dictionary as an argument and uses the
        CONVEYOR_NAME key to get the name of the actuator.
        It then tries to get the actuator from the machine
        using the name. If the actuator is not found, it
        raises an exception. If the actuator is found, it
        sets the actuator_name to the name of the actuator
        and sets the actuator to the actuator object. It also
        sets the actuator_is_vfd to True if the actuator is
        an ac motor and False if the actuator is not an ac motor.
        '''
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
            except MachineException as e:
                raise Exception(f"Actuator {self.actuator_name} not found") from e

    def set_actuator_params(self, kwargs):
        '''
        A method that is used to set the parameters of the actuator.
        It takes a dictionary as an argument and uses the AXIS_PARAMETERS
        key to get the parameters of the actuator. It then sets the
        actuator_speed, actuator_acceleration, and actuator_deceleration
        to the values of the speed, acceleration, and deceleration parameters
        respectively.
        '''
        axis_params = kwargs.get(AXIS_PARAMETERS, {})
        self.actuator_speed = axis_params.get(SPEED)
        self.actuator_acceleration = axis_params.get(ACCELERATION)
        self.actuator_deceleration = axis_params.get(DECCELERATION)

    def initialize_box_sensor(self, kwargs):
        '''
        A method that is used to initialize the box sensor.
        It takes a dictionary as an argument and uses the
        BOX_DETECTION_SENSOR_NAME key to get the name of the
        box sensor. It then tries to get the box sensor from
        the machine using the name. If the box sensor is not
        found, it sets the box_sensor to None. If the box sensor
        is found, it sets the box_sensor to the box sensor object.
        It also sets the reverse_box_logic to True if the reverse
        box logic is set to True in the dictionary and False if it
        is not set to True in the dictionary.
        '''
        sensor = kwargs.get(BOX_DETECTION_SENSOR_NAME)
        self.reverse_box_logic = kwargs.get(REVERSE_BOX_LOGIC).lower() == 'true'
        if sensor:
            self.box_sensor = machine.get_input(sensor)
        else:
            self.box_sensor = None

    def get_box_sensor_state(self):
        '''
        A method that is used to get the state of the box sensor.
        It returns the state of the box sensor if the reverse_box_logic
        is set to False. If the reverse_box_logic is set to True, it returns
        the opposite of the state of the box sensor.
        '''
        state = self.box_sensor.state.value
        if self.reverse_box_logic:
            return not state
        else:
            return state

    def initialize_accumulation_sensor(self, kwargs):
        '''
        A method that is used to initialize the accumulation sensor.
        It takes a dictionary as an argument and uses the ACCUMULATION_SENSOR_NAME
        key to get the name of the accumulation sensor. It then tries to get the
        accumulation sensor from the machine using the name. If the accumulation
        sensor is not found, it sets the accumulation_sensor to None. If the
        accumulation sensor is found, it sets the accumulation_sensor to the
        accumulation sensor object. It also sets the reverse_accumulation_logic
        to True if the reverse accumulation logic is set to True in the dictionary
        and False if it is not set to True in the dictionary.
        '''
        sensor = kwargs.get(ACCUMULATION_SENSOR_NAME)
        self.reverse_accumulation_logic = kwargs.get(REVERSE_ACCUMULATION_LOGIC).lower() == 'true'
        if sensor:
            self.accumulation_sensor = machine.get_input(sensor)
        else:
            self.accumulation_sensor = None

    def get_accumulation_sensor_state(self):
        '''
        A method that is used to get the state of the accumulation sensor.
        It returns the state of the accumulation sensor if the reverse_accumulation_logic
        is set to False. If the reverse_accumulation_logic is set to True, it returns
        the opposite of the state of the accumulation sensor.
        '''
        state = self.accumulation_sensor.state.value
        if self.reverse_accumulation_logic:
            return not state
        else:
            return state

    def initialize_pusher(self, kwargs):
        '''
        A method that is used to initialize the pusher.
        It takes a dictionary as an argument and uses the PUSHER_CONFIG
        key to get the parameters of the pusher. It then sets the pusher_present
        to True if the pusher is present and False if the pusher is not present.
        If the pusher is present, it sets the pusher to the pusher object and
        sets the pusher_extend_logic and pusher_retract_logic to the extend and
        retract logic of the pusher respectively. It also sets the pusher_extend_delay
        and pusher_retract_delay to the extend and retract delay of the pusher respectively.
        It also sets the pusher_sensor_present to True if the pusher sensor is present
        and False if the pusher sensor is not present.
        '''
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
        '''
        A method that is used to get the state of the pusher.
        It returns True if the state of the pusher is equal to the desired state
        and False if the state of the pusher is not equal to the desired state.
        '''
        if self.pusher_sensor_present:
            if self.pusher.state == desired_state:
                return True
            else:
                return False
        else:
            return False

    def initialize_stopper(self, kwargs):
        '''
        A method that is used to initialize the stopper.
        It takes a dictionary as an argument and uses the STOPPER_CONFIG
        key to get the parameters of the stopper. It then sets the stopper_present
        to True if the stopper is present and False if the stopper is not present.
        If the stopper is present, it sets the stopper to the stopper object and
        sets the stopper_extend_logic and stopper_retract_logic to the extend and
        retract logic of the stopper respectively. It also sets the stopper_extend_delay
        and stopper_retract_delay to the extend and retract delay of the stopper respectively.
        It also sets the stopper_sensor_present to True if the stopper sensor is present
        and False if the stopper sensor is not present.
        '''
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
                self.stopper_sensor = machine.get_input(
                    self.stopper_config.get(STOPPER_SENSOR_NAME)
                    )

    def stopper_state(self, desired_state):
        '''
        A method that is used to get the state of the stopper.
        It returns True if the state of the stopper is equal to the desired state
        and False if the state of the stopper is not equal to the desired state.
        '''
        if self.stopper_present:
            if self.stopper_sensor.state.value == desired_state:
                return True
            else:
                return False
        else:
            return False

    def move_conveyor(self):
        '''
        A method that is used to move the conveyor.
        It moves the conveyor forward if the actuator is a vfd.
        If the actuator is not a vfd, it moves the conveyor continuously
        at the speed and acceleration set in the parameters.
        '''
        if self.actuator_is_vfd:
            self.actuator.move_forward()
        else:
            self.actuator.move_continuous_async(self.actuator_speed, self.actuator_acceleration)
  
    def stop_conveyor(self):
        '''
        A method that is used to stop the conveyor.
        It stops the conveyor if the actuator is a vfd.
        If the actuator is not a vfd, it stops the conveyor with the deceleration
        set in the parameters.
        '''
        if self.actuator_is_vfd:
            self.actuator.stop()
        else:
            self.actuator.stop(self.actuator_deceleration)

    def set_conveyor_state_to_init(self):
        '''
        A method that is used to set the conveyor state to INIT.
        '''
        self.conveyor_state = ConveyorState.INIT

    def get_status(self):
        '''
        A method that is used to get the status of the conveyor.
        It returns the state of the conveyor.
        '''
        return self.conveyor_state


class InfeedConveyor(Conveyor):
    '''
    InfeedConveyor class is used to control the infeed conveyor.
    It is used to control the behavior of the infeed conveyor.
    Attributes:
        system_state: A SystemState object that is used to keep track of the state of the system.
        robot_is_picking: An InterThreadBool object used to keep track the robot is picking or not.
        pusher_present: A boolean used to keep track of whether the pusher is present or not.
        pusher: A machine object that is used to control the pusher.
        pusher_extend_logic: A string to keep track of the logic for extending the pusher.
        pusher_retract_logic: A string used to keep track of the logic for retracting the pusher.
        pusher_extend_delay: A float used to keep track of the delay for extending the pusher.
        pusher_retract_delay: A float used to keep track of the delay for retracting the pusher.
        pusher_sensor_present: A boolean used to track of whether the pusher sensor is present.
        restart_conveyor_timer: A Timer object used to track of the time to restart the conveyor.
        not_moving: A boolean used to keep track of whether the conveyor is moving or not.
    Methods:
        run: A method used to define the behavior of the infeed conveyor when it is running.
        stop: A method used to define the behavior of the infeed conveyor when it is stopped.
    '''
    def __init__(self, 
                system_state: SystemState,
                parentConveyor: Conveyor, 
                robot_is_picking: InterThreadBool = InterThreadBool(),
                **kwargs):
        super().__init__(system_state, **kwargs)

        self.initialize_box_sensor(kwargs)
        self.initialize_pusher(kwargs)

        self.parent_conveyor = parentConveyor

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
            if not self.get_box_sensor_state() and \
            not self.robot_is_picking.get() and \
            not self.restart_conveyor_timer.started:
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
    """
    This class is used to control the infeed conveyor for the pick station.
    """
    def __init__(self, system_state: SystemState, robot_is_picking: InterThreadBool = InterThreadBool(), **kwargs):
        super().__init__(system_state, **kwargs)
        self.drives_are_ready = self.system_state.drives_are_ready
        self.robot_is_picking = robot_is_picking
        self.initialize_timers(**kwargs)
        self.initialize_box_sensor(kwargs)
        self.initialize_pusher(kwargs)

        self.restart_conveyor_timer = Timer(kwargs.get(RESTART_TIME))
        self.boxes_to_queue = 2 
        self.box_was_picked = False

    def initialize_timers(self, **kwargs):
        '''
        A method that is used to initialize the timers.
        It takes a dictionary as an argument and uses the
        STARTUP_TIME, SUSTAIN_TIME, and PACING_TIME keys to
        get the startup, sustain, and pacing times respectively.
        It then initializes the startup_timer, sustain_timer, and
        pacing_timer with the values of the startup, sustain, and
        pacing times respectively.
        '''
        self.startup_timer = Timer(kwargs.get(STARTUP_TIME))
        self.sustain_timer = Timer(kwargs.get(SUSTAIN_TIME))
        self.pacing_timer = Timer(kwargs.get(PACING_TIME))

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
                if self.box_sensor.state.value:
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
            if self.stopper_sensor_present and self.stopper_sensor.state.value:
                self.boxes_to_queue -= 1
            if self.boxes_to_queue == 0:
                self.stopper.idle_async()
                self.move_conveyor()
                self.conveyor_state = ConveyorState.RUNNING

        elif self.conveyor_state == ConveyorState.RUNNING:
            self.stopper.push_async()
            if self.box_sensor.state.value and self.get_accumulation_sensor_state() and not self.sustain_timer.started:
                self.sustain_timer.start()
            if self.sustain_timer.done():
                self.sustain_timer.stop()
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
            if not self.box_sensor.state.value or not self.get_accumulation_sensor_state():
                self.box_was_picked = True
            if self.box_was_picked and not self.robot_is_picking.get() and not self.restart_conveyor_timer.started:
                self.restart_conveyor_timer.start()
            if self.restart_conveyor_timer.done():
                self.restart_conveyor_timer.stop()
                self.boxes_to_queue = 2
                if self.box_sensor.state.value:
                    self.boxes_to_queue -= 1
                if self.get_accumulation_sensor_state():
                    self.boxes_to_queue -= 1
                self.move_conveyor()
                if self.pacing_timer.started:
                    self.pacing_timer.start()
                self.conveyor_state = ConveyorState.PACING

        elif self.conveyor_state == ConveyorState.PACING:
            if self.pacing_timer.done():
                self.pacing_timer.stop()
                if self.boxes_to_queue > 0:
                    self.stopper.idle_async()
                print("[Pacing] Boxes to queue: " + str(self.boxes_to_queue))
                self.conveyor_state = ConveyorState.QUEUEING

    def stop(self):
        self.conveyor_state = ConveyorState.INIT
        self.stop_conveyor()
        self.restart_conveyor_timer.stop()
        self.startup_timer.stop()
        self.sustain_timer.stop()
        self.pacing_timer.stop()

        if self.pusher_present:
            self.pusher.idle_async()
        if self.stopper_present:
            self.stopper.push_async()


class ControlAllConveyor:
    '''
    ControlAllConveyor class is used to control all the conveyors.
    It is used to control the behavior of all the conveyors in the system.
    Attributes:
        list_of_conveyors: A list of all the conveyors in the system.
    Methods:
        run_all: A method that is used to run all the conveyors.
        stop_all: A method that is used to stop all the conveyors.
        set_init_state: A method that is used to set the state of all the conveyors to INIT.
    '''
    def __init__(self, list_of_conveyors: list):
        self.list_of_conveyors = list_of_conveyors

    def run_all(self):
        '''
        A method that is used to run all the conveyors.
        '''
        for conveyor in self.list_of_conveyors:
            conveyor.run()

    def stop_all(self):
        '''
        A method that is used to stop all the conveyors.
        '''
        for conveyor in self.list_of_conveyors:
            conveyor.stop()

    def set_init_state(self):
        '''
        A method that is used to set the state of all the conveyors to INIT.
        '''
        for conveyor in self.list_of_conveyors:
            conveyor.set_conveyor_state_to_init()
