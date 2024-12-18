import json
import logging
import numpy as np
import threading
from functools import wraps
from collections import OrderedDict
import importlib

from tntserver import robotmath

log = logging.getLogger(__name__)

"""
Node should have 'init' function that is called only after all nodes and relations are created.
'init' can take any number of kwargs
Node can have 'properties'
Some 'properties' can store value to persistent store and read them in next startup
persistent properties must be json-compatible
"""


"""JSON number, which may be int or float"""


def get_node_class(class_path):
    """
    Get Node subclass from tntserver based on class path.
    :param class_path: Class path such as "TnT.Gestures".
    :return: Class corresponding to the path.
    """
    module = importlib.import_module("tntserver." + class_path)
    class_name = class_path.split(".")[-1]
    cls = getattr(module, class_name)

    return cls


def html_out(some_function):
    @wraps(some_function)
    def wrapper(cls, **args):
        rv = some_function(cls, **args)
        return "text/html", rv.encode("utf-8")

    return wrapper


def ascii_out(some_function):
    @wraps(some_function)
    def wrapper(cls, **args):
        rv = some_function(cls, **args)
        return "text/ascii", rv.encode("utf-8")

    return wrapper


def json_in(method=None, **kwargs):
    """
    TODO: Seems that this is not used anywhere.
    :param method: Function to be wrapped (not filled if kwargs are)
    :param kwargs: Will be passed to json.loads
    """
    def func_wrapper(some_function):
        @wraps(some_function)
        def wrapper(self, payload):
            return some_function(self, **json.loads(payload, **kwargs))
        wrapper.decodes = True
        return wrapper
    if method is not None:
        return func_wrapper(method)
    else:
        return func_wrapper


def _content_type_unpack(something):
    """
    Unpack return value
    :return: tuple of (response code, response payload, response headers)
    """
    if isinstance(something, tuple):
        if len(something) == 1:
            return None, something[0], None
        elif len(something) == 2:
            return None, something[0], something[1]
        elif len(something) == 3:
            return something
        else:
            raise NodeException("Too many values in tuple")
    else:
        return None, something, None


def _content_type_pack(response_code, response_type, response_payload, response_headers):
    if response_code is not None:
        return response_code, response_type, response_payload, response_headers
    elif response_headers is not None:
        return response_type, response_payload, response_headers
    elif response_type is not None:
        return response_type, response_payload
    else:
        return response_payload


def out(content_type):
    def content_out(some_function):
        @wraps(some_function)
        def wrapper(cls, *args, **kwargs):
            code, rv, headers = _content_type_unpack(some_function(cls, *args, **kwargs))
            if isinstance(rv, np.ndarray):
                rv = rv.tobytes()
            if not isinstance(rv, bytes):
                log.error("Handler func %s did not return bytes, instead %s", some_function.__name__, type(rv))
                raise NodeException('Internal server error')
            return _content_type_pack(code, content_type, rv, headers)
        return wrapper
    return content_out


def json_out(some_function):
    @wraps(some_function)
    def wrapper(cls, *args, **kwargs):
        code, rv, headers = _content_type_unpack(some_function(cls, *args, **kwargs))
        return _content_type_pack(code, "application/json", json.dumps(rv).encode("utf-8"), headers)

    return wrapper


text_out = out("text/plain")
jpeg_out = out("image/jpeg")
png_out = out("image/png")
wav_out = out("audio/x-wav")


def thread_safe(some_function):
    @wraps(some_function)
    def wrapper(cls, *args, **kwargs):
        return some_function(cls, *args, **kwargs)

    wrapper._RequestHandler__thread_safe = True

    return wrapper

def multipart(is_multipart):
    def wrapper(func):
        func.multipart = is_multipart
        return func
    return wrapper

def private(some_function):
    p = some_function
    components = p.__qualname__.split('.')
    class_name = components[0]
    property_name = components[1]

    if not class_name in Node.__private_properties__:
        Node.__private_properties__[class_name] = {}
    Node.__private_properties__[class_name][property_name] = True

    return some_function


def skip_nones(some_function):
    p = some_function
    components = p.__qualname__.split('.')
    class_name = components[0]
    property_name = components[1]

    if not class_name in Node.__hide_nones__:
        Node.__hide_nones__[class_name] = {}
    Node.__hide_nones__[class_name][property_name] = True

    return some_function


