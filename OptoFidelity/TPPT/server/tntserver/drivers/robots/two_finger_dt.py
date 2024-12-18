"""
Robot driver for two-finger DT controller.
The controller implements API for running both DT robot and two-finger.
Communication with the box is via TCP/IP using XML formatted remote procedure calls.
"""
import xmlrpc.client
import sys
import os
sys.path.append(os.path.dirname(__file__))

import logging
import tntserver.robotmath as robotmath
import numpy as np
import math
from math import radians, degrees, sin, cos, atan2, acos
from http.client import RemoteDisconnected

log = logging.getLogger(__name__)

def to_floats(lst):
    return [float(a) for a in lst]

def diff_angle_from_frames(start, end):
    """
    2-finger tool's rotation is represented by the y-basis vector of a frame.
    Calculates signed angle difference from start frame to end frame.
    :param start: Frame where motion is started.
    :param end: Frame where motion will end.
    :return: Signed angle for 2-finger rotation.
    """
    y_start = start.A[0:2, 1]
    y_end = end.A[0:2, 1]

    y_start_len = np.linalg.norm(y_start)
    y_end_len = np.linalg.norm(y_end)

    d = np.dot(y_start, y_end) / (y_start_len * y_end_len)

    # Make sure d is in valid range for acos() in case of round-off errors.
    d = np.clip(d, -1.0, 1.0)

    # Compute the span angle of two vectors.
    # Note that this can be at most 180 degrees.
    angle = degrees(acos(d))

    # Use cross-product to determine sign of rotation angle.
    if y_start[0] * y_end[1] - y_start[1] * y_end[0] > 0:
        angle = -angle

    return angle

class XmlRPCClient:
    """
    XML RPC client is a wrapper/proxy class to call methods from xmlrpclib
    ServerProxy. This is needed to work out a concurrency problem of xmlrpclib:
    Concurrent requests causes the server to crash.

    As a solution ServerProxy is wrapped with a proxy class which create a
    new serverProxy for all requests.
    """

    def __init__(self, host='10.10.12.4', port=6842, thread_safe=True):
        self._host = host
        self._port = port
        self._thread_safe = thread_safe

        if not thread_safe:
            self._server = xmlrpc.client.ServerProxy("http://%s:%i" % (self._host, self._port))

    def __getattr__(self, name):
        """
        XmlRPCClient class is used as if it defined methods whose names correspond to 2-finger-dt API.
        For example, the API defines command "Robot_GoHome".
        To call this via XmlRPCClient:
        client = XmlRPCClient()
        client.Robot_GoHome() # This methods call translates into RPC command.
        :param name: Method name.
        :return: Function object that corresponds to RPC call.
        """

        # Define the function object to be returned.
        def xmlrpc_method(*args, **kwargs):
            # If connection reports error, retry forever.
            while True:
                try:
                    if self._thread_safe == True:
                        server = xmlrpc.client.ServerProxy("http://%s:%i" % (self._host, self._port))
                    else:
                        server = self._server

                    attr = getattr(server, name)

                    # Execute command to get the results
                    result = attr(*args, **kwargs)

                    return result
                except AttributeError as e:
                    log.error("XML RPC server has no such method -- {}".format(name))
                    raise e # Raise exception again to be handed by caller
                except (TimeoutError, RemoteDisconnected) as e:
                    # In case remote is disconnected, retry connection.
                    log.error(str(e))
                    log.warning("Retrying two-finger-dt RPC")


        return xmlrpc_method

def record(func):
    """
    Decorator for XmlRPCClientSimulator to record 2-finger-dt API calls.
    :param func: Function to decorate.
    """
    def wrapper(object, *args):
        """
        Decorator wrapper.
        :param object: Instance of XmlRPCClientSimulator.
        :param args: Arguments to func.
        :return: Decorated function.
        """
        # Put command to record.
        object.record_command(func.__name__, args)

        return func(object, *args)

    return wrapper


