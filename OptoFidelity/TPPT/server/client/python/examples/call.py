"""
This test is a more advanced example that makes use of functionality introduced in the other tests. The icon detetction
and OCR functions are defined in the file helper_functions.py to make this test case be more readable.

The test wakes up a smartphone, makes a call from it by using icon detection and OCR, then answers and ends the call on
a different smartphone, and after that proceeds to lock the first smartphone again.
"""
import time
import tntclient.tnt_client as tnt_client
from .helper_functions import tap_icon, swipe_icon, tap_text

# The client is used to create different client objects for other things like DUTs and robot
client = tnt_client.TnTClient()

# Initialize a robot client and set speed to ensure that the robot moves at a good pace
robot = client.robot('Robot1')
robot.set_speed(100, 400)

# Initialize the two DUTs to be used in the test
dut1 = client.dut('test_dut_1')
dut1.robot = robot
dut2 = client.dut('test_dut_2')
dut2.robot = robot

# Jump to 40mm over the top left corner of the DUT.
# Jumping is the safest way to move between DUTs in the workspace, by default it uses the maximum z height for the robot
dut1.jump(0, 0, 40)

# Press the power button to initialize unlock
robot.press_physical_button('dut1_power')
# Swipe up from the bottom of the screen to unlock the device
dut1.swipe(dut1.width/2, dut1.height, dut1.width/2, dut1.height/2)

# Find the contacts icon and tap to open the contacts list
tap_icon(dut1, 'contacts')

# Find a contact for the second DUT, e.g. 'call_test_number' and tap
tap_text(dut1, 'call_test_number')

# Tap on text 'Call' to initiate a phone call
tap_text(dut1, 'Call')

# Jump over to the second DUT and wait for the call to come through
dut2.jump(dut2.width/2, dut2.height/2, 20)
time.sleep(3)

# Answer the call by swiping up starting from the accept call icon
swipe_icon(dut2, 'accept_call', direction='up', swipe_length=20)

# Wait for a few seconds and end the call
time.sleep(3)
tap_icon(dut2, 'end_call')

# Lock the first DUT again
robot.press_physical_button('dut1_power')
