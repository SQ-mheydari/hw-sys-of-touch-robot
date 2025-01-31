from tntserver.Nodes.Node import Node, json_out, thread_safe
import json
import numpy as np
import logging
log = logging.getLogger(__name__)


class NodeSurfaceProbe(Node):
    """
    This class controls a surface probing sequence for the given robot.
    """

    def __init__(self, name):
        super().__init__(name)
        self._robot = None
        self._aborted = False
        self._surface_probe = None
        self.surface_probe_settings = None

    def _init(self, robot, **kwargs):
        self._robot = Node.find(robot)

    @json_out
    def put_probe_z_surface(self, return_to_start=True, tool_name="tool1"):
        """
        Starts automatic DUT surface z height probing sequence. Robot will move to negative direction along the robot
        coordinate system Z-axis in steps. Once the surface touch has been detected, the robot either stays at the
        found surface location or moves back up. Function will block during the probing sequence.
        :param return_to_start: If True, return to start position when surface is found.
        :param tool_name: Name of the tool to use for surface probing.
        Otherwise move effective position to found surface.
        :return: Detected surface position.
        """
        return self.probe_z_surface(return_to_start, tool_name)

    def probe_z_surface(self, return_to_start=True, tool_name="tool1"):
        """
        Executes probing sequence and returns robot pose at found surface level.
        :param return_to_start: If True, return to start position when surface is found.
        :param tool_name: Name of the tool to use for surface probing.
        Otherwise move effective position to found surface.
        :return: Robot pose at probed surface.
        """
        self._aborted = False
        self._surface_probe = self._robot.surface_probe

        self._surface_probe.set_tool(tool_name)
        self._robot.surface_probe.set_probing_parameters(self.surface_probe_settings)
        self._surface_probe.return_to_start = return_to_start
        surface_pose = self._robot.effective_pose()

        # Setup robot configuration for surface probing and start probing one step at a time.
        with self._surface_probe:
            while not self._aborted:
                self._surface_probe.execute_probing_step()

                # If surface probe is triggered, return found surface pose.
                if self._surface_probe.surface_probe_triggered:
                    surface_pose = self._surface_probe.surface_pose()
                    break

        return surface_pose.tolist()

    @thread_safe
    @json_out
    def put_abort(self):
        """
        Aborts currently running surface probing.
        """
        self._aborted = True
        return "ok"

    @json_out
    def put_test_repeatability(self, n):
        """
        Simple test for surface probing repeatability.
        :param n: Number of repetitions.
        :return: Mean z-coordinate and it's 3-sigma repeatability.
        """
        surface_positions = np.array([])
        self._aborted = False
        for _ in range(n):
            if self._aborted:
                break
            retval = self.put_probe_z_surface()
            pos = np.array(json.loads(retval[1].decode()))
            surface_positions = np.append(surface_positions, pos[2, 3])

        return {"mean": np.mean(surface_positions),
                "3-sigma": 3*np.std(surface_positions)}


class RobotSurfaceProbe(Node):
    """
    Base class for surface probe. Each robot should implement the member functions in its own robot-specific way.
    """

    def __init__(self, robot):
        super().__init__(name=robot.name + "_surfaceprobe")
        self._robot = robot
        self.return_to_start = True

    def surface_pose(self):
        """
        Return the found surface as a robot pose.
        :return: Robot pose of DUT surface.
        """
        raise NotImplementedError("Abstract base class method.")

    def __enter__(self):
        """
        Setup the robot configuration for surface probing, e.g. extend the voice coil, change current limits etc.
        :return: None
        """
        raise NotImplementedError("Abstract base class method.")

    def __exit__(self, *args, **kwargs):
        """
        Reset robot configuration back to normal after surface probing.
        :param args:
        :param kwargs:
        :return: None
        """
        raise NotImplementedError("Abstract base class method.")

    def execute_probing_step(self):
        """
        Executes one incremental step in the surface probing sequence.
        :return: None
        """
        raise NotImplementedError("Abstract base class method.")

    def surface_probe_triggered(self):
        """
        Return True if surface contact has been detected.
        :return: True if surface found, else False.
        """
        raise NotImplementedError("Abstract base class method.")

    def set_probing_parameters(self, probing_settings: dict):
        """
        Set parameters used during probing.
        :param probing_settings: Dict of parameters.
        """
        raise NotImplementedError("Abstract base class method.")

    def set_tool(self, tool_name: str):
        """
        Set tool to be used for surface probing.
        :param tool_name: Name of the tool.
        """
        raise NotImplementedError("Abstract base class method.")
