"""
Motion and gesture API tests.
These tests should be ran when there is a change in motion planning that can affect multiple gestures.
Run the file in debugger and step through each gesture. Make sure by visual inspection the robot performs
correct motion. Take a note of the gesture parameters and inspect that that parameter correctly affects the motion.

Requirements:
- TnT Client must be installed.
- TnT Server must have following configured:
  - DUT named "dut1"
  - Physical button named "button"
  - Synchro robot must have tips attached to both fingers and force must be calibrated.
"""
try:
    from tntclient.tnt_client import TnTClient, TnTDutPoint
except ImportError:
    print("TnT Client not found!")

import time
import random


def test_tap_repeatability(dut, num):
    """
    Tap DUT origin multiple times to test e.g. axis drifting.
    :return:
    """
    for i in range(num):
        print("Tap {} / {}".format(i + 1, num))
        dut.tap(x=0.0, y=0.0, z=5.0, clearance=-1)


def test_basic_gestures(dut, z=10):
    """
    Test gestures defined in the TnT.Gestures class.
    :param dut: DUT to test with.
    :param z: Z-coordinate in DUT context that is reachable with the robot.
    """
    cx = dut.width / 2
    cy = dut.height / 2
    w = dut.width
    h = dut.height

    # Jump
    dut.jump(x=0, y=0, z=z, jump_height=None)

    # Move
    dut.move(x=0, y=0, z=1, tilt=0, azimuth=0)
    dut.move(x=cx, y=0, z=1, tilt=0, azimuth=0)
    dut.move(x=cx, y=cy, z=1, tilt=0, azimuth=90)
    dut.move(x=cx, y=cy, z=z, tilt=0, azimuth=0)

    # Path
    points = [TnTDutPoint(x=0, y=0, z=z), TnTDutPoint(x=0, y=0, z=0), TnTDutPoint(x=cx, y=cy, z=0), TnTDutPoint(x=cx, y=cy, z=z)]
    dut.path(points=points)

    # Swipe
    dut.swipe(x1=0, y1=cy, x2=w, y2=cy, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=0, radius=6)
    dut.swipe(x1=0, y1=cy, x2=w, y2=cy, tilt1=0, tilt2=0, azimuth1=90, azimuth2=180, clearance=0, radius=6)
    dut.swipe(x1=cx, y1=0, x2=cx, y2=h, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=0, radius=6)

    # Drag
    dut.drag(x1=0, y1=cy, x2=w, y2=cy, z=z, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=0, predelay=0, postdelay=0)
    dut.drag(x1=0, y1=cy, x2=w, y2=cy, z=z, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=0, predelay=1,
             postdelay=2)
    dut.drag(x1=0, y1=cy, x2=w, y2=cy, z=z, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=-1, predelay=0,
             postdelay=0)
    dut.drag(x1=0, y1=cy, x2=w, y2=cy, z=z, tilt1=0, tilt2=0, azimuth1=90, azimuth2=180, clearance=0, predelay=0,
             postdelay=0)

    # Tap
    dut.tap(x=0, y=0, z=z, azimuth=0, clearance=0, duration=0)
    dut.tap(x=w, y=0, z=z, azimuth=0, clearance=0, duration=0)
    dut.tap(x=0, y=h, z=z, azimuth=0, clearance=0, duration=0)
    dut.tap(x=w, y=h, z=z, azimuth=0, clearance=0, duration=0)
    dut.tap(x=0, y=0, z=z, azimuth=90, clearance=0, duration=0)
    dut.tap(x=0, y=0, z=z, azimuth=0, clearance=-1, duration=0)
    dut.tap(x=0, y=0, z=z, azimuth=0, clearance=1, duration=0)
    dut.tap(x=0, y=0, z=5, azimuth=0, clearance=0, duration=0)
    dut.tap(x=0, y=0, z=5, azimuth=0, clearance=1, duration=0)
    dut.tap(x=0, y=0, z=5, azimuth=0, clearance=-1, duration=0)
    dut.tap(x=0, y=0, z=z, azimuth=0, clearance=0, duration=2)

    # Double tap
    dut.double_tap(x=0, y=0, z=z, azimuth=0, clearance=0, duration=0, interval=1)
    dut.double_tap(x=0, y=0, z=z, azimuth=-90, clearance=0, duration=0, interval=1)
    dut.double_tap(x=0, y=0, z=z, azimuth=0, clearance=-1, duration=0, interval=1)
    dut.double_tap(x=0, y=0, z=z, azimuth=0, clearance=1, duration=0, interval=1)
    dut.double_tap(x=0, y=0, z=5, azimuth=0, clearance=0, duration=0, interval=1)
    dut.double_tap(x=0, y=0, z=5, azimuth=0, clearance=1, duration=0, interval=1)
    dut.double_tap(x=0, y=0, z=5, azimuth=0, clearance=-1, duration=0, interval=1)
    dut.double_tap(x=0, y=0, z=z, azimuth=0, clearance=0, duration=2, interval=1)
    dut.double_tap(x=0, y=0, z=z, azimuth=0, clearance=0, duration=0, interval=2)

    # Multitap
    points = [TnTDutPoint(0, 0, 0), TnTDutPoint(cx, 0, 0), TnTDutPoint(cx, cy, 0)]
    dut.multi_tap(points=points, lift=z / 2, clearance=0)
    dut.multi_tap(points=points, lift=z, clearance=-1)

    # Circle
    r = min(w, h) / 4
    dut.circle(x=cx, y=cy, r=r, n=1, angle=0, z=z, tilt=0, azimuth=0, clearance=0, clockwise=False)
    dut.circle(x=cx, y=cy, r=r, n=3, angle=0, z=z, tilt=0, azimuth=0, clearance=0, clockwise=False)
    dut.circle(x=cx, y=cy, r=r, n=1, angle=90, z=z, tilt=0, azimuth=0, clearance=0, clockwise=False)
    dut.circle(x=cx, y=cy, r=r, n=1, angle=0, z=z, tilt=0, azimuth=90, clearance=0, clockwise=False)
    dut.circle(x=cx, y=cy, r=r, n=1, angle=0, z=z, tilt=0, azimuth=0, clearance=-1, clockwise=False)
    dut.circle(x=cx, y=cy, r=r, n=1, angle=0, z=z, tilt=0, azimuth=0, clearance=0, clockwise=True)