class XmlRPCClientSimulator:
    """
    Simple numeric simulator for two-finger XML RPC connection.
    Can be used to debug ideal robot movements by keeping track of
    position values and logging them.
    """
    def __init__(self, axes):
        self.joints = [0, 0, 0, 0, 0]
        self.axes = axes

        self.executed_commands = None

    def start_recording_commands(self):
        # Empty list starts new recording.
        self.executed_commands = []

    def stop_recording_commands(self):
        # None means that commands are not recorded.
        self.executed_commands = None

    def record_command(self, command, command_parameters):
        if self.executed_commands is not None:
            self.executed_commands.append((command, command_parameters))

    @record
    def Robot_Initialize(self, speed):
        return {"Command": "Robot_Initialize"}

    @record
    def Robot_GoHome(self, arg):
        self.joints[0] = self.axes["x"].max
        self.joints[1] = self.axes["y"].max
        self.joints[2] = self.axes["z"].min
        return {"Command": "Robot_GoHome"}

    @record
    def Version(self):
        return {"Status": "Ok"}

    @record
    def TwoFinger_FingerGoHome(self):
        self.joints[4] = 0
        return {"Command": "TwoFinger_FingerGoHome"}

    @record
    def TwoFinger_RotateGoHome(self):
        self.joints[3] = 0
        return {"Command": "TwoFinger_RotateGoHome"}

    @record
    def Robot_ChangeSpeed(self, speed):
        return {"Array": speed}

    @record
    def Robot_ChangeAcceleration(self, accel):
        return {"Array": accel}

    @record
    def Robot_SaveLocation(self, timeout=0):
        return {"Array": self.joints}

    @record
    def Robot_MoveToPosition(self, joints):
        self.joints[0:len(joints)] = joints
        log.info("Moved to: {}, {}, {}".format(joints[0], joints[1], joints[2]))
        return {"Array": joints}

    @record
    def Robot_Gesture(self, param):
        if param[0] == 0:  # Tap
            # Require tap xy-location and duration.
            assert len(param) >= 3
            self.joints[0:2] = param[1:3]
        elif param[0] == 3:  # Swipe
            assert len(param[1]) == 10

            # TODO: Not sure what the final position should be after swipe.
            self.joints[0:4] = param[5:9]
        else:
            assert False, "Gesture not supported"

        return {"Array": param}

    @record
    def TwoFinger_MoveFinger(self, dist):
        self.joints[4] += dist[0]
        log.info("Moved two-finger to: {}".format(self.joints[4]))
        return {"Command": "TwoFinger_MoveFinger"}

    @record
    def TwoFinger_FingerJumpTo(self, dist):
        self.joints[4] = dist[0]
        log.info("Moved two-finger to: {}".format(self.joints[4]))
        return {"Command": "TwoFinger_FingerJumpTo"}

    @record
    def TwoFinger_Rotate(self, angle):
        self.joints[3] += angle[0]
        log.info("Rotated two-finger to: {}".format(self.joints[3]))
        return {"Command": "TwoFinger_Rotate"}

    @record
    def TwoFinger_RotateJumpTo(self, angle):
        self.joints[3] = angle[0]
        log.info("Rotated two-finger to: {}".format(self.joints[3]))
        return {"Command": "TwoFinger_RotateJumpTo"}

    @record
    def TwoFinger_SaveLocation(self):
        return {"Array": self.joints[3:]}

    @record
    def TwoFinger_MoveSpeed(self, speed):
        return {"Command": "TwoFinger_MoveSpeed"}

    @record
    def TwoFinger_RotateSpeed(self, speed):
        return {"Command": "TwoFinger_RotateSpeed"}

class Axis:
    def __init__(self, _min, _max):
        # These limits are axis values.
        self.min = _min
        self.max = _max

    def clamp(self, value):
        return max(min(value, self.max), self.min)

