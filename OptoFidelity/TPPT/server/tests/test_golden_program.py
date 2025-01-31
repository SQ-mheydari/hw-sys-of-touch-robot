from tntserver.drivers.robots.golden_program import *
from tntserver.Nodes.Node import Node
import pytest


class RobotPosition(RobotKinematics.RobotPositionBase):
    __slots__ = ["frame", "d", "t", "separation"]
    pass


class FailCommand(Command):
    def __init__(self):
        super().__init__()

    def execute(self):
        raise Exception()


class StubKinematics:
    def __init__(self):
        self._robotposition_cls = RobotPosition
        self._arc_r = 50.0

    def arc_r(self, toolframe, kinematic_name):
        return self._arc_r


class StubDriver:
    def __init__(self):
        self.axes = {}
        self.force_active = False
        self.current_frame = robotmath.identity_frame()
        self._kinematics = StubKinematics()

    def create_robot_position(self, **kwargs):
        return self._kinematics._robotposition_cls(**kwargs)

    def position(self, kinematic_name, tool):
        pos = self.create_robot_position()
        pos.frame = self.current_frame

        return pos


class StubRobot(Node):
    def __init__(self, name):
        super().__init__(name)

        self.driver = StubDriver()


class StubPrimitive:
    """
    Stub class to act as Primitive for the tests.
    """

    def __init__(self, length):
        self._length = length
        self._positions = []

    def append_to_path(self, path):
        pass

    def set_positions(self, p):
        self._positions = p

    def length(self):
        return self._length


class StubProgram:
    def __init__(self, arc_r, position=None):
        self._arc_r = arc_r
        self._position = position

        self.previousContext = None
        self.context = None
        self.transform = None
        self.surface = None

        self.robot = StubRobot("robot")

        self.speed = None
        self.acceleration = None

    def arc_r(self):
        return self._arc_r

    def position(self):
        return self._position

    def create_robot_position(self, **kwargs):
        return self.robot.driver.create_robot_position(**kwargs)


def test_join_primitive():
    """
    Test JoinPrimitive class with multiple different join examples.
    """

    def test_join_primitive_stubs(lengths, speed, acceleration, plot):
        """
        Test JoinPrimitive with multiple stub primitives to be joined.
        """
        stubs = []

        for length in lengths:
            stubs.append(StubPrimitive(length))

        join = JoinPrimitive(stubs, 0.0)
        join.set_speed_acceleration(speed, acceleration)

        path = []
        join.append_to_path(path)

        # Get primitive track positions after primitives have been joined.
        positions = []

        travel = 0

        for primitive in join._primitives:
            primitive_positions = [d + travel for d, t in primitive._positions]
            positions += primitive_positions
            travel += primitive.length()

        # Create track the same way as in JoinPrimitive for comparison.
        track = create_track(join._speed, join._acceleration, join.length())

        # Original track must be the same as track obtained by combining the joined primitives.
        # Positions are in mm. Choose absolute tolerance appropriate for this range.
        assert len(track) == len(positions)
        assert np.allclose(positions, np.array(track)[:, 0], atol=1e-6)

        # Optionally plot the positions created by JoinPrimitive.
        if plot:
            import matplotlib.pyplot as plt

            plt.figure(1)
            t_vect = np.linspace(0, TIME_STEP * len(positions), len(positions))
            plt.subplot(311)
            plt.plot(t_vect, positions)
            plt.subplot(312)
            plt.plot(t_vect[1:], np.diff(positions)*(1/TIME_STEP))
            plt.subplot(313)
            plt.plot(t_vect[2:], np.diff(positions, n=2)*(1/TIME_STEP)**2)
            plt.grid()
            plt.show()

    # Test different number of primitives and different speeds and accelerations.
    test_join_primitive_stubs([10, 50, 10], 296, 496, False)
    test_join_primitive_stubs([10, 50, 10], 248, 52, False)
    test_join_primitive_stubs([10, 50, 10], 15, 53, False)

    test_join_primitive_stubs([183, 81, 94, 174], 296, 496, False)
    test_join_primitive_stubs([182, 285], 296, 496, False)
    test_join_primitive_stubs([64], 296, 496, False)