def test_synchro_gestures(dut, z=10):
    """
    Test gestures defined in the Synchro.Gestures class.
    :param dut: DUT to test with.
    :param z: Z-coordinate in DUT context that is reachable with the robot.
    """
    cx = dut.width / 2
    cy = dut.height / 2
    w = dut.width
    h = dut.height

    # Tap (2-finger)
    dut.tap(x=cx, y=cy, z=z, azimuth=0, clearance=0, duration=0)
    dut.tap(x=cx, y=cy, z=z, azimuth=0, clearance=0, duration=0, tool_name="tool1")
    dut.tap(x=cx, y=cy, z=z, azimuth=0, clearance=-1, duration=0, tool_name="tool1")
    dut.tap(x=cx, y=cy, z=z, azimuth=0, clearance=1, duration=0, tool_name="tool1")
    dut.tap(x=cx, y=cy, z=z, azimuth=0, clearance=0, duration=0, tool_name="tool1", separation=30)
    dut.tap(x=cx, y=cy, z=z, azimuth=90, clearance=0, duration=0, tool_name="tool1", separation=30)
    dut.tap(x=cx, y=cy, z=z, azimuth=0, clearance=0, duration=0, tool_name="tool2")
    dut.tap(x=cx, y=cy, z=z, azimuth=0, clearance=-1, duration=0, tool_name="tool2")
    dut.tap(x=cx, y=cy, z=z, azimuth=0, clearance=1, duration=0, tool_name="tool2")
    dut.tap(x=cx, y=cy, z=z, azimuth=0, clearance=0, duration=0, tool_name="tool2", separation=30)
    dut.tap(x=cx, y=cy, z=z, azimuth=90, clearance=0, duration=0, tool_name="tool2", separation=30)
    dut.tap(x=cx, y=cy, z=z, azimuth=0, clearance=0, duration=0, tool_name="both")
    dut.tap(x=cx, y=cy, z=z, azimuth=0, clearance=-1, duration=0, tool_name="both")
    dut.tap(x=cx, y=cy, z=z, azimuth=0, clearance=1, duration=0, tool_name="both")
    dut.tap(x=cx, y=cy, z=z, azimuth=0, clearance=0, duration=0, tool_name="both", separation=50)
    dut.tap(x=cx, y=cy, z=z, azimuth=90, clearance=0, duration=0, tool_name="both", separation=50)

    # Double tap (2-finger)
    dut.double_tap(x=cx, y=cy, z=z, azimuth=0, clearance=0, duration=1, interval=2)
    dut.double_tap(x=cx, y=cy, z=z, azimuth=0, clearance=0, duration=1, interval=2, tool_name="tool1")
    dut.double_tap(x=cx, y=cy, z=z, azimuth=0, clearance=-1, duration=1, interval=2, tool_name="tool1")
    dut.double_tap(x=cx, y=cy, z=z, azimuth=0, clearance=1, duration=1, interval=2, tool_name="tool1")
    dut.double_tap(x=cx, y=cy, z=z, azimuth=0, clearance=0, duration=1, interval=2, tool_name="tool1", separation=30)
    dut.double_tap(x=cx, y=cy, z=z, azimuth=90, clearance=0, duration=1, interval=2, tool_name="tool1", separation=30)
    dut.double_tap(x=cx, y=cy, z=z, azimuth=0, clearance=0, duration=1, interval=2, tool_name="tool2")
    dut.double_tap(x=cx, y=cy, z=z, azimuth=0, clearance=-1, duration=1, interval=2, tool_name="tool2")
    dut.double_tap(x=cx, y=cy, z=z, azimuth=0, clearance=1, duration=1, interval=2, tool_name="tool2")
    dut.double_tap(x=cx, y=cy, z=z, azimuth=0, clearance=0, duration=1, interval=2, tool_name="tool2", separation=30)
    dut.double_tap(x=cx, y=cy, z=z, azimuth=90, clearance=0, duration=1, interval=2, tool_name="tool2", separation=30)
    dut.double_tap(x=cx, y=cy, z=z, azimuth=0, clearance=0, duration=1, interval=2, tool_name="both")
    dut.double_tap(x=cx, y=cy, z=z, azimuth=0, clearance=-1, duration=1, interval=2, tool_name="both")
    dut.double_tap(x=cx, y=cy, z=z, azimuth=0, clearance=1, duration=1, interval=2, tool_name="both")
    dut.double_tap(x=cx, y=cy, z=z, azimuth=0, clearance=0, duration=1, interval=2, tool_name="both", separation=50)
    dut.double_tap(x=cx, y=cy, z=z, azimuth=90, clearance=0, duration=1, interval=2, tool_name="both", separation=50)

    # Swipe (2-finger)
    dut.swipe(x1=0, y1=cy, x2=w, y2=cy, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=0, radius=6)
    dut.swipe(x1=0, y1=cy, x2=w, y2=cy, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=0, radius=6, tool_name="tool1")
    dut.swipe(x1=0, y1=cy, x2=w, y2=cy, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=-0.5, radius=6, tool_name="tool1")
    dut.swipe(x1=0, y1=cy, x2=w, y2=cy, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=1, radius=6, tool_name="tool1")
    dut.swipe(x1=0, y1=cy, x2=w, y2=cy, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=0, radius=6, tool_name="tool1", separation=30)
    dut.swipe(x1=0, y1=cy, x2=w, y2=cy, tilt1=0, tilt2=0, azimuth1=90, azimuth2=90, clearance=0, radius=6, tool_name="tool1", separation=30)
    dut.swipe(x1=0, y1=cy, x2=w, y2=cy, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=0, radius=6, tool_name="tool2")
    dut.swipe(x1=0, y1=cy, x2=w, y2=cy, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=-0.5, radius=6, tool_name="tool2")
    dut.swipe(x1=0, y1=cy, x2=w, y2=cy, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=1, radius=6, tool_name="tool2")
    dut.swipe(x1=0, y1=cy, x2=w, y2=cy, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=0, radius=6, tool_name="tool2", separation=30)
    dut.swipe(x1=0, y1=cy, x2=w, y2=cy, tilt1=0, tilt2=0, azimuth1=90, azimuth2=90, clearance=0, radius=6, tool_name="tool2", separation=30)
    dut.swipe(x1=cx, y1=0, x2=cx, y2=h, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=0, radius=6, tool_name="both")
    dut.swipe(x1=cx, y1=0, x2=cx, y2=h, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=-0.5, radius=6, tool_name="both")
    dut.swipe(x1=cx, y1=0, x2=cx, y2=h, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=1, radius=6, tool_name="both")
    dut.swipe(x1=cx, y1=0, x2=cx, y2=h, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=0, radius=6, tool_name="both", separation=50)
    dut.swipe(x1=0, y1=cy, x2=w, y2=cy, tilt1=0, tilt2=0, azimuth1=90, azimuth2=90, clearance=0, radius=6, tool_name="both", separation=50)

    # Watchdog tap
    dut.watchdog_tap(x=0, y=0, z=z, azimuth=0, clearance=0, duration=0)
    dut.watchdog_tap(x=0, y=0, z=z, azimuth=90, clearance=0, duration=0)
    dut.watchdog_tap(x=0, y=0, z=z, azimuth=0, clearance=-1, duration=0)
    dut.watchdog_tap(x=0, y=0, z=z, azimuth=0, clearance=0, duration=2)

    # Pinch
    dut.pinch(x=cx, y=cy, d1=50, d2=70, azimuth=0, z=z, clearance=0)
    dut.pinch(x=cx, y=cy, d1=50, d2=70, azimuth=90, z=z, clearance=0)
    dut.pinch(x=cx, y=cy, d1=50, d2=70, azimuth=0, z=z, clearance=-1)

    # Drumroll
    dut.drumroll(x=cx, y=cy, azimuth=0, separation=50, tap_count=10, tap_duration=5, clearance=0)
    dut.drumroll(x=cx, y=cy, azimuth=0, separation=50, tap_count=10, tap_duration=5, clearance=-1)
    dut.drumroll(x=cx, y=cy, azimuth=90, separation=50, tap_count=10, tap_duration=5, clearance=0)

    # Compass
    dut.compass(x=cx, y=cy, azimuth1=0, azimuth2=90, separation=50, z=z, clearance=0)
    dut.compass(x=cx, y=cy, azimuth1=0, azimuth2=90, separation=50, z=z, clearance=-1)

    # Compass tap
    dut.compass_tap(x=cx, y=cy, azimuth1=0, azimuth2=120, separation=50, tap_azimuth_step=20, z=z,
                tap_with_stationary_finger=False, clearance=0)
    dut.compass_tap(x=cx, y=cy, azimuth1=0, azimuth2=120, separation=50, tap_azimuth_step=20, z=z,
                    tap_with_stationary_finger=False, clearance=-1)
    dut.compass_tap(x=cx, y=cy, azimuth1=0, azimuth2=120, separation=50, tap_azimuth_step=20, z=z,
                    tap_with_stationary_finger=True, clearance=0)

    # Touch and tap
    dut.touch_and_tap(touch_x=cx-20, touch_y=cy, tap_x=cx+20, tap_y=cy, z=z,
                      number_of_taps=1, tap_predelay=0, tap_duration=0, tap_interval=0, clearance=0)
    dut.touch_and_tap(touch_x=cx - 20, touch_y=cy, tap_x=cx + 20, tap_y=cy, z=z,
                      number_of_taps=4, tap_predelay=0, tap_duration=0, tap_interval=0, clearance=0)
    dut.touch_and_tap(touch_x=cx - 20, touch_y=cy, tap_x=cx + 20, tap_y=cy, z=z,
                      number_of_taps=3, tap_predelay=1, tap_duration=2, tap_interval=3, clearance=0)
    dut.touch_and_tap(touch_x=cx - 20, touch_y=cy, tap_x=cx + 20, tap_y=cy, z=z,
                      number_of_taps=1, tap_predelay=0, tap_duration=0, tap_interval=0, clearance=-1)

    dut.touch_and_tap(touch_x=cx - 20, touch_y=cy, tap_x=cx + 20, tap_y=cy, z=z,
                      number_of_taps=1, tap_predelay=0, tap_duration=0, tap_interval=0, clearance=0)
    dut.touch_and_tap(touch_x=cx - 20, touch_y=cy, tap_x=cx + 20, tap_y=cy, z=z,
                      number_of_taps=1, tap_predelay=1, tap_duration=0, tap_interval=0, clearance=0, touch_duration=1)
    dut.touch_and_tap(touch_x=cx - 20, touch_y=cy, tap_x=cx + 20, tap_y=cy, z=z,
                      number_of_taps=1, tap_predelay=1, tap_duration=0, tap_interval=0, clearance=0, touch_duration=3)
    dut.touch_and_tap(touch_x=cx - 20, touch_y=cy, tap_x=cx + 20, tap_y=cy, z=z,
                      number_of_taps=1, tap_predelay=2, tap_duration=0, tap_interval=0, clearance=0, touch_duration=0.1)
    dut.touch_and_tap(touch_x=cx - 20, touch_y=cy, tap_x=cx + 20, tap_y=cy, z=z,
                      number_of_taps=1, tap_predelay=0, tap_duration=0, tap_interval=0, clearance=0, touch_duration=0)

    # Line tap
    dut.line_tap(x1=cx, y1=0, x2=cx, y2=h, tap_distances=[h/4, h/2], separation=50, azimuth=0, z=z, clearance=0)
    dut.line_tap(x1=cx, y1=0, x2=cx, y2=h, tap_distances=[h / 4, h / 2], separation=50, azimuth=90, z=z, clearance=0)
    dut.line_tap(x1=cx, y1=0, x2=cx, y2=h, tap_distances=[h / 4, h / 2], separation=50, azimuth=0, z=z, clearance=-1)

    # Rotate
    dut.rotate(x=cx, y=cy, azimuth1=0, azimuth2=90, separation=50, z=z, clearance=0)
    dut.rotate(x=cx, y=cy, azimuth1=0, azimuth2=90, separation=50, z=z, clearance=-1)
    dut.rotate(x=cx, y=cy, azimuth1=160, azimuth2=260, separation=50, z=z, clearance=0)

    # Touch and drag
    dut.touch_and_drag(x0=0, y0=cy, x1=50, y1=cy-50, x2=50, y2=cy+50, z=z, clearance=0)
    dut.touch_and_drag(x0=0, y0=cy, x1=50, y1=cy - 50, x2=50, y2=cy + 50, z=z, clearance=-1)
    dut.touch_and_drag(x0=0, y0=cy, x1=50, y1=cy - 50, x2=50, y2=cy + 50, z=z, clearance=0, delay=3)
    dut.touch_and_drag(x0=0, y0=cy, x1=50, y1=cy - 50, x2=50, y2=cy + 50, z=z, clearance=0, delay=1, touch_duration=1)
    dut.touch_and_drag(x0=0, y0=cy, x1=50, y1=cy - 50, x2=50, y2=cy + 50, z=z, clearance=0, delay=1, touch_duration=2)
    dut.touch_and_drag(x0=0, y0=cy, x1=50, y1=cy - 50, x2=50, y2=cy + 50, z=z, clearance=0, delay=2, touch_duration=1)
    dut.touch_and_drag(x0=0, y0=cy, x1=50, y1=cy - 50, x2=50, y2=cy + 50, z=z, clearance=0, delay=0, touch_duration=0)

    # Fast swipe
    dut.fast_swipe(x1=0, y1=cy, x2=w, y2=cy, separation1=50, separation2=80, speed=100, acceleration=200, tilt1=0, tilt2=0, clearance=0, radius=6)
    dut.fast_swipe(x1=0, y1=cy, x2=w, y2=cy, separation1=50, separation2=80, speed=100, acceleration=200, tilt1=0, tilt2=0, clearance=-0.5, radius=6)

    # Drag
    dut.drag(x1=0, y1=cy, x2=w, y2=cy, z=z, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=0, predelay=0,
             postdelay=0, separation=30, tool_name="tool1")
    dut.drag(x1=0, y1=cy, x2=w, y2=cy, z=z, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, clearance=0, predelay=0,
             postdelay=0, separation=30, tool_name="tool2")
    dut.drag(x1=0, y1=cy, x2=w, y2=cy, z=z, tilt1=0, tilt2=0, azimuth1=90, azimuth2=90, clearance=0, predelay=0,
             postdelay=0, separation=30, tool_name="both")

    # Circle
    r = min(w, h) / 4
    dut.circle(x=cx, y=cy, r=r, n=1, angle=0, z=z, tilt=0, azimuth=0, clearance=0, clockwise=False, separation=30,
               tool_name="tool1")
    dut.circle(x=cx, y=cy, r=r, n=1, angle=0, z=z, tilt=0, azimuth=0, clearance=0, clockwise=False, separation=30,
               tool_name="tool2")
    dut.circle(x=cx, y=cy, r=r, n=1, angle=0, z=z, tilt=0, azimuth=0, clearance=0, clockwise=False, separation=30,
               tool_name="both")

    # Path
    points = [TnTDutPoint(x=cx, y=0, z=z), TnTDutPoint(x=cx, y=0, z=0), TnTDutPoint(x=cx, y=cy, z=0),
              TnTDutPoint(x=cx, y=cy, z=z)]
    dut.path(points=points, clearance=0, separation=30, tool_name="tool1")
    dut.path(points=points, clearance=0, separation=30, tool_name="tool2")
    dut.path(points=points, clearance=0, separation=30, tool_name="both")


