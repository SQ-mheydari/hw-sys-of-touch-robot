from tntserver.Nodes.Node import *
import pytest


def decode_json_out(data):
    return json.loads(data[1].decode('utf-8'))

class Object1(Object):
    def __init__(self):
        super().__init__()


class Object2(Object):
    def __init__(self):
        super().__init__()

class Node1(Node):
    def __init__(self, name):
        super().__init__(name)
        self.initialized = False
        self._property1 = "property 1"
        self._property2 = "property 2"

    def _init(self, arg1, arg2, **kwargs):
        assert arg1 == "Hello"
        assert arg2 == "World"
        self.initialized = True

    @property
    def property1(self):
        return self._property1

    @property1.setter
    def property1(self, value):
        self._property1 = value

    @property
    def property2(self):
        return  self._property2

    @property2.setter
    def property2(self, value):
        self._property2 = value


class Node2(Node):
    def __init__(self, name):
        super().__init__(name)


def test_node_init():
    node1 = Node1("my node 1")

    assert node1.name == "my node 1"
    assert node1.parent is None
    assert len(node1.children) == 0

    node2 = Node1("my node 2")
    node1.add_child(node2)

    node3 = Node1("my node 3")
    node2.add_child(node3)

    assert not node1.initialized
    assert not node2.initialized
    assert not node3.initialized

    # Init the root node. This should init all children.
    node1.init(arg1="Hello", arg2="World")

    assert node1.initialized
    assert node2.initialized
    assert node3.initialized



def test_object_tree():
    """
    Test object insertion and removal on object tree

       root
       /  \
     o1    o2  -  o4
            \
            o3
    """
    root = Object()
    root.name = "root"

    assert root.object_parent is None
    assert len(root.object_children) == 0

    o1 = Object()
    o1.name = "o1"
    root.add_object_child(o1)

    o2 = Object()
    o2.name = "o2"
    root.add_object_child(o2)

    o3 = Object()
    o3.name = "o3"
    o2.add_object_child(o3)

    o4 = Object()
    o4.name = "o4"
    o2.add_object_child(o4)

    assert root.object_parent is None
    assert root.object_children["o1"] == o1
    assert root.object_children["o2"] == o2
    assert len(root.object_children) == 2
    assert o1.object_parent == root
    assert o2.object_parent == root
    assert len(o1.object_children) == 0
    assert o2.object_children["o3"] == o3
    assert o2.object_children["o4"] == o4
    assert o3.object_parent == o2
    assert o4.object_parent == o2
    assert len(o3.object_children) == 0
    assert len(o4.object_children) == 0

    root.remove_object_from_parent()

    o2.remove_object_from_parent()

    assert o2.object_parent is None
    assert "o2" not in root.object_children
    assert root.object_children["o1"] == o1
    assert len(root.object_children) == 1


def test_find_object_parent_by_class_name():
    """
    Test finding object by class name in tree:

       root
       /  \
     o1    o2  -  o4  - o5
            \
            o3
    """
    root = Object()
    root.name = "root"

    assert root.object_parent is None
    assert len(root.object_children) == 0

    o1 = Object()
    o1.name = "o1"
    root.add_object_child(o1)

    o2 = Object1()
    o2.name = "o2"
    root.add_object_child(o2)

    o3 = Object()
    o3.name = "o3"
    o2.add_object_child(o3)

    o4 = Object2()
    o4.name = "o4"
    o2.add_object_child(o4)

    o5 = Object()
    o5.name = "o5"
    o4.add_object_child(o5)

    assert o5.find_object_parent_by_class_name("Object1") == o2
    assert o5.find_object_parent_by_class_name("Object2") == o4
    assert o4.find_object_parent_by_class_name("Object1") == o2


