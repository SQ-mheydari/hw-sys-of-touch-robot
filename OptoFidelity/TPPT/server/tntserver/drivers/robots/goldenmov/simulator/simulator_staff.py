import math


class Simulator_staff:
    """
    Simulator for STAFF robot.
    """
    name = "staff"
    title = "staff"

    axis = \
        {
            1:
                {
                    'alias': 'x',
                    'limits': (-5, 605)
                },
            2:
                {
                    'alias': 'y',
                    'limits': (-5, 605)
                },
            3:
                {
                    'alias': 'z',
                    'limits': (-2, 170)
                },
            4:
                {
                    'alias': 'azimuth',
                    'limits': (-179, 179)
                },
            5:
                {
                    'alias': 'tilt',
                    'limits': (-5, 90)
                },

            6:
                {
                    'alias': 'voicecoil1',
                    'limits': (-4, 4)
                }
        }

    def __init__(self, connection, kinematic):
        self.connection = connection

        self._mount_detach_coordinates = [60, 0, 20, 0, 0, 0]

    def create_model(self):
        c = self.connection

        c.resetModel()

        # Set root transform to identity and camera to rotate around the z-axis.
        # This makes it easier to match the robot visualization coordinates to the actual robot workspace coordinates.
        # Model origins have been set so that the visualization origin matches the robot workspace origin.
        # Visualization does still deviate from robot workspace by handedness: robot x maps to -x in visualization.
        c.moveObject("root", [0, 0, 0, 0, 0, 0])
        c.setCameraUp(0, 0, 1)

        # create object tree
        c.addObject("base")
        c.addObject("oy", parent_name="base")
        c.addObject("ox", parent_name="oy")
        c.addObject("oz", parent_name="ox")
        c.addObject("oazimuth", parent_name="oz")
        c.addObject("ovc", parent_name="oazimuth")
        c.addObject("otilt", parent_name="ovc")
        c.addObject("ostylusmount", parent_name="otilt")
        c.addObject("ostylus", parent_name="ostylusmount")
        c.addObject("oestop", parent_name="base")

        # table object should be in every simulator
        # sets standard position and orientation for the perforated table board on robot
        # should always be located at the rearmost left hole of the table
        c.addObject("table", parent_name="base")
        c.moveObject("table", [6.2604, 55.2341, -292.772, 0, 0, 0])

        c.addObject("otipmount", parent_name="table")
        c.addObject("otipmount_head", parent_name="otipmount")
        c.moveObject("otipmount_head", [-60.1281, 40.6461, -63.4549, 0, 0, 0], parent="otipmount")

        c.addObject("otip9", parent_name="base")
        c.addObject("otiprack", parent_name="base")

        # camera mount
        c.addObject("camera", parent_name="oazimuth")
        c.moveObject("camera", [-61.252, -31.9968, -179.799, 0, 0, 0])

        # actual camera
        c.addCamera("Camera1", parent_name="camera", fov=35, focal_length=None)

        # stylus calibration cameras
        c.addObject("styluscalibcamerax", parent_name="table")
        c.moveObject("styluscalibcamerax", [-383, 100, -34, -0.5 * math.pi, math.pi, -0.5 * math.pi])
        c.addCamera("StylusCalibCameraX", parent_name="styluscalibcamerax", fov=35, focal_length=None)
        c.addObject("styluscalibcameray", parent_name="table")
        c.moveObject("styluscalibcameray", [-362, 122, -34, -0.5 * math.pi, 0.5 * math.pi, -0.5 * math.pi])
        c.addCamera("StylusCalibCameraY", parent_name="styluscalibcameray", fov=35, focal_length=None)

        path = "http://127.0.0.1:8010/model/staff/"

        c.addStl(path + "base.stl",  'base', 0x111111, [0, 0, 0])
        c.addStl(path + 'y.stl', 'oy', 0x222222, [0, 0, 0])
        c.addStl(path + 'x.stl', 'ox', 0x333333, [0, 0, 0])
        c.addStl(path + 'z.stl', 'oz', 0x333333, [0, 0, 0])
        c.addStl(path + 'azimuth.stl',   'oazimuth', 0x222222, [0, 0, 0])
        c.addStl(path + 'vc.stl', 'ovc', 0x222222, [0, 0, 0])
        c.addStl(path + 'tilt.stl', 'otilt', 0x2a3665, [0, 0, 0])
        c.addStl(path + 'stylusmount.stl', 'ostylusmount', 0x212121, [0, 0, 0])
        c.addStl(path + 'stylus.stl', 'ostylus', 0xcc9900, [0, 0, 0])
        c.addStl(path + 'estop.stl', 'oestop', 0x990000, [0, 0, 0])
        c.addStl(path + 'tipmount.stl', 'otipmount', 0x212121, [0, 0, 0])
        c.addStl(path + 'tip9.stl', 'otip9', 0xcc9900, [0, 0, 0])
        c.addStl(path + 'tiprack.stl', 'otiprack', 0x212121, [0, 0, 0])

        c.moveObject("otipmount", self._mount_detach_coordinates)
        c.moveObject("otip9", [-69.6901, 165.954, -266.624, 0, 0, 0], parent="base")

        # set visualization kinematics function
        f = """
        function(joints)
            {
            var x = joints['x'];
            var y = joints['y'];
            var z = joints['z'];
            var azimuth = joints['azimuth'] / 180 * Math.PI
            var tilt = joints['tilt'] / 180 * Math.PI
            var vc = joints['voicecoil1'];

            var mx = [1, 0, 0, -x, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
            var my = [1, 0, 0, 0, 0, 1, 0, y, 0, 0, 1, 0, 0, 0, 0, 1];
            var mz = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, -z, 0, 0, 0, 1];
            var mvc = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, -vc, 0, 0, 0, 1];

            var c = Math.cos(tilt);
            var s = Math.sin(tilt);
            var mtilt = [
            c, 0, -s, 0, 
            0, 1, 0, 0,
            s, 0, c, -207.94, 
            0, 0, 0, 1];

            c = Math.cos(azimuth);
            s = Math.sin(azimuth);
            var mazimuth = [
            c, -s, 0, 6.2604, 
            s, c, 0, 55.2341, 
            0, 0, 1, 103.497, 
            0, 0, 0, 1];

            return { "ox":mx, "oy":my, "oz": mz, "oazimuth": mazimuth, "otilt": mtilt, "ovc": mvc }
            }
        """
        c.set_kinematic_function(f)
        c.set_axes(__class__.axis)

    def attach_tip(self, tip_name, kinematic_name):
        if tip_name == "tip9":
            self.connection.moveObject("otip9", [0, 0, 0, 0, 0, 0], "otipmount_head")

    def detach_tip(self, tip_name):
        if tip_name == "tip9":
            self.connection.reparent("otip9", "base")

    def attach_tool(self, tool_name, mount_name):
        if tool_name == "tool1":
            self.connection.moveObject("ostylusmount", [0, 0, 0, 0, 0, 0], "otilt")
        elif tool_name == "tool2":
            self.connection.moveObject("otipmount", [0, 0, 0, 0, 0, 0], "otilt")

    def detach_tool(self, tool_name):
        if tool_name == "tool1":
            self.connection.moveObject("ostylusmount", self._mount_detach_coordinates, "table")
        elif tool_name == "tool2":
            self.connection.moveObject("otipmount", self._mount_detach_coordinates, "table")

    def set_tip_slot_in(self, tip_name, slot_in):
        pass