def test_create_track():
    positions = create_track(100, 200, 30)

    # N.B. the positions list is one step short of the segment [0, 30].
    ref_positions = [(0.0, 0), (0.0015999999999999999, 0.004), (0.0063999999999999994, 0.008), (0.0144, 0.012), (0.025599999999999998, 0.016), (0.04, 0.02), (0.0576, 0.024), (0.07840000000000001, 0.028), (0.10239999999999999, 0.032), (0.12960000000000002, 0.036000000000000004), (0.1600000000000001, 0.04000000000000001), (0.1936000000000001, 0.04400000000000001), (0.23040000000000013, 0.048000000000000015), (0.2704000000000002, 0.05200000000000002), (0.31360000000000027, 0.05600000000000002), (0.3600000000000003, 0.060000000000000026), (0.4096000000000004, 0.06400000000000003), (0.4624000000000005, 0.06800000000000003), (0.5184000000000005, 0.07200000000000004), (0.5776000000000006, 0.07600000000000004), (0.6400000000000007, 0.08000000000000004), (0.7056000000000008, 0.08400000000000005), (0.7744000000000009, 0.08800000000000005), (0.8464000000000009, 0.09200000000000005), (0.9216000000000011, 0.09600000000000006), (1.0000000000000013, 0.10000000000000006), (1.0816000000000012, 0.10400000000000006), (1.1664000000000014, 0.10800000000000007), (1.2544000000000015, 0.11200000000000007), (1.345600000000002, 0.11600000000000008), (1.440000000000002, 0.12000000000000008), (1.537600000000002, 0.12400000000000008), (1.6384000000000023, 0.12800000000000009), (1.7424000000000022, 0.1320000000000001), (1.8496000000000026, 0.1360000000000001), (1.9600000000000026, 0.1400000000000001), (2.073600000000003, 0.1440000000000001), (2.190400000000003, 0.1480000000000001), (2.3104000000000036, 0.1520000000000001), (2.4336000000000033, 0.1560000000000001), (2.5600000000000036, 0.16000000000000011), (2.689600000000004, 0.16400000000000012), (2.822400000000004, 0.16800000000000012), (2.9584000000000046, 0.17200000000000013), (3.0976000000000043, 0.17600000000000013), (3.2400000000000047, 0.18000000000000013), (3.3856000000000055, 0.18400000000000014), (3.534400000000005, 0.18800000000000014), (3.6864000000000057, 0.19200000000000014), (3.8416000000000055, 0.19600000000000015), (4.000000000000006, 0.20000000000000015), (4.161600000000006, 0.20400000000000015), (4.326400000000007, 0.20800000000000016), (4.494400000000007, 0.21200000000000016), (4.6656000000000075, 0.21600000000000016), (4.840000000000008, 0.22000000000000017), (5.017600000000008, 0.22400000000000017), (5.1984000000000075, 0.22800000000000017), (5.382400000000008, 0.23200000000000018), (5.569600000000008, 0.23600000000000018), (5.760000000000009, 0.24000000000000019), (5.953600000000009, 0.2440000000000002), (6.150400000000009, 0.2480000000000002), (6.3504000000000085, 0.25200000000000017), (6.553600000000009, 0.25600000000000017), (6.760000000000009, 0.2600000000000002), (6.969600000000009, 0.2640000000000002), (7.182400000000009, 0.2680000000000002), (7.39840000000001, 0.2720000000000002), (7.61760000000001, 0.2760000000000002), (7.8400000000000105, 0.2800000000000002), (8.065600000000012, 0.2840000000000002), (8.294400000000012, 0.2880000000000002), (8.526400000000011, 0.2920000000000002), (8.761600000000012, 0.2960000000000002), (9.000000000000012, 0.3000000000000002), (9.241600000000014, 0.3040000000000002), (9.486400000000012, 0.3080000000000002), (9.734400000000013, 0.3120000000000002), (9.985600000000014, 0.3160000000000002), (10.240000000000014, 0.32000000000000023), (10.497600000000014, 0.32400000000000023), (10.758400000000016, 0.32800000000000024), (11.022400000000015, 0.33200000000000024), (11.289600000000016, 0.33600000000000024), (11.560000000000016, 0.34000000000000025), (11.833600000000018, 0.34400000000000025), (12.110400000000016, 0.34800000000000025), (12.390400000000017, 0.35200000000000026), (12.673600000000018, 0.35600000000000026), (12.960000000000019, 0.36000000000000026), (13.24960000000002, 0.36400000000000027), (13.542400000000022, 0.36800000000000027), (13.83840000000002, 0.3720000000000003), (14.13760000000002, 0.3760000000000003), (14.440000000000023, 0.3800000000000003), (14.745600000000023, 0.3840000000000003), (15.054301533139132, 0.3880000000000003), (15.361978868532317, 0.3920000000000003), (15.666456203925504, 0.3960000000000003), (15.967733539318692, 0.4000000000000003), (16.265810874711878, 0.4040000000000003), (16.560688210105067, 0.4080000000000003), (16.85236554549825, 0.4120000000000003), (17.140842880891437, 0.4160000000000003), (17.426120216284627, 0.4200000000000003), (17.708197551677813, 0.4240000000000003), (17.987074887071, 0.4280000000000003), (18.262752222464187, 0.43200000000000033), (18.53522955785737, 0.43600000000000033), (18.80450689325056, 0.44000000000000034), (19.070584228643746, 0.44400000000000034), (19.33346156403693, 0.44800000000000034), (19.59313889943012, 0.45200000000000035), (19.849616234823305, 0.45600000000000035), (20.10289357021649, 0.46000000000000035), (20.35297090560968, 0.46400000000000036), (20.599848241002864, 0.46800000000000036), (20.843525576396054, 0.47200000000000036), (21.084002911789238, 0.47600000000000037), (21.32128024718243, 0.48000000000000037), (21.555357582575613, 0.4840000000000004), (21.786234917968798, 0.4880000000000004), (22.013912253361987, 0.4920000000000004), (22.238389588755172, 0.4960000000000004), (22.459666924148355, 0.5000000000000003), (22.67774425954154, 0.5040000000000003), (22.89262159493473, 0.5080000000000003), (23.104298930327914, 0.5120000000000003), (23.312776265721098, 0.5160000000000003), (23.51805360111429, 0.5200000000000004), (23.720130936507477, 0.5240000000000004), (23.91900827190066, 0.5280000000000004), (24.114685607293847, 0.5320000000000004), (24.307162942687036, 0.5360000000000004), (24.49644027808022, 0.5400000000000004), (24.682517613473408, 0.5440000000000004), (24.865394948866594, 0.5480000000000004), (25.04507228425978, 0.5520000000000004), (25.22154961965297, 0.5560000000000004), (25.394826955046156, 0.5600000000000004), (25.56490429043934, 0.5640000000000004), (25.731781625832525, 0.5680000000000004), (25.895458961225714, 0.5720000000000004), (26.0559362966189, 0.5760000000000004), (26.213213632012085, 0.5800000000000004), (26.367290967405275, 0.5840000000000004), (26.518168302798465, 0.5880000000000004), (26.665845638191644, 0.5920000000000004), (26.81032297358483, 0.5960000000000004), (26.951600308978016, 0.6000000000000004), (27.089677644371207, 0.6040000000000004), (27.22455497976439, 0.6080000000000004), (27.35623231515758, 0.6120000000000004), (27.484709650550762, 0.6160000000000004), (27.60998698594395, 0.6200000000000004), (27.73206432133714, 0.6240000000000004), (27.850941656730328, 0.6280000000000004), (27.966618992123507, 0.6320000000000005), (28.079096327516698, 0.6360000000000005), (28.188373662909882, 0.6400000000000005), (28.29445099830307, 0.6440000000000005), (28.397328333696258, 0.6480000000000005), (28.497005669089447, 0.6520000000000005), (28.593483004482636, 0.6560000000000005), (28.686760339875818, 0.6600000000000005), (28.776837675269, 0.6640000000000005), (28.863715010662187, 0.6680000000000005), (28.947392346055373, 0.6720000000000005), (29.027869681448564, 0.6760000000000005), (29.10514701684175, 0.6800000000000005), (29.179224352234932, 0.6840000000000005), (29.250101687628124, 0.6880000000000005), (29.317779023021302, 0.6920000000000005), (29.382256358414494, 0.6960000000000005), (29.44353369380768, 0.7000000000000005), (29.50161102920087, 0.7040000000000005), (29.556488364594053, 0.7080000000000005), (29.60816569998724, 0.7120000000000005), (29.65664303538042, 0.7160000000000005), (29.70192037077361, 0.7200000000000005), (29.743997706166798, 0.7240000000000005), (29.782875041559986, 0.7280000000000005), (29.81855237695318, 0.7320000000000005), (29.851029712346357, 0.7360000000000005), (29.88030704773954, 0.7400000000000005), (29.906384383132725, 0.7440000000000005), (29.929261718525915, 0.7480000000000006), (29.948939053919105, 0.7520000000000006), (29.965416389312292, 0.7560000000000006), (29.978693724705472, 0.7600000000000006), (29.98877106009866, 0.7640000000000006), (29.99564839549184, 0.7680000000000006), (29.99932573088503, 0.7720000000000006)]

    assert np.allclose(positions, ref_positions)