def debug_calculated_trajectory(some_function):
    # TODO: Seems that this is not used anywhere.
    @wraps(some_function)
    def wrapper(*args, **kwargs):
        try:
            return some_function(*args, **kwargs)
        except NodeException as e:
            if hasattr(e, 'positions'):
                import pip, importlib
                if all("matplotlib" not in dist.project_name for dist in pip.get_installed_distributions()):
                    # If matplot lib is not installed, raise exception
                    # Otherwise, print a plot with positions
                    raise
                plt = importlib.import_module("matplotlib.pyplot")
                x = e.positions['x']
                y = e.positions['y']
                z = e.positions['z']
                if 'azimuth' in e.positions and 'tilt' in e.positions:
                    azimuth = e.positions['azimuth']
                    tilt = e.positions['tilt']
                plt.plot(x, label='X')
                plt.plot(y, label='Y')
                plt.plot(z, label='Z')
                if 'azimuth' in e.positions and 'tilt' in e.positions:
                    plt.plot(azimuth, label='az')
                    plt.plot(tilt, label='tilt')
                plt.legend()
                plt.grid()
                plt.show()
            raise

    return wrapper


class NodeException(Exception):
    def __init__(self, title, http_code=500, messages=None):
        self.title = title
        self.http_code = http_code
        self.messages = messages if messages is not None else []


class NotFound(NodeException):
    def __init__(self):
        super().__init__('Not found', 404)

class Object:
    """
    Object should be derived and given a name.
    Objects create a tree that define the geometrical relations.
    """
    def __init__(self):
        self.object_parent = None
        self.object_children = {}
        self.name = "unknown"

    def translate(self, frame:np.matrix, target):
        """
        translate coordinate frame from source object
        :param frame: coordinate frame to translate to this object
        :param source: where the frame is translated from
        :return: translated frame
        """
        return robotmath.translate(frame, self, target)

    def add_object_child(self, object):
        """
        Add object as child to self.
        If given object is already a child of some other object, the child relation is removed.
        Object can only be a child of one object.
        :param object: Object to set as child.
        """
        object.remove_object_from_parent()

        self.object_children[object.name] = object
        object.object_parent = self

    def remove_object_from_parent(self):
        """
        Remove object (self) from its parent.
        """
        if self.object_parent is not None:
            del self.object_parent.object_children[self.name]
            self.object_parent = None

    def find_object_parent_by_class_name(self, class_name):
        """
        Find object parent node whose class name matches given name.
        :param class_name: Name of class.
        :return: Node object if found, otherwise None.
        """
        node = self.object_parent

        while node is not None:
            if node.__class__.__name__ == class_name:
                return node

            node = node.object_parent

        return None