def test_node_tree():
    """
    Test node insertion and removal on object / node tree

       root
       /  \
     o1    o2  -  o4
            \
            o3
    """
    root = Node("root")

    assert root.object_parent is None
    assert len(root.object_children) == 0

    o1 = Node("o1")
    root.add_child(o1)

    o2 = Node("o2")
    root.add_child(o2)

    o3 = Node("o3")
    o2.add_child(o3)

    o4 = Node("o4")
    o2.add_child(o4)

    # Test node relations.
    assert root.parent is None
    assert root.children["o1"] == o1
    assert root.children["o2"] == o2
    assert len(root.children) == 2
    assert o1.parent == root
    assert o2.parent == root
    assert len(o1.children) == 0
    assert o2.children["o3"] == o3
    assert o2.children["o4"] == o4
    assert o3.parent == o2
    assert o4.parent == o2
    assert len(o3.children) == 0
    assert len(o4.children) == 0

    # Test object relations which should reflect node relations.
    assert root.object_parent is None
    assert root.object_children["o1"] == o1
    assert root.object_children["o2"] == o2
    assert len(root.object_children) == 2
    assert o1.object_parent == root
    assert o2.object_parent == root
    assert len(o1.object_children) == 0
    assert o2.object_children["o3"] == o3
    assert o2.object_children["o4"] == o4
    assert o3.object_parent == o2
    assert o4.object_parent == o2
    assert len(o3.object_children) == 0
    assert len(o4.object_children) == 0

    root.remove_child(o2)

    # Test node relations.
    assert o2.parent is None
    assert "o2" not in root.children
    assert root.children["o1"] == o1
    assert len(root.children) == 1

    # Test object relations which should reflect node relations.
    assert o2.object_parent is None
    assert "o2" not in root.object_children
    assert root.object_children["o1"] == o1
    assert len(root.object_children) == 1


def test_node_find():
    """
    Test node find method on node tree

       root
       /  \
     o1    o2  -  o4
            \
            o3
    """
    root = Node("root")

    # Set global root node to enable find operations.
    Node.root = root

    assert root.object_parent is None
    assert len(root.object_children) == 0

    o1 = Node1("o1")
    root.add_child(o1)

    o2 = Node("o2")
    root.add_child(o2)

    o3 = Node2("o3")
    o2.add_child(o3)

    o4 = Node2("o4")
    o2.add_child(o4)

    assert Node.find("root") == root
    assert Node.find("o1") == o1
    assert Node.find("o2") == o2
    assert Node.find("o3") == o3
    assert Node.find("o4") == o4

    assert Node.find_from(root, "root") == root
    assert Node.find_from(o1, "o1") == o1
    assert Node.find_from(o1, "root") is None
    assert Node.find_from(o2, "o2") == o2
    assert Node.find_from(o2, "root") is None
    assert Node.find_from(o2, "o3") == o3
    assert Node.find_from(o2, "o4") == o4
    assert Node.find_from(o2, "o1") is None

    assert Node.find_from(o3, "o3") == o3
    assert Node.find_from(o3, "o2") is None
    assert Node.find_from(o3, "o4") is None
    assert Node.find_from(o3, "root") is None
    assert Node.find_from(o3, "o1") is None

    assert Node.find_class("Node1")[0] == o1
    nodes = Node.find_class("Node2")
    assert o3 in nodes
    assert o4 in nodes
    assert len(nodes) == 2

    assert Node.find_class_from(root, "Node1")[0] == o1
    assert Node.find_class_from(o1, "Node1")[0] == o1
    nodes = Node.find_class_from(root, "Node2")
    assert o3 in nodes
    assert o4 in nodes
    assert len(nodes) == 2

    nodes = Node.find_class_from(o2, "Node2")
    assert o3 in nodes
    assert o4 in nodes
    assert len(nodes) == 2

    assert len(Node.find_class_from(o1, "Node2")) == 0
    assert len(Node.find_class_from(o2, "Node1")) == 0
    assert len(Node.find_class_from(o3, "Node1")) == 0
    assert len(Node.find_class_from(o4, "Node1")) == 0

    assert root.find_child_with_path("o1") == o1
    assert root.find_child_with_path("o2") == o2

    with pytest.raises(NodeException):
        root.find_child_with_path("o3")

    with pytest.raises(NodeException):
        root.find_child_with_path("o4")


class NodeWithoutFrame(Node):
    def __init__(self):
        super().__init__()

    @property
    @private
    def frame(self):
        return "private frame"

def test_node_without_frame():
    node = Node()

    assert np.allclose(node.frame, robotmath.identity_frame())

    node = NodeWithoutFrame()

    assert node.frame == "private frame"

def test_node_frame():
    node = Node()

    was_saved = False

    def save():
        nonlocal  was_saved
        was_saved = True

    # Patch save which is called by put_frame().
    node.save = save

    assert np.allclose(node.frame, robotmath.identity_frame())

    frame = robotmath.xyz_to_frame(10, 20, 30)

    node.frame = frame

    assert np.allclose(node.frame, frame)

    frame2 = robotmath.xyz_to_frame(40, 50, 60)

    node.put_frame(frame2.tolist())
    assert was_saved

    assert np.allclose(node.frame, frame2)
    assert np.allclose(decode_json_out(node.get_local_frame()), frame2)