def test_create_track_zero_length():
    positions = create_track(100, 200, 0)

    assert len(positions) == 1
    assert np.allclose(positions, [(0.0, 0.0)])


def test_create_track_invalid_parameters():
    with pytest.raises(Exception):
        create_track(max_speed=-1, acceleration=200, distance=30)

    with pytest.raises(Exception):
        create_track(max_speed=0, acceleration=200, distance=30)

    with pytest.raises(Exception):
        create_track(max_speed=10, acceleration=-1, distance=30)

    with pytest.raises(Exception):
        create_track(max_speed=10, acceleration=0, distance=30)

    with pytest.raises(Exception):
        create_track(max_speed=100, acceleration=200, distance=-1)


def test_primitive():
    p = Primitive()

    assert p.length() == 0

    path = []
    p.append_to_path(path)
    assert len(path) == 0

    assert p._positions == None

    positions = [1, 2, 3]
    p.set_positions(positions)

    assert np.allclose(p._positions, positions)

    assert p._speed is None
    assert p._acceleration is None

    p.set_speed_acceleration(30, 60)

    assert p._speed == 30
    assert p._acceleration == 60


def test_line_primitive_move():
    program = StubProgram(arc_r=0.0)

    f1 = robotmath.xyz_to_frame(10, 20, 30)
    f2 = robotmath.xyz_to_frame(40, 50, 60)

    p = LinePrimitive(f1, f2)
    p.program = program

    assert np.isclose(p.length(), math.sqrt(3 * 30**2))


def test_line_primitive_rotate():
    program = StubProgram(arc_r=50.0)

    # Rotate quarter revolution.
    f1 = robotmath.xyz_euler_to_frame(0, 0, 0, 0, 0, 90)
    f2 = robotmath.xyz_euler_to_frame(0, 0, 0, 0, 0, 180)

    p = LinePrimitive(f1, f2)
    p.program = program

    # Check arc length.
    assert np.isclose(p.length(), 2 * math.pi * program.arc_r() / 4)


def test_line_primitive_move_and_rotate():
    program = StubProgram(arc_r=50.0)

    arc_length = 2 * math.pi * program.arc_r() / 4

    # Rotate quarter revolution and move less than that.
    f1 = robotmath.xyz_euler_to_frame(0, 0, 0, 0, 0, 90)
    f2 = robotmath.xyz_euler_to_frame(arc_length / 2, 0, 0, 0, 0, 180)

    p = LinePrimitive(f1, f2)
    p.program = program

    # Length should be arc length.
    assert np.isclose(p.length(), arc_length)

    # Rotate quarter revolution and move more than that.
    f1 = robotmath.xyz_euler_to_frame(0, 0, 0, 0, 0, 90)
    f2 = robotmath.xyz_euler_to_frame(arc_length * 2, 0, 0, 0, 0, 180)

    p = LinePrimitive(f1, f2)
    p.program = program

    # Length should be move length.
    assert np.isclose(p.length(), arc_length * 2)


def test_line_primitive_zero_length_path():
    program = StubProgram(arc_r=0.0)

    f1 = robotmath.xyz_to_frame(10, 20, 30)
    f2 = robotmath.xyz_to_frame(10, 20, 30)

    p = LinePrimitive(f1, f2)
    p.program = program

    path = []

    p.append_to_path(path)

    assert len(path) == 1

    position = path[0]
    assert np.allclose(position.frame, robotmath.xyz_to_frame(10, 20, 30))
    assert position.d == 0
    assert position.t == 0


