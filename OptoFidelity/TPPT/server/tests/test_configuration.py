from datetime import datetime

from tntserver.configuration import TnTConfigurationManager, convert_to_default_types
import argparse
from tntserver.Nodes.TnT.Robot import Robot as tnt_robot
from tntserver.Nodes.TnT.Robot import *
from tntserver.Nodes.Voicecoil.Robot import Robot as voicecoil_robot
from tntserver.Nodes.Synchro.Robot import Robot as synchro_robot
from tntserver.Nodes.NodeFileServer import *
from tntserver.Nodes.DutServer import *
from tntserver.Nodes.DutSimulation import *
from tntserver.drivers.cameras.camera_simulator import *
from shutil import copyfile, rmtree
from ruamel.yaml.scalarbool import *
from ruamel.yaml.scalarfloat import *
from ruamel.yaml.scalarint import *
from ruamel.yaml.scalarstring import *

# ---------------------------------------------
# Followings are the ones do actual tests
# ---------------------------------------------

# robot model name, same as the name in configuration file
robots = ('3axis', 'hmdiq', 'synchro_hsup_hsuf', 'two_finger_dt', '3axis_voicecoil')

init_goldenmove = None
init_voicecoil = None
init_synchro = None
init_node_file_server = None
init_dut_server = None
del_dut_server = None
init_dut_simulation = None
del_dut_simulation = None
resolution_camera_simulator = None


def test_convert_to_default_types():
    def verify_lists(a, b):
        assert len(a) == len(b)

        for i in range(len(a)):
            assert a[i] == b[i]
            assert type(a[i]) == type(b[i])

    data = {
        "normal_types": [1, 2, "hello", False, 3.0],
        "yamel_yaml_bool_types": [ScalarBoolean(True), ScalarBoolean(False)],
        "yamel_yaml_int_types": [ScalarInt(1), BinaryInt(2), OctalInt(3), HexInt(4), HexCapsInt(5), DecimalInt(6)],
        "yamel_yaml_float_types": [ScalarFloat(2.0), ExponentialFloat(3.0), ExponentialCapsFloat(4.0)],
        "yamel_yaml_str_types": [ScalarString("test1"), LiteralScalarString("test2"), FoldedScalarString("test3"),
                                 SingleQuotedScalarString("test4"), DoubleQuotedScalarString("test5"),
                                 PlainScalarString("test6")],
        "yaml_nested_types": {
            "sublist": [1, True, "Hello", 3.2, ScalarBoolean(False), ScalarInt(4), ScalarFloat(2.0), ScalarString("test1")],
        }
    }

    result = convert_to_default_types(data)

    verify_lists(result["normal_types"], [1, 2, "hello", False, 3.0])
    verify_lists(result["yamel_yaml_bool_types"], [True, False])
    verify_lists(result["yamel_yaml_int_types"], [1, 2, 3, 4, 5, 6])
    verify_lists(result["yamel_yaml_float_types"], [2.0, 3.0, 4.0])
    verify_lists(result["yamel_yaml_str_types"], ["test1", "test2", "test3", "test4", "test5", "test6"])

    verify_lists(result["yaml_nested_types"]["sublist"], [1, True, "Hello", 3.2, False, 4, 2.0, "test1"])


def stub_robot_init_goldenmov(self, **kwargs):
    """
    stub for Robot _init_goldenmov(), not to start server, not simulator
    :param self:
    :param kwargs:
    :return:
    """
    host = kwargs["host"]
    port = kwargs["port"]
    model = str(kwargs["model"])
    #simulator = kwargs.get("simulator", False)
    simulator = False
    axis_specs = kwargs.get("axis_specs", None)
    position_limits = kwargs.get("position_limits", None)
    api_name = kwargs.get("api_name", "optomotion")

    visualize = kwargs.get("visualize", True)

    if "program_arguments" in kwargs:
        visualize = kwargs["program_arguments"].visual_simulation

    driver_log_level = kwargs.get("driver_log_level", 2)

    self.driver = None

    self.program = golden_program.Program(self)

def stub_voicecoil_robot_init(self, **kwargs):
    """
    Stub for Voicecoil.Robot._init(), not to use self.driver
    :param self:
    :param kwargs:
    :return:
    """
    pass

def stub_synchro_robot_init(self, **kwargs):
    """
    Stub for Synchro.Robot._init(), not to use self.driver
    :param self:
    :param kwargs:
    :return:
    """
    pass

def stub_fileserver_init(self, path, port, **kwargs):
    """
    Stub for FileServer _init(), not to start server
    :param self:
    :param path:
    :param port:
    :param kwargs:
    :return:
    """
    pass

