
class SystemState:
    """
    SystemState class is used to keep track of the state of the system.
    It is used to keep track of the state of the drives and the state of the estop.
    Attributes:
        _observers: A list of observers that are subscribed to the estop and smartDrives/areReady
                    topics on the mqtt broker.
        drives_are_ready: A boolean that is used to keep track of the state of the drives.
                        It is set to True when the drives are ready and False when the drives are not ready.
        estop: A boolean that is used to keep track of the state of the estop.
            It is set to True when the estop is active and False when the estop is not active.
    Methods:
        subscribe_to_estop: Subscribes to the estop/status topic on the mqtt broker.
            When a message is received on this topic, the estop_callback function is called.
        estop_callback: This function is called when a message is received on the estop/status topic.
            It sets the estop variable to the value of the payload.
        subscribe_to_drive_readiness: Subscribes to the smartDrives/areReady topic on the mqtt broker.
            When a message is received on this topic, the smart_drive_callback function is called.
        smart_drive_callback: This function is called when a message is received on the smartDrives/areReady topic.
            It sets the drives_are_ready variable to the value of the payload.
    """

    def __init__(self, Machine):
        """
        Constructor for the SystemState class. It initializes the _observers list and sets the drives_are_ready
        and estop variables to False. It also subscribes to the estop and smartDrives/areReady topics on the mqtt
        broker.
        """
        self.machine = Machine
        self._observers = []
        self.drives_are_ready = False
        self.estop = False
        self.subscribe_to_estop()
        self.subscribe_to_drive_readiness()
        self.program_run = False

    def publish_conv_state(self, id_conv, state):
        print(f'conveyors/{id_conv}/state', state)
        self.machine.publish_mqtt_event(f'conveyors/{id_conv}/state', state)

    def subscribe_to_estop(self):
        """ Subscribes to the estop/status topic on the mqtt broker. When a message is received on this topic,
        the estop_callback function is called."""
        self.machine.on_mqtt_event('estop/status', self.estop_callback)

    def estop_callback(self, topic: str, payload: str):
        """ This function is called when a message is received on the estop/status topic.
        It sets the estop variable to the value of the payload."""
        if payload.lower() == "true":
            self.estop = True
        elif payload.lower() == "false":
            self.estop = False
        else:
            print(f"Unexpected payload received in estopCallback: {payload}")

    def subscribe_to_drive_readiness(self):
        """ Subscribes to the smartDrives/areReady topic on the mqtt broker.
        When a message is received on this topic, the smart_drive_callback function is called."""
        self.machine.on_mqtt_event('smartDrives/areReady', self.smart_drive_callback)

    def smart_drive_callback(self, topic: str, payload: str):
        """ This function is called when a message is received on the smartDrives/areReady topic.
         It sets the drives_are_ready variable to the value of the payload."""
        if payload.lower() == "true":
            self.drives_are_ready = True
        elif payload.lower() == "false":
            self.drives_are_ready = False
        else:
            print(f"Unexpected payload received in smartDriveCallback: {payload}")

    def start_conveyors(self):
        self.program_run = True

    def stop_conveyors(self):
        self.program_run = False

    def subscribe_to_control_topics(self):
        self.machine.on_mqtt_event('conveyors/control/start', self.on_start_command)
        self.machine.on_mqtt_event('conveyors/control/stop', self.on_stop_command)

    def on_start_command(self, topic, payload):
        self.start_conveyors()

    def on_stop_command(self, topic, payload):
        self.stop_conveyors()