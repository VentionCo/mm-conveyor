import os
import json


def write_to_json(payload: str):
    print(f"Payload: {payload}")
    """Write the payload to the JSON file."""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON payload: {e}")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    conveyor_configuration_path = os.path.join(script_dir, 'configured_conveyors.json')

    try:
        with open(conveyor_configuration_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)
        print(f"Successfully wrote configuration to {conveyor_configuration_path}")
    except IOError as e:
        print(f"Failed to write to file: {e}")