class TwoFingerDT:
    """
    Two-finger DT robot driver.

    DT robot axes form a right-handed system where:
    - x-axis point to the left
    - y-axis points to the back
    - z-axis points down
    as seen when looking at robot "normally" from the front side.
    This means that (0,0,0) is at right-front-top.
    However, robot home position is at left-back-top (max_x,max_y,0).
    """

    def __init__(self, ip="10.10.12.4", port=6842, axis_limits=None, tf_rotate_speed=30, tf_move_speed=30,
                 thresholds=None, simulator=False, separation_offset=10.0, safe_distance=200.0):
        self.calibration = None
        self.use_calib_back_x = False
        self.use_calib_back_y = False

        # Define axes with limits.
        # Separation axis maximum of dev 2-finger was experimentally found to be 147 mm.
        if axis_limits is None:
            # TODO: These (at least xyz) should be read from controller as there is an API for that.
            self.axes = {
                "x": Axis(0, 600),
                "y": Axis(0, 500),
                "z": Axis(0, 100),
                "azimuth": Axis(-math.inf, math.inf),
                "separation": Axis(0, 147)
            }
        else:
            self.axes = {
                "x": Axis(axis_limits["x_min"], axis_limits["x_max"]),
                "y": Axis(axis_limits["y_min"], axis_limits["y_max"]),
                "z": Axis(axis_limits["z_min"], axis_limits["z_max"]),
                "azimuth": Axis(axis_limits.get("azimuth_min", -math.inf), axis_limits.get("azimuth_max", math.inf)),
                "separation": Axis(axis_limits.get("separation_min", 0), axis_limits.get("separation_max", 147))
            }

        self.simulator = simulator

        if self.simulator:
            self.client = XmlRPCClientSimulator(self.axes)
        else:
            self.client = XmlRPCClient(ip, port)

        log.info("Two-finger-DT robot communication established.")

        speed = 100

        # Distance from x and y axis limits where it is safe to rotate tool.
        self.safe_distance = safe_distance

        self.error = None

        # Angle that server sees when 2-finger is at home position.
        # 2-finger controller home position (controller's zero angle) is typically so that the tool points to +y in workspace.
        # If server wants home position to be +x axis direction in workspace, then home_angle should be -90 deg
        self.home_angle = -90.0

        # Default tool orientation in relation to robot base.
        # This is the final transformation in the forward kinematics chain to make the robot local z-axis point
        # "down" i.e. along negative robot base z-axis.
        self._tool_orientation = robotmath.xyz_euler_to_frame(0, 0, 0, 180, 0, 180)
        self._tool_orientation_I = self._tool_orientation.I

        # This offset is added to the separation axis value to get the
        # real world separation between the two fingers.
        # Must be greater than zero.
        self.separation_offset = separation_offset

        # Current target finger separation in mm.
        # Separation is controlled independently i.e. not part of frame based kinematics.
        self.separation = self.separation_offset

        # Transform from the axial finger to the moving finger.
        self.separation_transform = None
        self.separation_transform_I = None

        self.set_separation_transform(self.separation_offset)

        # Threshold values are used when comparing current position to target position.
        # Movement commands are time-consuming and should be avoided for insignificant movements.
        if thresholds is None:
            self.angle_threshold = 0.01
            self.position_threshold = 0.005
            self.separation_threshold = 0.1
        else:
            self.angle_threshold = thresholds["angle"]
            self.position_threshold = thresholds["position"]
            self.separation_threshold = thresholds["separation"]

        # Keep track of current angle where two-finger should be at.
        # This allows conversion from direction vector -> angle without ambiguity.
        self.current_angle = self.home_angle

        try:
            result = self.client.Robot_Initialize([speed])["Command"]

            if result != "Robot_Initialize":
                raise Exception("Robot initialization failed")
        except Exception as e:
            log.error(str(e))

        log.info("Two-finger-DT robot initialized.")

        #log.info(self.get_status())

        # Set some appropriate speed and acceleration.
        self.speed = 50
        self.acceleration = 200
        self.tf_move_speed = tf_move_speed
        self.tf_rotate_speed = tf_rotate_speed

        # Robot is homed at init.
        self.home()

    def set_separation_transform(self, separation):
        # Transform has 180 deg azimuthal rotation so that two-finger arm
        # has the same orientation in global frame regardless of which is the active finger
        # with fixed azimuth in kinematics frame.
        # This is crucial when changing tip to both fingers when the finger rack positioning has been
        # done with only one of the fingers.
        self.separation_transform = robotmath.xyz_euler_to_frame(separation, 0, 0, 0, 0, 180)
        self.separation_transform_I = self.separation_transform.I

    def get_status(self):
        status_str = self.client.Version()["Status"]

        return status_str

    def home(self):
        # First home xyz to make sure frame() works correctly for rotation homing sequence.
        self.home_xyz()
        self.tf_rotate_home()
        self.tf_finger_home()

        # Home xyz again. This is not actually necessary.
        self.home_xyz()

    def home_xyz(self):
        log.info("Homing xyz.")

        result = self.client.Robot_GoHome([1])["Command"]

    def tf_finger_home(self):
        """
        Moves fingers to home position. Fingers are as close each other as possible.
        After this command, next finger movement might start with jerk movement.
        Do not use this command in the middle of testing, use instead TwoFinger_MoveFinger([0])
        """

        log.info("Homing finger offset.")

        ret = self.client.TwoFinger_FingerGoHome()

        if ret["Command"] == "TwoFinger_Error":
            raise Exception("Two-finger homing failed!")

    def tf_rotate_home(self):
        """
        Moves fingers to home position.
        """

        log.info("Homing finger rotation.")

        self.current_angle = self.home_angle

        # Use identity matrix as tool frame when preparing to home rotation axis.
        tool_frame = robotmath.identity_frame()

        bounds = self.bounds(tool=tool_frame)

        # First move into position where rotation is safe.
        frame = self.frame(tool=tool_frame, kinematic_name="tool1")
        robotmath.set_frame_xyz(frame, bounds["x"][0] + 150, bounds["y"][0], bounds["z"][1])

        joints = self.frame_to_joints(frame, kinematic_name="tool1", tool_inv=tool_frame.I)
        ret = self.client.Robot_MoveToPosition(to_floats(list(joints[0:3])))["Array"]
        self._check_status(ret)

        ret = self.client.TwoFinger_RotateGoHome()

        if ret["Command"] == "TwoFinger_Error":
            raise Exception("Two-finger rotate homing failed!")

    @property
    def speed(self):
        return self._speed

    @speed.setter
    def speed(self, value):
        """
        :param value: Speed in mm/s.
        """
        self._speed = value
        result = self.client.Robot_ChangeSpeed([value])["Array"]

    @property
    def acceleration(self):
        raise Exception("Not implemented")

    @acceleration.setter
    def acceleration(self, value):
        """
        :param value: Acceleration in mm/s^2.
        """
        accel_time = self.speed / value

        # number of 7 ms steps to accelerate to current speed
        num_steps = accel_time / 0.007

        num_steps = max(num_steps, 15)  # Minimum recommended acl and acm is 15
        acl = num_steps
        acm = num_steps
        result = self.client.Robot_ChangeAcceleration([acl, acm])["Array"]

    def frame_to_joints(self, frame, kinematic_name, tool_inv):
        """
        Converts server frame to robot's joint values.
        Joints are given as list [x, y, z, angle, separation].
        Note that angle is computed from frame's y-basis vector so that
        it is in range (-180, 180). Thus angle -180 / 180 is ambiguous.
        """

        frame = frame * tool_inv * self._tool_orientation_I

        if kinematic_name == "tool1":
            # tool1 is on rotation axis
            pass
        elif kinematic_name == "tool2":
            frame = frame * self.separation_transform_I
        elif kinematic_name == "camera":
            # Camera does not rotate so remove rotation.
            x, y, z = robotmath.frame_to_xyz(frame)
            frame = robotmath.xyz_to_frame(x, y, z)
        else:
            raise Exception("Unrecognized kinematic name '{}'".format(kinematic_name))

        x, y, z = robotmath.frame_to_xyz(frame)

        y_basis = frame.A[0:2, 1]

        angle = degrees(atan2(y_basis[0], y_basis[1]))

        # Use the calibration data to translate the given
        if self.calibration is not None:
            position = self.calibration.translate(x=x, y=y, z=z, x_back=self.use_calib_back_x, y_back=self.use_calib_back_y)
            x, y, z = position

        # Each DT robot axis points to opposite direction compared to server frames.
        x *= -1
        y *= -1
        z *= -1

        if x < self.axes["x"].min or x > self.axes["x"].max:
            raise Exception("Violated x-axis limits!")

        if y < self.axes["y"].min or y > self.axes["y"].max:
            raise Exception("Violated y-axis limits!")

        if z < self.axes["z"].min or z > self.axes["z"].max:
            raise Exception("Violated z-axis limits!")

        # X, Y and Z must be within 0 and given max (max > 0)
        x = self.axes["x"].clamp(x)
        y = self.axes["y"].clamp(y)
        z = self.axes["z"].clamp(z)

        separation = max(self.separation - self.separation_offset, 0)

        return [x, y, z, angle, separation]

    def joints_to_frame(self, joints, kinematic_name, tool):
        """
        Converts robot joint values to server frame.
        """

        x, y, z = joints[0:3]

        if self.calibration is not None:
            x, y, z = self.calibration.back_translate(x=x, y=y, z=z,
                                          x_back=self.use_calib_back_x,
                                          y_back=self.use_calib_back_y)

        # X, Y and Z must be within 0 and given max (max > 0)
        x = self.axes["x"].clamp(x)
        y = self.axes["y"].clamp(y)
        z = self.axes["z"].clamp(z)

        # Each DT robot axis points to opposite direction compared to server frames.
        x *= -1
        y *= -1
        z *= -1

        frame = robotmath.xyz_euler_to_frame(x, y, z, 0, 0, -joints[3])

        if kinematic_name == "tool1":
            # tool1 is on rotation axis
            pass
        elif kinematic_name == "tool2":
            frame = frame * self.separation_transform
        elif kinematic_name == "camera":
            # Camera does not rotate.
            frame = robotmath.xyz_to_frame(x, y, z)
        else:
            raise Exception("Unrecognized kinematic name '{}'".format(kinematic_name))

        return frame * self._tool_orientation * tool

    def get_position(self, timeout=20.0):
        """
        Request robots current location coordinates i.e. joints values.
        """
        log.debug("Get position")

        res = self.client.Robot_SaveLocation(timeout)
        pos = res["Array"]
        if len(pos) < 2:
             log.warning(res)
        #     status = res["Status"]
        #     log.error("Robot failed to query position. %s" % (status))
        #     raise Exception("Robot failed to query position")

        # Set current rotation to be the current ideal angle to avoid drifting.
        if len(pos) > 3:
            log.info("Rotation: {}".format(pos[3]))
            pos[3] = self.current_angle

        return pos

    def get_joint_positions(self):
        """
        Get joint positions in a dictionary format
        :return: joint positions in a dictionary
        """
        pos = self.get_position()
        joint_positions = {}
        joints = ["x", "y", "z", "azimuth", "separation"]
        # The number of returned positions might vary
        for i, value in enumerate(pos):
            joint_positions[joints[i]] = value
        return joint_positions



    def _check_status(self, joint_values):
        """
        Check that movement was succesfull by comparing returned position to actual position.
        After unsuccesfull movement returned position is [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        """

        if not joint_values:
            raise Exception("Robot movement error!")
        elif joint_values[:3] == [0.0, 0.0, 0.0]: #TODO: this does not seem correct

            if self.get_position(2)[:3] != joint_values[:3]:
                raise Exception("Robot movement error!")

    def move(self, frame, tool, kinematic_name):
        """
        Moves the robot head into absolute coordinates given as a parameter array.
        Movement is performed as a linear move. U coordinate is optional.
        :param frame: Effector frame.
        X-coordinate [mm], Y-coordinate [mm], Z-coordinate [mm], U-rotation [deg] or
        X-coordinate [mm], Y-coordinate [mm], Z-coordinate [mm]
        """

        joints = self.frame_to_joints(frame, kinematic_name=kinematic_name, tool_inv=tool.I)

        current_joints = self.get_position()
        current_frame = self.joints_to_frame(current_joints, kinematic_name=kinematic_name, tool=tool)

        # Compute angle difference between current frame and frame to move to.
        diff_angle = diff_angle_from_frames(current_frame, frame)

        # Rotate and move fingers before xyz-movement.
        # Angle seems to have no effect if passed down to MoveToPosition.
        # These two-finger calls are very slow and should be avoided if possible.
        if abs(diff_angle) > self.angle_threshold:
            # Use relative rotation from current position to avoid angular ambiguity in frame->angle conversion.
            self.current_angle += diff_angle
            self.tf_rotate_abs(self.current_angle)

        if abs(joints[4] - current_joints[4]) > self.separation_threshold:
            self.tf_move_finger_abs(joints[4])

        if abs(joints[0] - current_joints[0]) > self.position_threshold or \
                abs(joints[1] - current_joints[1]) > self.position_threshold \
                or abs(joints[2] - current_joints[2]) > self.position_threshold:
            ret = self.client.Robot_MoveToPosition(to_floats(list(joints[0:3])))["Array"]
            self._check_status(ret)

        # TwoFinger_Robot_SyncMove is much faster than separate commands and seems to work ok.
        #ret = self.client.TwoFinger_Robot_SyncMove(to_floats([joints[3], joints[4], joints[0], joints[1], joints[2], self._speed]))["Array"]
        #self._check_status(ret)

    def tap(self, frame, tool, kinematic_name, duration=0.0):
        """
        Do tap gesture. Moves head in z-direction to given position and
        back.
        :param frame: Effector frame.
        :param duration: Tap duration in seconds.
        """

        joints = self.frame_to_joints(frame, kinematic_name=kinematic_name, tool_inv=tool.I)

        ret = self.client.Robot_Gesture([0.0, float(joints[2]), float(duration)])["Array"]
        self._check_status(ret)

    def swipe(self, start, end, radius, tool, kinematic_name):
        """
        Do swipe gesture.
        :param start: Effector frame where robot starts to accelerate towards swipe height.
        :param end: Effector frame at the end of complete swipe after deceleration to rest.
        :param radius: Radius of acceleration arc. Robot moves this distance down along z from start_frame.
        :return:
        """

        tool_inv = tool.I

        start_joints = self.frame_to_joints(start, kinematic_name=kinematic_name, tool_inv=tool_inv)
        end_joints = self.frame_to_joints(end, kinematic_name=kinematic_name, tool_inv=tool_inv)

        # Absolute z-joint position during the actual swipe after acceleration over the arc.
        swipe_z = start_joints[2] + radius

        ret = self.client.Robot_Gesture([3.0, to_floats(start_joints[0:4]) + to_floats(end_joints[0:4]) + [float(radius), float(swipe_z)]])["Array"]
        self._check_status(ret)

    def frame(self, tool, kinematic_name):
        """
        Retrieves actual joint values from controller and computes server robot frame.
        :return: Robot frame.
        """
        pos = self.get_position()

        frame = self.joints_to_frame(pos, kinematic_name=kinematic_name, tool=tool)

        return frame

    def bounds(self, tool, kinematic_name=None):

        # Shrink bounds a little bit to avoid hitting controller limits due to e.g. numerical inaccuracy.
        margin = 1.0

        bounds_dict = {
            'x': [-self.axes["x"].max + margin, -self.axes["x"].min - margin],
            'y': [-self.axes["y"].max + margin, -self.axes["y"].min - margin],
            'z': [-self.axes["z"].max + margin, -self.axes["z"].min - margin]
        }

        # Take tool into account in maximum effector z coordinate.
        x, y, z = robotmath.frame_to_xyz(tool)

        bounds_dict['z'][1] -= z

        return bounds_dict

    def tf_move_finger_rel(self, distance):
        """
        Moves the finger by a number of millimeters from last position.
        """
        ret = self.client.TwoFinger_MoveFinger([float(distance)])
        if ret["Command"] == "TwoFinger_Error":
            raise Exception("Could not move fingers by relative distance")

        pos = self.get_position()

        self.set_separation_transform(pos[4] + self.separation_offset)

    def tf_move_finger_abs(self, distance):
        """
        Moves finger a number of millimeters from home position.
        """
        ret = self.client.TwoFinger_FingerJumpTo([float(distance)])
        if ret["Command"] == "TwoFinger_Error":
            raise Exception("Could not move fingers to absolute position")

        pos = self.get_position()

        self.separation = pos[4] + self.separation_offset

        self.set_separation_transform(self.separation)

    def tf_rotate_rel(self, degrees):
        """
        Rotates the finger by a number of degrees from last position.
        """
        ret = self.client.TwoFinger_Rotate([float(degrees)])
        if ret["Command"] == "TwoFinger_Error":
            raise Exception("Could not rotate finger by relative angle")

        # Update current angle if command was successful.
        self.current_angle += degrees

    def tf_rotate_abs(self, degrees):
        """
        Rotates finger a number of degrees from home position.
        """
        ret = self.client.TwoFinger_RotateJumpTo([float(degrees - self.home_angle)])
        if ret["Command"] == "TwoFinger_Error":
            raise Exception("Could not rotate finger to absolute angle")

        # Update current angle if command was successful.
        self.current_angle = degrees

    def tf_get_position(self):
        """
        Request two finger current location coordinates.
        :return: [rotation_angle, finger_position]
        """
        return self.client.TwoFinger_SaveLocation()["Array"]

    @property
    def tf_move_speed(self):
        raise Exception("Not implemented")

    @tf_move_speed.setter
    def tf_move_speed(self, speed):
        """
        Finger movement  speed in mm/s (Range 1 - 70 mm/s).
        """
        ret = self.client.TwoFinger_MoveSpeed([speed])["Command"]

    @property
    def tf_rotate_speed(self):
        raise Exception("Not implemented")

    @tf_rotate_speed.setter
    def tf_rotate_speed(self, speed):
        """
        Finger rotation  speed in deg/s (Range 5 - 180 deg/s).
        """
        ret = self.client.TwoFinger_RotateSpeed([speed])["Command"]

    def set_finger_separation(self, distance):
        """
        Set finger separation. This will move the finger to position where
        the two finger centers are given distance apart.
        :param distance: Absolute distance in mm.
        """

        self.tf_move_finger_abs(max(distance - self.separation_offset, 0))

    def get_finger_separation(self):
        return self.separation

    def get_finger_separation_limits(self):
        """
        Get minimum and maximum limits of finger separation if robot has such properties.
        These are not the limits of the axis but rather the limits of axis-to-axis finger distances.
        Usually at axis position 0 fingers are at certain non-zero axis-to-axis home separation.
        :return: Minimum and maximum limits.
        """
        # Spec limits are joint limits. Add home separation to transform to finger axis-to-axis separation limits.
        min_limit = self.axes["separation"].min + self.separation_offset
        max_limit = self.axes["separation"].max + self.separation_offset

        # Decrease limit range by small margin to make sure robot can actually be commanded to given
        # values in case there is some round-off error.
        margin = 0.001
        min_limit += margin
        max_limit -= margin

        return [min_limit, max_limit]


if __name__ == "__main__":
    log.setLevel(logging.INFO)
    dt = TwoFingerDT()
    dt.move([10, 0, 0])
    log.info("Done")

