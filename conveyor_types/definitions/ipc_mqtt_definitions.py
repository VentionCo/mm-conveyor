
mqtt_topics = {
    'conveyor/state': 'conveyors/{id_conv}/state',
    'estop/status': 'estop/status',
    'smartDrivesReady': 'smartDrives/areReady',
    'conveyorControlStart': 'conveyors/control/start',
    'conveyorControlStop': 'conveyors/control/stop',
    'sensor': 'io-expander/devices/{device}/inputs/{port}',
    'robotPick': 'robot/picking',
}

mqtt_messages = {
    'sensorTrigger': '1',
    'sensorUnTrigger': '0',
    'estopTrigger': 'true',
    'estopUnTrigger': 'false',
    'smartDrivesReady': 'true',
    'smartDrivesNotReady': 'false',
    'robotPicking': 'true',
    'parentRunning': 'running',
    'parentStopped': 'stopped',
}


def format_message(template, **kwargs):
    """
    Formats a message template with provided keyword arguments.

    :param template: The message template string to format.
    :param kwargs: Keyword arguments to substitute into the template.
    :return: Formatted message string.
    """
    return template.format(**kwargs)