def test_line_primitive_path():
    program = StubProgram(arc_r=50.0)

    # Rotate quarter revolution and move less than that.
    f1 = robotmath.xyz_euler_to_frame(0, 0, 0, 0, 0, 80)
    f2 = robotmath.xyz_euler_to_frame(20, 0, 0, 0, 0, 90)

    p = LinePrimitive(f1, f2)
    p.program = program
    p.set_speed_acceleration(100, 800)

    path = []

    p.append_to_path(path)

    positions = []

    for robotpos in path:
        x, y, z, a, b, c = robotmath.frame_to_xyz_euler(robotpos.frame)
        positions.append((x, y, z, c))

    ref_positions = [(0.0, 0.0, 0.0, 80.00000000000003), (0.0063999999999999994, 0.0, 0.0, 80.0032), (0.025599999999999998, 0.0, 0.0, 80.0128), (0.057599999999999998, 0.0, 0.0, 80.0288), (0.10239999999999999, 0.0, 0.0, 80.0512), (0.16, 0.0, 0.0, 80.08000000000001), (0.23039999999999999, 0.0, 0.0, 80.11519999999999), (0.31360000000000005, 0.0, 0.0, 80.15679999999999), (0.40959999999999996, 0.0, 0.0, 80.2048), (0.51840000000000008, 0.0, 0.0, 80.2592), (0.64000000000000035, 0.0, 0.0, 80.32000000000001), (0.77440000000000042, 0.0, 0.0, 80.38719999999999), (0.92160000000000042, 0.0, 0.0, 80.46079999999999), (1.0816000000000008, 0.0, 0.0, 80.5408), (1.2544000000000011, 0.0, 0.0, 80.62719999999999), (1.4400000000000013, 0.0, 0.0, 80.71999999999998), (1.6384000000000016, 0.0, 0.0, 80.81920000000001), (1.8496000000000019, 0.0, 0.0, 80.92480000000002), (2.0736000000000021, 0.0, 0.0, 81.03679999999999), (2.3104000000000022, 0.0, 0.0, 81.15520000000001), (2.5600000000000027, 0.0, 0.0, 81.28), (2.8224000000000031, 0.0, 0.0, 81.4112), (3.0976000000000035, 0.0, 0.0, 81.54879999999999), (3.3856000000000037, 0.0, 0.0, 81.6928), (3.6864000000000043, 0.0, 0.0, 81.8432), (4.0000000000000053, 0.0, 0.0, 82.00000000000001), (4.3264000000000049, 0.0, 0.0, 82.16320000000002), (4.6656000000000057, 0.0, 0.0, 82.3328), (5.0176000000000069, 0.0, 0.0, 82.5088), (5.3824000000000076, 0.0, 0.0, 82.69120000000001), (5.7600000000000069, 0.0, 0.0, 82.88), (6.1504000000000083, 0.0, 0.0, 83.0752), (6.5500000000000096, 0.0, 0.0, 83.27499999999999), (6.9500000000000099, 0.0, 0.0, 83.47500000000001), (7.3500000000000103, 0.0, 0.0, 83.67500000000003), (7.7500000000000107, 0.0, 0.0, 83.87500000000001), (8.1500000000000092, 0.0, 0.0, 84.075), (8.5500000000000114, 0.0, 0.0, 84.275), (8.9500000000000099, 0.0, 0.0, 84.47499999999998), (9.3500000000000121, 0.0, 0.0, 84.67500000000001), (9.7500000000000107, 0.0, 0.0, 84.87500000000003), (10.150000000000013, 0.0, 0.0, 85.075), (10.550000000000011, 0.0, 0.0, 85.275), (10.950000000000014, 0.0, 0.0, 85.475), (11.350000000000012, 0.0, 0.0, 85.67500000000001), (11.750000000000014, 0.0, 0.0, 85.87500000000001), (12.150000000000013, 0.0, 0.0, 86.07499999999999), (12.550000000000015, 0.0, 0.0, 86.275), (12.950000000000014, 0.0, 0.0, 86.47500000000001), (13.350000000000016, 0.0, 0.0, 86.675), (13.750000000000014, 0.0, 0.0, 86.875), (14.143600000000013, 0.0, 0.0, 87.07180000000002), (14.524400000000014, 0.0, 0.0, 87.2622), (14.892400000000015, 0.0, 0.0, 87.44620000000002), (15.247600000000014, 0.0, 0.0, 87.62379999999999), (15.590000000000014, 0.0, 0.0, 87.795), (15.919600000000013, 0.0, 0.0, 87.95980000000002), (16.23640000000001, 0.0, 0.0, 88.11820000000002), (16.540400000000012, 0.0, 0.0, 88.27019999999999), (16.831600000000012, 0.0, 0.0, 88.41580000000002), (17.110000000000014, 0.0, 0.0, 88.555), (17.375600000000013, 0.0, 0.0, 88.6878), (17.62840000000001, 0.0, 0.0, 88.8142), (17.868400000000012, 0.0, 0.0, 88.9342), (18.095600000000008, 0.0, 0.0, 89.04779999999998), (18.310000000000006, 0.0, 0.0, 89.15500000000003), (18.511600000000008, 0.0, 0.0, 89.2558), (18.700400000000009, 0.0, 0.0, 89.3502), (18.876400000000007, 0.0, 0.0, 89.43820000000001), (19.039600000000004, 0.0, 0.0, 89.5198), (19.190000000000005, 0.0, 0.0, 89.595), (19.327600000000007, 0.0, 0.0, 89.66379999999998), (19.452400000000004, 0.0, 0.0, 89.72619999999999), (19.564400000000003, 0.0, 0.0, 89.78219999999999), (19.663600000000002, 0.0, 0.0, 89.83179999999999), (19.750000000000007, 0.0, 0.0, 89.87500000000001), (19.823600000000003, 0.0, 0.0, 89.91179999999999), (19.884399999999999, 0.0, 0.0, 89.9422), (19.932400000000001, 0.0, 0.0, 89.96619999999997), (19.967600000000004, 0.0, 0.0, 89.9838), (19.990000000000002, 0.0, 0.0, 89.99499999999999), (19.999599999999997, 0.0, 0.0, 89.9998)]

    assert np.allclose(positions, ref_positions)


def test_arc_primitive_mid_2d():
    # Set some frames even though these are not used in this test.
    f0 = robotmath.xyz_to_frame(0, 0, 0)
    f1 = robotmath.xyz_to_frame(10, 0, 0)
    f2 = robotmath.xyz_to_frame(0, 10, 0)

    p = ArcPrimitive(f0, f1, f2)

    mid = p.arc_mid_2d((0, 0), (10, 0), (0, 10))

    assert np.allclose(mid, (5, 5))


def test_arc_primitive_length():
    # Quarter circle arc.
    radius = 10.0
    f0 = robotmath.xyz_to_frame(radius, 0, 0)
    f1 = robotmath.xyz_to_frame(radius / math.sqrt(2), radius / math.sqrt(2), 0)
    f2 = robotmath.xyz_to_frame(0, radius, 0)

    p = ArcPrimitive(f0, f1, f2)

    assert np.isclose(p.length(), math.pi * radius / 2)

    # Extend arc to full circle.
    p = ArcPrimitive(f0, f1, f2, degrees=360)

    assert np.isclose(p.length(), 2 * math.pi * radius)


