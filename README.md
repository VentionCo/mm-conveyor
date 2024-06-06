# Conveyor Process Setup Guide for Multi-Process Machine Code Python Applications
This README provides step-by-step instructions on how to integrate and configure conveyor processes within 
your multi-process machine code Python applications using the Vention platform. 
Follow these steps to ensure a smooth setup.

## Prerequisites
Before you begin, ensure that you have:

- Access to the Vention Control Center.
- Basic knowledge of Python and JSON file editing.

## Step 1: Configure All Inputs, Pneumatics, Actuators
Ensure all physical inputs, including pneumatics and actuators, are correctly configured and tested within your system.
This initial setup is crucial for the seamless integration of the conveyor process. 
Assign a meaningful name and configuration according to your project requirements.

## Step 2: Create a New Application in Control Center
1. Connect to the MachineMotion.
2. Navigate to the application section and create a new application.

## Step 3: Navigate to the Application Directory
After creating your application, navigate to its directory located at:

```bash
cd mm-execution-engine/LibrarySaveArea/MachineCode/<uuid>
```
Replace `<uuid>` with the actual UUID of your newly created application.

## Step 4: Clone the Conveyor Library
Within the uuid directory, clone the conveyor library from GitHub:

``` bash
 git clone https://github.com/VentionCo/mm-conveyor.git 
 ```
This command adds the conveyor library to your project directory.
### Note: Editing Conveyor Behavior
Edit the run function of the type of conveyor you are using within the `conveyor_types` folder as required to suit your application needs.

## Step 5: Edit the Conveyor Configuration with the custom UI
1. Download the latest build in the release section [mm-conveyor-ui]('https://github.com/VentionCo/mm-conveyor-ui')
2. Create a ui folder in the Application direcotry
```bash
mkdir ui
```
3. Drag and drop the contents of the build in this directory 

## Step 6: Add the node process to persist the configuration
1. Drag and drop the `conveyor_config_api.js` file in the root of the Application folder [conveyor-api]('https://github.com/VentionCo/mm-conveyor-ui/blob/main/conveyor_config_api.js')
2. Configure this process in the `project.json`
```json
{
  "name": "UI API",
  "command": "node conveyor_config_api.js"
}
```


## Step 7: Update the Project Configuration
Edit the project.json file in your project's root directory to include a new entry for the conveyor process:

```json
{
  "name": "conveyor process",
  "command": "python3 -u mm-conveyor/conveyor_control.py"
} 
```
This entry ensures that the conveyor process starts with your application.

## Step 8: Reload the Control Center and Run Your Application
After completing the setup, reload the MachineMotion Control Center to update the application view. You can now run your application directly from the Control Center.

## Conclusion
Following these steps will integrate the conveyor process into your multi-process machine code Python application.
For further customization and support, refer to the documentation within the `mm-conveyor` library or contact Vention support.