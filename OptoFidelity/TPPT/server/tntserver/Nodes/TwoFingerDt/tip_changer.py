from tntserver.Nodes.TnT.Tips import TipChanger
import numpy as np

class TwoFingerTipChanger(TipChanger):
    """
    Tip changer for 2-finger robot where one finger is aligned with azimuth
    rotation axis and the other finger has active separation.
    Assumes that when the separated finger kinematic is controlled, the azimuth has 180 deg
    rotation with respect to the axial finger kinematic. This kind of kinematic does not require
    any special movements when changing fingers to either of the two fingers. Only multifinger
    requires that specific separation is set.
    """
    def __init__(self, robot):
        super().__init__(robot)

    def get_safe_distance(self, separation):
        # Robot driver may define safe_distance that is distance from xy axis limits where it is safe to rotate azimuth.
        return  getattr(self._robot.driver, "safe_distance", 0.0)