def test_force_gestures(dut, z=10):
    """
    Test force gestures. Make sure that force calibration as been done correctly.
    :param dut: DUT to test with.
    :param z: Z-coordinate in DUT context that is reachable with the robot.
    :return:
    """
    cx = dut.width / 2
    cy = dut.height / 2
    w = dut.width
    h = dut.height

    # Jump
    dut.jump(x=0, y=0, z=z, jump_height=None)

    # Press
    dut.press(x=0, y=0, force=100, z=10, azimuth=0, duration=2, press_depth=-1)
    dut.press(x=0, y=0, force=100, z=4, azimuth=0, duration=2, press_depth=-1)
    dut.press(x=0, y=0, force=100, z=10, azimuth=90, duration=2, press_depth=-1)
    dut.press(x=0, y=0, force=100, z=10, azimuth=0, duration=5, press_depth=-1)
    dut.press(x=0, y=0, force=100, z=10, azimuth=0, duration=2, press_depth=-2)
    dut.press(x=0, y=0, force=200, z=10, azimuth=0, duration=2, press_depth=-2)

    # Drag force
    dut.drag_force(x1=0, y1=cy, x2=w, y2=cy, force=100, z=10, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0)
    dut.drag_force(x1=0, y1=cy, x2=w, y2=cy, force=200, z=10, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0)


