import collections.abc
import importlib
import logging

import numpy as np

from tntserver.Nodes.Node import *
import pkgutil

log = logging.getLogger(__name__)

"""

Functions related to
- loading Node tree from a file
- storing Node tree to a file

"""

class ConfigurationException(Exception):
    pass

def import_nodes():
    def fnone(f, *args):
        try:
            r = f(*args)
            return r
        except:
            return None

    # create list of import names
    import_names = [b for a, b, c in pkgutil.walk_packages(__file__) if str.startswith(b, "tntserver.Nodes")]

    # create list of modules
    modules = [(a, fnone(importlib.import_module, a)) for a in import_names]

    # create dict of classes
    items = {}
    for name, module in modules:
        if module is not None:
            try:
                className = name.split('.')[-1]
                cls = getattr(module, className)
                items[name.split("tntserver.Nodes.")[1]] = cls
            except:
                pass

    return items


def get_node_path(name, node_paths):
    """
    Get node path by using node name and a set of existing node paths.
    A full path is e.g. "tnt.workspaces.ws" whereas name of a node is e.g. "ws".
    :param name: Name of node or full node path.
    :param node_paths: Known node paths.
    :return: Full path of node.
    """

    # If name exactly matches a known path, it is already correct.
    for path in node_paths:
        if name == path:
            return path

    # For legacy compatibility allow matches to the end of parent name.
    # For example name="robots" will match node path "tnt.workspaces.ws.robots".
    # Such simplified naming will only work if node names in the entire node tree are unique.
    # Otherwise "robots" could also match "tnt.workspaces.ws2.robots".
    for path in node_paths:
        if path.endswith("." + name):
            return path

    raise ConfigurationException("Node path not found for {}. Known node paths: {}".format(name, node_paths))


def load(nodes_js):
    child_parent = []
    child_object_parent = []
    root_node = None
    nodes = {}
    object_nodes = {}

    #node_classes = import_nodes()

    for node_js in nodes_js:
        node = load_node(node_js)
        if node is None:
            continue

        parent_name = node_js["parent"] if "parent" in node_js else None
        if parent_name:
            full_parent_name = get_node_path(parent_name, nodes.keys())
            nodes[full_parent_name + "." + node.name] = node
            child_parent.append((node, full_parent_name))

            # Object parent is by default node parent if not specifically set below.
            full_object_parent_name = get_node_path(parent_name, object_nodes.keys())
            object_nodes[full_object_parent_name + "." + node.name] = node
        else:
            nodes[node.name] = node
            root_node = node

            # Object parent is by default node parent if not specifically set below.
            object_nodes[node.name] = node

        object_parent_name = node_js["connection"] if "connection" in node_js else None
        if object_parent_name is not None:
            object_parent_name = get_node_path(object_parent_name, object_nodes.keys())
            object_nodes[object_parent_name + "." + node.name] = node
            child_object_parent.append((node, object_parent_name))
        else:
            object_nodes[node.name] = node


    for node, parent_name in child_parent:
        if parent_name not in nodes:
            log.error("Configuration contain node '%s' with unknown parent '%s'", node.name, parent_name)
            raise ConfigurationException("Configuration contain node '{}' with unknown parent '{}'".format(node.name, parent_name))

        parent = nodes[parent_name]
        parent.children[node.name] = node
        node.parent = parent

    for node, parent_name in child_object_parent:
        parent = object_nodes[parent_name]
        parent.object_children[node.name] = node
        node.object_parent = parent

    #debug_print_node(root_node)

    return root_node


def decode_parameter(s: str):
    if s is None:
        return None
    if not issubclass(s.__class__, str):
        return s

    v = None
    try:
        v = eval(s.strip(), {}, {})
    except Exception as e:
        pass

    if v is None:
        v = str(s)
    return v

