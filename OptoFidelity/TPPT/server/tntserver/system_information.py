import datetime
import glob
import logging
import os
import sys
from shutil import copy, make_archive, rmtree

from optomotion import OptoMotionComm
from tntserver.configuration import fetch_configuration

log = logging.getLogger(__name__)


def get_latest_directory(dirs):
    """
    Gets newest server, ui, analysis or tppt directory.
    :param dirs: list of directory paths.
    :returns: last directory of a sorted dirs-list
    """
    if len(dirs) == 0:
        return None
    elif len(dirs) == 1:
        return dirs[0]
    else:
        dirs.sort()
        return dirs[len(dirs) - 1]


class SystemInformationCollector:
    """
    Collects configuration and log files from the given locations. Also collects axis and motherboard firmwares.
    """

    def __init__(self, robot_ip='192.168.127.254'):

        if sys.platform == 'win32':
            self.folder_path = "C:\\OptoFidelity\\system_information_{}" \
                .format(datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
            self.location_list = [('server', 'c:\\OptoFidelity\\TnT Server\\version.txt'),
                              ('server', 'c:\\OptoFidelity\\Tnt Server\\configuration\\start.yaml'),
                              ('server', 'c:\\OptoFidelity\\Tnt Server\\configuration\\client_config.yaml'),
                              ('ui', 'c:\\OptoFidelity\\Tnt UI\\version.txt'),
                              ('ui', 'c:\\OptoFidelity\\Tnt UI\\configuration\\start.yaml'),
                              ('tppt', 'c:\\OptoFidelity\\TPPT\\version.txt'),
                              ('analysis', 'c:\\OptoFidelity\\TPPT Analysis\\version.txt'),
                              ('log', 'c:\\OptoFidelity\\log\\socket_logger_debug.log'),
                              ('log', 'c:\\OptoFidelity\\log\\socket_logger_filtered.log'),
                              ('log', 'c:\\OptoFidelity\\log\\socket_logger_info.log')]
        else:
            self.folder_path = os.path.expanduser("~/optofidelity/system_information_{}".format(
                datetime.datetime.now().strftime("%Y%m%d-%H%M%S")))

            server_dirs = glob.glob(os.path.expanduser("~/optofidelity/") + "TnT_Server_*")
            ui_dirs = glob.glob(os.path.expanduser("~/optofidelity/") + "TnT_UI_*")
            analysis_dirs = glob.glob(os.path.expanduser("~/optofidelity/") + "TPPT_Analysis_*")
            tppt_dirs = glob.glob(os.path.expanduser("~/optofidelity/") + "TPPT_*")

            self.location_list = []

            if len(server_dirs) > 0:
                server_dir = get_latest_directory(server_dirs)
                self.location_list.extend([('server', server_dir + '/version.txt'),
                                           ('server', server_dir + '/configuration/start.yaml'),
                                           ('server', server_dir + '/configuration/client_config.yaml'),
                                           ('server', server_dir + '/tnt_server.log')])

            if len(ui_dirs) > 0:
                ui_dir = get_latest_directory(ui_dirs)
                self.location_list.extend([('ui', ui_dir + '/version.txt'),
                                           ('ui', ui_dir + '/configuration/start.yaml'),
                                           ('ui', ui_dir + '/tnt_ui.log')])

            if len(analysis_dirs) > 0:
                analysis_dir = get_latest_directory(analysis_dirs)
                self.location_list.append(('analysis', analysis_dir + '/version.txt'))

            if len(tppt_dirs) > 0:
                tppt_dir = get_latest_directory(tppt_dirs)
                self.location_list.append(('analysis', tppt_dir + '/version.txt'))


        self.robot_ip = robot_ip
        self.optomotion_initialized = False

        # Set up optomotion
        # In older mother boards firmware automatic axis detection does not work when axis specs are given. In
        # that case give empty list in axis specs. When this is done the program won't crash, but axis firmare is not
        # found.
        try:
            self.optomotion = OptoMotionComm(self.robot_ip)
            self.optomotion_initialized = True
            log.info('Optomotion initialized. Robot Ip is {}'.format(self.robot_ip))
        except:
            log.debug("Automatic axis discovery failed during initialization. Optomotion initialized with empty axis "
                      "specifications. Axis firmware will not be returned.")
            try:
                self.optomotion = OptoMotionComm(self.robot_ip, [])
                self.optomotion_initialized = True
                log.info('Optomotion initialized with empty axis spec. Robot Ip is {}'.format(self.robot_ip))
            except Exception as e:
                log.debug('Optomotion could not be initialized. Axis and motherboard firmware versions will not be '
                          'returned')
                log.error(e)

        try:
            self.axis_spec = self.optomotion.get_axis_specs()
        except:
            log.debug('Could not get axis specs from OptoMotion')
            self.axis_spec = []

    def collect_system_information(self, configuration_ip=None):
        """
        Collects the system information to a compressed folder.
        """

        log.info('Files are saved in {}.zip.'.format(self.folder_path))
        os.mkdir(self.folder_path)

        # Get all the files that can be just copied
        for location in self.location_list:
            log.info('Trying to get file {}'.format(location[1]))
            try:
                folder = os.path.join(self.folder_path, location[0], '')
                if not os.path.exists(folder):
                    os.mkdir(folder)

                copy(location[1], folder)
            except:
                log.info("did not find {}.".format(location[1]))

        try:
            if configuration_ip is not None:
                fetch_configuration(configuration_file=os.path.join(self.folder_path, 'server', 'start_ftp.yaml'),
                                    configuration_ip=configuration_ip)
        except:
            log.debug("Could not get configuration through FTP.")

        if self.optomotion_initialized:
            self.get_firmware_versions(self.folder_path)

        make_archive(self.folder_path, 'zip', self.folder_path)
        rmtree(self.folder_path)

    def get_firmware_versions(self, folder):
        """
        Gets firmware versions for axes and motherboards and write them into a file.
        :param folder: Path of the folder where data is stored.
        """
        file_path = os.path.join(folder, 'fm_versions.txt')
        log.info('Firmware versions are saved in {}'.format(file_path))
        with open(file_path, 'w') as file:
            file.write("Axis firmware versions: \n")
            for axis in self.axis_spec:
                log.info('Getting firmware version for axis {}'.format(axis.alias))
                try:
                    axis_fm = self.optomotion.get_axis_firmware_version(axis.alias)
                    file.write(axis.alias + ' fm: ' + axis_fm + '\n')
                except:
                    log.debug('Could not get firmware version for axis {}'.format(axis.alias))

            file.write("\nMotherboard firmware version\n")
            log.info('Getting firmware version for motherboard')
            try:
                mb_fm = self.optomotion.get_motherboard_fw_version(self.robot_ip)
                file.write(mb_fm + '\n')
            except:
                log.debug('Could not get motherboard firmware version')
