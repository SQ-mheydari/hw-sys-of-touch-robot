from tntserver.drivers.robots.goldenmov import *
import pytest


def test_plan_joint_motion():
    joint_setpoints = {"x": 10, "y": 20, "z": 30}

    buffer = plan_joint_motion(joint_setpoints, {"x": 20, "y": 5, "z": 31}, 100, 400)

    # All buffers must be of same length.
    assert len(buffer["x"]) == len(buffer["y"]) == len(buffer["z"])

    # First position must match current setpoint position.
    assert buffer["x"][0] == 10
    assert buffer["y"][0] == 20
    assert buffer["z"][0] == 30

    # End position must be approximately target position.
    # Exact match is not guaranteed because create_track() may omit the last position.
    assert buffer["x"][-1] == pytest.approx(19.998549465163947)
    assert buffer["y"][-1] == pytest.approx(5.002175802254079)
    assert buffer["z"][-1] == pytest.approx(30.999854946516393)
