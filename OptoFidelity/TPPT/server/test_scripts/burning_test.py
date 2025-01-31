from os import path
import logging
from datetime import datetime
import random
logger = logging.getLogger(__name__)

try:
    from tntclient import tnt_robot_client, tnt_dut_client, tnt_client
except ImportError:
    print("TnT Client not found!")


def get_best_score(results):
    score = 0

    for result in results:
        score = max(score, result['score'])

    return score


class Settings:
    def __init__(self):
        # Test time in hours.
        self.testing_time = 64

        # Names of DUTs to use in tests
        self.dut_names = ["DUT1", "DUT2"]

        # Workspace limits for the tests.
        # Make sure that especially z range is such that there is no danger of collision.
        self.robot_min_x = 10
        self.robot_max_x = 550
        self.robot_min_y = 10
        self.robot_max_y = 550
        self.robot_min_z = -20
        self.robot_max_z = -20

        # Wrist motion limits for testing of Stylus testers.
        # Use zeros by default to be compatible with all standard robots.
        self.tilt_min = 0
        self.tilt_max = 0  # 45
        self.azimuth_min = 0  # -45
        self.azimuth_max = 0  # 45

        # Velocity and acceleration are randomly chosen between min and max values.
        # For the first test round, set both min and max values to the maximum values that the robot should
        # be able to handle. This is to make sure there will be no errors. If that is ok, then make the min values
        # something much smaller than max.
        self.min_acceleration = 300
        self.max_acceleration = 300
        self.min_velocity = 120
        self.max_velocity = 120

        # Velocity and acceleration are randomly chosen between min and max values.
        # These are used for movements where effector travels an arc i.e. there is azimuth rotation involved.
        # Usually lower velocity and acceleration must be used than in linear movement.
        #self.min_arc_acceleration = 50
        self.min_arc_acceleration = 100
        self.max_arc_acceleration = 100
        self.min_arc_velocity = 50
        self.max_arc_velocity = 50

        # Force in grams.
        self.min_force = 100
        self.max_force = 500

        # Settings for icon detection test.
        self.object_image = "test_image.png"
        self.object_shm = "of_logo.shm,robot.shm,atom.shm,coffee.shm"

        # Settings for OCR test.
        self.text_string = "OptoFidelity,Touch Panel Performance Test"
        self.text_image = "test_image.png"

        # Number of times to go around the workspace in movement test.
        self.movement_count = 2
        self.tap_count = 10
        self.swipe_count = 10
        self.press_count = 10
        self.drag_count = 10

        # Padding for DUT. Positive value makes gestures performed closer to DUT center.
        self.dut_padding = 20
        self.min_clearance = -0.5
        self.max_clearance = 2
        self.swipe_radius = 6

        # Synchro settings.
        self.min_separation = 40
        self.max_separation = 60

        # Names of tests to run.
        self.test_names = [
            "homing",
            "movement",
            "two_finger",
            "tap",
            "swipe",
            "drag",
            "random",
            "pinch",
            "drumroll",
            "compass",
            "compass_tap",
            "touch_and_tap",
            "line_tap",
             "press",
             "find_object",
             "search_text"
        ]


