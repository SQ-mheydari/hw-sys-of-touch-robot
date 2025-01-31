from tntserver.Nodes.TnT.Duts import *
from tntserver.Nodes.TnT.Dut import *
from tntserver.Nodes.TnT.Tips import *
from tntserver.Nodes.TnT.PhysicalButtons import *
from tntserver.Nodes.TnT.Images import *
from tests.test_camera import *
import numpy as np
import uuid


# -------------------------------------
# test Images (only add image, no way to remove image)
# -------------------------------------
def test_images_add():
    """
    Test adding image: Images.post_self()
    :return: none
    """
    def get_image():
        return np.ones((200, 500, 3), dtype=np.uint16) * 255

    images = Images("images")
    images.image_folder_path = os.path.join(os.getcwd(), 'tests', 'images')
    object_children = len(list(images.object_children.values()))
    children = len(list(images.children.values()))

    # Create image with unique name to avoid clashes with existing images.
    # Also need to give a name because Images() init will load any images under data/images
    # and if there are more than max_images then creating new image without explicit name will fail.
    img_name = images.add(name=str(uuid.uuid1()))
    images.find_from(images, img_name).set_data(get_image())

    new_object_children = len(list(images.object_children.values()))
    new_children = len(list(images.children.values()))
    assert new_object_children - object_children == 1
    assert new_children - children == 1
    assert img_name is not None

    os.remove(os.path.join(images.image_folder_path, img_name + ".png"))


# -------------------------------------
# test Duts
# -------------------------------------
def init_duts():
    """
    Create Duts object and initialize it
    :return: name, Duts object
    """
    name = 'duts1'
    duts = Duts(name)

    # have to set this, otherwise Dut init fail
    param = dict()
    param['gestures_cls'] = 'TnT.Gestures'
    duts.init(**param)
    return name, duts


def add_dut(name, duts):
    """
    Add a dut into a Duts object, also test the method: Duts.put_add().
    This function is also used by testing of removing a dut.
    :param name: name of the Duts object
    :param duts: Duts object
    :return: Info of the newly generated DUT
    """
    assert len(list(duts.object_children.values())) == 0
    assert len(list(duts.children.values())) == 0
    info = duts.put_add()
    object_children = list(duts.object_children.values())
    children = list(duts.children.values())
    assert info is not None
    assert from_jsonout(info)['parent'] == name
    assert len(object_children) == 1
    assert len(children) == 1
    assert type(object_children[0]) == Dut
    assert type(children[0]) == Dut
    return info


def test_duts_add_remove():
    """
    Test adding and removing a dut: Duts.put_add() and Duts.put_remove()
    :return: none
    """
    def save():
        nonlocal was_saved
        was_saved = True

    # remove dut when there is only 1 dut
    was_saved = False
    name, duts1 = init_duts()
    duts1.save = save
    info = add_dut(name, duts1)
    assert was_saved

    was_saved = False
    new_dut_name = from_jsonout(info)['name']
    duts1.put_remove(new_dut_name)
    assert was_saved
    object_children = list(duts1.object_children.values())
    children = list(duts1.children.values())
    # dut is not removed from object_children, TOUCH5705-580 is created
    # assert len(object_children) == 0
    assert len(children) == 0
    assert duts1.find(new_dut_name) is None

    # remove dut when there are more than 1 dut
    name, duts1 = init_duts()
    was_saved = False
    duts1.save = save
    info = add_dut(name, duts1)
    assert was_saved
    was_saved = False
    duts1.put_add()
    assert was_saved
    object_children = list(duts1.object_children.values())
    children = list(duts1.children.values())
    assert len(object_children) == 2
    assert len(children) == 2

    new_dut_name = from_jsonout(info)['name']
    duts1.put_remove(new_dut_name)
    object_children = list(duts1.object_children.values())
    children = list(duts1.children.values())
    # assert len(object_children) == 1
    assert len(children) == 1
    assert duts1.find(new_dut_name) is None


# -------------------------------------
# common for Tips, PhysicalButtons
# -------------------------------------
def init_nodes(cls):
    """
    Create and initialize a ListingNode object
    :param cls: type of ListingNode
    :return: ListingNode object
    """
    name = 'test1'
    nodes = cls(name)
    return nodes


def add_node(nodes, name_node, params):
    """
    Add a node into a ListingNode object, also test the method: ListingNode.post_self().
    This function is also used by testing of removing a node.
    :param nodes: ListingNode object
    :param name_node: the name of node to be added
    :param params: parameters of the node
    :return: none
    """
    assert len(list(nodes.object_children.values())) == 0
    assert len(list(nodes.children.values())) == 0
    if hasattr(nodes, 'resources'):
        nodes.post_self(name=name_node, type=list(nodes.resources.keys())[0], **params)
        object_children = list(nodes.object_children.values())
        children = list(nodes.children.values())
        assert len(object_children) == 1
        assert len(children) == 1
        assert object_children[0].name == name_node
        assert children[0].name == name_node


def add_remove(cls, params=None):
    """
    Test adding and removing a node: ListingNode.pose_self(), DeletableNode.delete_self()
    :param cls: type of ListingNode
    :param params: parameters of the node to be added and removed
    :return: none
    """
    def save():
        nonlocal was_saved
        was_saved = True

    # remove a node when there is one node
    was_saved = False
    if params is None:
        params = dict()
    name_node = 'node_test'
    nodes = init_nodes(cls)
    nodes.save = save
    add_node(nodes, name_node, params)
    assert was_saved

    # delete a node
    was_saved = False
    status = nodes.object_children[name_node].delete_self()
    assert was_saved
    assert from_jsonout(status)['status'] == 'ok'
    assert len(list(nodes.object_children.values())) == 0
    assert len(list(nodes.children.values())) == 0
    assert nodes.find(name_node) is None

    # remove a node when there are more than one node
    nodes = init_nodes(cls)
    was_saved = False
    nodes.save = save

    # add 1st
    add_node(nodes, name_node, params)
    assert was_saved

    # add 2nd
    was_saved = False
    nodes.post_self(name='node_test2', type=list(nodes.resources.keys())[0], **params)
    assert was_saved
    object_children = list(nodes.object_children.values())
    children = list(nodes.children.values())
    assert len(object_children) == 2
    assert len(children) == 2

    # delete a node
    was_saved = False
    status = nodes.object_children[name_node].delete_self()
    assert was_saved
    assert from_jsonout(status)['status'] == 'ok'
    assert len(list(nodes.object_children.values())) == 1
    assert len(list(nodes.children.values())) == 1
    assert nodes.find(name_node) is None


# -------------------------------------
# test Tips
# -------------------------------------
def test_tips_add_remove():
    """
    Test adding and removing a tip
    :return: none
    """
    params = dict()
    params['length'] = 5
    params['model'] = 'Standard'
    params['diameter'] = 1
    add_remove(Tips, params)


# -------------------------------------
# test PhysicalButtons
# -------------------------------------
def test_physical_buttons_add_remove():
    """
    Test adding and removing a physical button
    :return: none
    """
    add_remove(PhysicalButtons)