def test_arc_primitive_path():
    program = StubProgram(arc_r=50.0)

    # Quarter circle arc.
    radius = 10.0
    f0 = robotmath.xyz_euler_to_frame(radius, 0, 0, 0, 0, 0)
    f1 = robotmath.xyz_euler_to_frame(radius / math.sqrt(2), radius / math.sqrt(2), 0, 0, 0, 90)
    f2 = robotmath.xyz_euler_to_frame(0, radius, 0, 0, 0, 180)

    separation = 60.0

    p = ArcPrimitive(f0, f1, f2, separation=separation)
    p.program = program
    p.set_speed_acceleration(100, 800)

    path = []

    p.append_to_path(path)

    positions = []

    for robotpos in path:
        x, y, z, a, b, c = robotmath.frame_to_xyz_euler(robotpos.frame)
        positions.append((x, y, z, c))

        assert np.isclose(robotpos.separation, separation)

    ref_positions = [(10.0, 4.355561602068429e-16, 0.0, 0.0), (9.9999979520000704, 0.0063999995630931927, 0.0, 0.07333859777674538), (9.9999672320178963, 0.02559997203798163, 0.0, 0.2933543911069816), (9.9998341124586467, 0.057599681495568558, 0.0, 0.6600473799907086), (9.9994757165812818, 0.1023982104396762, 0.0, 1.1734175644279263), (9.9987200273064332, 0.15999317342071456, 0.0, 1.833464944418635), (9.9973459094115906, 0.23037961622359523, 0.0, 2.6401895199628345), (9.9950831549755872, 0.31354860089506087, 0.0, 3.5935912910605254), (9.9916125647468181, 0.40948547714606987, 0.0, 4.693670257711707), (9.9865660809143542, 0.51816784108138358, 0.0, 5.940426419916379), (9.9795269895522996, 0.63956318280309377, 0.0, 7.333859777674542), (9.970030213776754, 0.77362622523970681, 0.0, 8.8739703309862), (9.9575627213905591, 0.92029595759901162, 0.0, 10.560758079851345), (9.9415640734785189, 1.0794923681625472, 0.0, 12.394223024269987), (9.9214271430367695, 1.2511128827620823, 0.0, 14.374365164242112), (9.8964990352511162, 1.4350285172336292, 0.0, 16.50118449976773), (9.8660822434537145, 1.6310797544593956, 0.0, 18.774681030846846), (9.8294360770522164, 1.8390721593086945, 0.0, 21.19485475747945), (9.7857783998032186, 2.0587717478984322, 0.0, 23.76170567966554), (9.7342877186489982, 2.2899001311322036, 0.0, 26.47523379740511), (9.6741056649037453, 2.53212945646096, 0.0, 29.33543911069819), (9.6043399108079122, 2.7850771762488469, 0.0, 32.34232161954476), (9.5240675653055007, 3.0483006760317686, 0.0, 35.49588132394482), (9.4323390932719597, 3.321291801322718, 0.0, 38.79611822389836), (9.3281828022570572, 3.603471327439097, 0.0, 42.24303231940541), (9.2106099400288475, 3.8941834230865124, 0.0, 45.83662361046594), (9.078620444728525, 4.192690165103695, 0.0, 49.576892097079956), (8.9312093871833778, 4.498166168816744, 0.0, 53.463837779247456), (8.7673741417852806, 4.8096934058165104, 0.0, 57.49746065696847), (8.5861223182311139, 5.1262562885963447, 0.0, 61.67776073024298), (8.386480481244929, 5.4467371092882608, 0.0, 66.00473799907094), (8.1675036790651827, 5.7699119276169819, 0.0, 70.47839246345242), (7.9304792810165878, 6.0915924332941565, 0.0, 75.05747116213799), (7.6805370179206776, 6.4038543953114795, 0.0, 79.64113352318456), (7.418307534023274, 6.705871556379047, 0.0, 84.22479588423116), (7.1442103405593054, 6.9971607534660443, 0.0, 88.80845824527775), (6.858683934567364, 7.2772559859955148, 0.0, 93.39212060632434), (6.5621850973879861, 7.5457091613458731, 0.0, 97.97578296737096), (6.2551881639109492, 7.8020908117035122, 0.0, 102.55944532841752), (5.9381842637406264, 8.0459907811197002, 0.0, 107.14310768946412), (5.6145038461161505, 8.2751040212161051, 0.0, 111.68767807848559), (5.2924627780163522, 8.4846825363894105, 0.0, 116.09091401961578), (4.973716808552914, 8.6753755600733644, 0.0, 120.34747276519245), (4.6594383959127796, 8.8481429596663812, 0.0, 124.45735431521572), (4.3506956776438974, 9.0039684095697883, 0.0, 128.42055866968542), (4.048456810736516, 9.1438502531264767, 0.0, 132.23708582860172), (3.7535947142719905, 9.2687931642144967, 0.0, 135.90693579196443), (3.4668921233065273, 9.3798005845196499, 0.0, 139.43010855977374), (3.189046870513514, 9.4778679067429472, 0.0, 142.8066041320295), (2.9206773198344811, 9.5639763693457791, 0.0, 146.03642250873176), (2.662327883897575, 9.6390876248025403, 0.0, 149.11956368988052), (2.4144745641805896, 9.7041389406234764, 0.0, 152.05602767547586), (2.1775304597653342, 9.7600389905365734, 0.0, 154.84581446551766), (1.9518511970071177, 9.8076641920868148, 0.0, 157.48892406000596), (1.7377402384947196, 9.8478555464383373, 0.0, 159.9853564589408), (1.535454035280635, 9.8814159362684659, 0.0, 162.33511166232216), (1.3452069915063678, 9.9091078382467117, 0.0, 164.53818967014996), (1.1671762152285474, 9.9316514076262656, 0.0, 166.59459048242434), (1.0015060334721291, 9.9497228938759381, 0.0, 168.50431409914518), (0.84831225330489346, 9.9639533479885767, 0.0, 170.26736052031256), (0.70768615405810742, 9.9749275840656839, 0.0, 171.88372974592647), (0.57969819872837647, 9.9831833599504254, 0.0, 173.35342177598685), (0.46440145510828579, 9.9892107440224382, 0.0, 174.6764366104937), (0.36183471933226841, 9.9934516377418738, 0.0, 175.85277424944712), (0.27202533631588643, 9.9962994261077558, 0.0, 176.88243469284703), (0.19499171304030405, 9.998098730851062, 0.0, 177.76541794069345), (0.13074552181830335, 9.9991452438958248, 0.0, 178.5017239929864), (0.079293591604944424, 9.9996856213748231, 0.0, 179.09135284972584), (0.04063948611576329, 9.9999174212674511, 0.0, 179.5343045109118), (0.014784768020680517, 9.9999890705257553, 0.0, 179.83057897654425), (0.0017299488240087868, 9.999999850363853, 0.0, 179.98017624662324)]

    assert np.allclose(positions, ref_positions)


