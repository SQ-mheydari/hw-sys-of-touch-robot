import numpy as np


"""
Simulator for HMDIQ 6-axis

The real robot has two tools
    - Camera
    - Confocal sensor
    
Has 6 axis to move DUT under the tools, in this order:
    x      (looking from above, moves DUT SouthEast)
    y      (looking from above, moves DUT NorthEast)
    z      (looking from above, moves DUT towards the eye)
    yaw    (looking from above, rotates DUT clockwise)
    pitch  (looking from right side, rotates DUT clockwise)
    roll   (looking from front, rotates DUT counter-clockwise)
    
This simulator supports camera with name "Camera1"
This simulator supports set_camera_mount_z -function which offsets camera z-mount position.

The real robot has H-axis x/y movement, simulator has traditional x/y axes because the visuals are moving that way.
This is compensated in the javascript kinematic function. 
    
"""


# noinspection PyPep8Naming
class Simulator_hmdiq:
    name = "hmdiq"
    title = "HMDIQ 6axis"
    axis = \
        {
            1:
                {
                    'alias': 'x',
                    'limits': (-1000, 1000)
                },
            2:
                {
                    'alias': 'y',
                    'limits': (-1000, 1000)
                },
            3:
                {
                    'alias': 'z',
                    'limits': (-1000, 1000)
                },
            4:
                {
                    'alias': 'yaw',
                    'limits': (-90, 90)
                },
            5:
                {
                    'alias': 'pitch',
                    'limits': (-90, 90)
                },
            6:
                {
                    'alias': 'roll',
                    'limits': (-90, 90)
                }
        }

    def __init__(self, connection, kinematic):
        self.connection = connection
        self.kinematic = kinematic

    def create_model(self):

        #
        # Threejs library is strongly typed as right-handed coordinate system
        # If coordinates are changed to left-handed ( as in TnT ), objects will
        # show as inside-out since backface culling works inverted.
        # The workaround in this simulator is to change the world to left-handed
        # but revert the change at the end of each object tree for the object itself
        # Right-handed to left handed coordinate system is done by inverting z-axis.
        #
        invert_z_axis = np.array([[1, 0, 0, 0],
                                  [0, 1, 0, 0],
                                  [0, 0, -1, 0],
                                  [0, 0, 0, 1]])

        c = self.connection

        # clear everything
        c.resetModel()

        # create object tree
        c.addObject("base")
        c.addObject("origo")
        c.setObjectFrame("origo", invert_z_axis)

        path = "http://127.0.0.1:8010/model/hmdiq/"

        # kinematic chain + visual objects
        objs = [
            ["assem6sw-00006038.stl",           "origo",    0x202025, [0, 0, 0], [190-40, 0, 162]],
            ["copyofassem13sw-00006038.stl",    "y",        0x202520, [0, 0, 0], [190, 0, 162]],
            ["copyofassem12sw-00006038.stl",    "x",        0x252020, [0, 0, 0], [0, 0, 162]],
            [None,                              "z",        0x252020, [0, 0, 0], [0, 0, 0]],
            ["assem4sw-00006038.stl",           "a",        0x101010, [0, 0, 0], [0, 0, 0]],
            ["Assem3SW-00006038rev2.stl",       "b",        0x101510, [0, 0, 103], [0, 0, 0]],
            ["assem2sw-00006038osa2rev2.stl",   "c",        0x151010, [0, 0, 0], [0, 0, -10]],
            ["last_stage.stl",                  "d",        0x404040, [0, 61, 10], [112, 4, -25, 0, -90, -90]],
            [None, "mount", 0x000000, [0, 0, -14], [0, 0, 0, 0, 0, 0]],
        ]

        # This STL file is under customer NDA, therefore not included in git repository
        objs.append(["DUT_w_Cradle.stl", "simulation_DUT", 0x424242, [98, -5.5, -26], [0, 0, 0, 90, 0, 180]])

        # This STL file is not included in git repository
        objs.append(["SW-00007558_kalibraattori.stl", "calibrator", 0x7d707d, [-107.75, -33.25, 14], [0, 0, 0, 180, 0, 90]])

        parent_name = "origo"
        for filename, name, color, offset, model_offset in objs:
            obj_name = name + "_obj"
            mnt_name = name + "_mnt"

            offset = offset + [0, 0, 0, 0, 0, 0][len(offset):]

            # offset frame
            c.addObject(obj_name, parent_name)
            c.moveObject(obj_name, offset)

            # transformable object
            c.addObject(name, obj_name)

            # object for 3d model
            c.addObject(mnt_name, name)
            c.setObjectFrame(mnt_name, invert_z_axis)
            if filename:
                c.addStl(path + filename, mnt_name, color, model_offset)

            parent_name = name

        c.addObject("fiducial_origo", "simulation_DUT")
        c.addObject("fiducial_dot_1", "fiducial_origo")
        c.addObject("fiducial_dot_2", "fiducial_origo")
        c.addObject("fiducial_dot_3", "fiducial_origo")

        c.addCylinder("fiducial_dot_1", 0x2bff2b, 1, 0.2)
        c.addCylinder("fiducial_dot_2", 0x2bff2b, 1, 0.2)
        c.addCylinder("fiducial_dot_3", 0x2bff2b, 1, 0.2)
        c.addCylinder("fiducial_origo", 0xff452b, 1, 0.2)

        c.setObjectFrame("fiducial_dot_1", invert_z_axis)
        c.setObjectFrame("fiducial_dot_2", invert_z_axis)
        c.setObjectFrame("fiducial_dot_3", invert_z_axis)
        c.setObjectFrame("fiducial_origo", invert_z_axis)

        # Create circular pattern of fiducial "dots" around the origin. Measurements are from mechanical
        # drawing.
        c.moveObject("fiducial_origo", [-52.25, -53, 89, 0, 0, 0])  # angle in radians
        c.moveObject("fiducial_dot_1", [0, 27.5, -3, 0, 0, 0])
        c.moveObject("fiducial_dot_2", [19.269, -11.125, -2.1, 0, 0, 0])
        c.moveObject("fiducial_dot_3", [-19.269, -11.125, -2.1, 0, 0, 0])

        # Add green dot inside calibrator block
        c.addObject("calibrator_origo", "calibrator")
        c.addObject("calibrator_origo_dot", "calibrator_origo")
        c.addCylinder("calibrator_origo_dot", 0x2bff2b, 0.5, 0.2)
        c.setObjectFrame("calibrator_origo_dot", invert_z_axis)
        c.moveObject("calibrator_origo_dot", [-35.45, -20.8, 25.5, 0, 0, 0])

        # camera 3d-object not in same orientation as other objects
        c.addObject("camera_mount", parent_name="origo")
        c.addObject("camera_obj", "camera_mount")
        c.setObjectFrame("camera_obj", invert_z_axis)
        c.addStl(path + "assem5sw-00006038_no_CFS.stl", "camera_obj", 0x222222, [0, 0, 0, 180, 180, 0])

        # move camera mount point to an arbitrary position
        # this is approximately right, but only a guess.
        c.moveObject("camera_mount", [150, 0, 350, 0, 0, 0])

        # move camera lens to correct position and orientation
        c.addObject("camera_lens", parent_name="camera_obj")
        c.moveObject("camera_lens", [0, 96, 80, np.pi, 0, 0*np.pi])

        # add camera to camera lens
        c.addCamera("Camera1", "camera_lens", 120, 20)

        # Positioning camera
        c.addObject("positioning_camera_mount", parent_name="origo")
        c.addObject("positioning_camera", "positioning_camera_mount")
        c.setObjectFrame("positioning_camera", invert_z_axis)
        c.moveObject("positioning_camera_mount", [224+24.75, 50, 307+0.25, 0, 0, 0])

        c.addStl(path + "CFS_ja_Cam_assy.stl", "positioning_camera", 0x222222, [2, 97, -215, 90, 0, 0])

        # move camera lens to correct position and orientation
        c.addObject("pos_camera_lens", parent_name="positioning_camera")
        c.moveObject("pos_camera_lens", [42.5, 69, -11, np.pi, 0, 0*np.pi])

        # add camera to camera lens
        c.addCamera("Basler_camera", "pos_camera_lens", 120, 20)


        f = """
        function(joints)
            {
            var xy1 = joints['x'];
            var xy2 = joints['y'];
            var z = joints['z'];
            var ra = joints['yaw'] * Math.PI / 180;
            var rb = joints['pitch'] * Math.PI / 180;
            var rc = joints['roll'] * Math.PI / 180;
            
            var u = 0.7071067811865476;
            var x = (xy1 - xy2) * u;
            var y = (xy1 + xy2) * u;
            
            var mx = [1,0,0,x, 0,1,0,0, 0,0,1,0, 0,0,0,1];
            var my = [1,0,0,0, 0,1,0,y, 0,0,1,0, 0,0,0,1];
            var mz = [1,0,0,0, 0,1,0,0, 0,0,1,z, 0,0,0,1];
    
            // rotate around z-axis
            var c = Math.cos(ra);
            var s = Math.sin(ra);
            var ma = [c, -s, 0, 0,  s, c, 0, 0,  0, 0, 1, 0,  0, 0, 0, 1];
    
            // rotate around x-axis
            var c = Math.cos(rb);
            var s = Math.sin(rb);
            var mb = [1, 0, 0, 0,  0, c, -s, 0,  0, s, c, 0,  0, 0, 0, 1];
    
            // rotate around y-axis
            var c = Math.cos(rc);
            var s = Math.sin(rc);
            var mc = [c, 0, -s, 0,  0, 1, 0, 0,  s, 0, c, 0,  0, 0, 0, 1];
            
            r = {"x":mx, "y":my, "z":mz, 'b': ma, 'c': mb, 'd': mc};
            return r;
            }
        """
        c.set_kinematic_function(f)
        c.set_axes(__class__.axis)

    def set_camera_mount_z(self, z: float):
        c = self.connection
        c.moveObject("camera_mount", [150, 0, 350 + z, 0, 0, 0])


