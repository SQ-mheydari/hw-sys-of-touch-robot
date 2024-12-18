"""
Functions to parse run-time node structure to client API structure
that can then be written as TnT Client for desired programming languages.
"""
from tntserver.Nodes.Node import Node
import importlib


def has_super_attr(cls, attr_name):
    """
    Has super classes of given class a given attribute?
    :param cls: Class to inspect.
    :param attr_name: Attribute name to check.
    :return: True if attribute was found in one of the superclasses.
    """
    for base in cls.__bases__:
        if hasattr(base, attr_name):
            return True

    return False


class ApiMethodParameter:
    """
    Represents node method parameter.
    """
    def __init__(self, name, ptype):
        """
        Initialize object.
        :param name: Parameter name.
        :param ptype: Parameter type (Python type such as int).
        """
        self.name = name
        self.type = ptype

        self._default = None
        self.has_default = False

        # TODO: Make possible to convert parameter (e.g. from bytes to base64 encoded bytes).

    @property
    def default(self):
        """
        Method parameter default value if one is specified.
        """
        if not self.has_default:
            raise Exception("Method parameter does not have default value.")

        return self._default

    @default.setter
    def default(self, value):
        self._default = value
        self.has_default = True


class ApiMethod:
    """
    Represents node method.
    """
    def __init__(self, name, request_type, doc):
        """
        Initialize object.
        :param name: Method name.
        :param request_type: Request type as string (one of "get", "put", "post").
        :param doc: Method docstring. Can be None if there is no docstring.
        """
        self.name = name
        self.client_name = name
        self.request_type = request_type
        self.parameters = []
        self.doc = doc.strip() if doc is not None else None
        self.node_path = None
        self.content_type = None
        self.content = False  # If True, client API parameters is passed as content.


class ApiProperty:
    """
    Represents node property.
    """
    def __init__(self, name, doc, settable):
        """
        Initialize object.
        :param name: Property name.
        :param doc: Property docstring. Can be None if there is no docstring.
        :param settable: Is property settable?
        """
        self.name = name
        self.doc = doc.strip() if doc is not None else None
        self.settable = settable
        self.node_path = None


class ApiNode:
    """
    Represents a node.
    """
    def __init__(self, client_name, resource_type, doc):
        """
        Initialize object.
        :param client_name: Name of class that appears in client (e.g. "TnTDUTClient").
        :param resource_type: Resource type of client (e.g. "dut").
        :param doc: Node docstring. Can be None if there is no docstring.
        """
        self.client_name = client_name
        self.resource_type = resource_type
        self.methods = []
        self.properties = []
        self.doc = doc.strip() if doc is not None else None

        # Client name parameter. If None, then must be given as init parameter.
        self.object_name = None

        # Does node have capability to delete the resource?
        self.deletable = False
        
        self.module_name = None



def generate_api_method(method):
    """
    Generate API method based on given method object.
    :param method: Method object (method of Node subclass).
    :return: ApiMethod object.
    """

    method_name = method.__name__

    # Number of function arguments.
    argcount = method.__code__.co_argcount

    # Argument names.
    args = method.__code__.co_varnames[:argcount]

    # Function docstring.
    method_doc = method.__doc__

    method_name_raw = method_name

    request_type = None

    # Create function definition.
    if method_name.startswith("put_") or method_name.startswith("get_"):
        method_name_raw = method_name[4:]
        request_type = method_name[:3]
    elif method_name.startswith("post_"):
        method_name_raw = method_name[5:]
        request_type = "post"

    api_method = ApiMethod(method_name_raw, request_type, method_doc)

    arg_defaults = method.__defaults__

    # Parse method parameters.
    for i, arg in enumerate(args):
        if arg == "self":
            continue

        # TODO: Determine parameter type.
        api_param = ApiMethodParameter(arg, None)

        if arg_defaults is not None:
            defaults_start = argcount - len(arg_defaults)

            if i >= defaults_start:
                api_param.default = arg_defaults[i - defaults_start]

        api_method.parameters.append(api_param)

    return api_method


def generate_api_node(cls, node_path, client_name, resource_type, mapping, object_name, include, exclude):
    """
    Generate node API based on given node.
    :param cls: Class to generate API for.
    :param node_path: Node path (see ApiNode).
    :param client_name: Name of API in client (see ApiNode).
    :param resource_type: Resource type of node (see ApiNode).
    :param mapping: Dictionary that maps client attribute name to server attribute name.
    :param object_name: Name of client object if it should be determined. Can be None.
    :param include: List of members to include. If None then everything is included.
    :param exclude: List of members to exclude. If None then nothing is excluded.
    :return: ApiNode object.
    """

    attr_names = dir(cls)

    api_node = ApiNode(client_name, resource_type, cls.__doc__)
    api_node.object_name = object_name

    # Methods
    for attr_name in attr_names:
        attr = getattr(cls, attr_name)

        if not callable(attr):
            continue

        while hasattr(attr, "__wrapped__"):
            attr = getattr(attr, "__wrapped__")
            attr_name = attr.__name__

        if attr_name.startswith("_"):
            continue

        if exclude is not None and attr_name in exclude:
            continue

        if include is not None and attr_name not in include:
            continue

        if mapping is None or attr_name not in mapping:
            if (not attr_name.startswith("put_")) and (not attr_name.startswith("get_")) and (not attr_name.startswith("post_")):
                continue

        # Skip Node class methods.
        if hasattr(Node, attr_name):
            continue

        method = generate_api_method(attr)
        method.node_path = node_path

        if mapping is not None and attr_name in mapping:
            method.client_name = mapping[attr_name]["client_name"]
            method.request_type = mapping[attr_name]["request_type"]
            method.content_type = mapping[attr_name].get("content_type", None)
            method.content = mapping[attr_name].get("content", False)

        api_node.methods.append(method)

    # Properties
    for attr_name in attr_names:
        attr = getattr(cls, attr_name)

        if not isinstance(attr, property):
            continue

        # Skip Node class properties.
        if hasattr(Node, attr_name):
            continue

        if exclude is not None and attr_name in exclude:
            continue

        if include is not None and attr_name not in include:
            continue

        settable = attr.fset is not None

        api_property = ApiProperty(attr_name, attr.__doc__, settable)
        api_property.node_path = node_path

        api_node.properties.append(api_property)

    if hasattr(cls, "delete_self"):
        api_node.deletable = True

    return api_node


