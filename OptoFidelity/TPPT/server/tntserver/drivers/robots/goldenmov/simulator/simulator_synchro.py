import math
import numpy as np
import json
import os
from tntserver import robotmath


class Simulator_synchro:
    name = "synchro"
    title = "Synchro"

    axis = \
        {
            1:
                {
                'alias': 'y',
                    'limits': (-1, 650)
                },
            32:
                {
                'alias': 'x',
                    'limits': (-1, 650)
                },
            31:
                {
                'alias': 'z',
                    'limits': (-1, 120)
                },
            22:
                {
                'alias': 'azimuth',
                'limits': (-1000000, 1000000)
                },
            21:
                {
                'alias': 'separation',
                'limits': (-2, 130)
                },

            11:
                {
                'alias': 'voicecoil1',
                'limits': (-10, 10)
                },
            12:
                {
                'alias': 'voicecoil2',
                'limits': (-10, 10)
                }
        }

    def __init__(self, connection, kinematic):
        self.connection = connection

        self.tips = ["tip1", "tip2"]

        # Dictionary of known slot-in positions as tip_name: [pos_x, pos_y, pos_z].
        self.slot_in_positions = {}

        self.kinematic = kinematic

        # Transform from robot coordinates to simulator base object coordinates.
        # Ideally the STL model placement would be such that this transform is not needed.
        # This transform was approximately found by visual inspection.
        self.robot_to_base = np.matrix([
            [1, 0, 0, 0.029],
            [0, 0, 1, -100 + 22],
            [0, 1, 0, 10 - 9.928],
            [0, 0, 0, 1]
        ])

    def create_model(self):
        c = self.connection

        c.resetModel()

        # create object tree
        c.addObject("base")
        c.addObject("oy", parent_name="base")

        # left z-stage
        # c.addObject("ox1", parent_name="oy")
        # c.addObject("oz1", parent_name="ox1")
        # c.addObject("otool1", parent_name="oz1")

        # right z-stage
        c.addObject("ox2", parent_name="oy")
        c.addObject("oz2", parent_name="ox2")
        c.addObject("oa2", parent_name="oz2")
        c.addObject("osynchro", parent_name="oa2")          # zero fingertip point for synchro fingers
        c.addObject("synchrotool1", parent_name="osynchro")    # offset to left with synchro
        c.addObject("synchrotool2", parent_name="osynchro")    # offset to right with syncro
        c.addObject("ovoicecoil1", parent_name="synchrotool1")
        c.addObject("ovoicecoil2", parent_name="synchrotool2")
        c.addObject("tool1", parent_name="ovoicecoil1")  # finger 1 mount tool
        c.addObject("tool2", parent_name="ovoicecoil2")  # finger 2 mount tool
        # c.addObject("osf1", parent_name="voicecoil1")        # finger 1 position
        # c.addObject("osf2", parent_name="voicecoil2")        # finger 2 position

        c.addObject("t", parent_name="tool2")

        # with these stl models, the base must be rotated to rotate all models to right orientation
        # also add a translation to center the object, simulator is nicer to use like so
        c.moveObject("base", [-300, 100, -500, -math.pi/2, 0, 0])

        # move finger mounts at place
        # c.moveObject("otool1", [0, -78, 0, 0,0,0])
        c.moveObject("osynchro", [0, -78, 0, 0,0,0])
        c.moveObject("tool1", [-20, 0, 0, 0,0,0])
        c.moveObject("tool2", [ 20, 0, 0, 0,0,0])

        # camera1 mount
        c.addObject("camera1", parent_name="oz2")
        c.moveObject("camera1", [0, 100, 70, -math.pi/2, 0, math.pi])
        #c.addSphere("camera1", 0xff0000, 3)

        # hsup_camera mount
        c.addObject("hsup_camera", parent_name="oz2")
        c.moveObject("hsup_camera", [0, 100, 70, -math.pi / 2, 0, math.pi])

        #c.addObject("tmp", parent_name="camera1")
        # actual camera
        c.addCamera("Camera1", parent_name="camera1", fov=35, focal_length=None)
        c.addCamera("hsup_camera", parent_name="hsup_camera", fov=20, focal_length=None)

        # add table object for easy-to-place simulator objects
        # this is the position of farthest left table hole
        # axis: x=right, y=towards front, z=down
        # ( x & y same as in TnTz down instead of up because Three.js is strongly of different handedness )
        c.addObject("table", "base")
        c.moveObject("table", [19.1, -193, -115.5, math.pi/2, 0, 0])
        #c.addSphere("table", 0xff0000, 3)

        c.addObject("rack", parent_name="table")
        c.moveObject("rack", [10, 500, -60, 0, 0, -math.pi/2])

        c.addObject("tip1", parent_name="base")
        c.addObject("tip2", parent_name="base")

        # load models and connect to tree objects

        #0.18, -62, 0.4

        path = "http://127.0.0.1:8010/model/synchro_asvcf/"
        local_path = os.path.join("tntserver", "web", "model", "synchro_asvcf")
        c.addStl(path + "Stationary.STL",   'base', 0x000000, [-25.88, -279.0, -216.9])
        c.addStl(path + "X-stage.STL",      'oy',   0x000000, [-54.88, -279.0, -321.9])
        c.addStl(path + "Z-unit2.STL",      'ox2',  0x000000, [-102.88, -193.0, -161.9])
        c.addStl(path + "Rotation_unit.STL",'oz2',  0x444444, [-102.88, -110.5, -63.9])

        c.addStl(path + "Synchro_rotating.STL", 'oa2', 0x222222, [-114.9, -104.5, -77.4])

        c.addStl(path + "Synchro_finger_1.STL", 'tool1', 0x888888, [-51.25, -26.5, -26.5])
        c.addStl(path + "Synchro_finger_2.STL", 'tool2', 0x888888, [-154.3, -26.5, -18.0])

        # add fingers
        c.addStl(path + "8mm_finger.STL", 'tip1',  0xcc8833, [-5, -6, -5])
        c.addStl(path + "8mm_finger.STL", 'tip2',  0xcc8833, [-5, -6, -5])

        c.addStl(path + "Basler.STL", "camera1", 0x222222, [-445,-24,-450,0,0,0])

        #c.addSphere("otool1", 0xff0000, 3)
        #c.addCylinder("otool1", 0x0000ff, 1, 600)

        c.addStl(path + "Finger_rack_small.STL", "rack", 0x888888, [0, 0, 0])

        multifinger_name = "multifinger_5.STL"
        multifinger_rack_name = "multifinger_rack.STL"
        tip_rack_name = "tip_rack.STL"
        tip_rack_fiducials_name = "tip_rack_fiducials.STL"
        tip_name = "tip_10mm.STL"

        if os.path.exists(os.path.join(local_path, multifinger_name)):
            c.addObject("multifinger", parent_name="base")
            c.addStl(path + multifinger_name, "multifinger", 0x888888, [-5, -6, -5])
            self.tips.append("multifinger")

        if os.path.exists(os.path.join(local_path, multifinger_rack_name)):
            c.addObject("multifinger_rack", parent_name="base")
            c.addStl(path + multifinger_rack_name, "multifinger_rack", 0x888888, [300, -195, 20])

        if os.path.exists(os.path.join(local_path, tip_rack_name)):
            c.addObject("tip_rack", parent_name="table")
            c.moveObject("tip_rack", [500, 200, 20, -math.pi / 2, -math.pi / 2, 0])
            c.addStl(path + tip_rack_name, "tip_rack", 0x888888, [0, 0, 0])

        if os.path.exists(os.path.join(local_path, tip_rack_fiducials_name)):
            c.addObject("tip_rack_fiducials", parent_name="table")
            c.moveObject("tip_rack_fiducials", [500, 200, 20, -math.pi / 2, -math.pi / 2, 0])
            c.addStl(path + tip_rack_fiducials_name, "tip_rack_fiducials", 0xffffff, [0, 0, 0])

        if os.path.exists(os.path.join(local_path, tip_name)):
            c.addObject("tip3", parent_name="base")
            c.addStl(path + tip_name, 'tip3', 0xcc8833, [-5, -6, -5])
            c.addObject("tip4", parent_name="base")
            c.addStl(path + tip_name, 'tip4', 0xcc8833, [-5, -6, -5])
            self.tips.append("tip3")
            self.tips.append("tip4")

        # set visualization kinematics function

        # Convert offset matrices to 1-D lists in JSON format.
        tool1_offset_json = json.dumps(self.kinematic.tool1_offset.A1.tolist())
        tool2_offset_json = json.dumps(self.kinematic.tool2_offset.A1.tolist())

        # Set tool offsets to simulator kinematics. Note that the offsets are only updated at server init.
        f = """
        function(joints)
            {
            var y = joints['y'];
            var x = joints['x'];
            var z = joints['z'];
            var a = -joints['azimuth'] / 180 * Math.PI
            var synchro = joints['separation'];
            var vc1 = joints["voicecoil1"];
            var vc2 = joints["voicecoil2"];
            
            var my = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, y, 0, 0, 0, 1];
            var mx = [1, 0, 0, x, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
            var mz = [1, 0, 0, 0, 0, 1, 0, -z, 0, 0, 1, 0, 0, 0, 0, 1];

            var ms1 = %s;
            var ms2 = %s;
            
            ms1[3] -= synchro * 0.5;
            ms2[3] += synchro * 0.5;

            vc1 = [1, 0, 0, 0, 0, 1, 0, -vc1, 0, 0, 1, 0, 0, 0, 0, 1];
            vc2 = [1, 0, 0, 0, 0, 1, 0, -vc2, 0, 0, 1, 0, 0, 0, 0, 1];

            var c = Math.cos(a);
            var s = Math.sin(a);
            var ma = [c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, 0, 0, 0, 1];
            
            r = { "oy":my, "ox2":mx, "oz2":mz, "oa2":ma, "tool1":ms1, "tool2":ms2, "ovoicecoil1":vc1, "ovoicecoil2": vc2 };
            console.log(r);
            return r;
            }
        """ % (tool1_offset_json, tool2_offset_json)

        c.set_kinematic_function(f)
        c.set_axes(__class__.axis)

    def attach_tip(self, tip_name, kinematic_name):
        c = self.connection

        # Parent new tip to robot z-axis.
        if tip_name in self.tips:
            c.moveObject(tip_name, [0,0,0,0,0,0], kinematic_name)

    def detach_tip(self, tip_name):
        c = self.connection

        # Reparent unattached tips to rack (could also be root).
        # The global tip positions are retained to allow configuring new tip rack positions.
        if tip_name in self.tips:
            c.reparent(tip_name, "base")

    def set_tip_slot_in(self, tip_name, slot_in):
        """
        Set tip slot-in position.
        :param tip_name: name of tip
        :param slot_in: slot-in position as list [x, y, z]
        :return:
        """

        if tip_name not in self.tips:
            return

        slot_in_sim = np.array(slot_in)

        self.slot_in_positions[tip_name] = slot_in_sim

        slot_in_sim = robotmath.transform_position(self.robot_to_base, slot_in)

        self.connection.reparent(tip_name, "base")
        self.connection.moveObject(tip_name, [slot_in_sim[0], slot_in_sim[1], slot_in_sim[2], 0, 0, 0])
