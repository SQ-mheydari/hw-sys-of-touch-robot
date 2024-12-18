import json
import time
import logging

logger = logging.getLogger(__name__)

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class Stop(Exception):
    def __init__(self, message=None):
        self.message = message
        pass


class Controls:
    def __init__(self):
        self._info = {}
        self._indices = {}

    def get_controls(self):
        controls = []

        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue

            controls.append((key, self._indices[key]))

        # Sort controls according to index defined in info.
        controls = sorted(controls, key=lambda x: x[1])

        return [c[0] for c in controls]

    @property
    def info(self):
        return self._info

    @info.setter
    def info(self, value):
        self._info = value

    def __setattr__(self, name, value):
        if name.startswith('_'):
            self.__dict__[name] = value
        else:
            if name not in self.__dict__:
                self._indices[name] = len(self.get_controls())

            self.__dict__[name] = value

    def to_dict(self):
        members = {c: getattr(self, c) for c in self.get_controls()}

        d = {'members': members, 'info': self._info, 'indices': self._indices}

        return d

    def from_dict(self, d):
        for key, value in d['members'].items():
            # Set value and preserve original type (prevent e.g. bool -> int conversion).
            control_type = type(getattr(self, key))
            setattr(self, key, control_type(value))

        self._info = d['info']
        self._indices = d['indices']


class Node:
    def __init__(self, name):
        self.name = name
        self.children = []
        self.parent = None

        self.enabled = True
        self.display_enabled = False
        self.controls = Controls()

    def add_child(self, node):
        self.children.append(node)
        node.parent = self

    def traverse(self, method, *args):
        m = getattr(self, method)
        m(*args)

        for c in self.children:
            c.traverse(method, *args)

    def execute(self):
        pass

    def get_child(self, name):
        for c in self.children:
            if c.name == name:
                return c

    @property
    def num_enabled_children(self):
        num = 0

        for c in self.children:
            if c.enabled:
                num += 1

        return num

    def to_dict(self):
        children = [c.to_dict() for c in self.children]

        d = {'name': self.name, 'enabled': self.enabled, 'display_enabled': self.display_enabled, 'children': children, 'controls': self.controls.to_dict()}

        return d

    def from_dict(self, d):
        self.enabled = d['enabled']
        self.display_enabled = d['display_enabled']
        self.controls.from_dict(d['controls'])

        for child in d['children']:
            self.get_child(child['name']).from_dict(child)

    def find_by_name(self, name):
        """
        Finds node object by its name non-recursively.
        :param name: The name of the node.
        :return: The node object or None if not found.
        """
        for node in self.children:
            if node.name == name:
                return node

        return None

class TestStep(Node):
    __test__ = False  # Pytest ignore.

    def __init__(self, name):
        super().__init__(name)
        self.display_enabled = True
        self.enabled = False

class Parameter:
    def __init__(self, name, value='', single_line=True):
        self.name = name
        self.value = value
        self.single_line = single_line

    def to_dict(self):
        return {'name': self.name, 'value': self.value, 'single_line': self.single_line}


class RootNode(Node):
    """
    Root node contains all other nodes and does not contain any additional controls or objects.
    It is not directly visible in the UI.
    """

    def __init__(self):
        super().__init__('root')


def load_script_history_headers(filename):
    """
    Load script history headers from JSON file.
    :param filename: Name of history file.
    :return: List of header strings.
    """
    try:
        with open(filename) as file:
            data = json.load(file)
    except:
        return []

    headers = [key for key, value in data.items()]

    headers.sort(reverse=True)

    return headers


def node_to_dict(node):
    """
    Convert node value state to dictionary.
    The state consists of essentially the control values and enabled-state.
    :param node: Node to convert.
    :return: Dictionary that contains the value state.
    """
    controls = {}
    children = {}

    # Store node enabled state.
    node_data = {'enabled': node.enabled, 'controls': controls, 'children': children}

    # Store node control values.
    for control_name in node.controls.get_controls():
        control_value = getattr(node.controls, control_name)

        if isinstance(control_value, bool):
            controls[control_name] = "True" if control_value else "False"
        else:
            controls[control_name] = control_value

    # Recurse over children.
    for child in node.children:
        children[child.name] = node_to_dict(child)

    return node_data


def save_script_values(filename, nodes, parameters, name=None):
    """
    Save script values to JSON file.
    :param filename: Name of the file.
    :param nodes: Nodes to save (list of Node objects).
    :param parameters: Parameters to save (list of Parameter objects).
    :param name: Optional name to use for parameter set instead of generated timestamp
    """
    try:
        with open(filename) as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}

    # Time and date is identifier for saved state.
    name = time.strftime(TIME_FORMAT) if name is None else name

    p_data = {}
    nodes_data = {}

    # Save parameters.
    data[name] = {'parameters': p_data, 'nodes': nodes_data}

    for p in parameters:
        p_data[p.name] = {'value': p.value}

    # Save nodes.
    for node in nodes:
        nodes_data[node.name] = node_to_dict(node)

    with open(filename, 'w') as file:
        json.dump(data, file, sort_keys=True, indent=4, separators=(',', ': '))


def dict_to_node(dict, node):
    """
    Convert dictionary to node value state.
    :param dict: Disctionary that contains the value state.
    :param node: List of Node objects where the state is set to.
    """
    # Set node enabled state.
    try:
        node.enabled = bool(dict['enabled'])
    except KeyError:
        logger.error('"enabled" key not found in script history!')

    controls = None

    # Set node control values.
    try:
        controls = dict['controls']
    except KeyError:
        logger.error('"controls" key not found in script history!')

    for control_name, control_value in controls.items():
        # Explicitly cast loaded value to type of the control variable.
        # It sometimes happens that e.g. boolean value has been saved as integer.
        if hasattr(node.controls, control_name):
            control_type = type(getattr(node.controls, control_name))

            # Boolean values are serialized as string 'True'/'False'.
            if control_type is bool:
                setattr(node.controls, control_name, control_value == 'True')
            else:
                setattr(node.controls, control_name, control_type(control_value))
        else:
            logger.error('Node ' + node.name + ' has no control variable named ' + control_name)

    # Recurse over node children.
    children = None

    try:
        children = dict['children']
    except KeyError:
        logger.error('"children" key not found in script history!')

    for child_name, child_data in children.items():
        child = node.get_child(child_name)

        if child is None:
            if bool(child_data.get('enabled', False)):
                logger.warning("Node {} is enabled in history but it no longer exists in node tree.".format(child_name))
        else:
            dict_to_node(child_data, child)


def load_script_values(filename, name, nodes, parameters):
    """
    Load script values from JSON history file.
    :param filename: Name of the the file.
    :param name: Name of piece of history to load (date and time).
    :param nodes: List of Node objects where values are loaded to.
    :param parameters: List of Parameter objects where values are loaded to.
    """

    with open(filename) as file:
        data = json.load(file)

    data = data[name]

    parameter_data = None

    # Load parameters.
    try:
        parameter_data = data['parameters']
    except KeyError:
        logger.error('"parameters" key not found in script history!')

    for p_name, p_data in parameter_data.items():
        for p in parameters:
            if p.name == p_name:
                p.value = p_data['value']
                break

    # Load nodes values.
    nodes_data = None

    try:
        nodes_data = data['nodes']
    except KeyError:
        logger.error('"nodes" key not found in script history!')

    for node in nodes:
        try:
            dict_to_node(nodes_data[node.name], node)
        except KeyError:
            logger.error(node.name + " node not found in script history")