class Node(Object):
    """
    Base for all nodes.
    Nodes create a tree that defines the REST API.

    By default nodes in the tree are saved to configuration file. To prevent this for a particular node class,
    define following class variable:

        transient = True

    """
    root = None
    _msg_lock = threading.Lock()
    _msgs = []  # TODO: It seems that this is not used anywhere.
    _msg_channels = {}

    __private_properties__ = {}
    __hide_nones__ = {}


    def __init__(self, name = None):
        """

        :param name: unique name or None. If None, the name will be autogenerated when added to parent with add_child
        :param path: rest api path
        """
        super().__init__()

        self._api_lock = threading.Lock()

        self.name = name
        self.children = OrderedDict()
        self.parent = None
        if not self.private_property('frame'):
            self.frame = robotmath.identity_frame()

    def listen_channel(self, channel:str):
        # TODO: Allows duplicate entries in list which seems error prone.
        with Node._msg_lock:
            if not channel in Node._msg_channels:
                Node._msg_channels[channel] = []
            Node._msg_channels[channel].append(self)

    def send_message(self, channel:str, message:str):
        # TODO: Should be static method.
        with Node._msg_lock:
            if channel in Node._msg_channels:
                for listener in Node._msg_channels[channel]:
                    listener.message(message)

    def message(self, message:str):
        log.warning("Message listener for node {} not implemented".format(self.name))

    # TODO: Make class function.
    def private_property(self, property_name):
        private = False

        # Loop through node class and its super classes to see if property is declared private.
        for cls in self.__class__.mro():
            try:
                if Node.__private_properties__[cls.__name__][property_name]:
                    private = True
            except:
                pass
        return private

    def hidden_none(self, property_name):
        hide_none = False
        try:
            hide_none = Node.__hide_nones__[self.__class__.__name__][property_name]
        except:
            pass
        return hide_none

    @json_out
    def api_info(self):
        """
        Just general info, part of every Node.
        """
        parent_name = self.parent.name if self.parent is not None else ""
        object_parent_name = self.object_parent.name if self.object_parent is not None else ""

        #info = { 'name' : self.name, 'path' : self.path, 'properties' : {}, 'functions' : {}, '_links': {} }
        info = {'name': self.name, 'parent': parent_name, 'connection': object_parent_name, 'properties': {}, 'functions': {}, '_links': []}

        f_get = [('get', p[4:]) for p in dir(self.__class__) if p[:4] == "get_"]
        f_put = [('put', p[4:]) for p in dir(self.__class__) if p[:4] == "put_"]
        f_post = [('post', p[5:]) for p in dir(self.__class__) if p[:4] == "post_"]
        functions = f_get + f_put + f_post

        info["functions"] = functions

        property_names = [p for p in dir(self.__class__) if isinstance(getattr(self.__class__, p), property)]

        for name in property_names:
            try:
                if name[0] != "_":
                    value = getattr(self, name)
                    if isinstance(value, np.matrix):
                        value = [[float(v) for v in a] for a in value.A]
                    info['properties'][name] = value
            except Exception as e:
                log.error("could not read property {} of {} : {}".format(name, self.name, e))

        # create href links
        pth = ""
        n = self
        while n is not None:
            pth = "/" + n.name + pth
            n = n.parent
        pth = "http://127.0.0.1:8000" + pth + "/"

        for t, f in functions:
            info["_links"].append({"method": t.upper(), "href": pth + f })

        # list children if any
        if len(self.children) > 0:
            lst = []
            for c_name in self.children:
                c = self.children[c_name]
                lst.append({"name": c_name, "type": c.__class__.__name__, "kind": ""})
            info[self.name] = lst
        """
        for c_name in self.children:
            c = self.children[c_name]
            link = {}
            link["resourcekind"] = c.__class__.__name__.lower()
            link["resourcename"] = c.name
            link["rel"] = "child"
            info["_links"].append(link)
        if self.parent is not None:
            link = {}
            link["resourcekind"] = self.parent.__class__.__name__.lower()
            link["resourcename"] = self.parent.name
            link["rel"] = "parent"
            info["_links"].append(link)
        """
        return info

    @json_out
    def tnt2_info(self):
        """
        Returns node information in tnt2 supported format.
        This is needed for sequence generator support.
        :return:
        """

        children = []
        if len(self.children) > 0:
            lst = []
            for c_name in self.children:
                c = self.children[c_name]
                # If the child has the _kind attribute report that, otherwise 'Unknown'
                try:
                    c_kind = c._kind
                except AttributeError:
                    c_kind = 'Unknown'

                children.append({"name": c_name, "type": c.__class__.__name__, "kind": c_kind})

        #

        links = []
        f_get = [('get', p[4:]) for p in dir(self.__class__) if p[:4] == "get_"]
        f_put = [('put', p[4:]) for p in dir(self.__class__) if p[:4] == "put_"]
        f_post = [('post', p[5:]) for p in dir(self.__class__) if p[:4] == "post_"]
        functions = f_get + f_put + f_post

        # create href links
        pth = ""
        n = self
        while n is not None:
            pth = "/" + n.name + pth
            n = n.parent
        pth = "http://127.0.0.1:8000" + pth + "/"

        for t, f in functions:
            links.append({"method": t.upper(), "href": pth + f})

        info = {self.name: children, "_links": links}

        #

        property_names = [p for p in dir(self.__class__) if isinstance(getattr(self.__class__, p), property)]
        if len(property_names) > 0:
            properties = {}
            for name in property_names:
                try:
                    if name[0] != "_":
                        value = getattr(self, name)
                        if isinstance(value, np.matrix):
                            value = [[float(v) for v in a] for a in value.A]
                        elif issubclass(value.__class__, Node):
                            # Node objects are not json serializable, use the name of the Node as value instead
                            value = value.name

                        properties[name] = value
                except Exception as e:
                    log.error("could not read property {} of {} : {}".format(name, self.name, e))

            info["properties"] = properties

        # now some tnt_gt extra info needed by TnT UI

        return info

    @json_out
    def get_relations(self):
        """
        Moved from default info to here because breaks TnT2 compatibility
        :return:
        """
        parent_name = self.parent.name if self.parent is not None else ""
        object_parent_name = self.object_parent.name if self.object_parent is not None else ""
        info = {'name': self.name, 'parent': parent_name, 'connection': object_parent_name}
        return info

    @json_out
    def put_set_connection(self, connection_name):
        connection_node = Node.find(connection_name)
        if connection_node is not None:
            connection_node.add_object_child(self)
            self.save()
        else:
            raise NodeException('Node {} not found'.format(connection_name))

    @json_out
    def get_connection(self):
        return self.object_parent.name

    def init(self, **kwargs):
        """
        Initialize node and its children recursively. Calls node's _init method.
        :param kwargs: Keyword arguments that are passed down to the _init method of each node.
        """

        try:
            # Make a copy to avoid updating self._init_arguments by kwargs that are not node specific.
            arguments = self._init_arguments.copy()
        except:
            arguments = {}

        # Make sure that _init_arguments don't conflict with kwargs.
        for key in arguments.keys():
            assert key not in kwargs

        arguments.update(kwargs)

        try:
            log.info("init '%s' with arguments %s", self.name, arguments)
            self._init(**arguments)
        except Exception:
            log.exception("init of '%s' failed", self.name)

        for child in self.children.values():
            child.init(**kwargs)

    def _init(self, **kwargs):
        pass

    def help(self):
        s = ""
        #functions = [p[4:] for p in dir(self.__class__) if p[:4] == "api_"]
        f_get = [('get', p[4:]) for p in dir(self.__class__) if p[:4] == "get_"]
        f_put = [('put', p[4:]) for p in dir(self.__class__) if p[:4] == "put_"]
        f_post = [('post', p[5:]) for p in dir(self.__class__) if p[:4] == "post_"]
        functions = f_get + f_put + f_post



        d = {
            "properties" : self.__properties(),
            "functions" : functions,
            "name" : self.name,
            "classname" : self.__class__.__name__,
            "object" : self
            }
        return d

    def add_child(self, node):

        if node is None:
            print(node)

        self.children[node.name] = node
        node.parent = self

        self.object_children[node.name] = node
        node.object_parent = self

    def remove_child(self, node):
        del self.children[node.name]
        node.parent = None

        if node.object_parent is not None:
            del node.object_parent.object_children[node.name]
            node.object_parent = None

    def find(self, name: str):
        """
        Find Node with name recursively using this node as root
        TODO: This function clashes with staticmethod find() and should be removed.
        :param name: name of the Node to find
        :return: found Node or None
        """
        return Node.find_from(self, name)

    @staticmethod
    def find(name):
        """
        Find Node with name recursively from whole tree
        :param name: name of the Node to find
        :return: found Node or None
        """
        if Node.root is None:
            return None
        found = Node.find_from(Node.root, name)
        return found

    @staticmethod
    def find_from(from_node, name : str):
        """
        Find Node with name recursively using from_node as root
        :param name: name of the Node to find
        :return: found Node or None
        """
        if from_node.name == name:
            return from_node
        if hasattr(from_node, 'children'):
            for child in from_node.children.values():
                found = Node.find_from(child, name)
                if found:
                    return found
        return None

    @staticmethod
    def find_node_by_path(from_node, path : str):
        """
        Find node by path description. Path description consists of node names separated by dots.
        :param from_node: Node where to start finding through children.
        :param path: Path description in relation to from_node. E.g. "root.child_of_root.child_of_child_of_root".
        :return: Node object if found. None if not found.
        """
        def find_node_by_path_recursively(node, sub_path):
            if sub_path == node.name:
                return node

            if "." not in sub_path:
                return None

            # Remove current node.
            sub_path = sub_path.split(".", maxsplit=1)[1]

            parts = sub_path.split(".", maxsplit=1)

            for child in node.children.values():
                if parts[0] == child.name:
                    if len(parts) == 1:
                        return child
                    else:
                        n = find_node_by_path_recursively(child, sub_path)

                        if n is not None:
                            return n

            return None

        return find_node_by_path_recursively(from_node, path)


    @staticmethod
    def find_class(class_name):
        """
        Find recursively all Nodes in the tree with class named class_name
        :param class_name: class name to find
        :return: list of Nodes found
        """
        return Node.find_class_from(Node.root, class_name)

    @staticmethod
    def find_class_from(from_node, class_name):
        """
        Find recursively all Nodes with class named class_name using from_node as root
        :param from_node root node for the search
        :return: list of Nodes found
        """
        lst = []
        if from_node.__class__.__name__ == class_name:
            lst.append(from_node)
        if hasattr(from_node, 'children'):
            for child in from_node.children.values():
                lst += Node.find_class_from(child, class_name)
        return lst

    def find_parent_by_class_name(self, class_name):
        """
        Find parent node whose class name matches given name.
        :param class_name: Name of class.
        :return: Node object if found, otherwise None.
        """
        node = self.parent

        while node is not None:
            if node.__class__.__name__ == class_name:
                return node

            node = node.parent

        return None

    def json(self):
        f = [[float(a) for a in b] for b in self.frame.A]
        #r = {'name': self.name, 'path': self.path, 'frame' : f}
        r = {'name': self.name, 'frame': f}
        if self.parent is not None:
            r['parent'] = self.parent.name

        return r

    @staticmethod
    def from_json(v):
        # TODO: It seems that this is not used anywhere.
        path = v['path'] if 'path' in v else None
        self = Node(v['name'], path)

        try:
            m = v['frame']
        except:
            m = [[1,0,0,0], [0,1,0,0], [0,0,1,0], [0,0,0,1]]
        self.frame = np.matrix(m)

        try:
            self.parent = Node.find(v['parent'])
        except:
            pass

        return self

    def save(self):
        """
        Saves a node.
        """
        try:
            # TODO: self.manager not declared in init.
            self.manager.update_nodes()

            try:
                self.manager.backup_configuration(is_init=False)
            except Exception as e:
                logging.exception("Could not create backup configuration because there was an error {}".format(str(e)))

        except Exception as e:
            logging.exception("Could not save node {}, error:{}".format(self.name, str(e)))

    def fullname(self):
        parts = []
        node = self
        while node:
            parts.append(node.name)
            node = node.parent
        name = ".".join(parts[::-1])
        return name

    def find_child_with_path(self, path):
        # TODO: path is misleading. Is this function needed in addition to find_from()?
        for child in self.children.values():
            if child.name == path:
                return child
        raise NodeException("Child not found", 404)

    def __properties(self):
        properties = {}

        def map_dict(d):
            ret = {}
            for name, value in d.items():
                if isinstance(value, dict):
                    ret[name] = map_dict(value)
                else:
                    ret[name] = {"value": str(value), "type": value.__class__.__name__}
            return ret

        property_names = [p for p in dir(self.__class__) if isinstance(getattr(self.__class__, p), property)]
        for name in property_names:
            if name[0] == "_":
                continue
            try:
                value = getattr(self, name)
                if isinstance(value, dict):
                    properties[name] = map_dict(value)
                else:
                    properties[name] = {"value": str(value), "type": value.__class__.__name__}
            except Exception as e:
                log.error("could not read property {} of {} : {}".format(name, self.name, e))

        return properties

    @json_out
    def put_properties(self, **kwargs):
        fail = False
        for name in kwargs:
            if self.private_property(name):
                log.debug("{} : skip set private property {}".format(self.name, name))
                continue
            value = kwargs[name]
            try:
                setattr(self, name, value)
                log.info("{} : set property {} = {}".format(self.name, name, value))
            except Exception as e:
                log.exception(e)    # Better to get information about original exception
                log.warning("could not set property '{}' of '{}' to {}", name, self.fullname(), value)
                fail = True

        if fail:
            raise Exception("setting property failed")
        else:
            self.save()

        return ""

    @json_out
    def get_properties(self):
        p = self.__properties()
        return p

    @json_out
    def get_property(self, name):
        """
        Get value and type of given property
        :param name: name of the property
        :return: property value and type in dict
        """
        p = self.__properties()
        if name in p.keys():
            return p[name]
        else:
            log.error("property '{}' not found for '{}'".format(name, self.fullname()))
            raise KeyError("property '{}' not found for '{}'".format(name, self.fullname()))

    @json_out
    def get_frame(self, context):
        """
        returns the node's frame in target context
        :param context_name: name of target context Node
        :return: translated frame of self
        """
        target_frame = Node.find(context)
        frame = robotmath.translate(self.frame, self.object_parent, target_frame)
        return frame.tolist()

    @json_out
    def put_frame(self, frame):
        self.frame = np.matrix(frame)
        self.save()

    @json_out
    def get_local_frame(self):
        """
        :return: the node's local frame
        """
        return self.frame.tolist()

    @json_out
    def put_name(self, name):
        """
        Renames the Node.
        :param name: New name for the node.
        :returns: JSON with old and new name.
        """
        old_name = self.name
        if name != old_name:
            parent = self.parent
            object_parent = self.object_parent
            if parent is not None:
                if name in parent.children.keys():
                    raise Exception("Node with name {} already exists.".format(name))
                parent.children[name] = parent.children[old_name]
                parent.children.pop(old_name)

            if object_parent is not None:
                if name in object_parent.object_children.keys():
                    raise Exception("Node with name {} already exists.".format(name))
                object_parent.object_children[name] = object_parent.object_children[old_name]
                object_parent.object_children.pop(old_name)

            self.name = name
            self.save()
        return {"old_name": old_name, "name": name}

# Avoid getting all imports transitively with "from tntserver.Node import *"
#__all__ = ["Node", "NodeException", "validate_params", "json_out", "html_out", "ascii_out", "jpeg_out",
#           "thread_safe", "private", "skip_nones", "debug_calculated_trajectory"]
