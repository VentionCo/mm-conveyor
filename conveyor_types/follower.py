from conveyor_types.base import Conveyor, ConveyorState
from conveyor_types.system import SystemState
from transitions import Machine as MachineTransitions
from transitions.extensions import GraphMachine as MachineTransitions
import time
import threading


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


class FollowerFSMConveyor(Conveyor):
    def __init__(self, system_state: SystemState, parentConveyor: Conveyor, index, **kwargs):
        super().__init__(system_state, **kwargs)
        self.parentConveyor = parentConveyor
        self.states = ['running', 'stopped']
        self.machine = MachineTransitions(model=self, states=self.states, initial='stopped')
        self.machine.add_transition(trigger='start', source='stopped', dest='running', before='before_start',
                                    after='after_start')
        self.machine.add_transition(trigger='stop', source='running', dest='stopped', before='before_stop',
                                    after='after_stop')
        self.start_polling_parent_state()
        self.machine.get_graph().draw('./conveyor_types/state_images/follower_conveyor_state_diagram.png', prog='dot')

    def start_polling_parent_state(self):
        """
        Starts a thread that polls the state of the parent conveyor and updates the state of this conveyor accordingly.
        """

        def poll_parent_state():
            while True:  # You might want a way to gracefully terminate this thread.
                if self.parentConveyor.state == 'running':
                    if self.state != 'running':
                        self.start()
                else:
                    if self.state != 'stopped':
                        self.stop()
                time.sleep(1)  # Poll every second; adjust as necessary
        # Start the polling in a background thread
        threading.Thread(target=poll_parent_state, daemon=True).start()

    def start(self):
        """Start the conveyor. Method dynamically added by the transitions library."""
        pass

    def stop(self):
        """Stop the conveyor. Method dynamically added by the transitions library."""
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