def test_synchro_force_gestures(dut, z=10):
    """
    Test synchro force gestures. Make sure that force calibration as been done correctly.
    :param dut: DUT to test with.
    :param z: Z-coordinate in DUT context that is reachable with the robot.
    """
    cx = dut.width / 2
    cy = dut.height / 2
    w = dut.width
    h = dut.height

    # Jump
    dut.jump(x=0, y=0, z=z, jump_height=None)

    # Press
    dut.press(x=cx, y=cy, force=100, z=z, azimuth=0, duration=2, press_depth=-1, separation=30, tool_name="tool1")
    dut.press(x=cx, y=cy, force=100, z=z, azimuth=0, duration=2, press_depth=-1, separation=30, tool_name="tool2")
    dut.press(x=cx, y=cy, force=100, z=z, azimuth=90, duration=2, press_depth=-1, separation=30, tool_name="both")

    # Drag force
    dut.drag_force(x1=0, y1=cy, x2=w, y2=cy, force=100, z=z, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, separation=30, tool_name="tool1")
    dut.drag_force(x1=0, y1=cy, x2=w, y2=cy, force=100, z=z, tilt1=0, tilt2=0, azimuth1=0, azimuth2=0, separation=30, tool_name="tool2")
    dut.drag_force(x1=0, y1=cy, x2=w, y2=cy, force=100, z=z, tilt1=0, tilt2=0, azimuth1=90, azimuth2=90, separation=30, tool_name="both")