def stub_dutserver_init(self, **kwargs):
    """
    Stub for DutServer _init(), not to start server
    :param self:
    :param kwargs:
    :return:
    """
    pass

def stub_dutserver__del__(self):
    """
    Stub for DutServer __del__() to avoid exception message
    :param self:
    :return:
    """
    pass


def stub_dutsimulation_init(self, **kwargs):
    """
    Stub for DutSimulation, not to start server
    :param self:
    :param kwargs:
    :return:
    """
    pass

def stub_dutsimulation__del__(self):
    """
    Stub for DutSimulation.__del__, as self._client.socket not asigned, otherwise exception would occur
    :param self:
    :return:
    """
    pass

@property
def stub_camera_simulator_resolution(self):
    """
    Stub for CameraSimulator.resolution, not to use any simulator, otherwise exception message would occur
    :param self:
    :return:
    """
    return 10, 10

def save_original_init():
    """
    Save these original methods which are replaced by stubs during this test.
    After this test, set back the originals, otherwise, other tests after this test would use stubs and cause failures.
    :return:
    """
    global init_goldenmove, init_voicecoil, init_synchro, init_node_file_server, init_dut_server, del_dut_server
    global init_dut_simulation, del_dut_simulation, resolution_camera_simulator
    # keep original _init_goldenmov, put it back after this test. Otherwise, other unit tests fail.
    # during this test, _init_goldenmov will be replaced by stub
    init_goldenmove = tnt_robot._init_goldenmov

    # same for others
    init_voicecoil = voicecoil_robot._init
    init_synchro = synchro_robot._init
    init_node_file_server= NodeFileServer._init
    init_dut_server = DutServer._init
    del_dut_server = DutServer.__del__
    init_dut_simulation = DutSimulation._init
    del_dut_simulation = DutSimulation.__del__
    resolution_camera_simulator = Camera_Simulator.resolution


def replace_servers_with_stubs():
    """
    # use stubs for servers to avoid process hanging when intiate all nodes, and avoid exception messages
    :return:
    """
    # robot server
    tnt_robot._init_goldenmov = stub_robot_init_goldenmov
    voicecoil_robot._init = stub_voicecoil_robot_init
    synchro_robot._init = stub_synchro_robot_init

    # file server
    NodeFileServer._init = stub_fileserver_init

    # dut server
    DutServer._init = stub_dutserver_init
    DutServer.__del__ = stub_dutserver__del__

    # dut simulation
    DutSimulation._init = stub_dutsimulation_init
    DutSimulation.__del__ = stub_dutsimulation__del__

    # camera simulator, to avoid exeption message
    Camera_Simulator.resolution = stub_camera_simulator_resolution

def return_original_init():
    """
    Following methods are replaced by stubs during this test.
    After this test, return the originals, otherwise, other tests after this test would use stubs and cause failures.
    :return:
    """
    tnt_robot._init_goldenmov = init_goldenmove
    voicecoil_robot._init = init_voicecoil
    synchro_robot._init = init_synchro
    NodeFileServer._init = init_node_file_server
    DutServer._init = init_dut_server
    DutServer.__del__ = del_dut_server
    DutSimulation._init = init_dut_simulation
    DutSimulation.__del__ = del_dut_simulation
    Camera_Simulator.resolution = resolution_camera_simulator


class Args:
    def __init__(self):
        self.configuration = None
        self.log_configuration = None
        self.visual_simulation = False
        self.check = False


