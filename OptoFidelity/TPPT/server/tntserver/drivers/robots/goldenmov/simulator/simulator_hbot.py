import math, types
import numpy as np

class Simulator_hbot:
    """
    Simulator model for HBOT robot.
    """
    name = "hbot"
    title = "hbot"
    axis = \
        {
            12:
                {
                    'alias': 'y',
                    'limits': (-1000, 1000)
                },
            11:
                {
                    'alias': 'x',
                    'limits': (-1000, 1000)
                },

            21:
                {
                    'alias': 'z',
                    'limits': (-2, 20)
                }
        }

    def __init__(self, connection, kinematic):
        """
        Initialize simulator.
        :param connection: Simulator connection object.
        :param kinematic: Kinematics object.
        """
        self.connection = connection

    def create_model(self):
        """
        Create the model and load 3D model files.
        """
        c = self.connection

        # Clear everything.
        c.resetModel()

        # Create object tree.
        c.addObject("base")
        c.addObject("oy", parent_name="base")
        c.addObject("ox", parent_name="oy")
        c.addObject("oz", parent_name="ox")

        # Table object should be in every simulator.
        c.addObject("table", parent_name="base")

        # Move table so that it can be reached with tip attached to the robot.
        c.moveObject("table", [0, 0, -35, math.pi, 0, 0])

        # Camera object.
        c.addObject("Camera1", parent_name="base")

        # Set tips.
        self.tips = ["tip1"]

        for tip_name in self.tips:
            c.addObject(tip_name, parent_name="base")

        # With these stl models, the base must be rotated to rotate all models to right orientation.
        c.moveObject("base", [0, 0, 0, -math.pi, 0, 0])

        # Load models and connect to tree objects.
        path = "http://127.0.0.1:8010/model/hbot/"

        c.addStl(path + "base.stl",  'base', 0x444444, [0, 0, 0])
        c.addStl(path + 'y.stl',     'oy',   0x444444, [0, 0, 0])
        c.addStl(path + 'x.stl',     'ox',   0x444444, [0, 0, 0])
        c.addStl(path + 'z.stl',     'oz',   0x444444, [0, 0, 0])

        # Move camera where it should be.
        c.moveObject("Camera1", [150, -260, 255, 0, 0, math.pi])

        # Add the camera.
        c.addCamera("Camera1", "Camera1", fov=19, focal_length=None)

        # Add hsup_camera.
        c.addObject("hsup_camera", parent_name="oz")
        c.moveObject("hsup_camera", [150, -300, 255, 0, 0, math.pi])
        c.addCamera("hsup_camera", parent_name="hsup_camera", fov=20, focal_length=None)

        # Camera test sphere. Uncomment to visualize camera position.
        #c.addSphere("Camera1", 0xff0000, 10)

        # Load tip model.
        c.addStl(path + "tip.stl", "tip1", 0xcc8833, [0, 0, 0])

        # Set the visualization kinematics function.
        # Because the visuals are rotated, also the kinematic model is rotated (y and z axis are swapped).
        f = """
        function(joints)
            {
            var x = joints['x'];
            var y = joints['y'];
            var z = joints['z'];
            var mx = [1, 0, 0, -x+y, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
            var my = [1, 0, 0, 0, 0, 1, 0, x+y, 0, 0, 1, 0, 0, 0, 0, 1];
            var mz = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, -z, 0, 0, 0, 1];
            return { "ox":mx, "oy":my, "oz": mz }
            }
        """
        c.set_kinematic_function(f)

        # Name of tip currently attached to robot in simulator's book-keeping.
        self.current_tip_name = None

        # Dictionary of known slot-in positions as tip_name: [pos_x, pos_y, pos_z].
        self.slot_in_positions = {}

    def attach_tip(self, tip_name, kinematic_name):
        """
        Attach tip in simulator model
        :param tip_name: Name of tip to attach.
        :param kinematic_name: Name of kinematics used to attach tip.
        """
        c = self.connection

        # Parent new tip to robot z-axis.
        if tip_name in self.tips:
            c.moveObject(tip_name, [0,0,0,0,0,0], "oz")

    def detach_tip(self, tip_name):
        """
        Detach tip in simulator model.
        :param tip_name: Name of tip to detach.
        """
        c = self.connection

        # Reparent unattached tips to rack (could also be root).
        # The global tip positions are retained to allow configuring new tip rack positions.
        # Could also use self.slot_in_positions, but reparenting avoids jumps in case
        # self.server_root_to_simulator_offset is not accurate.
        if tip_name in self.tips:
            c.reparent(tip_name, "base")

    def set_tip_slot_in(self, tip_name, slot_in):
        """
        Set tip slot-in position.
        :param tip_name: Name of tip.
        :param slot_in: Slot-in position as list [x, y, z].
        """
        slot_in_sim = np.array(slot_in)

        self.slot_in_positions[tip_name] = slot_in_sim

        # If tip is not current, move it to given slot-in position because this position was
        # unknown up to this point and the tip may be at incorrect place.
        if tip_name != self.current_tip_name:
            self.connection.moveObject(tip_name, slot_in_sim.tolist() + [0,0,0], "base")