if __name__ == '''__main__''':
    """
    Stand-alone test.
    Starts file server and simulator.
    Uses buffered move to robot axis.
    
    One could use this test for kinematics testing without the whole TnT server.
    
    """


    def _start_simulator():
        from tntserver.Nodes.NodeFileServer import NodeFileServer
        from tntserver.Nodes.NodeSimulator import NodeSimulator
        from tntserver.drivers.robots.goldenmov.simulator.comm import WebGoldenSimulatorComm

        fileserver = NodeFileServer()
        # noinspection PyProtectedMember
        fileserver._init("web", 8010)

        simulator = NodeSimulator()
        # noinspection PyProtectedMember
        simulator._init()

        connection = WebGoldenSimulatorComm("127.0.0.1", 4001, Simulator_hmdiq.axis)
        model = Simulator_hmdiq(connection, None)
        model.create_model()


    def _move_robot():
        import time
        from tntserver.drivers.robots.goldenmov.simulator.comm import WebGoldenSimulatorComm
        simu = WebGoldenSimulatorComm("127.0.0.1", 4001, axis_info=Simulator_hmdiq.axis)

        # move axes forever with the following ranges:
        axis_ranges = {
            "x":        [150, 151],
            "y":        [-221, -220],
            "z":        [29, 30],
            "yaw":      [-30, 30],
            "pitch":    [-10, 10],
            "roll":     [-30, 30],
            }

        counter = 0

        # loop the move test forever
        while True:

            def move_buffered():
                move_buffer = {'x': [0],
                               'y': [0],
                               'z': [0],
                               'a': [0],
                               'b': [0],
                               'c': [0]}

                for axis_name in axis_ranges:
                    vmin, vmax = axis_ranges[axis_name]
                    position = 0.5 * (np.sin(counter) + 1.0) * (vmax - vmin) + vmin
                    if axis_name in ["yaw", "pitch", "roll"]:
                        position = np.radians(position)
                    move_buffer[axis_name] = [position]

                simu.move_buffered(move_buffer)

            #move_buffered()

            time.sleep(1.0 / 30.0)
            counter += np.pi / 30

    _start_simulator()
    _move_robot()
