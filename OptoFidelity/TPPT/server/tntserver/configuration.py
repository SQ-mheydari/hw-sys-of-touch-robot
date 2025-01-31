import glob
import shutil
import time
from datetime import datetime
from sys import platform
import contextlib
import filecmp
import logging
import os
from ftplib import FTP
import io

import ruamel.yaml as yaml

from tntserver.Nodes.Node import Node
import tntserver.Tree as Tree

log = logging.getLogger(__name__)

# Must be in 8.3 capital name formatting.
REMOTE_CONFIG_FILENAME = "SERVER.YML"
REMOTE_CONFIG_TEMP_FILENAME = "TEMP.YML"


class FileManager:
    """
    Base class for loading and saving files.
    Subclasses can implement varying file transfer methods.
    """
    def __init__(self):
        pass

    def load(self):
        raise NotImplemented

    def save(self, data):
        raise NotImplemented


class LocalFileManager(FileManager):
    """
    Load and save files locally.
    """
    def __init__(self, path):
        super().__init__()

        self.path = path

    def load(self):
        log.debug("Loading local file '{}'.".format(self.path))

        try:
            with open(self.path, 'r') as file:
                data = file.read()
        except Exception as e:
            raise Exception("Could not load local file.") from e

        return data

    def save(self, data):
        log.debug("Saving local file '{}'.".format(self.path))

        temp_name = self.path + "_"

        # Try to write the entire file first to temporary file.
        try:
            with open(temp_name, 'w') as file:
                file.write(data)

            if os.path.exists(self.path):
                os.remove(self.path)

            os.rename(temp_name, self.path)
        except Exception as e:
            raise Exception("Could not save local file.") from e


class FTPFileManager(FileManager):
    """
    Load and save files via FTP.
    """
    def __init__(self, ip_address, timeout=16):
        super().__init__()

        self.ip_address = ip_address
        self.timeout = timeout

    def load(self):
        log.debug("Loading remote configuration file from IP address '{}'.".format(self.ip_address))

        data = ""

        try:
            with FTP(self.ip_address, timeout=self.timeout) as ftp:
                ftp.login()
                log.debug(ftp.getwelcome())

                def writeline(line):
                    nonlocal data
                    data += line + "\n"

                ftp.retrlines('RETR ' + REMOTE_CONFIG_FILENAME, writeline)
        except Exception as e:
            raise Exception("Could not load configuration via FTP.") from e

        return data

    def save(self, data):
        log.debug("Saving remote configuration file to IP address '{}'.".format(self.ip_address))

        buf = io.BytesIO(data.encode("utf-8"))

        try:
            with FTP(self.ip_address, timeout=self.timeout) as ftp:
                ftp.login()

                # Try to write the entire file first to temporary file.
                ftp.storlines('STOR ' + REMOTE_CONFIG_TEMP_FILENAME, buf)

                if REMOTE_CONFIG_FILENAME in ftp.nlst():
                    ftp.delete(REMOTE_CONFIG_FILENAME)

                ftp.rename(REMOTE_CONFIG_TEMP_FILENAME, REMOTE_CONFIG_FILENAME)
        except Exception as e:
            raise Exception("Could not save configuration via FTP.") from e


def fetch_configuration(configuration_file, configuration_ip):
    """
    Fetch configuration from FTP server and save as local file.
    :param configuration_file: Target local configuration file path.
    :param configuration_ip: IP address of FTP server where to fetch configuration.
    """
    loader = FTPFileManager(configuration_ip)
    data = loader.load()

    saver = LocalFileManager(configuration_file)
    saver.save(data)


def push_configuration(configuration_file, configuration_ip):
    """
    Push configuration file to FTP server.
    :param configuration_file: Source local configuration file path.
    :param configuration_ip: IP address of FTP server where to push the configuration.
    """
    loader = LocalFileManager(configuration_file)
    data = loader.load()

    saver = FTPFileManager(configuration_ip)
    saver.save(data)


