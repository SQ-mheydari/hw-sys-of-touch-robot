import math, types
import numpy as np


class Simulator_xyza_vc_stylus:
    name = "Stylus"
    title = "Standard stylus"
    axis = \
        {
            32:
                {
                    'alias': 'x',
                    'limits': (-5, 605)
                },
            1:
                {
                    'alias': 'y',
                    'limits': (-5, 605)
                },

            31:
                {
                    'alias': 'z',
                    'limits': (-2, 205)
                },
            22:
                {
                    'alias': 'azimuth',
                    'limits': (-100000, 100000)
                },
            11:
                {
                    'alias': 'voicecoil1',
                    'limits': (-1, 15),
                    'force_support': False
                },
            12:
                {
                    'alias': 'tilt_slider',
                    'limits': (-1, 95)
                }
        }

    def __init__(self, connection, kinematic):
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
        c.addObject("oazimuth", parent_name="oz")
        c.addObject("ovc", parent_name="oazimuth")
        c.addObject("otilt_slider", parent_name="ovc")
        c.addObject("olink1", parent_name="ovc")
        c.addObject("olink2", parent_name="otilt_slider")

        # Table object should be in every simulator.
        c.addObject("table", parent_name="base")

        # Move table so that it can be reached with tip attached to the robot.
        c.moveObject("table", [-200, 300, 119, math.pi, 0, 0])

        # Camera object.
        c.addObject("Camera1", parent_name="oz")

        # Set tips.
        self.tips = ["tip1"]

        for tip_name in self.tips:
            c.addObject(tip_name, parent_name="base")

        # With these stl models, the base must be rotated to rotate all models to right orientation.
        c.moveObject("base", [0, 0, 0, -math.pi, 0, 0])

        # Load models and connect to tree objects.
        path = "http://127.0.0.1:8010/model/stylus/"

        c.addStl(path + "base.stl", 'base', 0x444444, [0, 0, 0])
        c.addStl(path + 'y.stl', 'oy', 0x444444, [0, 0, 0])
        c.addStl(path + 'x.stl', 'ox', 0x444444, [0, 0, 0])
        c.addStl(path + 'z.stl', 'oz', 0x444444, [0, 0, 0])
        c.addStl(path + 'azimuth.stl', 'oazimuth', 0x444444, [0, 0, 0])
        c.addStl(path + 'vc.stl', 'ovc', 0x444444, [0, 0, 0])
        c.addStl(path + 'tilt_slider.stl', 'otilt_slider', 0x444444, [0, 0, 0])
        c.addStl(path + 'link1.stl', 'olink1', 0x444444, [0, 0, 0])
        c.addStl(path + 'link2.stl', 'olink2', 0x444444, [0, 0, 0])

        # Move camera where it should be.
        c.moveObject("Camera1", [-300.67, 199.901, 453.889, 0, 0, math.pi])

        # Add the camera.
        c.addCamera("Camera1", "Camera1", fov=19, focal_length=None)

        # Add hsup_camera.
        c.addObject("hsup_camera", parent_name="oz")
        c.moveObject("hsup_camera", [-400.67, 199.901, 453.889, 0, 0, math.pi])
        c.addCamera("hsup_camera", parent_name="hsup_camera", fov=20, focal_length=None)

        # Camera test sphere. Uncomment to visualize camera position.
        #c.addSphere("Camera1", 0xff0000, 10)

        # Set the visualization kinematics function.
        # In visualization the y axis is flipped in relation to robot frame. This also changes the handedness.
        # The offsets of visualized parts where determined from the 3D model and are hard-coded below.
        f = """
            function(joints)
            {
                const tilt_slider_offset = 25.88;
                
                var x = joints['x'];
                var y = joints['y'];
                var z = joints['z'];
                var vc = joints['voicecoil1'];
                var ts = joints['tilt_slider'] + tilt_slider_offset;
                var a = joints['azimuth'] / 180 * Math.PI
                
                var link_length = 50.0;
                
                var mx = [1, 0, 0, x, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
                var my = [1, 0, 0, 0, 0, 1, 0, -y, 0, 0, 1, 0, 0, 0, 0, 1];
                var mz = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, -z, 0, 0, 0, 1];
                var mvc = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, -vc, 0, 0, 0, 1];
                var mts = [1, 0, 0, ts, 0, 1, 0, 0, 0, 0, 1, -123.665, 0, 0, 0, 1];
                
                c = Math.cos(a);
                s = Math.sin(a);
                var ma = [c, -s, 0, -300.665, s, c, 0, 256.61, 0, 0, 1, 456.92, 0, 0, 0, 1];
                
                var link1_angle = -Math.acos(0.5 * ts / link_length) + Math.PI * 0.5;
                c = Math.cos(link1_angle);
                s = Math.sin(link1_angle);
                var mlink1 = [c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, -123.665, 0, 0, 0, 1];
                
                c = Math.cos(-link1_angle);
                s = Math.sin(-link1_angle);
                var mlink2 = [c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, 0, 0, 0, 1];
                
                return { "ox":mx, "oy":my, "oz": mz, "oazimuth": ma, "ovc": mvc, "otilt_slider": mts, "olink1": mlink1, "olink2": mlink2 }
                }
            """
        c.set_kinematic_function(f)

        # Name of tip currently attached to robot in simulator's book-keeping.
        self.current_tip_name = None

        # Dictionary of known slot-in positions as tip_name: [pos_x, pos_y, pos_z].
        self.slot_in_positions = {}

    def attach_tip(self, tip_name, kinematic_name):
        c = self.connection


    def detach_tip(self, tip_name):
        c = self.connection

    def set_tip_slot_in(self, tip_name, slot_in):
        """
        Set tip slot-in position.
        :param tip_name: name of tip
        :param slot_in: slot-in position as list [x, y, z]
        :return:
        """
        slot_in_sim = np.array(slot_in)

        self.slot_in_positions[tip_name] = slot_in_sim