def test_node_get_frame():
    root = Node("root")

    o1 = Node("o1")
    root.add_child(o1)

    o2 = Node("o2")
    root.add_child(o2)

    o3 = Node("o3")
    o2.add_child(o3)

    o4 = Node("o4")
    o2.add_child(o4)

    o1.frame = robotmath.xyz_to_frame(10, 20, 30)
    o2.frame = robotmath.xyz_to_frame(40, 0, 0)
    o3.frame = robotmath.xyz_to_frame(0, 0, 30)

    np.allclose(decode_json_out(o1.get_frame(context="root")), robotmath.xyz_to_frame(10, 20, 30))
    np.allclose(decode_json_out(o2.get_frame(context="root")), robotmath.xyz_to_frame(40, 0, 0))
    np.allclose(decode_json_out(o3.get_frame(context="root")), robotmath.xyz_to_frame(40, 0, 30))
    np.allclose(decode_json_out(o3.get_frame(context="o2")), robotmath.xyz_to_frame(0, 0, 30))
    np.allclose(decode_json_out(o4.get_frame(context="o2")), robotmath.xyz_to_frame(0, 0, 0))
    np.allclose(decode_json_out(o4.get_frame(context="root")), robotmath.xyz_to_frame(40, 0, 0))

class Listener(Node):
    def __init__(self, name):
        super().__init__(name)
        self.prev_message = None

    def message(self, message:str):
        self.prev_message = message


def test_node_channels():
    """
    Test node channels on node tree

       root
       /  \
     o1    o2  -  o4
            \
            o3
    """
    root = Node("root")

    # Set global root node to enable find operations.
    Node.root = root

    assert root.object_parent is None
    assert len(root.object_children) == 0

    o1 = Listener("o1")
    root.add_child(o1)
    o1.listen_channel("channel 1")

    o2 = Node("o2")
    root.add_child(o2)

    o3 = Listener("o3")
    o2.add_child(o3)
    o3.listen_channel("channel 1")

    o4 = Listener("o4")
    o2.add_child(o4)
    o4.listen_channel("channel 2")

    assert o1.prev_message is None
    assert o3.prev_message is None
    assert o4.prev_message is None

    root.send_message("channel 1", "Hello channel 1")
    assert o1.prev_message == "Hello channel 1"
    assert o3.prev_message == "Hello channel 1"
    assert o4.prev_message is None

    root.send_message("channel 2", "Hello channel 2")
    assert o1.prev_message == "Hello channel 1"
    assert o3.prev_message == "Hello channel 1"
    assert o4.prev_message == "Hello channel 2"

    root.send_message("channel 3", "Hello channel 3")
    assert o1.prev_message == "Hello channel 1"
    assert o3.prev_message == "Hello channel 1"
    assert o4.prev_message == "Hello channel 2"

    # Test duplicate listen. Current implementation allows duplicate entries. Change test if this is changed in future.
    #o4.listen_channel("channel 2")
    #assert Node._msg_channels["channel 2"].count(o4) == 1


class NodeWithPrivateProperties(Node):
    def __init__(self, name):
        super().__init__(name)

    @property
    def not_private_property1(self):
        return "not private 1"

    @property
    def not_private_property2(self):
        return "not private 2"

    @property
    @private
    def private_property1(self):
        return "private 1"

    @property
    @private
    def private_property2(self):
        return "private 2"

class NodeWithInheritedPrivateProperties(NodeWithPrivateProperties):
    def __init__(self, name):
        super().__init__(name)

    @property
    def subclass_not_private_property1(self):
        return "not private subclass"

    @property
    @private
    def subclass_private_property(self):
        return "private subclass"

def test_node_private_property():
    node = NodeWithPrivateProperties("node")

    assert not node.private_property("not_private_property1")
    assert not node.private_property("not_private_property2")
    assert node.private_property("private_property1")
    assert node.private_property("private_property2")

    node = NodeWithInheritedPrivateProperties("node")
    assert not node.private_property("not_private_property1")
    assert not node.private_property("not_private_property2")
    assert not node.private_property("subclass_not_private_property1")
    assert node.private_property("private_property1")
    assert node.private_property("private_property2")
    assert node.private_property("subclass_private_property")


