import math, types
import numpy as np

class Simulator_3axis:
    name = "3axis"
    title = "Standard 3-axis"
    axis = \
        {
            2:
                {
                    'alias': 'x',
                    'limits': (-15, 404)
                },
            1:
                {
                    'alias': 'y',
                    'limits': (-45, 416)
                },

            3:
                {
                    'alias': 'z',
                    'limits': (-2, 111)
                }
        }

    def __init__(self, connection, kinematic):
        self.connection = connection

    def create_model(self):
        c = self.connection

        # clear everything
        c.resetModel()

        # create object tree
        c.addObject("base")
        c.addObject("oy", parent_name="base")
        c.addObject("ox", parent_name="oy")
        c.addObject("oz", parent_name="ox")

        # table object should be in every simulator
        # sets standard position and orientation for the perforated table board on robot
        # should always be located at the rearmost left hole of the table
        c.addObject("table", parent_name="base")
        #c.addSphere("table", 0x00ff00, 2) # for positioning to the hole
        c.moveObject("table", [-10.2,179.5,-116.5,math.pi,0,0])

        # Basler camera
        c.addObject("Camera1", parent_name="oz")

        # tool tips
        self.tips = ["tip1", "tip2"]
        for tip_name in self.tips:
            c.addObject(tip_name, parent_name="base")
        #c.addObject("tip2", parent_name="oz")

        # finger rack
        c.addObject("rack1", parent_name="base")

        # with these stl models, the base must be rotated to rotate all models to right orientation
        c.moveObject("base", [0, 0, 0, -math.pi, 0, 0])

        # load models and connect to tree objects
        path = "http://127.0.0.1:8010/model/3axis/"

        # origo at tool tip where the Tips are mounted
        ox = -51.2
        oy = -3
        oz = -197

        c.addStl(path + "Base.STL",  'base', 0x444444, [0+ox, -500+oy, 0+oz])
        c.addStl(path + 'Y.STL',     'oy',   0x444444, [-100+ox, 0+oy, 0+oz])
        c.addStl(path + 'X.STL',     'ox',   0x444444, [-180+ox, 32+oy, 67+oz])
        c.addStl(path + 'Z.STL',     'oz',   0x444444, [-180+ox, -68+oy, 60+oz])


        # move camera where it should be
        c.moveObject("Camera1", [0.1, -52, 255, 0, 0, math.pi])

        # add the camera
        c.addCamera("Camera1", "Camera1", fov=19, focal_length=None)

        # hsup_camera mount
        c.addObject("hsup_camera", parent_name="oz")
        c.moveObject("hsup_camera", [0.1, -52, 255, 0, 0, math.pi])
        c.addCamera("hsup_camera", parent_name="hsup_camera", fov=20, focal_length=None)

        # camera test sphere
        #c.addSphere("Camera1", 0xff0000, 10)

        # tool tips
        c.addStl(path + "8mm_finger.STL", "tip1", 0xcc8833, [-4.86, 4.86, -16, 90, 0, 0])
        c.addStl(path + "8mm_finger.STL", "tip2", 0xcc8833, [-4.86, 4.86, -16, 90, 0, 0])

        # finger rack
        #c.addStl(path + "Finger_rack_tall.STL", "rack1", 0xeeece0, [-27, -198.7, 10, 0,0,0])
        c.addStl(path + "Finger_rack_tall.STL", "rack1", 0xb0b1b2, [-12.3, -31, -18.5, 0, 0, 0])
        rack_x = 14
        rack_y = 7
        rox = -27 + 12.3
        roy = 198.7 -31
        roz = -10 + -18.5
        hole_distance = 25
        c.moveObject("rack1", [hole_distance * rack_x + rox,
                               hole_distance * -rack_y + roy,
                               roz,
                               math.pi, 0, 0])

        # set visualization kinematics function
        # because the visuals are rotated, also the kinematic model is rotated ( y and z axis are swapped )
        f = """
        function(joints)
            {
            var x = joints['x'];
            var y = joints['y'];
            var z = joints['z'];
            var mx = [1, 0, 0, x, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
            var my = [1, 0, 0, 0, 0, 1, 0, -y, 0, 0, 1, 0, 0, 0, 0, 1];
            var mz = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, -z, 0, 0, 0, 1];
            return { "ox":mx, "oy":my, "oz": mz }
            }
        """
        c.set_kinematic_function(f)
        #c.set_axes(__class__.axis)

        # This can be used to place tips in pre-determined position in rack.
        #for i, tip in enumerate(self.tips):
        #    c.moveObject(tip, [20 * i,0,0,math.pi,0,0], "rack1")

        #self.set_tip("tip2")

        # Approximated offset from server robot root position to simulator root position.
        self.server_root_to_simulator_offset = np.array([0, -15, 0])

        # Name of tip currently attached to robot in simulator's book-keeping.
        self.current_tip_name = None

        # Dictionary of known slot-in positions as tip_name: [pos_x, pos_y, pos_z].
        self.slot_in_positions = {}

    def attach_tip(self, tip_name, kinematic_name):
        c = self.connection

        # Parent new tip to robot z-axis.
        if tip_name in self.tips:
            c.moveObject(tip_name, [0,0,0,0,0,0], "oz")

    def detach_tip(self, tip_name):
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
        :param tip_name: name of tip
        :param slot_in: slot-in position as list [x, y, z]
        :return:
        """
        slot_in_sim = np.array(slot_in)
        slot_in_sim += self.server_root_to_simulator_offset

        self.slot_in_positions[tip_name] = slot_in_sim

        # If tip is not current, move it to given slot-in position because this position was
        # unknown up to this point and the tip may be at incorrect place.
        if tip_name != self.current_tip_name:
            self.connection.moveObject(tip_name, slot_in_sim.tolist() + [0,0,0], "base")
