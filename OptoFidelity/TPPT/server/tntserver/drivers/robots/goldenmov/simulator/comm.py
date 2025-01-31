import json
import socket
import time
import base64
import cv2
import numpy as np
from copy import copy
from threading import Lock
from collections import OrderedDict
from tntserver.drivers.robots import sm_regs


class PositionLimits:
    def __init__(self, min, max):
        self.min = min
        self.max = max


class ScalingFactors:
    """
    This class creates a proper struct from given scaling factors.
    """
    def __init__(self, acceleration, posToDevice, posFromDevice, velocity):
        self.acceleration = acceleration
        self.posToDevice = posToDevice
        self.posFromDevice = posFromDevice
        self.velocity = velocity


class SimulatorAxisSpec:
    def __init__(self, acceleration=1, posToDevice=1, posFromDevice=1, velocity=1):
        self.address = None
        self.alias = None
        self.homing_priority = None
        self.inverted = None
        self.max_acceleration = None
        self.max_velocity = None
        self.position_limits = None
        self.position_limits = PositionLimits(0, 0)
        self.scaling_factors = ScalingFactors(acceleration, posToDevice, posFromDevice, velocity)


class ForceAxisSimulator:
    """
    Simulator for axis that has force firmware for Optostandard force.
    Simulates taring and surface seek procedures.
    """
    def __init__(self):
        self._tare_enabled = False
        self._tare_success = False
        self._tare_start = 0
        self._seek_surface_enabled = False
        self._seek_surface_start = 0

    def set_axis_parameter(self, register, value):
        if register == sm_regs.SMP_FORCE_MODE:
            if value == sm_regs.FORCE_MODE_TARE:
                self._tare_enabled = True
                self._tare_success = False
                self._tare_start = time.time()
            elif value == sm_regs.FORCE_MODE_TOUCH_PROBE_CTRL:
                self._seek_surface_enabled = True
                self._seek_surface_start = time.time()
            else:
                self._tare_enabled = False
                self._seek_surface_enabled = False

    def get_axis_parameter(self, param):
        if param == sm_regs.SMP_FORCE_FUNCTIONS_STATUS:
            status = 0

            if self._tare_enabled:
                if time.time() - self._tare_start < 0.2:
                    status |= 1 << sm_regs.FFS_TARE_BUSY
                else:
                    self._tare_success = True

            if self._tare_success:
                status |= 1 << sm_regs.FFS_TARE_SUCCESS

            if self._seek_surface_enabled:
                if time.time() - self._seek_surface_start > 0.2:
                    status |= 1 << sm_regs.FFS_TOUCH_PROBE_SUCCESS

            return status

        return None


class SimulatorCommBase:
    """
    Base class for robot simulators.
    """
    def __init__(self, axis_info):
        self._buffer = ""

        addresses = []
        aliases = []
        axis_position_limits = []

        self.move_ready_callback = None

        # Simulators for special type of axes such as force.
        self._axis_simulators = {}

        for address in sorted(axis_info):
            a = axis_info[address]
            alias = a['alias']
            limits = a['limits']
            limits = PositionLimits(limits[0], limits[1])

            addresses.append(address)
            aliases.append(alias)
            axis_position_limits.append(limits)

            if a.get("force_support", False):
                self._axis_simulators[alias] = ForceAxisSimulator()

        self.axis_specs = self.create_axis_specs(addresses, aliases, axis_position_limits)
        self.force_value = 0


    def axis_address_to_alias(self, address):
        for alias, spec in self.axis_specs.items():
            if spec.address == address:
                return alias

    def create_axis_specs(self, addresses, aliases, axis_position_limits):
        axis_specs = OrderedDict()
        for address, alias, position_limits in zip(addresses, aliases, axis_position_limits):
            a = SimulatorAxisSpec()
            a.address = address
            a.alias = alias
            a.position_limits = position_limits
            axis_specs[a.alias] = a
        return axis_specs

    def register_move_ready_callback(self, callback):
        self.move_ready_callback = callback

    def get_axis_specs(self):
        return list(self.axis_specs.values())

    def clear_errors(self):
        pass

    def get_errors(self):
        return []

    def tare(self):
        pass

    def remove_axis(self, axis):
        pass

    def get_force(self, *params):
        return self.force_value

    def get_executed_positions(self):
        return []

    def wait(self, milliseconds):
        time.sleep(milliseconds / 1000)

    def disable_axes(self, a):
        pass

    def restore_axis_configuration(self, axis=None):
        pass

    def set_axis_parameter(self, axis, register, value):
        """
        Sets value to Simplemotion register address.
        :param axis: Axis name (needed for compatibility reasons).
        :param register: Register address.
        :param value: Parameter value to write.
        :return: None.
        """
        setattr(self.axis_specs[axis], str(register), value)

        axis_simulator = self._axis_simulators.get(axis, None)

        if axis_simulator is not None:
            axis_simulator.set_axis_parameter(register, value)

    def limit_axis_speeds(self, speeds):
        pass

    def limit_axis_accelerations(self, accelerations):
        pass

    def clear_axis_limits(self):
        pass

    def read_axis_parameter(self, axis, parameter):
        return self.get_axis_parameter(axis=axis, param=parameter)

    def get_axis_parameter(self, axis, param):
        """
        Returns Simplemotion parameter value, if it has been set.
        :param axis: Axis name (needed for compatibility reasons)
        :param param: Parameter address to read.
        :return: Parameter value if it has been written earlier, otherwise 1.
        """

        axis_simulator = self._axis_simulators.get(axis, None)

        if axis_simulator is not None:
            value = axis_simulator.get_axis_parameter(param)

            # If force axis simulator was able to handle the parameter, return that value.
            if value is not None:
                return value

        if hasattr(self.axis_specs[axis], str(param)):
            return int(getattr(self.axis_specs[axis], str(param)))
        else:
            return int(1)

    def discover_axis(self, address, axis_alias):
        """
        Calls discover_axis of optomotion and gathers each optomotion (Simplemotion) level axis specs to a dict.
        :param address: Axis address to discover.
        :param axis_alias: Axis alias.
        :return: None.
        """
        a = SimulatorAxisSpec()
        a.address = address
        a.alias = axis_alias
        a.position_limits = None
        self.axis_specs[a.alias] = a

    def get_scaled_axis_setpoint(self, axis_alias):
        raise NotImplementedError