class NodeWithSkipNones(Node):
    def __init__(self, name):
        super().__init__(name)

    @property
    @skip_nones
    def skip_none_property(self):
        return "skip none"

    @property
    def normal_property(self):
        return "normal property"

def test_node_skip_nones_property():
    node = NodeWithSkipNones("node")

    assert not node.hidden_none("normal_property")
    assert node.hidden_none("skip_none_property")


class NodeWithFormatDecorators(Node):
    def __init__(self, name):
        super().__init__(name)

    @html_out
    def some_html_out(self):
        return "Some HTML"

    @ascii_out
    def some_ascii_out(self):
        return "Some ASCII"

    @jpeg_out
    def some_jpeg_out(self):
        return b"Some JPEG"

    @png_out
    def some_png_out(self):
        return b"Some PNG"

    @wav_out
    def some_wav_out(self):
        return b"Some WAV"


def test_format_decorators():
    node = NodeWithFormatDecorators("node")

    result = node.some_html_out()
    assert isinstance(result[1], bytes)
    assert result[0] == "text/html"
    assert result[1] == b"Some HTML"
    assert len(result) == 2

    result = node.some_ascii_out()
    assert isinstance(result[1], bytes)
    assert result[0] == "text/ascii"
    assert result[1] == b"Some ASCII"
    assert len(result) == 2

    result = node.some_jpeg_out()
    assert isinstance(result[1], bytes)
    assert result[0] == "image/jpeg"
    assert result[1] == b"Some JPEG"
    assert len(result) == 2

    result = node.some_png_out()
    assert isinstance(result[1], bytes)
    assert result[0] == "image/png"
    assert result[1] == b"Some PNG"
    assert len(result) == 2

    result = node.some_wav_out()
    assert isinstance(result[1], bytes)
    assert result[0] == "audio/x-wav"
    assert result[1] == b"Some WAV"
    assert len(result) == 2


def test_node_api_info():
    """
    Test node api info.
    """
    root = Node("root")

    # Set global root node to enable find operations.
    Node.root = root

    o1 = Node1("o1")
    root.add_child(o1)

    info = o1.api_info()

    assert info[0] == 'application/json'

    data = decode_json_out(info)
    assert data["parent"] == "root"
    assert data["connection"] == "root"
    assert data["name"] == "o1"

    functions = data["functions"]

    def has_function(functions, method, name):
        for f in functions:
            if f[0] == method and f[1] == name:
                return True

        return False

    assert has_function(functions, "get", "frame")
    assert has_function(functions, "get", "local_frame")
    assert has_function(functions, "get", "properties")
    assert has_function(functions, "get", "relations")
    assert has_function(functions, "put", "frame")
    assert has_function(functions, "put", "properties")

    def has_link(links, method, href):
        for link in links:
            if link["method"] == method and link["href"] == href:
                return True

        return False

    assert has_link(data["_links"], "GET", "http://127.0.0.1:8000/root/o1/frame")
    assert has_link(data["_links"], "GET", "http://127.0.0.1:8000/root/o1/local_frame")
    assert has_link(data["_links"], "GET", "http://127.0.0.1:8000/root/o1/properties")
    assert has_link(data["_links"], "GET", "http://127.0.0.1:8000/root/o1/relations")
    assert has_link(data["_links"], "PUT", "http://127.0.0.1:8000/root/o1/frame")
    assert has_link(data["_links"], "PUT", "http://127.0.0.1:8000/root/o1/properties")


def test_node_tnt2_info():
    """
    Test node tnt2 info.
    """
    root = Node("root")

    # Set global root node to enable find operations.
    Node.root = root

    o1 = Node1("o1")
    root.add_child(o1)

    info = o1.tnt2_info()

    assert info[0] == 'application/json'

    data = decode_json_out(info)

    assert len(data["o1"]) == 0

    def has_link(links, method, href):
        for link in links:
            if link["method"] == method and link["href"] == href:
                return True

        return False

    assert has_link(data["_links"], "GET", "http://127.0.0.1:8000/root/o1/frame")
    assert has_link(data["_links"], "GET", "http://127.0.0.1:8000/root/o1/local_frame")
    assert has_link(data["_links"], "GET", "http://127.0.0.1:8000/root/o1/properties")
    assert has_link(data["_links"], "GET", "http://127.0.0.1:8000/root/o1/relations")
    assert has_link(data["_links"], "PUT", "http://127.0.0.1:8000/root/o1/frame")
    assert has_link(data["_links"], "PUT", "http://127.0.0.1:8000/root/o1/properties")