def test_robot_motion(robot, x_min, x_max, y_min, y_max, z_min, z_max):
    """
    Test robot motion via robot client.
    Make sure that the parameters define a volume in space where it is safe to move the robot from point to point.
    :param robot: Robot client object.
    :param x_min: Minimum x-coordinate in workspace.
    :param x_max: Maximum x-coordinate in workspace.
    :param y_min: Minimum y-coordinate in workspace.
    :param y_max: Maximum y-coordinate in workspace.
    :param z_min: Minimum z-coordinate in workspace.
    :param z_max: Maximum z-coordinate in workspace.
    """
    w = x_max - x_min
    h = y_max - y_min
    d = z_max - z_min

    # Move
    robot.move(x=x_min, y=y_min, z=z_max, tilt=None, azimuth=None, context="tnt")
    robot.move(x=x_max, y=y_max, z=z_max, tilt=None, azimuth=None, context="tnt")
    robot.move(x=x_min+w/2, y=y_min+h/2, z=z_min+d/2, tilt=None, azimuth=None, context="tnt")
    robot.move(x=x_min+w/2, y=y_min+h/2, z=z_min+d/2, tilt=None, azimuth=90, context="tnt")
    robot.move(x=x_min+w/2, y=y_min+h/2, z=z_min+d/2, tilt=None, azimuth=None, context="tnt")

    # Move relative
    robot.move_relative(x=w/10, y=None, z=None, tilt=None, azimuth=None)
    robot.move_relative(x=None, y=h/10, z=None, tilt=None, azimuth=None)
    robot.move_relative(x=None, y=None, z=-d/10, tilt=None, azimuth=None)
    robot.move_relative(x=None, y=None, z=None, tilt=None, azimuth=90)


