"""
This test demonstrates the possibilities of OCR on a smartphone by trying to find a certain contact in the contacts.

Icon detection and handling in this test is done using a helper function, a simple example of icon detection is
available in the test defined in move_icon.py.

The test assumes that the contacts icon is visible on the main screen.
"""
import tntclient.tnt_client as tnt_client
from .helper_functions import tap_icon

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

# Tap contacts icon to open the contacts application
tap_icon(dut1, 'contacts')

# Try to find the contact on the screen
text_data = dut1.search_text('name_of_contact')

# If text is found tap to open the details
if len(text_data['results']) != 0:
    # Choose the first index from the results since it is always the best match
    results = text_data['results'][0]
    # Tap on the text location
    dut1.tap(results['centerX'], results['centerY'], clearance=-1)

else:
    # The text was not found on the first screen, scroll up by swiping on the screen and try again

    # Define the swipe start and end positions
    # Start from the bottom of the screen
    start_x = dut1.width/2
    start_y = dut1.height
    # End in the center of the screen, x coordinate is the same since we swipe straight up
    end_x = start_x
    end_y = dut1.height/2

    # Swipe on the screen with the defined positions
    dut1.swipe(start_x, start_y, end_x, end_y)

    # Try again to find the contact on the screen
    text_data = dut1.search_text('name_of_contact')

    # If the contact is found this time tap to open the details
    if len(text_data['results']) != 0:
        # Choose the first index from the results since it is always the best match
        results = text_data['results'][0]
        # Tap on the text location
        dut1.tap(results['centerX'], results['centerY'], clearance=-1)