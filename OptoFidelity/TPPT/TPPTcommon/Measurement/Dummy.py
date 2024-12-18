from .Base import *
import numpy
import math
import TPPTcommon.containers as Containers
import time
import random
from TPPTcommon.grid import azimuth_direction
from TPPTcommon.Measurement.Base import *
from .DummyPIT import DummyPIT

END_POINT = 1  # to clarify code
ROUND_DECIMALS = 3  # accuracy of results

DOWN_EVENT = 0
TOUCH_EVENT = 2
UP_EVENT = 1
HOVER_EVENT = 7  # This is hover_move as defined in devicesocket.py


class Driver(DriverBase):

    def __init__(self, **kwargs):
        """
        This function is called already when the "Load Script" button is pressed
        """
        super().__init__()

        self.driver_name = "Dummy"
        self.active_dut_node = None
        self.pit = DummyPIT()
        self.pit_index = 1

    def init_at_test_start(self, **kwargs):
        """
        This function is called every time the dut is changed.
        """
        self.active_dut_node = kwargs.get("active_dut")
        self.active_dut_node.context.html_color("{} is using dummy driver, the results are not real touch events."
                                                .format(self.active_dut_node.name), "red")

    def close_at_test_finish(self, **kwargs):
        """
        This function is called when the "Stop" or "Finish" button is pressed.
        """
        pass

    def get_device_resolution(self, dut_node):
        """
        Dummy version of this method. It calculates some resolution with correct aspect ratio.
        :param dut_node: DUT node for current device.
        :returns: Device resolution as a list ([x, y])
        """
        dut = dut_node.tnt_dut
        width = dut.width
        height = dut.height
        aspect_ratio = width / height
        x = 400
        y = int(round(x / aspect_ratio))
        return [x, y]


class PerfectSettings:
    # Common parameters for all measurements
    max_x_error = 0  # mm
    max_y_error = 0  # mm
    max_azimuth_error = 0  # deg
    max_tilt_error = 0  # deg
    lost_points = 0  # point is never lost

    # Common parameters for all continous measurements
    max_time_error = 0  # ms(?)
    ghost_finger = 0  # no ghost fingers
    marginal = 2  # making sure we don't do any modifications to close to the edge

    # Parameters only for continous line measurement
    report_rate = 7  # ms(?)
    num_of_line_points_per_mm = 1
    min_size_of_broken_line = 0
    lost_lines = 0  # no lines  are lost
    line_point_var = 0  # number of line points is always the same
    broken_line = 0  # no lines are broken
    max_lost_points = 2  # has to be >1 to work, does not affect anything if broken_line = 0
    start_end_hover_enabled = False  # adds hoover events in the beginning and to the end of a line
    max_hover_events = 0

    # Parameters only for continous point measurement
    num_events_min = 5
    num_events_max = num_events_min
    max_lost_events = 2  # has to be >1 to work, does not affect anything if touch_error = 0
    touch_error = 0  # 0.1 = 10 percent of points have issues with touch signal
    lost_multifinger = 0  # No multifinger touches are lost

    # Parameters only for latency measurement
    min_delay = 0  # minimum delay from trigger event to registered touch
    max_delay = 0  # maximum delay from trigger event to registered touch