def convert_to_default_types(v):
    """
    Convert types contained in deep dictionary / list to basic Python types.
    ruamerl.yaml uses several internal types which otherwise end up deep within the application
    and may cause issues.
    """
    class_name = v.__class__.__name__

    base_class_names = [base.__name__ for base in v.__class__.__bases__]

    if class_name in ['CommentedSeq', 'list']:
        r = [convert_to_default_types(a) for a in list(v)]
        return r
    elif class_name in ['CommentedMap', 'dict']:
        r = {}
        for n in v:
            r[n] = convert_to_default_types(v[n])
        return r
    elif class_name == 'ScalarFloat' or 'ScalarFloat' in base_class_names:
        return float(v)
    elif class_name == 'ScalarInt' or 'ScalarInt' in base_class_names:
        return int(v)
    elif class_name == 'ScalarString' or 'ScalarString' in base_class_names:
        return str(v)
    elif class_name == 'ScalarBoolean' or 'ScalarBoolean' in base_class_names:
        return bool(v)
    elif class_name in ['int', 'float', 'str', 'bool', 'NoneType']:
        return v

    raise Exception("Unrecognized configuration variable type '{}'".format(class_name))

def get_backup_time(filename):
    """
    Parses the time part out of given filename and turns it to the seconds since epoch.
    :param filename: File name to be parsed.
    :returns: File creation time as seconds since epoch.
    """
    try:
        parts = filename.split('.yaml')[0]
        parts = parts.split('_')
        time_string = parts[-2] + '_' + parts[-1]
        parsed_time = datetime.strptime(time_string, "%Y%m%d_%H%M%S")
        return parsed_time.timestamp()
    except:
        log.debug("Timestamp could not be parsed from file {}".format(filename))
        return 0

class LoggingConfigurationManager:
    def __init__(self, configuration_file):
        self._configuration_file = configuration_file

    def get_configuration(self):
        _yaml = yaml.YAML(typ='unsafe')
        with open(self._configuration_file, 'r') as file:
            config = _yaml.load(file)
        return config


