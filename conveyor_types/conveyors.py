"""
Definitions for the different types of conveyors
"""


class ControlAllConveyor:
    """
    ControlAllConveyor class is used to control all the conveyors.
    It is used to control the behavior of all the conveyors in the system.
    Attributes:
        list_of_conveyors: A list of all the conveyors in the system.
    Methods:
        run_all: A method that is used to run all the conveyors.
        stop_all: A method that is used to stop all the conveyors.
        set_init_state: A method that is used to set the state of all the conveyors to INIT.
    """

    def __init__(self, list_of_conveyors: list):
        self.list_of_conveyors = list_of_conveyors

    def run_all(self):
        """
        A method that is used to run all the conveyors.
        """
        for conveyor in self.list_of_conveyors:
            conveyor.run()

    def stop_all(self):
        """
        A method that is used to stop all the conveyors.
        """
        for conveyor in self.list_of_conveyors:
            conveyor.stop()

    def set_init_state(self):
        """
        A method that is used to set the state of all the conveyors to INIT.
        """
        for conveyor in self.list_of_conveyors:
            conveyor.set_conveyor_state_to_init()