class ErroneousSettings:
    # Common parameters for all measurements
    max_x_error = 0.5  # mm
    max_y_error = 0.5  # mm
    max_azimuth_error = 0.5  # deg
    max_tilt_error = 0.5  # deg
    lost_points = 0.005  # 0.1 = 10 percent of points are lost

    # Common parameters for all continuous measurements
    max_time_error = 0.5  # ms(?)
    ghost_finger = 0.005  # 0.1 = 10 percent of points have wrong finger id (ghost finger)
    marginal = 2  # making sure we don't do any modifications to close to the edge

    # Parameters only for continuous line measurement
    report_rate = 7  # ms(?)
    num_of_line_points_per_mm = 1
    min_size_of_broken_line = 20
    lost_lines = 0.005  # 0.1 = 10 percent of lines are lost
    line_point_var = 5  # variation in number of line points
    broken_line = 0.01  # 0.1 = 10 percent of lines are broken
    max_lost_points = 20  # number of points that can be lost from the middle of the swipe, always >1
    start_end_hover_enabled = False  # adds hoover events in the beginning and to the end of a line
    max_hover_events = 5

    # Parameters only for continuous point measurement
    num_events_min = 7
    num_events_max = 20
    max_lost_events = 2  # max num of events lost in the middle of single point measurement, always >1
    touch_error = 0.005  # 0.1 = 10 percent of points have issues with touch signal
    lost_multifinger = 0.005  # 0.1 = 10 percent of multifinger touches are lost

    # Parameters only for latency measurement
    min_delay = -51  # minimum delay from trigger event to registered touch, it is possible for this value be too low
    max_delay = 51  # maximum delay from trigger event to registered touch, it is possible for this value be too high


# Choose here perfect results or results with pre-defined
# maximum errors
settings = ErroneousSettings()


def mm_to_pixels(dut_width, dut_height, dut_resolution, x_mm, y_mm):
    '''
    transforms the given x and y coordinates to pixels based on
    active dut resolution and dimensions
    :param x: x coordinate (in mm)
    :param y: y coordinate (in mm)
    :return: x, y (in pixels)
    '''
    x_pixels = x_mm * dut_resolution[0] / dut_width
    y_pixels = y_mm * dut_resolution[1] / dut_height

    return x_pixels, y_pixels


class TapMeasurement(TapMeasurementBase):
    '''
    Dummy tap measurement. Generates randomized test data.
    The following errors are possible:
    - loosing a point completely
    - adding randomized error to individual points
    '''

    def __init__(self, indicators, point, driver):
        super(TapMeasurement, self).__init__(indicators, point)
        active_dut = driver.active_dut_node
        self.dut_resolution = active_dut.resolution
        self.dut_width = active_dut.tnt_dut.width
        self.dut_height = active_dut.tnt_dut.height

    def _start(self):
        pass

    def _read_results(self):
        if self.point is None:
            self.results = [(406, 235, 0, 0, 11, str(time.time())), 'OK', '']
        else:

            # the whole point is lost with certain probability
            if random.uniform(0, 1) < settings.lost_points:
                pass

            else:
                # Calculate results
                error_x = round(random.uniform(-1, 1) * settings.max_x_error, ROUND_DECIMALS)
                error_y = round(random.uniform(-1, 1) * settings.max_y_error, ROUND_DECIMALS)
                error_azimuth = round(random.uniform(-1, 1) * settings.max_azimuth_error, ROUND_DECIMALS)
                error_tilt = round(random.uniform(-1, 1) * settings.max_tilt_error, ROUND_DECIMALS)

                x = self.point.x + error_x
                y = self.point.y + error_y
                azimuth = self.point.azimuth + error_azimuth
                tilt = self.point.tilt + error_tilt

                x, y = mm_to_pixels(self.dut_width, self.dut_height, self.dut_resolution, x, y)

                self.results = [(x, y, 0, 0, 11, str(time.time()), 0, azimuth, tilt), 'OK', '']