def test_physical_button(robot, button):
    """
    Test physical button.
    :param robot: Robot client object.
    :param button: Name of button to press.
    """
    robot.press_physical_button(button, duration=1.0)


def test_synchro_azimuth(robot, x, y, z):
    """
    Test that azimuth rotations over 180 degrees don't cause any sudden jumps.
    """
    robot.move(x=x, y=y, z=z, tilt=None, azimuth=None, context="tnt")
    robot.set_finger_separation(30)

    for i in range(100):
        print(i)
        robot.move_relative(azimuth=random.uniform(-90, 90))
        time.sleep(random.uniform(0, 1))
        robot.move_relative(azimuth=180)
        time.sleep(random.uniform(0, 1))


def run_tests():
    tntclient = TnTClient()
    robot = tntclient.robot("Robot1")

    # Set appropriate speed and acceleration.
    robot.set_speed(30, 50)

    dut = tntclient.dut("dut1")

    # Optionally test tap repeatability.
    #test_tap_repeatability(dut, 10000)

    z = 10

    test_basic_gestures(dut, z)
    test_synchro_gestures(dut, z)
    test_force_gestures(dut, z)
    test_synchro_force_gestures(dut, z)
    test_robot_motion(robot, 10, 400, 10, 400, -50, -10)
    test_physical_button(robot, button="button")
    test_synchro_azimuth(robot, x=50, y=50, z=-20)


run_tests()