def test_pause_primitive():
    position = RobotPosition()
    position.frame = robotmath.xyz_to_frame(10, 20, 30)
    position.d = 1.0
    position.t = 2.0

    program = StubProgram(arc_r=50.0, position=position)

    p = PausePrimitive(1.6)
    p.program = program

    # Pause primitive (spatial) length is always zero.
    assert p.length() == 0

    # Test that zero duration pause does not append any points.
    path = []

    p = PausePrimitive(0.0)
    p.program = program
    p.append_to_path(path)

    assert len(path) == 0

    # Check that pause appends correct amount of points.
    duration = 1.6

    p = PausePrimitive(duration)
    p.program = program
    p.append_to_path(path)

    assert len(path) == int(duration * SAMPLES_PER_SECOND)

    assert path[0].t == 0

    # Make sure the path positions correspond to current program position.
    for pos in path:
        assert np.allclose(pos.frame, program.position().frame)
        assert pos.d == 0

    # Check edge case where pause is less than sample time.
    path = []
    duration = 0.5 / SAMPLES_PER_SECOND

    p = PausePrimitive(duration)
    p.program = program
    p.append_to_path(path)

    assert len(path) == 1

    # Make sure that latest path position is used if exists.

    position = RobotPosition()
    position.frame = robotmath.xyz_to_frame(40, 50, 60)
    position.d = 3.0
    position.t = 4.0
    path = [position]

    duration = 1.6

    p = PausePrimitive(duration)
    p.program = program
    p.append_to_path(path)

    # Path length should be pause primitive length plus 1 that was in path initially.
    assert len(path) == int(duration * SAMPLES_PER_SECOND) + 1

    # Make sure the path positions correspond to current program position.
    for pos in path[1:]:
        assert np.allclose(pos.frame, position.frame)
        assert pos.d == position.d


