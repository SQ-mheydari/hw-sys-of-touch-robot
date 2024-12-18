
from .tnt_client import *
from . import logger

log = logger.get_logger(__name__)

            
class TnTRobotClient(TnTClientObject):
    def __init__(self, name, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):
        TnTClientObject.__init__(self, host, port, workspace, "robots", name)
        
    def get_active_finger(self, ):    
        """
        Get active finger.
        :return: Active finger ID.
        """
        params = {
        }
        
        
        return self._GET('active_finger', params)
        
    def get_attached_tips(self, ):    
        """
        Get names of tips attached to the robot.
        :return: Dictionary where key is tool name and value is name of tip attached to that tool. If no tip is
        attached then value is None.
        """
        params = {
        }
        
        
        return self._GET('attached_tips', params)
        
    def get_finger_separation(self, ):    
        """
        Get separation of two fingers in mm.
        :return: Separation distance in mm.
        """
        params = {
        }
        
        
        return self._GET('finger_separation', params)
        
    def get_position(self, context='tnt', details=False, kinematic_name=None):    
        """
        Returns the current robot position in given context.
        :param context: Name of context where to evaluate the position.
        :param details: Return detailed position info.
        :param kinematic_name: Name of kinematic that corresponds to the position.
        :return: Dictionary with keys 'position' and 'status'.
        """
        params = {
            'context': context,
            'details': details,
        }
        
        if kinematic_name is not None:
            params['kinematic_name'] = kinematic_name
        
        return self._GET('position', params)
        
    def get_speed(self, ):    
        """
        Returns robot's current speed and acceleration.
        :return: Dictionary with keys 'speed' and 'acceleration'.
        """
        params = {
        }
        
        
        return self._GET('speed', params)
        
    def set_active_finger(self, finger_id):    
        """
        Set active finger.
        Kinematics are applied to the active finger so that it is possible
        to command either of the two fingers to specified pose.
        :param finger_id: ID of finger to set active. 0=axial finger, 1=separated finger.
        """
        params = {
            'finger_id': finger_id,
        }
        
        
        return self._PUT('active_finger', params)
        
    def change_tip(self, tip, finger_id=0, attach_manually=False):    
        """
        Commands robot to change new tool tip from tip holder.
        DEPRECATED: This is 2-finger TPPT compatibility and does the same as put_attach_tip().
        :param tip: Name of tip to make the current tip.
        :param finger_id: ID of finger where to change tip to. Ignored if robot has only one tool.
        :param attach_manually: If tip is to be attached manually and not with the tip changer.
        :return: Name of the tip that was attached as dict {"tip": tip_name}
        """
        params = {
            'tip': tip,
            'finger_id': finger_id,
            'attach_manually': attach_manually,
        }
        
        
        return self._PUT('change_tip', params)
        
    def detach_tip(self, tool_name='tool1', finger_id=None, detach_manually=False):    
        """
        Detach tip from robot finger if one is attached.
        :param tool_name: Name of tool node where tip is detached from. Must be a child of Mount node.
        :param finger_id: ID of finger.
        :param detach_manually: If tip is to be detached manually and not with the tip changer.
        :return: Name of the tip that was detached as dict {"tip": tip_name}.
        """
        params = {
            'tool_name': tool_name,
            'detach_manually': detach_manually,
        }
        
        if finger_id is not None:
            params['finger_id'] = finger_id
        
        return self._PUT('detach_tip', params)
        
    def set_finger_separation(self, distance, kinematic_name=None):    
        """
        Set separation of two fingers in mm. Separation distance is measured from finger axes.
        :param distance: Distance in mm.
        :param kinematic_name: Name of kinematic to use for the motion. If None then currently active kinematic is used.
        :return: Dictionary with "status" key.
        """
        params = {
            'distance': distance,
        }
        
        if kinematic_name is not None:
            params['kinematic_name'] = kinematic_name
        
        return self._PUT('finger_separation', params)
        
    def go_home(self, ):    
        """
        Commands the robot to go into home position.
        """
        params = {
        }
        
        
        return self._PUT('home', params)
        
    def move(self, x, y, z, tilt=None, azimuth=None, context='tnt'):    
        """
        Moves robot into a given location using a linear motion. Coordinates and angles are interpreted in given context.
        Values tilt and azimuth are taken from Euler angles for global static y and z axes (in selected context)
        that are applied in order y, z. Tilt is angle around y-axis and azimuth is negative angle around z-axis.
        :param x: Target x coordinate.
        :param y: Target y coordinate.
        :param z: Target z coordinate.
        :param tilt: Euler angle for static y-axis (default: 0) in selected context.
        :param azimuth: Negative Euler angle for static z-axis (default: 0) in selected context.
        :param context: Name of context where coordinates and angles are interpreted.
        """
        params = {
            'x': x,
            'y': y,
            'z': z,
            'context': context,
        }
        
        if tilt is not None:
            params['tilt'] = tilt
        if azimuth is not None:
            params['azimuth'] = azimuth
        
        return self._PUT('move', params)
        
    def move_joint_position(self, joint_position, speed=None, acceleration=None):    
        """
        Moves robot to a specified joint configuration.
        :param joint_position: Target joint configuration as a dictionary of (axis_name: value) items.
        :param speed: Speed of joint movement. If None, current robot speed is used.
        :param acceleration: Acceleration of joint movement. If None, current robot acceleration is used.
        """
        params = {
            'joint_position': joint_position,
        }
        
        if speed is not None:
            params['speed'] = speed
        if acceleration is not None:
            params['acceleration'] = acceleration
        
        return self._PUT('move_joint_position', params)
        
    def move_relative(self, x=None, y=None, z=None, tilt=None, azimuth=None):    
        """
        Moves robot axes by specified distance using linear motion.
        Parameters are relative to current position and can hence be negative or positive.

        :param x: Relative x axis movement.
        :param y: Relative y axis movement.
        :param z: Relative z axis movement.
        :param tilt: Relative tilt axis movement.
        :param azimuth: Relative azimuth axis movement.
        """
        params = {
        }
        
        if x is not None:
            params['x'] = x
        if y is not None:
            params['y'] = y
        if z is not None:
            params['z'] = z
        if tilt is not None:
            params['tilt'] = tilt
        if azimuth is not None:
            params['azimuth'] = azimuth
        
        return self._PUT('move_relative', params)
        
    def press_physical_button(self, button_name, duration=0):    
        """
        Performs a press gesture on the given button.

        :param button_name: The button to press.
        :param duration: How long to keep button pressed in seconds (default: 0s).
        :return: "ok" / error
        """
        params = {
            'button_name': button_name,
            'duration': duration,
        }
        
        
        return self._PUT('press_physical_button', params)
        
    def reset_robot_error(self, ):    
        """
        Resets robot error state.
        """
        params = {
        }
        
        
        return self._PUT('reset_error', params)
        
    def set_speed(self, speed, acceleration=None, override=None):    
        """
        Set robot speed and acceleration.
        :param speed: Linear movement speed in mm/s.
        :param acceleration: Robot acceleration in mm/s^2.
        :param override: Not used. DEPRECATED.
        """
        params = {
            'speed': speed,
        }
        
        if acceleration is not None:
            params['acceleration'] = acceleration
        if override is not None:
            params['override'] = override
        
        return self._PUT('speed', params)
        