def save_live_nodes(robot_model, location):
    """
    - this method can be used for both generating reference files and generating temporary files for testing
    - copy configuration file to tests/configuratios_test/temp, or .../reference
    - these are files which will be updated after call Node.save()
    :param robot_model: e.g. 3aix, hmdiq, etc...
    :param location: in folder /temp or /reference
    :return:
    """
    # for each robot model, set root to None, otherwise, init() is skipped
    Node.root = None
    # Save these original methods which are replaced by stubs during this test.
    save_original_init()

    # these configuration files under /configuration/ are the bases to use them to genereate referene files and
    # temporary files
    file_config = os.path.abspath(os.path.join(os.getcwd(), 'tests', 'configurations_test', 'reference', 'reference_simulation_' + robot_model + '.yaml'))
    path_temp = os.path.abspath(os.path.join(os.getcwd(), 'tests', 'configurations_test', location))
    if not os.path.exists(path_temp):
        os.makedirs(path_temp, exist_ok=True)
    file_temp = os.path.abspath(os.path.join(path_temp, location + '_simulation_' + robot_model + '.yaml'))
    copyfile(file_config, file_temp)

    args = Args()
    args.configuration = file_temp
    args.log_configuration = 'configuration/logging.yaml'

    # TnTConfigurationManager is needed when call save()
    manager_temp = TnTConfigurationManager(file_temp)
    nodes = manager_temp.config

    # remove those nodes need halcon, yasler, futek, etc
    class_remove = ('Detector', 'Detectors', 'Analyzer', 'Analyzers')
    name_remove = ('hsup_camera', 'futek', 'videosensor')
    nodes_new = []
    for node in nodes['nodes']:
        if node['cls'].split('.')[-1] not in class_remove \
                and node['name'] not in name_remove:
            nodes_new.append(node)

    manager_temp.config['nodes'] = nodes_new

    # use stubs for http servers to avoid process hanging when run create_tree()
    replace_servers_with_stubs()

    # initiate all nodes, to update properties
    try:
        manager_temp.create_tree(program_arguments=args)
    except:
        pass

    # run Node.save() to update properties, then call save() to save contents to temporary file
    # any newly added property in the nodes are saved to temporary file
    for node in nodes['nodes']:
        name = node["name"]
        live_node = Node.find(name)
        if live_node is not None:
            live_node.save()

    # After this test, return the originals, otherwise, other tests after this test would use stubs and cause failures.
    return_original_init()

def test_nodes():
    """
    - Check if there is any newly added property in node against
    the reference files (.../tests/configurations_test/reference) for each robot model
    - Call Node.save(), write to temporary files
    - Compare temporary files under .../tests/configurations_test/temp to reference file
    - Test fails if at least node having new property
    - In test result, those nodes checked are printed out, as well fail case
    - Require pytest-print installed for 'printer'
    :return:
    """
    # when run pytest for this script, it takes the location of this file as sys.argv[1],
    # then the error occurs 'error: unrecognized arguments' when call parser.parse_args()
    try:
        # Was getting IndexError with this line, that's why exception handling
        del sys.argv[1]
    except IndexError as e:
        log.exception(e)
    result = True
    for robot in robots:
        file_reference = os.path.abspath(os.path.join(os.getcwd(), 'tests', 'configurations_test', 'reference',
                                                      'reference_simulation_' + robot + '.yaml'))
        file_temp = os.path.abspath(os.path.join(os.getcwd(), 'tests', 'configurations_test', 'temp',
                                                 'temp_simulation_' + robot + '.yaml'))
        # initiate all nodes, call save(),  write to temporary file
        # if there is any newly defined properties in node, these proproties will be written into temporary file
        save_live_nodes(robot, 'temp')

        # reload nodes from updated temp file
        manager_temp = TnTConfigurationManager(file_temp)
        nodes_temp = manager_temp.config

        # load nodes from reference file
        manager_config = TnTConfigurationManager(file_reference)
        nodes_reference = manager_config.config

        # compare node properties in reference file and temporary file
        for node_temp in nodes_temp['nodes']:
            # only check those nodes having properties
            if "properties" in node_temp.keys():
                # only check those nodes without empty property
                if len(node_temp['properties']) > 0:
                    # find the nodes with the same name from temp file and configuration file
                    node_reference = next((item for item in nodes_reference['nodes'] if item["name"] == node_temp["name"]), None)
                    if node_reference is not None:
                        for ppty in node_temp['properties']:
                            # if there is any property in temporary file, but not in reference file, test fails.
                            if 'properties' in node_reference and ppty not in node_reference['properties'].keys():
                                result = False
    assert result

    # Remove temporary files.
    rmtree(os.path.abspath(os.path.join(os.getcwd(), 'tests', 'configurations_test', 'temp')))

def test_backuptime_from_filename():
    """
    - Check that the backup timestamp is properly parsed from the two different backup file names.
    :return:
    """
    filename = "C:\\Optofidelity\\Backups\\start_server_20201112_084017.yaml"
    reference_timestamp = datetime.strptime("20201112_084017", "%Y%m%d_%H%M%S").timestamp()
    assert reference_timestamp == tntserver.configuration.get_backup_time(filename)
    filename = "C:\\Optofidelity\\Backups\\start_server_init_20201112_084017.yaml"
    assert reference_timestamp == tntserver.configuration.get_backup_time(filename)

# ---------------------------------------------
# Following only runs once to generate reference files, and are not used in actual tests
# ---------------------------------------------
def get_reference_files():
    """
    - Get reference files for each robot module. This method is only used to generate reference files,
    not used in actual test.
    - As yarm files in configuration/ might not contain all needed properties, Node.save() needs to be called to get updated properties.
    :return:
    """
    for robot in robots:
        save_live_nodes(robot, 'reference')