def load_node(e):
    """
    Instantiates one Node from json definition
    :param e: json of the Node
    :param nodeclasses: dictionary containing all Node classes
    :return: instantiated Node
    """

    name = e['cls']
    import_name = "tntserver.Nodes." + name
    module = importlib.import_module(import_name)
    className = name.split('.')[-1]
    cls = getattr(module, className)

    #cls = nodeclasses[e['cls']] if e['cls'] in nodeclasses else None
    if cls is None:
        log.warning("Could not instantiate node {}".format(e['cls']))
        return None
    #path = e['path'] if 'path' in e else None
    node = cls(e['name'])

    if 'frame' in e:
        m = e['frame']
        node.frame = np.matrix(m)

    properties = e.get('properties', None)
    if properties is None:
        properties = {}
    if not isinstance(properties, collections.abc.Mapping):
        logging.warning("Properties should be dictionary {} for node %s", e['name'])

    for propertyname, value in properties.items():
        if propertyname[0] == "_" or node.private_property(propertyname):
            log.warning("%s: Skip set private property %s. Remove from config", node.name, propertyname)
            continue
        if node is None and node.hidden_none(propertyname):
            continue
        try:
            value = decode_parameter(value)
            setattr(node, propertyname, value)
        except Exception as ex:
            logging.exception("Failed to set node '{}' property {} : {}".format(node.name, propertyname, ex))

    arguments = e.get('arguments', {})
    node._init_arguments = arguments

    return node


def get_node_json(node):
    js = node.json()

    children = {}
    for child in node.children.values():
        children[child.name] = get_node_json(child)

    js["children"] = children
    return js


def __json_type(value):
    """
    Validate that value is fully JSON serializable
    """
    # TODO: how about just try: json.dump(value); return True; except: return False
    if value is None or isinstance(value, int) or isinstance(value, float) or isinstance(value, str):
        return True
    elif isinstance(value, list):
        if all(map(__json_type, value)):
            return True
    elif isinstance(value, dict):
        if all(map(lambda k: isinstance(k, str), value.keys())) and all(map(__json_type, value.values())):
            return True
    return False


def get_live_node_full_parent_name(node):
    """
    Get full path description of node parent. E.g. for node "ws" the full path of parent
    could be "tnt.workspaces".
    :param node: Node object.
    :return: Path of parent as string.
    """
    if node.parent is None:
        return None

    full_name = ""

    parent = node.parent

    while parent is not None:
        full_name = parent.name + "." + full_name

        if parent == Node.root:
            if full_name.endswith("."):
                full_name = full_name[:-1]

            return full_name

        parent = parent.parent

    return None


def get_live_node_full_object_parent_name(node):
    """
    Get full path description of node object parent. E.g. for node "ws" the full path of parent
    could be "tnt.workspaces".
    Note: This is essentially the same as get_live_node_full_parent_name() but uses object_parent instead of parent.
    :param node: Node object.
    :return: Path of parent as string.
    """
    if node.object_parent is None:
        return None

    full_name = ""

    object_parent = node.object_parent

    while object_parent is not None:
        full_name = object_parent.name + "." + full_name

        if object_parent == Node.root:
            if full_name.endswith("."):
                full_name = full_name[:-1]

            return full_name

        object_parent = object_parent.object_parent

    return None


def __update_node(node_js, live_node):
    """
    Update properties from Node to configuration
    """
    if not isinstance(node_js, dict):
        raise Exception("node_js should be dict")

    for property in dir(live_node):
        # Skip privates
        private = (property[0] == "_")
        try:
            private = private or live_node.private_property(property)
        except:
            pass
        if private:
            continue
        # Skip build-ins
        if property == "name" or property == "children" or property == "root":
            continue
        value = getattr(live_node, property)

        # Convert frame from 4x4 numpy array to list of lists
        if property == "frame":
            if ("frame" in node_js and node_js["frame"] is not None) or not np.array_equal(value, np.eye(4)):
                node_js["frame"] = value.tolist()
        # Convert parent reference to name
        elif property == "parent":
            node_js["parent"] = get_live_node_full_parent_name(live_node)
        #elif property == "path":
        #    node_js["path"] = value
        elif property == "object_parent":
            node_js["connection"] = get_live_node_full_object_parent_name(live_node)
        elif property == "object_children":
            pass
        else:
            if __json_type(value):
                if not "properties" in node_js or not node_js["properties"]:
                    node_js["properties"] = {}
                # Check if value should be hidden as none
                if value is None and live_node.hidden_none(property):
                    if property in node_js["properties"]:
                        del node_js["properties"][property]
                else:
                    node_js["properties"][property] = value


def conf_node_equal_to_tree_node(conf_node, tree_node):
    """
    Check if node in config form is the same as in Node object form.
    Nodes are considered equal if the names match and the parent names / paths match.
    :param conf_node: Node as dict.
    :param tree_node: Node as Node object.
    :return: True if they represent the same node.
    """
    if conf_node["name"] != tree_node.name:
        return False

    node_parent_name = get_live_node_full_parent_name(tree_node)

    if conf_node["parent"] != node_parent_name:
        return False

    return True