class YAMLConfigurationManager:
    def __init__(self, configuration_file, configuration_ip=None):
        self._configuration_file = configuration_file
        self._configuration_ip = configuration_ip
        self.start = True

        # Decide whether to use local file or remote file via FTP.
        # Local file has precedence.
        if configuration_file is not None and os.path.exists(configuration_file):
            self.file_manager = LocalFileManager(configuration_file)
        else:
            self.file_manager = FTPFileManager(configuration_ip)

        data = self.file_manager.load()

        _yaml = yaml.YAML()
        self._config = _yaml.load(io.StringIO(data))

    def get_configuration(self):
        data = self.file_manager.load()

        _yaml = yaml.YAML()
        config = _yaml.load(io.StringIO(data))

        config = convert_to_default_types(config)

        return config

    @contextlib.contextmanager
    def update_configuration(self):
        _yaml = yaml.YAML()

        if self._config is None:
            data = self.file_manager.load()

            self._config = _yaml.load(io.StringIO(data))

        yield self._config

        # Fix config formatting
        self._fix_format(self._config)

        strio = io.StringIO()
        _yaml.dump(self._config, strio)
        data = strio.getvalue()

        self.file_manager.save(data)

    def _is_frame(self, obj):
        """
        :return: True if obj is list of size 4 with four inner lists of size 4
        """
        if isinstance(obj, list) and len(obj) == 4:
            return all(isinstance(item, list) and len(item) == 4 for item in obj)
        return False

    def _fix_frame_format(self, frame):
        fmt = yaml.load("- [0.0, 0.0, 0.0, 0.0]\n" * 4, Loader=yaml.RoundTripLoader)
        for i in range(4):
            for j in range(4):
                fmt[i][j] = frame[i][j]
        return fmt

    def _fix_format(self, config):
        # Update node to have proper formatting
        for node in config["nodes"]:
            if "frame" in node and self._is_frame(node["frame"]):
                node["frame"] = self._fix_frame_format(node["frame"])

            if "properties" in node:
                for prop, val in node["properties"].items():
                    if self._is_frame(node["properties"][prop]):
                        node["properties"][prop] = self._fix_frame_format(node["properties"][prop])

    def get_port(self):
        return self._config["port"]

    def backup_config(self, is_init):
        """
        Handles backup for yaml config.
        """

        # Time stamp is added to backup file's name to differentiate backups.
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        if is_init:
            filename = 'start_server_init_{}.yaml'.format(current_time)
        else:
            filename = 'start_server_{}.yaml'.format(current_time)

        if platform == 'win32':
            backup_dir = 'C:\\OptoFidelity\\Backups'
        else:
            backup_dir = os.path.expanduser('~/optofidelity/backups')

        # If backup directory doesn't exist one is created.
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir, exist_ok=True)

        filepath = os.path.join(backup_dir, filename)

        # Find all backup files.
        server_backup_files = glob.glob(os.path.join(backup_dir, "start_server*"))

        # If server is shut down before backup process is finished, temporary files are not removed from
        # backup directory. Delete possible temporary files on init.
        if is_init:
            server_backup_files = self.clear_temp_files(server_backup_files, backup_dir)

        # If there is not backups then one is just created. Otherwise the latest backup is compared
        # to current config and new backup is only created if there is a difference.
        if len(server_backup_files) == 0:
            log.debug("Creating backup configuration {}.".format(filepath))
            data = self.file_manager.load()

            # Save backup as local file.
            saver = LocalFileManager(filepath)
            saver.save(data)
        else:
            # Datetime postfix in the backup filename is formatted so that when the filename list sorted in
            # the reverse order the first item in the list is the most recent backup.
            server_backup_files.sort(reverse=True, key=lambda x: get_backup_time(x))
            latest_backup = server_backup_files[0]

            # Copy current config file to temporary location to evaluate need for backup.
            data = self.file_manager.load()

            filepath_tmp = filepath + "_"
            saver = LocalFileManager(filepath_tmp)
            saver.save(data)

            # Always do backup in init. When running do backup on config update if at least 5 minutes is passed from
            # the previous backup.
            if is_init or time.time() - get_backup_time(latest_backup) >= 300:
                if not filecmp.cmp(filepath_tmp, latest_backup, False):
                    log.debug("Creating backup configuration {}.".format(filepath))
                    os.rename(filepath_tmp, filepath)
                else:
                    os.remove(filepath_tmp)
            else:
                os.remove(filepath_tmp)

    def clear_temp_files(self, server_backup_files, backup_dir):
        """
        Clears possible temporary files from backup folder. Temporary file has extension .yaml_.
        :param server_backup_files: List of backup file paths.
        :param backup_dir: Backup directory.
        :returns: A new list of backup files.
        """
        for file in server_backup_files:
            if file.endswith(".yaml_"):
                os.remove(os.path.join(backup_dir, file))

        return glob.glob(os.path.join(backup_dir, "start_server*"))


class TnTConfigurationManager:
    """
    Handles TnT configuration management
    """

    def __init__(self, configuration_file, configuration_ip=None):
        if configuration_file[-4:] == 'yaml':
            self._manager = YAMLConfigurationManager(configuration_file, configuration_ip)
        elif configuration_file[-3:] == 'xml':
            self._manager = XMLConfigurationManager(configuration_file)
        self.config = self._manager.get_configuration()

    def create_tree(self, program_arguments=None):
        if Node.root is None:
            Node.root = Tree.load(self.config["nodes"])
        Node.root.init(program_arguments=program_arguments)
        Node.manager = self

    def update_nodes(self):
        with self._manager.update_configuration() as config:
            Tree.update(config["nodes"])
            self.config = config

    def get_port(self):
        return self.config["port"]

    def backup_configuration(self, is_init=False):
        """
        Handles configuration backups
        """
        self._manager.backup_config(is_init)


