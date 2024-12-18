Script page is used for configuring and running the TPPT tests which are defined by a set of Python scripts.

## Script definition

On the left side of the page you can load the script that is used for the tests, and add information about the test session
such as the operator or manufacturer. 

![Script definition page_left.](ui_help_images/script_definition_page_left.png "script_definition_left")

On the right side you can choose which DUTs are being tested, which tips are being used and which tests are being run. 
Additionally you can modify various configurations for the DUTs and the tests. You can also set the robot speed and
acceleration that are being used during the session.

![Script definition page_right.](ui_help_images/script_definition_page_right.png "script_definition_right")

When tests have been chosen the points that will be measured can be previewed from "Show measurement points" button. The 
images of the tests that use random point generation (for example repeatability) are mostly for illustrative purposes 
as the points are re-generated at the beginning of the session. 

The test session can be ran from the "Run tests" button.

## Script execution

On the left side there is the possibility to stop or pause the script. After tests are done there will be a "Finish"
button. Test status is shown below the buttons. Under the status you can see a image displaying expected points or lines 
and measured points. In tap like tests expected and measured points are also written underneath the image.

![Script run page_left.](ui_help_images/script_run_page_left.png "script_execution_left")

On the right side you can see information about the execution of the test sequence.

![Script run page_right.](ui_help_images/script_run_page_right.png "script_execution_right")

## One finger testcase descriptions
The pre-defined testcases represent the most used practises to test a touch screen. Below one can see the explanations of what they are meant for and what types of gestures they consist of. All the testcases include many adjustable parameters. More information about the parameters can be seen if one moves the mouse cursor on top of the parameter name. Then a tooltip text box should appear.

### First contact Latency
First contact latency measures the time difference between the touch detected by the robot and the touch reported by the system. Running first contact requires special PIT (Panel Interface Tester) HW equipment.

### Non Stationary reporting rate
Non stationary reporting rate means the amount of touch events reported by the system in given time while performing moving gestures on the screen. In practice, this means swiping gestures and analyzing the touch event timestamps.

### Repeatability
Repeatability test analyzes the DUT's touch detection when tap gesture is repeated in the same exact location.

### Stationary jitter
Stationary jitter measures the touch events recorded when robot finger is touching the screen and hold in place.

### Stationary reporting rate
Stationary reporting rate means the amount of touch events reported by the system in given time when robot finger is touching the screen and hold in place.

### Swipe
In swipe test, swiping gestures are performed on DUT's screen. Then, in analysis, the touches reported by DUT are compared to the ones robot performed.

### Tap
In tap test, tapping gestures are performed on DUT's screen. Then, in analysis, the touches reported by DUT are compared to the ones robot performed. Note, that in addition to defining the tap grid by adjusting the parameters it is also possible to give the coordinates in a file.

## Two finger testcase descriptions
Two finger testcases require a robot that can hold and move two tips simultaneously.

### Separation
In separation test the DUT screen is tapped with both fingers simultaneously to see how far apart the fingers need to be so that two separate touches are detected.

## Multifinger testcase descriptions
Multifinger tests require a special tool end that has multiple fingers attached to it and a robot to which it is possible to attach such tool. As multifinger tool dimensions are larger than for a one finger tool, the test cases are also run in a slightly different way.

### Swipe
Multifinger swipe consists of one horizontal swipe in the middle of the screen, one vertical swipe in the middle of the screen and swipes on both diagonals. Swipes might be omitted if the DUT screen is too small for the tool to fit.

### Tap
Multifinger tap consists of one horizontal tap, one vertical tap and tap on both diagonals. All the tapping gestures are performed in the middle of the screen. Some taps might be omitted if the DUT screen is too small for the tool to fit.