class WebGoldenSimulatorComm(SimulatorCommBase):
    """
    Robot simulator that runs a socket based web backend.
    Browser visualizes the robot geometry and motion in WebGL object.
    """

    def __init__(self, host, port, axis_info):
        super().__init__(axis_info)

        self.host = host
        self.port = port
        self.lock = Lock()
        self.move_ready_callback = None

        retries = 10
        while True:
            try:
                self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.s.connect((host, port))
                break
            except:
                self.s.close()

                print("SimulatorComm could not connect to port {}, retries left {}".format(port, retries))
                time.sleep(1)

        self._buffer = ""

    def set_device_parameter(self, address: int, param: int, value: int) -> None:
        """
        Used to test set_device_parameter API with simulator
        :param bus_address:
        :param parameter:
        :param value:
        :return: None
        """
        return None

    def register_move_ready_callback(self, callback):
        self.move_ready_callback = callback

    def send_and_receive(self, msg):
        with self.lock:
            msg += "\n"
            data = msg.encode("ascii")
            retries = 10
            while self.s._closed and retries > 0:
                self.s.connect((self.host, self.port))
                time.sleep(1)
                retries -= 1

            self.s.sendall(data)

            data = self.recv()
            if data == 'ok':
                return data

            self.recv()
            return data

    def recv(self):
        while "\n" not in self._buffer:
            data = self.s.recv(100000)
            self._buffer += data.decode("ascii")

        messages = self._buffer.split("\n")
        data = messages[0]
        self._buffer = "\n".join(messages[1:])
        return data

    def is_busy(self):
        r = self.send_and_receive("busy")
        r = json.loads(r)
        return r

    def home(self):
        f = {axis: 0 for axis in self.axis_specs.keys()}
        self.move_absolute(f)

    def get_position(self):
        r = self.send_and_receive("pos")
        p = json.loads(r)

        # If simulator pose is empty, assume zeros
        for key in self.get_axis_specs():
            if key.alias not in p:
                p[key.alias] = 0

        return p

    def get_scaled_axis_setpoint(self, axis_alias):
        """
        :param axis_alias:
        :return:
        """
        pos = self.get_position()
        return pos[axis_alias]

    def move_buffered(self, buffer):
        # lists are not lists anymore but numpy arrays
        # after axis validation and scaling

        buffer2 = {}
        for axisname in buffer:
            axisdata = buffer[axisname]
            lst = [float(v) for v in axisdata]
            buffer2[axisname] = lst

        frames = json.dumps(buffer2)
        self.send_and_receive("mov " + frames)

    def get_axis_spec(self, *args, **kwargs):
        """
        Required for robot node init
        opto_std_force in __init__ calls self._com.get_axis_spec(self._axis)
        :param args:
        :param kwargs:
        :return: AxisSpec instance
        """
        spec = SimulatorAxisSpec()
        return spec

    def get_photo(self, camera_name):
        """
        Gets a photo from a named camera on simulator
        :param camera_name: name of the camera
        :return:
        """
        p = json.dumps({"name": camera_name})
        urlstring = self.send_and_receive("photo " + p)

        # remove header 'data:image/jpeg;base64,'
        base64_str = urlstring[23:]
        imgdata = base64.b64decode(base64_str)
        img_np = np.frombuffer(imgdata, dtype='uint8')
        image = cv2.imdecode(img_np, 1)
        return image

    def resetModel(self):
        self.send_and_receive("reset_model")

    def addObject(self, name, parent_name="root"):
        """
        Adds a node to object tree
        :param name: name for the node
        :param parent_name: (optional) parent node name
        :return: None
        """
        p = json.dumps({"name": name, "parent_name": parent_name})
        self.send_and_receive("add_object " + p)

    def removeObject(self, name):
        p = json.dumps({"name": name})
        self.send_and_receive("remove_object " + p)


    def moveObject(self, name, coordinates, parent=None):
        """
        moves object to given coordinates
        :param name: object name
        :param coordinates: list of coordinates, [x, y, z, a, b, c]
        :param parent: Optional new parent object's name
        :return: None
        """
        params = {"name": name, "coordinates": coordinates}
        if parent is not None:
            params['parent'] = parent

        p = json.dumps(params)
        self.send_and_receive("move_object " + p)

    def reparent(self, name, new_parent):
        """
        Change object parent while maintaining object's global transform.
        :param name: object name
        :param new_parent: name of new parent for the object
        :return: None
        """
        params = {"name": name, "new_parent": new_parent}

        p = json.dumps(params)
        self.send_and_receive("reparent " + p)

    def setObjectFrame(self, name: str, frame: np.matrix):
        """
        Sets the object's transformation matrix
        :param name: object name
        :param frame: 4x4 matrix
        :return: None
        """
        params = {"name": name, "frame": frame.flatten().tolist()}
        p = json.dumps(params)
        self.send_and_receive("set_object_frame " + p)


    def addBox(self, parent_name, color, size, texture=None):
        """

        :param parent_name: parent object name as string
        :param color: 24bit color value; like 0xff0000
        :param size: integer, like 10
        :param texture: texture
        :return: None
        """

        p = json.dumps({"parent_name": parent_name, "color": color, "size": size, "texture": texture})
        self.send_and_receive("add_box " + p)

    def addSphere(self, parent_name, color, radius):
        """

        :param parent_name: parent object name as string
        :param color: 24bit color value; like 0xff0000
        :param radius: integer, like 10
        :return: None
        """
        p = json.dumps({"parent_name": parent_name, "color": color, "radius": radius})
        self.send_and_receive("add_sphere " + p)

    def addCylinder(self, parent_name, color, radius, height):
        """

        :param parent_name: parent object name as string
        :param color: 24bit color value; like 0xff0000
        :param radius: integer, like 10
        :param height: integer, like 10
        :return: None
        """
        p = json.dumps({"parent_name": parent_name, "color": color, "radius": radius, "height": height})
        self.send_and_receive("add_cylinder " + p)

    def addLine(self, parent_name, p0, p1, color):
        """

        :param parent_name: parent object name as string
        :param p0: first point xyz array; [ x, y, z ]
        :param p1: second point xyz array; [ x, y, z ]
        :param color: 24bit color value; like 0xff0000
        :return: None
        """
        p = json.dumps({"parent_name": parent_name, "color": color, "p0": p0, "p1": p1})
        self.send_and_receive("add_line " + p)

    def addStl(self, url, parent_name, color, offset):
        """

        :param url: url for stl model
        :param parent_name: parent object name as string
        :param color: 24bit color value; like 0xff0000
        :param offset: array of three values [x, y, z]
        :return: None
        """
        p = json.dumps({"url": url, "parent_name": parent_name, "color": color, "offset": offset})
        self.send_and_receive("add_stl " + p)

    def addMesh(self, parent_name, x_list, y_list, z_list, u_list, v_list):
        x = x_list if isinstance(x_list, list) else [[float(v) for v in a] for a in x_list]
        y = y_list if isinstance(y_list, list) else [[float(v) for v in a] for a in y_list]
        z = z_list if isinstance(z_list, list) else [[float(v) for v in a] for a in z_list]
        u = u_list if isinstance(u_list, list) else [[float(v) for v in a] for a in u_list]
        v = v_list if isinstance(v_list, list) else [[float(v) for v in a] for a in v_list]
        p = json.dumps({"parent_name": parent_name, "x": x, "y": y, "z": z, "u": u, "v": v})
        self.send_and_receive("add_mesh " + p)

    def addCamera(self, name, parent_name, fov, focal_length):
        """
        adds a camera that points to z-direction in local ( parent ) coordinates
        :param name: camera name
        :param parent_name: object name
        :param fov: field of view ( or focal_length )
        :param focal_length ( or fov )
        :return: None
        """
        p = json.dumps({"name": name, "parent_name": parent_name, "fov": fov, "focal_length": focal_length})
        self.send_and_receive("add_camera " + p)

    def addProbe(self, name, parent_name):
        """
        adds a distance probe that points to z-direction in local ( parent ) coordinates
        :param name: probe name
        :param parent_name: object name
        :return: None
        """
        p = json.dumps({"name": name, "parent_name": parent_name})
        self.send_and_receive("add_probe " + p)

    def readProbe(self, name):
        """
        adds a distance probe that points to z-direction in local ( parent ) coordinates
        :param name: probe name
        :return: None
        """
        p = json.dumps({"name": name})
        r = self.send_and_receive("read_probe " + p)
        return json.loads(r)

    def setCameraUp(self, up_x, up_y, up_z):
        p = json.dumps({"up_x": up_x, "up_y": up_y, "up_z": up_z})
        self.send_and_receive("set_camera_up " + p)

    def set_kinematic_function(self, f: str):
        """
        sets the kinematic function used in javascript simulator code
        :param f: function as string
        """
        p = json.dumps({"f": f})
        self.send_and_receive("set_kinematic_function " + p)

    def createDynamicTexture(self, name, width, height):
        p = json.dumps({'name': name, 'width': width, 'height': height})
        self.send_and_receive("create_dynamic_texture " + p)

    def setObjectTexture(self, object_name, texture_name):
        p = json.dumps({'object_name': object_name, 'texture_name': texture_name})
        self.send_and_receive("set_object_texture " + p)

    def drawDynamicTexture(self, name, program, scale):
        p = json.dumps({'name': name, 'program': program, 'scale': scale})
        self.send_and_receive("draw_dynamic_texture " + p)

    def setTitle(self, title):
        self.send_and_receive("set_title " + title)

    def set_axes(self, axes):
        self.send_and_receive("set_axes " + json.dumps(axes))

    def home_axes(self, axis):
        f = {ax: 0 for ax in axis}
        self.move_absolute(f)

    def move_absolute(self, params, with_speed=False):
        params = json.dumps(params)
        self.send_and_receive("abs " + params)

    def force_move(self, grams, axis):
        params = json.dumps({"grams": grams, "axis": axis})
        self.send_and_receive("force " + params)
        self.force_value = grams

    def waiter(self):
        class simuwaiter:
            def wait(self, f):
                pass

        return simuwaiter()


