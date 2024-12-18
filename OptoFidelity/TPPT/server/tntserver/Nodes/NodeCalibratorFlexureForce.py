import logging
from tntserver.Nodes.NodeCalibratorOptoStdForce import NodeCalibratorOptoStdForce

log = logging.getLogger(__name__)


class NodeCalibratorFlexureForce(NodeCalibratorOptoStdForce):
    """
    Node for flexure force calibration.
    Implementation is based on NodeCalibratorOptoStdForce.
    """

    def _force_sequence(self, calibration_id: str, measurement_points: int, 
                        is_calibration: bool, window_size=None, press_duration=4.0, **kwargs):
        """
        Performs force sequence to calibrate or validate. Record state changes for the TnT UI
        in case of exceptions
        :param calibration_id: Calibration uuid
        :param measurement_points: The amount of measurement points
        :param is_calibration: Boolean value to define if the sequence is to be a calibration or a 
        validation
        :param window_size: Number of samples to use around middle of force press. Negative window size selects given
        index from a list of recorded sample values, i.e. -1 selects last one, -2 second to last one etc.
        :param kwargs: Possible additional arguments
        :return: None
        """

        force_driver = self.robot.force_driver

        specs = self.robot.driver.kinematics.get_axis_spec_by_alias(force_driver.voicecoil_axis)
        rest_position = specs.get("rest_position", 2.0)

        # Calibration procedure starts with the tip touching the force sensor plate.
        # Move up where voicecoil can be disabled (+ some margin).
        start_frame = self.robot.effective_frame
        calibration_frame = start_frame
        calibration_frame.A[2, 3] += rest_position + 0.5

        # Move robot to start position. Setting frame executes robot movement.
        self.robot.effective_frame = calibration_frame

        self.robot.disable_voicecoil()

        try:
            super()._force_sequence(calibration_id=calibration_id, measurement_points=measurement_points,
                                    is_calibration=is_calibration, window_size=window_size,
                                    press_duration=press_duration, **kwargs)

        finally:
            # Enable voicecoil and move robot back to original starting position
            self.robot.enable_voicecoil()
            calibration_frame.A[2, 3] -= rest_position + 0.5
            self.robot.effective_frame = calibration_frame