def test_point_primitive():
    position = RobotPosition()
    position.frame = robotmath.xyz_to_frame(10, 20, 30)
    position.d = 0.0
    position.t = 0.0

    program = StubProgram(arc_r=50.0, position=position)

    frame = robotmath.xyz_to_frame(20, 30, 40)
    p = PointPrimitive(frame)
    p.program = program

    # Test that if there are no positions in path then only the point is appended.
    path = []

    p.append_to_path(path)

    assert len(path) == 1
    assert np.allclose(path[0].frame, frame)

    # Test that if there are positions in path then connecting line primitive is created.
    c = SpeedCommand(200, 800)
    c.program = program
    c.execute()  # Need to set Command class speed and acceleration.
    path = [position]

    p.append_to_path(path)

    positions = []

    for robotpos in path:
        x, y, z = robotmath.frame_to_xyz(robotpos.frame)
        positions.append((x, y, z))

    # N.B. the first two positions are the same.
    ref_positions = [(10.0, 20.0, 30.0), (10.0, 20.0, 30.0), (10.003695041722814, 20.003695041722814, 30.003695041722814), (10.014780166891255, 20.014780166891253, 30.014780166891253), (10.033255375505323, 20.033255375505323, 30.033255375505323), (10.059120667565018, 20.059120667565018, 30.059120667565018), (10.09237604307034, 20.092376043070342, 30.092376043070342), (10.13302150202129, 20.13302150202129, 30.13302150202129), (10.181057044417866, 20.181057044417866, 30.181057044417866), (10.23648267026007, 20.23648267026007, 30.23648267026007), (10.299298379547903, 20.299298379547903, 30.299298379547903), (10.36950417228136, 20.36950417228136, 30.36950417228136), (10.447100048460447, 20.447100048460445, 30.447100048460445), (10.532086008085159, 20.532086008085159, 30.532086008085159), (10.624462051155501, 20.624462051155501, 30.624462051155501), (10.724228177671467, 20.724228177671467, 30.724228177671467), (10.831384387633062, 20.831384387633062, 30.831384387633062), (10.945930681040284, 20.945930681040284, 30.945930681040284), (11.067867057893134, 21.067867057893132, 31.067867057893132), (11.197193518191609, 21.197193518191611, 31.197193518191611), (11.333910061935713, 21.333910061935711, 31.333910061935711), (11.478016689125443, 21.478016689125443, 31.478016689125443), (11.629513399760802, 21.6295133997608, 31.6295133997608), (11.788400193841786, 21.788400193841788, 31.788400193841788), (11.954677071368399, 21.954677071368398, 31.954677071368398), (12.128344032340639, 22.128344032340639, 32.128344032340635), (12.309401076758506, 22.309401076758505, 32.309401076758505), (12.497848204621999, 22.497848204621999, 32.497848204622002), (12.693685415931121, 22.693685415931121, 32.693685415931121), (12.89691271068587, 22.896912710685868, 32.896912710685868), (13.107530088886246, 23.107530088886246, 33.107530088886243), (13.32553755053225, 23.32553755053225, 33.325537550532246), (13.550935095623879, 23.550935095623878, 33.550935095623878), (13.783722724161137, 23.783722724161137, 33.783722724161137), (14.023900436144022, 24.023900436144022, 34.023900436144018), (14.271468231572532, 24.271468231572534, 34.271468231572534), (14.526426110446671, 24.526426110446671, 34.526426110446671), (14.788774072766438, 24.788774072766437, 34.788774072766437), (15.058171740458111, 25.058171740458111, 35.058171740458114), (15.324737769598171, 25.324737769598173, 35.324737769598173), (15.583913715292603, 25.583913715292603, 35.583913715292603), (15.835699577541407, 25.835699577541405, 35.835699577541405), (16.080095356344586, 26.080095356344586, 36.080095356344586), (16.317101051702132, 26.317101051702132, 36.317101051702132), (16.546716663614056, 26.546716663614056, 36.546716663614056), (16.768942192080353, 26.768942192080353, 36.768942192080353), (16.983777637101021, 26.983777637101021, 36.983777637101021), (17.191222998676061, 27.191222998676061, 37.191222998676061), (17.391278276805476, 27.391278276805476, 37.39127827680548), (17.583943471489263, 27.583943471489263, 37.583943471489263), (17.769218582727422, 27.769218582727422, 37.769218582727419), (17.947103610519953, 27.947103610519953, 37.947103610519953), (18.117598554866859, 28.117598554866859, 38.117598554866859), (18.280703415768137, 28.280703415768137, 38.280703415768137), (18.436418193223787, 28.436418193223787, 38.436418193223787), (18.584742887233809, 28.584742887233809, 38.584742887233809), (18.725677497798209, 28.725677497798209, 38.725677497798209), (18.859222024916974, 28.859222024916974, 38.859222024916974), (18.985376468590118, 28.985376468590118, 38.985376468590118), (19.104140828817631, 29.104140828817631, 39.104140828817634), (19.215515105599518, 29.215515105599518, 39.215515105599522), (19.319499298935781, 29.319499298935781, 39.319499298935781), (19.416093408826413, 29.416093408826413, 39.416093408826413), (19.505297435271416, 29.505297435271416, 39.505297435271416), (19.587111378270798, 29.587111378270798, 39.587111378270798), (19.661535237824545, 29.661535237824545, 39.661535237824545), (19.72856901393267, 29.72856901393267, 39.72856901393267), (19.788212706595168, 29.788212706595168, 39.788212706595168), (19.840466315812037, 29.840466315812037, 39.840466315812037), (19.885329841583278, 29.885329841583278, 39.885329841583278), (19.922803283908895, 29.922803283908895, 39.922803283908891), (19.952886642788883, 29.952886642788883, 39.952886642788883), (19.975579918223247, 29.975579918223247, 39.975579918223247), (19.990883110211975, 29.990883110211975, 39.990883110211975), (19.998796218755079, 29.998796218755079, 39.998796218755075)]

    assert np.allclose(positions, ref_positions)


def test_context_command():
    root = Node("root")
    robot_base = Node("robot_base")
    robot_base.frame = robotmath.xyz_to_frame(10, 20, 30)
    root.add_child(robot_base)

    dut = Node("dut")
    dut.frame = robotmath.xyz_to_frame(40, 50, 60)
    robot_base.add_child(dut)

    program = StubProgram(arc_r=0.0)
    program.robot_base = robot_base

    # Test execution of context command for robot_base context.
    c = ContextCommand(robot_base)
    c.program = program
    c.execute()
    assert program.context == robot_base
    assert np.allclose(program.transform, robotmath.identity_frame())
    assert program.surface is None

    # Test execution of context command for dut context.
    c = ContextCommand(dut)
    c.program = program
    c.execute()
    assert program.context == dut
    assert np.allclose(program.transform, dut.frame)
    assert program.surface is None


def test_speed_command():
    program = StubProgram(arc_r=0.0)

    speed = 100
    acceleration = 200

    c = SpeedCommand(speed, acceleration)
    c.program = program

    c.execute()

    assert program.speed == speed
    assert program.acceleration == acceleration


def test_program():
    root_node = Node("root")
    robot_node = StubRobot("robot")
    root_node.add_child(robot_node)

    prog = Program(robot_node)

    robot_node.driver.current_frame = robotmath.xyz_to_frame(10, 20, 30)

    assert np.allclose(prog.position().frame, robot_node.driver.current_frame)

    assert prog.arc_r() == 50.0

    toolframe = robotmath.xyz_to_frame(1, 2, 3)
    kinematic_name = "tool1"

    with pytest.raises(Exception):
        prog.begin(None, toolframe, kinematic_name)

    prog.begin(robot_node, toolframe, kinematic_name)

    assert np.allclose(prog.toolframe, toolframe)
    assert prog.kinematic_name == kinematic_name

    assert isinstance(prog.program[0], ContextCommand)

    # Just test that program runs without errors.
    prog.run()

    prog.clear()
    assert len(prog.program) == 0


def test_program_reset():
    root_node = Node("root")
    robot_node = StubRobot("robot")
    root_node.add_child(robot_node)

    prog = Program(robot_node)

    prog.program = "foo"
    prog.transform = "foo"
    prog.surface = "foo"
    prog.context = "foo"
    prog.toolframe = "foo"

    prog.reset()

    assert isinstance(prog.program, list) and len(prog.program) == 0
    assert np.allclose(prog.transform, robotmath.identity_frame())
    assert prog.surface is None
    assert prog.context is None
    assert prog.toolframe is None