class BurningTest:
    """
    Burning test is used in development to run long test sequences that test
    robot functionality and stability.
    """

    # Exclude from pytest.
    __test__ = False

    def __init__(self, settings):
        self.settings = settings

        # Robot client.
        self.robot = tnt_client.TnTClient().robot("Robot1")

        # DUT clients.
        self.duts = []

    def set_random_velocity(self):
        robot = self.robot

        velocity_min = self.settings.min_velocity
        velocity_max = self.settings.max_velocity
        acceleration_min = self.settings.min_acceleration
        acceleration_max = self.settings.max_acceleration

        velocity = random.uniform(velocity_min, velocity_max)
        acceleration = random.uniform(acceleration_min, acceleration_max)

        print("Setting velocity {} and acceleration {}".format(velocity, acceleration))
        robot.set_speed(velocity, acceleration)

    def set_random_arc_velocity(self):
        robot = self.robot

        velocity_min = self.settings.min_arc_velocity
        velocity_max = self.settings.max_arc_velocity
        acceleration_min = self.settings.min_arc_acceleration
        acceleration_max = self.settings.max_arc_acceleration

        velocity = random.uniform(velocity_min, velocity_max)
        acceleration = random.uniform(acceleration_min, acceleration_max)

        print("Setting velocity {} and acceleration {}".format(velocity, acceleration))
        robot.set_speed(velocity, acceleration)

    def test_homing(self):
        x = (self.settings.robot_min_x + self.settings.robot_max_x) * 0.5
        y = (self.settings.robot_min_y + self.settings.robot_max_y) * 0.5

        # Move robot to center in xy plane and to minimum z.
        # Homing should be tested at minimum z to make sure the motor is powerful enough.
        self.robot.move(x, y, self.settings.robot_min_z)

        # Homer robot.
        self.robot.go_home()

    def test_movement(self):
        robot = self.robot

        for index in range(self.settings.movement_count):
            # Set speeds
            self.set_random_velocity()

            # Move around xy limits at max z.
            robot.move(self.settings.robot_min_x, self.settings.robot_min_y, self.settings.robot_max_z)
            robot.move(self.settings.robot_max_x, self.settings.robot_min_y, self.settings.robot_max_z)
            robot.move(self.settings.robot_max_x, self.settings.robot_max_y, self.settings.robot_max_z)
            robot.move(self.settings.robot_min_x, self.settings.robot_max_y, self.settings.robot_max_z)
            robot.move(self.settings.robot_min_x, self.settings.robot_min_y, self.settings.robot_max_z)

            # Move around xy limits at min z.
            robot.move(self.settings.robot_min_x, self.settings.robot_min_y, self.settings.robot_min_z)
            robot.move(self.settings.robot_max_x, self.settings.robot_min_y, self.settings.robot_min_z)
            robot.move(self.settings.robot_max_x, self.settings.robot_max_y, self.settings.robot_min_z)
            robot.move(self.settings.robot_min_x, self.settings.robot_max_y, self.settings.robot_min_z)
            robot.move(self.settings.robot_min_x, self.settings.robot_min_y, self.settings.robot_min_z)

    def test_two_finger(self):
        robot = self.robot
        robot_z = self.settings.robot_max_z

        # Use low linear speed to avoid large angular speed.
        self.set_random_arc_velocity()

        center_x = (self.settings.robot_min_x + self.settings.robot_max_x) / 2
        center_y = (self.settings.robot_min_y + self.settings.robot_max_y) / 2

        try:
            print("Active finger: ")
            print(robot.get_active_finger())

            # Move robot to workspace center and do some rotations and finger separation changes.
            robot.move(center_x, center_y, robot_z)
            robot.move(center_x, center_y, robot_z, azimuth=-60)
            robot.set_finger_separation(self.settings.max_separation)
            robot.move(center_x, center_y, robot_z, azimuth=60)
            robot.set_finger_separation((self.settings.min_separation + self.settings.max_separation) * 0.5)
            robot.move(center_x, center_y, robot_z)
            robot.set_finger_separation(self.settings.min_separation)

            print("Finger Separation: ")
            print(robot.get_finger_separation())

            robot.set_active_finger(1)
            print("Active finger: ")
            print(robot.get_active_finger())

            robot.move(center_x, center_y, robot_z)
            robot.move(center_x, center_y, robot_z, azimuth=-60)
            robot.set_finger_separation(self.settings.max_separation)
            robot.move(center_x, center_y, robot_z, azimuth=60)
            robot.set_finger_separation((self.settings.min_separation + self.settings.max_separation) * 0.5)
            robot.move(center_x, center_y, robot_z)
            robot.set_finger_separation(self.settings.min_separation)
        finally:
            # Make sure that active finger is reset in case of any errors.
            robot.set_active_finger(0)
            print("Active finger: ")
            print(robot.get_active_finger())

    def test_tap(self):
        for dut in self.duts:
            base_distance = dut.base_distance
            dut.jump(0, 0, base_distance)

            for i in range(self.settings.tap_count):

                # Random point
                padding = self.settings.dut_padding
                rand_x = random.uniform(padding, dut.width - padding)
                rand_y = random.uniform(padding, dut.height - padding)
                tilt = random.uniform(self.settings.tilt_min, self.settings.tilt_max)
                azimuth = random.uniform(self.settings.azimuth_min, self.settings.azimuth_max)
                clearance = random.uniform(self.settings.min_clearance, self.settings.max_clearance)

                self.set_random_velocity()

                dut.jump(rand_x, rand_y, base_distance, base_distance)

                # Perform tap gesture.
                dut.tap(rand_x, rand_y, tilt=tilt, azimuth=azimuth, clearance=clearance)
                dut.double_tap(rand_x, rand_y, tilt=tilt, azimuth=azimuth, clearance=clearance)

    def test_swipe(self):

        for dut in self.duts:
            # Jump over DUT origin.
            base_distance = dut.base_distance
            dut.jump(0.0, 0.0, base_distance)
            swipe_count = self.settings.swipe_count

            for i in range(swipe_count):
                # Random swipes
                padding = self.settings.dut_padding
                start_x = random.uniform(padding, dut.width - padding)
                start_y = random.uniform(padding, dut.height - padding)
                end_x = random.uniform(padding, dut.width - padding)
                end_y = random.uniform(padding, dut.height - padding)
                start_tilt = random.uniform(self.settings.tilt_min, self.settings.tilt_max)
                end_tilt = random.uniform(self.settings.tilt_min, self.settings.tilt_max)
                start_azimuth = random.uniform(self.settings.azimuth_min, self.settings.azimuth_max)
                end_azimuth = random.uniform(self.settings.azimuth_min, self.settings.azimuth_max)
                clearance = random.uniform(self.settings.min_clearance, self.settings.max_clearance)

                self.set_random_velocity()

                # Jump with default velocity over the start point of the line to swipe.
                dut.jump(start_x, start_y, base_distance, base_distance)

                # Perform swipe gesture.
                dut.swipe(start_x, start_y, end_x, end_y, tilt1=start_tilt, tilt2=end_tilt, azimuth1=start_azimuth,
                          azimuth2=end_azimuth, clearance=clearance, radius=self.settings.swipe_radius)

    def test_random(self):
        random_count = 10

        for i in range(random_count):
            test = random.randint(0, 3)
            dut_ix = random.randint(0, len(self.duts) - 1)
            dut = self.duts[dut_ix]

            base_distance = dut.base_distance

            padding = self.settings.dut_padding
            start_x = random.uniform(padding, dut.width - padding)
            start_y = random.uniform(padding, dut.height - padding)
            end_x = random.uniform(padding, dut.width - padding)
            end_y = random.uniform(padding, dut.height - padding)
            clearance = random.uniform(self.settings.min_clearance, self.settings.max_clearance)

            self.set_random_velocity()

            # Tap
            if test == 0:
                dut.jump(start_x, start_y, base_distance)
                dut.tap(start_x, start_y, clearance=clearance)
            # Swipe
            elif test == 1:
                dut.jump(start_x, start_y, base_distance)
                dut.swipe(start_x, start_y, end_x, end_y, clearance=clearance, radius=self.settings.swipe_radius)

    def test_pinch(self):
        self.set_random_arc_velocity()

        for dut in self.duts:
            base_distance = dut.base_distance
            dut.jump(0, 0, base_distance)

            x = dut.width / 2
            y = dut.height / 2

            dut.pinch(x, y, self.settings.min_separation, self.settings.max_separation, 0.0)
            dut.pinch(x, y, self.settings.max_separation, self.settings.min_separation, 0.0)

            dut.pinch(x, y, self.settings.min_separation, self.settings.max_separation, -60.0)
            dut.pinch(x, y, self.settings.max_separation, self.settings.min_separation, -60.0)

            dut.pinch(x, y, self.settings.min_separation, self.settings.max_separation, 60.0)
            dut.pinch(x, y, self.settings.max_separation, self.settings.min_separation, 60.0)

    def test_drumroll(self):
        self.set_random_arc_velocity()

        for dut in self.duts:
            base_distance = dut.base_distance
            dut.jump(0, 0, base_distance)

            x = dut.width / 2
            y = dut.height / 2

            separation = random.uniform(self.settings.min_separation, self.settings.max_separation)

            dut.drumroll(x, y, 0.0, self.settings.min_separation, 10, 5.0, -0.5)
            dut.drumroll(x, y, -60.0, self.settings.max_separation, 15, 5.0, -0.5)
            dut.drumroll(x, y, 60.0, separation, 10, 3.0, -0.5)

    def test_compass(self):
        self.set_random_arc_velocity()

        for dut in self.duts:
            base_distance = dut.base_distance
            dut.jump(0, 0, base_distance)

            x = dut.width / 2
            y = dut.height / 2

            dut.compass(x, y, -40.0, 40.0, self.settings.min_separation, 10, -0.5)
            dut.compass(x, y, -50.0, 50.0, self.settings.max_separation, 10, -0.5)

    def test_compass_tap(self):
        self.set_random_arc_velocity()

        for dut in self.duts:
            base_distance = dut.base_distance
            dut.jump(0, 0, base_distance)

            x = dut.width / 2
            y = dut.height / 2

            dut.compass_tap(x, y, -40.0, 40.0, self.settings.min_separation, 10.0, 10, False, -0.5)
            dut.compass_tap(x, y, -60.0, 60.0, self.settings.max_separation, 12.0, 10, True, -0.5)

    def test_touch_and_tap(self):
        self.set_random_arc_velocity()

        for dut in self.duts:
            base_distance = dut.base_distance
            dut.jump(0, 0, base_distance)

            x = dut.width / 2
            y = dut.height / 2

            dut.touch_and_tap(x, y, x + 40.0, y, 10, 4, 1.0, 0.5, 0.1, 0)
            dut.touch_and_tap(x, y, x, y + 40.0, 10, 4, 1.0, 0.5, 0.1, 0)

    def test_line_tap(self):
        self.set_random_arc_velocity()

        for dut in self.duts:
            base_distance = dut.base_distance
            dut.jump(0, 0, base_distance)

            x = dut.width / 2
            y = dut.height / 2

            separation = random.uniform(self.settings.min_separation, self.settings.max_separation)

            dut.line_tap(x, y, x + 60.0, y, [30.0, 35.0, 40.0], separation, 0.0, 10, 0)
            dut.line_tap(x, y, x, y + 60.0, [30.0, 35.0, 40.0], separation, 0.0, 10, 0)

    def test_press(self):

        press_count = self.settings.press_count

        for dut in self.duts:
            base_distance = dut.base_distance
            dut.jump(0, 0, base_distance)

            for i in range(press_count):
                # Random point
                padding = self.settings.dut_padding
                rand_x = random.uniform(padding, dut.width - padding)
                rand_y = random.uniform(padding, dut.height - padding)

                self.set_random_velocity()

                dut.jump(rand_x, rand_y, base_distance, base_distance)

                # Random force
                force = random.uniform(self.settings.min_force, self.settings.max_force)

                # Random duration
                duration = random.uniform(1, 5)

                # Perform tap gesture.
                dut.press(rand_x, rand_y, force, z=10, tilt=0, azimuth=0, duration=duration)

    def test_drag(self):
        drag_count = self.settings.drag_count

        for dut in self.duts:

            base_distance = dut.base_distance
            dut.jump(0, 0, base_distance)

            for i in range(drag_count):

                # Random point
                padding = self.settings.dut_padding
                start_x = random.uniform(padding, dut.width - padding)
                start_y = random.uniform(padding, dut.height - padding)
                end_x = random.uniform(padding, dut.width - padding)
                end_y = random.uniform(padding, dut.height - padding)
                clearance = random.uniform(self.settings.min_clearance, self.settings.max_clearance)

                self.set_random_velocity()

                dut.jump(start_x, start_y, base_distance, base_distance)

                # Perform tap gesture.
                dut.drag(start_x, start_y, end_x, end_y, clearance=clearance)

                # TODO: drag_force is not working on server side yet
                # dut.drag_force(line.end_x, line.end_y, line.start_x, line.start_y, force)

    def test_find_object(self):
        # TODO: Decide path and add icon data.
        SHM_DIR = "shm"

        for dut in self.duts:
            dut.send_image(self.settings.object_image)

            for object_shm in self.settings.object_shm.split(","):
                object_shm = object_shm.strip()

                print("Object to Find: " + object_shm)

                response = dut.find_objects(path.join(SHM_DIR, object_shm))

                if not response["success"] or len(response["results"]) == 0:
                    raise Exception("Could not find object {}!".format(object_shm))

                for result in response["results"]:
                    print("Found object with result: " + str(result))

                if get_best_score(response["results"]) < 0.95:
                    raise Exception("Could not find object {} with sufficient score!".format(object_shm))

            dut.send_image(None)

    def test_search_text(self):
        # TODO: Decide path and add image data.
        for dut in self.duts:
            dut.send_image(self.settings.text_image)

            for text in self.settings.text_string.split(","):
                text = text.strip()

                print("Text to Find: " + text)

                response = dut.search_text(text)

                if not response["success"] or len(response["results"]) == 0:
                    raise Exception("Could not find text!")

                for result in response["results"]:
                    print("Found text with result: " + str(result))

                if get_best_score(response["results"]) < 0.95:
                    raise Exception("Could not find object {} with sufficient score!".format(object_shm))

            dut.send_image(None)

    def execute(self):
        """
        Run selected tests.
        """

        # Get selected duts from main sequence
        client = tnt_client.TnTClient()
        self.duts = [client.dut(dut_name) for dut_name in self.settings.dut_names]

        if len(self.duts) == 0:
            raise Exception("Invalid dut(s)!")

        print("Running Burning Test for DUTs:")

        for dut_name in self.settings.dut_names:
            print(dut_name)

        print("Testing time: {} hours".format(self.settings.testing_time))

        # For taking time
        done = False
        start_time = datetime.now()
        print("Starting time: {}".format(start_time))

        random.seed()

        # Run test until the desired time is full.
        while done is False:

            # Loop through all test definitions.
            for test_name in self.settings.test_names:
                print("Burning test: " + test_name)

                # Test method name is determined from test name.
                method_name = "test_" + test_name

                method = getattr(self, method_name)

                # Run test.
                method()

            time_now = datetime.now()
            delta_time = time_now - start_time

            print("Testing time: {}".format(delta_time))

            if float(delta_time.seconds) / 60 / 60 >= float(self.settings.testing_time):
                done = True

        print("Burning test done.")


if __name__ == "__main__":
    settings = Settings()
    burning_test = BurningTest(settings)
    burning_test.execute()