class ContinuousMeasurement(ContinuousMeasurementBase):
    '''
    Creates continues measurement data with errors added based on the settings.

    For line the following errors can be created:
    - variation in the number of touch events per line
    - missing all data for a line
    - breaking the line with following pattern: UP_EVENT, lost point, DOWN_EVENT
    - breaking the line with arbitrary number of missing points
    - adding randomized error to individual points
    - adding randomized error to interval between reported points
    - changing randomly finger id (ghost finger for one finger tests)

    For point the following errors can be created:
    - variation in the number of touch events per point
    - breaking the line with following pattern; UP_EVENT, lost point, DOWN_EVENT
    - breaking the line with arbitrary number of missing points
    - adding randomized error to individual points
    '''

    def __init__(self, indicators, line, driver):
        super(ContinuousMeasurement, self).__init__(indicators, line)

        self.point = None
        active_dut = driver.active_dut_node
        self.dut_resolution = active_dut.resolution
        self.dut_width = active_dut.tnt_dut.width
        self.dut_height = active_dut.tnt_dut.height

    def _start(self):
        pass

    def _read_results(self):
        line = self.line

        # Going through all the lines
        if line is not None:
            for finger in range(line.fingers):

                # The whole line is lost with certain probability
                if random.uniform(0, 1) < settings.lost_lines:
                    continue

                # In multifinger case we have to calculate offsets for all the fingers
                # The azimuth angle is in 0 along the x-axis
                azimuth_angle = line.angle
                unit_vec = azimuth_direction(numpy.radians(azimuth_angle))
                offset = finger * line.finger_distance

                offset_x = unit_vec[0] * offset
                offset_y = unit_vec[1] * offset

                start_x = line.start_x + offset_x
                start_y = line.start_y + offset_y
                end_x = line.end_x + offset_x
                end_y = line.end_y + offset_y

                # Number of measurement points is randomized within limits
                number_of_points = int(round(line.length() * settings.num_of_line_points_per_mm))
                number_of_points = max(1, number_of_points + random.randint(-settings.line_point_var,
                                                                            settings.line_point_var))

                # Adding hoover points to the start and end of the line
                num_hover_pts_start = 0
                num_hover_pts_end = 0
                total_hover_pts = 0
                if settings.start_end_hover_enabled:
                    num_hover_pts_start = random.randint(0, settings.max_hover_events)
                    num_hover_pts_end = random.randint(0, settings.max_hover_events)
                    total_hover_pts = num_hover_pts_start + num_hover_pts_end
                    number_of_points += num_hover_pts_start + num_hover_pts_end

                # Deciding if the line is broken or not and from where it if broken and how
                index_to_be_broken = None
                last_broken_index = None
                # Making sure we can remove the wanted amount of points from the middle
                # also considering if there are hove points
                num_missing_points = random.randint(1, settings.max_lost_points)
                min_size_of_broken_line = num_missing_points + settings.marginal * 2 + total_hover_pts
                if random.uniform(0, 1) < settings.broken_line and number_of_points > min_size_of_broken_line:
                    # 0: the line is broken by pattern: UP_EVENT, lost point, DOWN_EVENT
                    # 1: the line is broken by just losing arbitrary amount of points in the middle
                    decision = random.randint(0, 1)
                    if decision == 0:
                        try:  # this might fail and then we just don't break the line
                            min_index = settings.marginal + num_hover_pts_start
                            max_index = number_of_points - settings.marginal - num_hover_pts_end
                            index_to_be_broken = random.randint(min_index, max_index)
                        except:
                            index_to_be_broken = None
                    # Making sure we can delete the wanted amount of points
                    if decision == 1 and (num_missing_points < (number_of_points - END_POINT * 2 - total_hover_pts)):
                        # making sure we can actually remove the correct amount of points
                        # starting from the chosen index
                        min_index = END_POINT + num_hover_pts_start
                        max_index = number_of_points - num_missing_points - END_POINT - num_hover_pts_end
                        try:
                            index_to_be_broken = random.randint(min_index, max_index)
                            last_broken_index = index_to_be_broken + num_missing_points
                        except:
                            index_to_be_broken = None
                            last_broken_index = None

                # Going through the points for a line
                for i in range(number_of_points):
                    # Deciding the event for the point
                    if i < num_hover_pts_start:
                        event = HOVER_EVENT
                    elif i == num_hover_pts_start:
                        event = DOWN_EVENT
                    elif i == number_of_points - num_hover_pts_end - 1:
                        event = UP_EVENT
                    elif i > number_of_points - num_hover_pts_end - 1:
                        event = HOVER_EVENT
                    else:
                        event = TOUCH_EVENT

                    # If the line is decided to be broken, the breaking happens here
                    # one case has only start index defined the other start and end indices
                    if index_to_be_broken is not None and last_broken_index is None:
                        if i == index_to_be_broken - 1:
                            event = UP_EVENT
                        elif i == index_to_be_broken:
                            continue
                        elif i == index_to_be_broken + 1:
                            event = DOWN_EVENT
                    elif index_to_be_broken is not None and last_broken_index is not None:
                        if i >= index_to_be_broken and i <= last_broken_index:
                            continue

                    finger_id = finger
                    # Changing finger id to simulate ghost finger. By using the amount of fingers
                    # we ensure that we don't use any "real" finger id for ghost fingers
                    if random.uniform(0, 1) < settings.ghost_finger and event == TOUCH_EVENT:
                        finger_id = int(line.fingers)

                    # The real robot coordinate of the point
                    x = start_x - i * (start_x - end_x) / (float(number_of_points) - 1.0)
                    y = start_y - i * (start_y - end_y) / (float(number_of_points) - 1.0)

                    # Calculating errors
                    error_x = round(random.uniform(-1, 1) * settings.max_x_error, ROUND_DECIMALS)
                    error_y = round(random.uniform(-1, 1) * settings.max_y_error, ROUND_DECIMALS)
                    error_time = random.uniform(-1, 1) * settings.max_time_error
                    error_azimuth = round(random.uniform(-1, 1) * settings.max_azimuth_error, ROUND_DECIMALS)
                    error_tilt = round(random.uniform(-1, 1) * settings.max_tilt_error, ROUND_DECIMALS)

                    # Calculating the reported point
                    x = x + error_x
                    y = y + error_y
                    timestamp = i * settings.report_rate + error_time
                    azimuth = line.azimuth + error_azimuth
                    tilt = line.tilt + error_tilt

                    # Ensuring the data is still valid after error calculation
                    if timestamp < 0:
                        timestamp = 0

                    # Clip to DUT boundaries.
                    x = numpy.clip(x, 0, self.dut_width)
                    y = numpy.clip(y, 0, self.dut_height)

                    x, y = mm_to_pixels(self.dut_width, self.dut_height, self.dut_resolution, x, y)

                    self.results.append([(x, y, 0, finger_id, 11, timestamp, event, azimuth, tilt), 'OK', ''])

        # Going through points
        elif self.point is not None:
            point = self.point

            # Deciding the amount of reported touches for point or if point is lost
            if random.uniform(0, 1) > settings.lost_points:
                if settings.num_events_min < settings.num_events_max:
                    num_events = numpy.random.randint(settings.num_events_min, settings.num_events_max)
                else:
                    num_events = settings.num_events_min
            else:
                num_events = 0

            # Deciding if touches are missing or if there is up/down movement in the middle
            index_to_be_broken = None
            last_broken_index = None
            num_of_missing_events = random.randint(1, settings.max_lost_events)
            min_num_of_events = num_of_missing_events + settings.marginal * 2
            if random.uniform(0, 1) < settings.touch_error and num_events >= min_num_of_events:
                # 0: the line is broken by pattern: UP_EVENT, lost point, DOWN_EVENT
                # 1: the line is broken by just losing arbitrary amount of points in the middle
                decision = random.randint(0, 1)
                if decision == 0:
                    try:  # this might fail and then we just don't break the line
                        min_index = settings.marginal
                        max_index = num_events - settings.marginal
                        index_to_be_broken = random.randint(min_index, max_index)
                    except:
                        index_to_be_broken = None
                if decision == 1:
                    # making sure we can actually remove the correct amount of events
                    # starting from the chosen index
                    min_index = END_POINT
                    max_index = num_events - settings.max_lost_events - END_POINT
                    index_to_be_broken = random.randint(min_index, max_index)
                    last_broken_index = index_to_be_broken + num_of_missing_events

            for finger in range(point.fingers):
                # Loose a single point if a multifinger tool touch
                if random.uniform(0, 1) < settings.lost_multifinger:
                    continue

                # In multifinger case we have to calculate offsets for all the fingers
                # The azimuth angle is in 0 along the x-axis
                azimuth_angle = point.angle
                unit_vec = azimuth_direction(numpy.radians(azimuth_angle))
                offset = finger * point.finger_distance

                offset_x = unit_vec[0] * offset
                offset_y = unit_vec[1] * offset

                for i in range(0, num_events):
                    if i == 0:
                        # Event 0 is "down". With some low probability down is replaced by "move".
                        event = DOWN_EVENT
                    elif i == num_events - 1:
                        # Event 1 is "up". With some low probability down is replaced by "move".
                        event = UP_EVENT
                    else:
                        event = TOUCH_EVENT

                    # If the event is decided to be corrupted, the magic happens here
                    if index_to_be_broken is not None and last_broken_index is None:
                        # UP_EVENT, lost_point, DOWN_EVENT
                        if i == index_to_be_broken - 1:
                            event = UP_EVENT
                        elif i == index_to_be_broken:
                            continue
                        elif i == index_to_be_broken + 1:
                            event = DOWN_EVENT
                    elif index_to_be_broken is not None and last_broken_index is not None:
                        # just remove points
                        if i >= index_to_be_broken and i <= last_broken_index:
                            continue

                    finger_id = finger
                    # Changing finger id to simulate ghost finger. By using the amount of fingers
                    # we ensure that we don't use any "real" finger id for ghost fingers
                    if random.uniform(0, 1) < settings.ghost_finger and event == TOUCH_EVENT:
                        finger_id = int(point.fingers)

                    error_x = round(random.uniform(-1, 1) * settings.max_x_error, ROUND_DECIMALS)
                    error_y = round(random.uniform(-1, 1) * settings.max_y_error, ROUND_DECIMALS)

                    x = self.point.x + error_x + offset_x
                    y = self.point.y + error_y + offset_y

                    error_time = random.uniform(-1, 1) * settings.max_time_error
                    timestamp = i * settings.report_rate + error_time

                    # Ensuring the data is still valid after error calculation
                    if timestamp < 0:
                        timestamp = 0

                    x, y = mm_to_pixels(self.dut_width, self.dut_height, self.dut_resolution, x, y)

                    self.results.append([(x, y, 0, finger_id, 11, timestamp, event, 0, 0, 0), 'OK', ''])

                    # Add some delay as required by e.g. stationary reporting rate test.
                    time.sleep(0.1)