def test_program_primitives():
    root_node = Node("root")
    robot_node = StubRobot("robot")
    root_node.add_child(robot_node)

    prog = Program(robot_node)

    pose0 = robotmath.xyz_to_frame(1, 2, 3)
    pose1 = robotmath.xyz_to_frame(4, 5, 6)
    pose2 = robotmath.xyz_to_frame(7, 8, 9)

    assert isinstance(prog.line(pose0, pose1), LinePrimitive)
    assert isinstance(prog.arc(pose0, pose1, pose2, degrees=90.0), ArcPrimitive)
    assert isinstance(prog.swipe(pose0, pose1, 20.0), JoinPrimitive)
    assert isinstance(prog.point(pose0), PointPrimitive)
    assert isinstance(prog.join(0.0, [prog.line(pose0, pose1), prog.line(pose1, pose2)]), JoinPrimitive)
    assert isinstance(prog.pause(1.0), PausePrimitive)

    tap = prog.tap(pose0, 10.0, -2.0, 1.0)
    assert isinstance(tap[0], LinePrimitive)
    assert isinstance(tap[1], PausePrimitive)
    assert isinstance(tap[2], LinePrimitive)


def test_program_set_speed():
    root_node = Node("root")
    robot_node = StubRobot("robot")
    root_node.add_child(robot_node)

    prog = Program(robot_node)

    assert len(prog.program) == 0

    prog.set_speed(100, 200)
    assert isinstance(prog.program[0], SpeedCommand)


def test_program_move():
    root_node = Node("root")
    robot_node = StubRobot("robot")
    root_node.add_child(robot_node)

    prog = Program(robot_node)

    pose0 = robotmath.xyz_to_frame(1, 2, 3)
    point = prog.point(pose0)

    assert len(prog.program) == 0

    prog.move(point)

    assert isinstance(prog.program[0], PathCommand)


def test_program_length():
    root_node = Node("root")
    robot_node = StubRobot("robot")
    root_node.add_child(robot_node)

    prog = Program(robot_node)

    pose0 = robotmath.xyz_to_frame(0, 0, 0)
    pose1 = robotmath.xyz_to_frame(100, 0, 0)
    pose2 = robotmath.xyz_to_frame(200, 0, 0)

    toolframe = robotmath.xyz_to_frame(1, 2, 3)
    kinematic_name = "tool1"

    prog.begin(robot_node, toolframe, kinematic_name)

    prog.move([LinePrimitive(pose0, pose1), LinePrimitive(pose1, pose2)])

    assert prog.length() == 200


def test_command_fail():
    root_node = Node("root")
    robot_node = StubRobot("robot")
    root_node.add_child(robot_node)

    prog = Program(robot_node)

    toolframe = robotmath.xyz_to_frame(1, 2, 3)
    kinematic_name = "tool1"

    prog.begin(robot_node, toolframe, kinematic_name)

    prog.program.append(FailCommand())

    with pytest.raises(Exception):
        prog.run()


def test_get_segment_ix():
    assert get_segment_ix(-1.0, 2, 1.0) == 0
    assert get_segment_ix(0.0, 2, 1.0) == 0
    assert get_segment_ix(0.4999, 2, 1.0) == 0
    assert get_segment_ix(0.50001, 2, 1.0) == 1
    assert get_segment_ix(1.0, 2, 1.0) == 1
    assert get_segment_ix(2.0, 2, 1.0) == 1


def test_compute_segment_coordinate():
    segment_lengths = [1.0, 0.3, 2.0]

    # Segment 0
    assert compute_segment_coordinate(-1.0, 0, segment_lengths) == pytest.approx(0)
    assert compute_segment_coordinate(0.0, 0, segment_lengths) == pytest.approx(0)
    assert compute_segment_coordinate(0.5, 0, segment_lengths) == pytest.approx(0.5)
    assert compute_segment_coordinate(1.0, 0, segment_lengths) == pytest.approx(1)
    assert compute_segment_coordinate(2.0, 0, segment_lengths) == pytest.approx(1)

    # Segment 1
    assert compute_segment_coordinate(0.0, 1, segment_lengths) == pytest.approx(0)
    assert compute_segment_coordinate(1.0, 1, segment_lengths) == pytest.approx(0)
    assert compute_segment_coordinate(1.15, 1, segment_lengths) == pytest.approx(0.5)
    assert compute_segment_coordinate(1.3, 1, segment_lengths) == pytest.approx(1)
    assert compute_segment_coordinate(2.0, 1, segment_lengths) == pytest.approx(1)

    # Segment 2
    assert compute_segment_coordinate(0.0, 2, segment_lengths) == pytest.approx(0)
    assert compute_segment_coordinate(1.3, 2, segment_lengths) == pytest.approx(0)
    assert compute_segment_coordinate(2.3, 2, segment_lengths) == pytest.approx(0.5)
    assert compute_segment_coordinate(3.3, 2, segment_lengths) == pytest.approx(1)
    assert compute_segment_coordinate(4.0, 2, segment_lengths) == pytest.approx(1)


def test_spline_primitive():
    program = StubProgram(arc_r=50.0)

    frames = []
    frames.append(robotmath.pose_to_frame(robotmath.xyz_euler_to_frame(0, 0, 0, 0, 0, 0)))
    frames.append(robotmath.pose_to_frame(robotmath.xyz_euler_to_frame(10, 0, 0, 0, 0, 90)))
    frames.append(robotmath.pose_to_frame(robotmath.xyz_euler_to_frame(20, 10, 10, 0, 0, 90)))
    frames.append(robotmath.pose_to_frame(robotmath.xyz_euler_to_frame(30, 40, 20, 0, 0, 90)))

    p = SplinePrimitive(frames, limits={"x": (-1e6, 1e6), "y": (-1e6, 1e6), "z": (-1e6, 1e6)})
    p.program = program

    # Test that p.tangent_length(0) matches a reference value.
    length = p.tangent_length(0)
    assert length == pytest.approx(39.370039370059025)

    total_length = p.segment_length(0, 1)
    assert total_length == pytest.approx(62.015533701232705)

    u = p.get_u_at_distance(0, 0, 0)
    assert u == pytest.approx(0)

    u = p.get_u_at_distance(total_length, 0, 0)
    assert u == pytest.approx(1.0)

    # Test that append_to_path() works without errors. Does not validate result.
    path = []
    p._speed = 200
    p._acceleration = 800
    p.append_to_path(path)
