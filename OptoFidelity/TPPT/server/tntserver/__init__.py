import argparse
import logging
import logging.config
import os
import time

import tntserver.globals
from tntserver import Tree
from tntserver.Nodes.Node import *
from tntserver.configuration import TnTConfigurationManager, LoggingConfigurationManager, push_configuration, \
    fetch_configuration
from tntserver.system_information import SystemInformationCollector
from tntserver.tnt_http import TntServerThreadingServer
from tntserver.client_generator.generator import generate_client
import ruamel.yaml as yaml

log = logging.getLogger(__name__)

# Version is in the form major.minor.patch
__version__ = "5.16.2"


class TraceLogger(logging.getLoggerClass()):
    VERBOSE = 5

    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        logging.addLevelName(TraceLogger.VERBOSE, "VERBOSE")

    def trace(self, msg, *args, **kwargs):
        if self.isEnabledFor(TraceLogger.VERBOSE):
            self._log(TraceLogger.VERBOSE, msg, args, **kwargs)

# Now all code in tntserver can use log.trace
logging.setLoggerClass(TraceLogger)


def check():
    ''' If Server does not import all nodes correctly, we don't get here '''
    log.info("Self check - passed")


def start_server(configuration_manager):
    """
    Starts the server
    :param configuration_manager: object for handling configuration. This is needed for backups.
    """
    opened = False
    while not opened:
        log.info("Trying to open server at port %s", globals.server_port)
        try:
            server = TntServerThreadingServer(("", globals.server_port))
            opened = True
            log.info("Server ready at port %s", globals.server_port)
            configuration_manager.backup_configuration(is_init=True)
            server.serve_forever(1000)

        except:
            log.exception("Could not open server")
            time.sleep(1)


def get_version():
    """ Returns TnT Server's version number string including Jenkins build number from version.txt exists.
    If version.txt doesn't exist, build number is set to 'x'.

    :return Version string.
    """

    build_number = "x"
    version_number = __version__
    platform = ""
    architecture = ""

    # Read build number from version.txt
    path = os.path.dirname(os.path.abspath(__file__))
    version_file_name = os.path.join(path, "..", "version.txt")

    if os.path.exists(version_file_name):
        with open(version_file_name, 'r') as file:
            # Read all "key: value" pairs into a dict
            version_info = dict(line.split(':', 1) for line in file)
            if 'Build' in version_info:
                build_number = version_info['Build'].strip()
            if 'Version' in version_info:
                version_number = version_info['Version'].strip()
            if 'Platform' in version_info:
                platform = version_info['Platform'].strip()
            if 'Architecture' in version_info:
                architecture = version_info['Architecture'].strip()

    return version_number + "." + build_number + " " + platform + " " + architecture


def main():
    """

    load configuration/start.txt
    and start server


    """

    parser = argparse.ArgumentParser()
    parser.add_argument('--configuration', metavar="CONFIGURATION_FILE", type=str, help='Configuration for TnT server',
                        default='configuration/start.yaml')
    parser.add_argument('--configuration-ip', type=str, help='IP address of FTP target for obtaining configuration.',
                        default='192.168.127.254')
    parser.add_argument('--fetch-configuration', help='Fetch configuration file via FTP and save locally.',
                        action="store_true", default=False)
    parser.add_argument('--push-configuration', help='Push configuration file via FTP.', action="store_true",
                        default=False)
    parser.add_argument('--log-configuration', metavar="CONFIGURATION_FILE", type=str,
                        help='Log configuration for TnT server', default='configuration/logging.yaml')
    parser.add_argument('--check', action="store_true",
                        help='Perform self-check', default=False)
    parser.add_argument('--visual-simulation', type=lambda x: (str(x).lower() == 'true'),
                        help='Show 3D visualization if robot is ran in simulation mode', default=True)
    parser.add_argument('--generate-client', type=str,
                        help='Generate TnT Client', default="")
    parser.add_argument('--system-information', action='store_true',
                        help='Collect all information from given system to be used in debug')
    parser.add_argument('--robot-ip', type=str, help='IP address of the robot.',
                        default='192.168.127.254')

    args = parser.parse_args()

    path = os.path.dirname(os.path.abspath(__file__))
    log_config_path = os.path.abspath(os.path.join(path, "..", args.log_configuration))

    log_config = LoggingConfigurationManager(log_config_path).get_configuration()
    logging.config.dictConfig(log_config['logging'])

    # Generate TnT Client and stop program.
    if len(args.generate_client) > 0:
        logging.info("Generating TnT Client.")

        with open(args.generate_client) as file:
            config = yaml.YAML().load(file)

            generate_client(config)
            return

    path = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.abspath(os.path.join(path, "..", args.configuration))
    configuration_ip = args.configuration_ip

    # Run the script for automatic system data collection
    if args.system_information:
        system_info_collector = SystemInformationCollector(robot_ip=args.robot_ip)
        system_info_collector.collect_system_information(configuration_ip=configuration_ip)
        return

    # Fetch configuration via FTP and stop program.
    if args.fetch_configuration:
        logging.info("Fetching configuration file via FTP.")

        fetch_configuration(configuration_file=config_path, configuration_ip=configuration_ip)
        return

    # Push configuration via FTP and stop program.
    if args.push_configuration:
        logging.info("Pushing configuration file via FTP.")

        push_configuration(configuration_file=config_path, configuration_ip=configuration_ip)
        return

    version = get_version()

    logging.info("Starting TnT Server...")

    logging.info("Logging initialized")
    logging.info("Welcome to TnT Server: {}".format(version))
    logging.info("  Configuration: {}".format(config_path))
    logging.info("  Log config:    {}".format(log_config_path))

    configuration_manager = TnTConfigurationManager(config_path, configuration_ip)
    tntserver.globals.server_port = configuration_manager.get_port()

    configuration_manager.create_tree(program_arguments=args)
    tntserver.configuration.configuration_manager = configuration_manager

    if args.check:
        check()
    else:
        start_server(configuration_manager)