def test_node_get_relations():
    """
    Test node get_relations.
    """
    root = Node("root")

    # Set global root node to enable find operations.
    Node.root = root

    o1 = Node1("o1")
    root.add_child(o1)

    info = o1.tnt2_info()

    assert info[0] == 'application/json'

    data = decode_json_out(info)

    data["connection"] = "root"
    data["name"] = "o1"
    data["parent"] = "root"


def test_node_help():
    """
    Test node help().
    """
    root = Node("root")

    # Set global root node to enable find operations.
    Node.root = root

    o1 = Node1("o1")
    root.add_child(o1)

    help = o1.help()

    assert help["classname"] == "Node1"
    assert help["name"] == "o1"
    assert help["object"] == o1
    assert help["properties"]["property1"]["type"] == "str"
    assert help["properties"]["property1"]["value"] == "property 1"
    assert help["properties"]["property2"]["type"] == "str"
    assert help["properties"]["property2"]["value"] == "property 2"

    def has_function(data, method, name):
        for d in data:
            if d[0] == method and d[1] == name:
                return True

        return False

    functions = help["functions"]
    assert has_function(functions, "get", "frame")
    assert has_function(functions, "get", "local_frame")
    assert has_function(functions, "get", "properties")
    assert has_function(functions, "get", "relations")
    assert has_function(functions, "put", "frame")
    assert has_function(functions, "put", "properties")


def test_node_json():
    """
    Test node json().
    """
    root = Node("root")

    # Set global root node to enable find operations.
    Node.root = root

    o1 = Node1("o1")
    root.add_child(o1)

    data = o1.json()

    assert data["name"] == "o1"
    assert data["parent"] == "root"
    assert np.allclose(data["frame"], robotmath.identity_frame())


def test_node_fullname():
    """
    Test node fullname().
    """
    root = Node("root")

    # Set global root node to enable find operations.
    Node.root = root

    o1 = Node1("o1")
    root.add_child(o1)

    o2 = Node2("o2")
    o1.add_child(o2)

    assert o2.fullname() == "root.o1.o2"

def test_node_properties():
    """
    Test node properties.
    """
    root = Node("root")

    # Set global root node to enable find operations.
    Node.root = root

    o1 = Node1("o1")
    root.add_child(o1)

    was_saved = False

    def save():
        nonlocal was_saved
        was_saved = True

    # Patch save which is called by put_properties().
    o1.save = save

    p = o1.get_properties()

    assert p[0] == 'application/json'

    data = decode_json_out(p)

    assert data["property1"]["type"] == "str"
    assert data["property1"]["value"] == "property 1"
    assert data["property2"]["type"] == "str"
    assert data["property2"]["value"] == "property 2"
    assert len(data) == 2

    data = decode_json_out(o1.get_property("property1"))
    assert data["type"] == "str"
    assert data["value"] == "property 1"

    o1.put_properties(property1="new property 1")
    assert was_saved
    data = decode_json_out(o1.get_properties())
    assert data["property1"]["value"] == "new property 1"
    assert data["property2"]["value"] == "property 2"

    o1.put_properties(property2="new property 2")
    data = decode_json_out(o1.get_properties())
    assert data["property1"]["value"] == "new property 1"
    assert data["property2"]["value"] == "new property 2"


def test_find_node_by_path():
    root = Node("root")

    o1 = Node("o1")
    root.add_child(o1)

    o11 = Node("o11")
    o1.add_child(o11)

    o12 = Node("o12")
    o1.add_child(o12)

    o2 = Node("o2")
    root.add_child(o2)

    o21 = Node("o21")
    o2.add_child(o21)

    o22 = Node("o22")
    o2.add_child(o22)

    assert Node.find_node_by_path(root, "root").name == "root"

    assert Node.find_node_by_path(root, "root.o1").name == "o1"
    assert Node.find_node_by_path(root, "root.o1.o11").name == "o11"
    assert Node.find_node_by_path(root, "root.o1.o12").name == "o12"

    assert Node.find_node_by_path(root, "root.o2").name == "o2"
    assert Node.find_node_by_path(root, "root.o2.o21").name == "o21"
    assert Node.find_node_by_path(root, "root.o2.o22").name == "o22"