class XMLConfigurationManager:
    """

    """

    def __init__(self, configuration_file):
        # import xml.etree.cElementTree as ET
        import xml.etree.ElementTree as ET
        import xml.dom.minidom as minidom
        from tntserver.Tree import load_node, import_nodes

        node_classes = import_nodes()

        f = open(configuration_file, 'r')
        s = f.read()
        f.close()

        def p_e(element):
            for c in element.childNodes:
                if c.__class__ != minidom.Element:
                    continue
                p_e(c)

        mt = minidom.parseString(s)
        p_e(mt.childNodes[0])

        e_configuration = mt.getElementsByTagName("configuration")[0]

        # tree = ET.XML(s)
        # print(tree)
        # print("---")

        def decode_parameter(s: str):
            if s is None:
                return s

            v = None
            try:
                v = eval(s.strip(), {}, {})
            except:
                pass

            if v is None:
                v = str(s)
            return v

        def parse_element(element):

            log.info("Parsing element {}".format(element.nodeName))

            """
            try:
                name = element.find('name').text
            except:
                return None
            """

            # e_parent = element.find('parent')
            # e_args = element.find('arguments')
            # e_props = element.find('properties')

            if element.nodeName == '#comment':
                # print("Comment")
                return None

            name = GetChildValue(element, 'name')
            if name is None:
                return None

            parent = GetChildValue(element, 'parent')
            e_args = GetChildNamed(element, 'arguments')
            e_props = GetChildNamed(element, 'properties')

            # parent = e_parent.text if e_parent is not None else None

            args = {}
            """
            if e_args is not None:
                for e in e_args.getchildren():
                    key = e.tag
                    value = decode_parameter(e.text)
                    args[key] = value
            """
            if e_args is not None:
                for e in e_args.childNodes:
                    key = e.nodeName
                    if key == '#text':
                        # whitespace etc.
                        continue

                    if key == '#comment':
                        # store comments?
                        continue

                    value = NodeValue(e)
                    args[key] = value

            props = {}
            """
            if e_props is not None:
                for e in e_props.getchildren():
                    key = e.tag
                    value = decode_parameter(e.text)
                    props[key] = value
            """
            if e_props is not None:
                for e in e_props.childNodes:
                    key = e.nodeName
                    if key == '#text':
                        continue
                    value = NodeValue(e)
                    props[key] = value

            e = {'cls': element.nodeName, 'name': name, 'parent': parent, 'arguments': args, 'properties': props}
            node = None
            try:
                node = load_node(e, node_classes)
            except Exception as e:
                log.warning("load_node failed {} {}".format(name, e))

            if parent is not None:
                parent_node = Node.find(parent)
                if parent_node is not None:
                    parent_node.add_child(node)
            return node

        def parse_recursive(element):
            node = parse_element(element)
            if node is not None:
                if Node.root is None:
                    Node.root = node

            e_children = element.childNodes
            for e in e_children:
                if e.nodeName == '#text':
                    continue
                node = parse_element(e)
                if node is not None:
                    if Node.root is None:
                        Node.root = node

        def NodeValue(element):
            values = [v.nodeValue for v in element.childNodes if v.nodeName == '#text']
            if len(values) == 0:
                return ""
            value = values[0]
            value = decode_parameter(value)
            return value

        def GetChildNamed(parent, name):
            a = [node for node in parent.childNodes if node.nodeName == name]
            if len(a) == 0:
                return None
            return a[0]

        def GetChildValue(parent, name):
            node = GetChildNamed(parent, name)
            if node is None:
                return None
            value = NodeValue(node)
            return value

        config = {}
        for e in e_configuration.childNodes:
            key = e.nodeName
            if key == '#text':
                continue
            elif key == 'api':
                parse_recursive(e)
            else:
                # value = decode_parameter(e.text)
                value = NodeValue(e)
                config[key] = value

        self._config = config

    def get_configuration(self):
        return self._config