class LatencyMeasurement(TapMeasurementBase):
    """
    Latency measurement for simulator.
    The following error is possible:
    - delay being too high or to low.
    """

    def __init__(self, indicators, point, driver):
        super(LatencyMeasurement, self).__init__(indicators, point)

        # These parameters are needed to display test points in correct location in the UI when running
        # the script.
        active_dut = driver.active_dut_node
        self.dut_resolution = active_dut.resolution
        self.dut_width = active_dut.tnt_dut.width
        self.dut_height = active_dut.tnt_dut.height

        self.pit = driver.pit
        self.pit_index = driver.pit_index

    def _start(self):
        """
        Starts LatencyMeasurement.
        """
        # Start CLine. Params:
        # 1: Cline timeout (ms)
        # 2: Finger interrupt timeout (ms)
        # 3: Wait finger interrupt
        self.pit.CLine(8000, 5000, True)

    def _read_results(self):
        """
        Generates results for the FirstContactLatency test.
        """
        # Calculate a random delay in the given range
        dummy_delay = random.uniform(settings.min_delay, settings.max_delay)

        touch_time = time.time()

        # Delay is calculated this way so that we get something that resembles results from actual PIT as a result.
        delay = touch_time + dummy_delay

        x, y = mm_to_pixels(self.dut_width, self.dut_height, self.dut_resolution, self.point.x, self.point.y)
        self.results = [(x, y, 0, 0, delay, touch_time), 'OK', '']

    def _end(self):
        """
        Ends LatencyMeasurement.
        """
        # Stop reading
        self.pit.CLineOff()
