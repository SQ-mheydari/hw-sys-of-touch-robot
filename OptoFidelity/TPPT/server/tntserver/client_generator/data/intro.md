# Getting started

TnT python client has been tested with python 3.5 in 32-bit Windows, 64-bit Windows, 32-bit MacOs, and 64-bit MacOs environments.

To get started, make sure that TnT Server is running. Then import TnTClient module and create an instance of TnTRobotClient or TnTDUTClient class.

To control robot in robot workspace frame, create an instance of TnTRobotClient class. TnTClient class implements some factory methods to help creating other robot control classes such as TnTRobotClient.

Example:

```
from tntclient.tnt_client import TnTClient
client = TnTClient()
robot = client.robot("Robot1")
robot.move(20.0, 20.0, 10.0) # example command
```

To control robots and actuators in DUT coordinate frame, create an instance of class TnTDUTClient. This can be done by first creating TnTClient object with required initialization and then by creating TnTDUTClient.

Example:

```
from tntclient.tnt_client import TnTClient
tntclient = TnTClient()
robot = tntclient.robot("Robot1")
dut = tntclient.dut("DUT1")
dut.robot = robot
dut.jump(x=20.0, y=20.0, z=10.0, jump_height=40.0) # example command
```

More examples can be found under examples/ directory in the TnT Client package.

# Units

In function parameters, following units are assumed unless otherwise stated:

- Linear length: millimeters [mm]
- Angle: degrees [deg]
- Time: seconds [s]
- Mass: grams [g]

Such parameters are represented with floating point types so that decimal values are allowed.