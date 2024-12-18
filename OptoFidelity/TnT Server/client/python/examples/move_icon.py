"""
This test demonstrates the possibilities of icon detection by finding an icon on a smartphone screen, moving it to
a different location and opening the application after the move.
"""
import tntclient.tnt_client as tnt_client

# The client is used to create different client objects for other things like DUTs and robot
client = tnt_client.TnTClient()

# Initialize a robot client and set speed to ensure that the robot moves at a good pace
robot = client.robot('Robot1')
robot.set_speed(100, 400)

# Initialize the DUT to be used in the test and set the DUT to use the previously defined robot
dut1 = client.dut('test_dut_1')
dut1.robot = robot

# Jump to 40mm over the top left corner of the DUT.
# Jumping is the safest way to move between DUTs in the workspace, by default it uses the maximum z height for the robot
dut1.jump(0, 0, 40)

# Find the icon for the app to be moved
object_data = dut1.find_objects('C:\\OptoFidelity\\TnT Server\\data\\icons\\app.shm')

# If the icon is found drag the icon to a new position
if len(object_data['results']) != 0:
    # Pick the first index from the results since it's the one with highest score, aka. most likely to be the right icon
    results = object_data['results'][0]
    # Drag starting position from the icon location
    start_x = results['centerX']
    start_y = results['centerY']

    # Move the icon 20mm to the right and 20mm down
    end_x = start_x + 20
    end_y = start_y + 20

    # Drag the icon. Predelay is needed to initialize the icon dragging by holding the tip down for 2s before moving
    dut1.drag(start_x, start_y, end_x, end_y, predelay=2)
else:
    raise Exception('Icon for app to be moved not found on DUT screen.')

# Find the icon for the app again since it has moved
object_data = dut1.find_objects('C:\\OptoFidelity\\TnT Server\\data\\icons\\app.shm')

# If the icon is found then tap on that icon
if len(object_data['results']) != 0:
    # Choose the first index from the results again
    results = object_data['results'][0]
    # And simply tap at the found location
    dut1.tap(results['centerX'], results['centerY'])
else:
    raise Exception('Icon for app to be opened not found on DUT screen.')