def __find_new_nodes(conf_node_list, tree_node, callback):
    """
    Search tree of nodes to find any nodes that do not exist in configuration
    """
    conf_node = [conf_node for conf_node in conf_node_list if conf_node_equal_to_tree_node(conf_node, tree_node)]
    conf_node = conf_node[0] if len(conf_node) else None

    if conf_node is None:
        callback(tree_node)
    for tree_child in tree_node.children.values():
        if hasattr(tree_child, 'transient') and tree_child.transient:
            # Skip transient nodes
            continue
        __find_new_nodes(conf_node_list, tree_child, callback)


def update(nodes_js):
    """
    Update current Node tree back to nodes_js structure.

    :param nodes_js: JSON compatible dict, list, str, bool, number object tree to be updated.
    """

    full_node_names = set()

    # Update existing nodes and add missing nodes
    to_delete = []
    for node_js in nodes_js:
        name = node_js["name"]

        parent_name = node_js["parent"] if "parent" in node_js else None
        if parent_name:
            full_parent_name = get_node_path(parent_name, full_node_names)
            name = full_parent_name + "." + name

        full_node_names.add(name)

        live_node = Node.find_node_by_path(Node.root, name)

        if live_node is not None:
            __update_node(node_js, live_node)
        else:
            to_delete.append(node_js)

    # Delete removed nodes
    for node in to_delete:
        nodes_js.remove(node)

    def add_new_node_to_config(node):
        try:
            clsname = node.__module__.split(".")
            clsname = clsname[2:]
            clsname = ".".join(clsname)
            conf_node = {"name": node.name,
                         "cls": clsname,
                         'parent': None,
                         #'path': node.name,
                         'frame': None,
                         'arguments': {},
                         'properties': {}
                         }


            if hasattr(node, '_init_arguments'):
                conf_node["arguments"] = node._init_arguments

            __update_node(conf_node, node)

            if conf_node["frame"] is None:
                del conf_node["frame"]

            nodes_js.append(conf_node)
            log.info("added new resource to config '%s'", node.name)
        except Exception:
            log.exception("Error while adding node '%s'", node.name)

    # Find new nodes
    __find_new_nodes(nodes_js, Node.root, add_new_node_to_config)


def debug_print_node(node:Node):
    import xml.etree.cElementTree as ET
    import xml.dom.minidom as MD

    def addNode(node: Node, parentElement):
        e = ET.SubElement(parentElement, node.__class__.__name__)

        ET.SubElement(e, "name").text = node.name
        if node.parent is not None:
            ET.SubElement(e, "parent").text = node.parent.name

        property_names = [p for p in dir(node.__class__) if isinstance(getattr(node.__class__, p), property)]
        if len(property_names) > 0:
            e_properties = ET.SubElement(e, "properties")

            for name in property_names:
                try:
                    s = getattr(node, name)
                except:
                    pass
                value = s

                if s.__class__.__name__ == 'CommentedMap':
                    t = {}
                    for k in value.keys():
                        t[k] = value[k]
                    value = t

                # reformat
                if issubclass(value.__class__, list):
                    t = np.array(value)
                    d = len(t.shape)
                    if d > 1:
                        s = "[\n"
                        for r in t:
                            s += str(r.tolist()) + "\n"
                        s += "]"
                        value = s


                if not issubclass(value.__class__, str):
                    value = str(value)

                ET.SubElement(e_properties, name).text=value

        arguments = node._init_arguments
        if len(arguments.values()) > 0:
            e_arguments = ET.SubElement(e, "arguments")
            for k in arguments:
                value = arguments[k]
                if value.__class__.__name__ == 'CommentedMap':
                    t = {}
                    for k in value.keys():
                        t[k] = value[k]
                    value = t

                value = str(value)

                ET.SubElement(e_arguments, k).text = value

        for c in node.children.values():
            addNode(c, parentElement)

    root = ET.Element("configuration")
    addNode(node, root)



    tree = ET.ElementTree(root)

    print("{}".format(MD.parseString(ET.tostring(tree.getroot(),'utf-8')).toprettyxml()))
    exit(0)