class NumericGoldenSimulatorComm(SimulatorCommBase):
    """
    Numeric robot simulator that implements the Goldenmov API and keeps
    track of axis positions and other necessary robot state but does not visualize anything.
    """

    def __init__(self, axis_info):
        super().__init__(axis_info)

        self.axis_values = {alias: 0.0 for alias in self.axis_specs.keys()}
        self.axes = None
        self.simulate_duration = False

        self.optomotion_spec = SimulatorAxisSpec(acceleration=10, posToDevice=0.1, posFromDevice=5, velocity=20)


    def get_axis_spec(self, axis):
        """
        Returns axis specifications of drive.
        :param axis: Axis name (needed for compatibility reasons).
        :return: Axis specifications.
        """
        return self.optomotion_spec

    def is_busy(self):
        return False

    def home(self):
        self.home_axes(self.axis_specs.keys())

    def set_axes(self, axes):
        self.axes = axes

    def home_axes(self, axis):
        # Assumes that home position of each axis is 0.
        for a in axis:
            self.axis_values[a] = 0.0

    def move_absolute(self, params, with_speed=False):
        for alias, value in params.items():
            self.axis_values[alias] = value

    def get_position(self):
        # Return copy of axis values to avoid user accidentally changing robot position by modifying the dict.
        return copy(self.axis_values)

    def force_move(self, grams, axis):
        pass

    def move_buffered(self, buffer):
        num_values = None

        for values in buffer.values():
            if num_values is None:
                num_values = len(values)
            else:
                assert len(values) == num_values

        # lists are not lists anymore but numpy arrays
        # after axis validation and scaling
        for i in range(num_values):
            for alias, values in buffer.items():
                self.axis_values[alias] = values[i]

            if self.simulate_duration:
                time.sleep(1 / 250)

    def waiter(self):
        class simuwaiter:
            def wait(self, f):
                pass
        return simuwaiter()

    def get_photo(self, camera_name):
        # Just return a black image to make the camera API work.
        return np.zeros((256, 256, 3), np.uint8)

    def enable_axes(self, a):
        pass

    def get_scaled_axis_setpoint(self, axis_alias):
        # Treat setpoint the same as position.
        return self.axis_values[axis_alias]

