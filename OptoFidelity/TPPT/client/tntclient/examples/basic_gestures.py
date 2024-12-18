"""
This test introduces the basic gestures executable on a DUT
"""

import tntclient.tnt_client as tnt_client
from tntclient.tnt_client import TnTDutPoint

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

# Move down to 10mm above the top left corner of the DUT
dut1.move(0, 0, 10)

# Define tap location as the center point of the defined DUT
tap_x = dut1.width / 2
tap_y = dut1.height / 2
# Tap the DUT at the defined position
dut1.tap(tap_x, tap_y)

# Define the swipe start and end positions
# Start from the bottom and center of the screen
start_x = dut1.width/2
start_y = dut1.height
# End in the top of the screen, x coordinate is the same since we swipe straight up
end_x = start_x
end_y = 0

# Swipe on the screen with the defined positions
dut1.swipe(start_x, start_y, end_x, end_y)

# Perform a drag in the opposite direction of the swipe
dut1.drag(end_x, end_y, start_x, start_y)

# Define three points on the DUT and draw a path on the screen between them
# The top left corner of the DUT
point1 = TnTDutPoint(0, 0, 0)
# The center point on the right edge of the DUT
point2 = TnTDutPoint(dut1.width, dut1.height / 2, 0)
# The bottom left corner of the DUT
point3 = TnTDutPoint(0, dut1.height, 0)

# Create a list of the points to give to the path command
list_of_points = [point1, point2, point3]

# Execute the path command defined above
dut1.path(list_of_points)
