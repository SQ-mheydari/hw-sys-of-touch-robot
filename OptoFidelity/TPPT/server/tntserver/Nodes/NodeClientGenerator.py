'''
Test with call

PUT http://127.0.0.1:8000/tnt/clientgen/generate_method

body:

{
 "module_name":"TnT.Gestures",
 "class_name":"Gestures",
 "method_name":"put_jump",
 "node_path":"gestures"
}

output:

def jump(self, x, y, z, jump_height, )
"""

        Performs a jump with given parameters.
        In case jump_height is not given, robot jumps to maximum height along robot z axis.

        :param x: Target x coordinate on DUT.
        :param y: Target y coordinate on DUT.
        :param z: Target z coordinate on DUT.
        :param jump_height: Height of the jump from DUT surface (default: jump to robot maximum height).

"""
params = {
'x': x
'y': y
'z': z
'jump_height': jump_height
}

self._PUT('gestures/jump', params)
'''

from tntserver.Nodes.Node import Node, json_out, text_out, get_node_class
from tntserver.client_generator.parser import generate_api_node
from tntserver.client_generator.python_writer import PythonWriter, api_node_to_python
from tntserver.client_generator.generator import generate_client
import shutil
import os


class NodeClientGenerator(Node):
    """
    Generate client API from server node structure.
    """
    def __init__(self, name):
        super().__init__(name)

        self.clients = {}
        self.merge = {}

    def _init(self, **kwargs):
        pass

    @text_out
    def put_generate_node_api(self, class_name, client_name, resource_type, node_path=None):
        """
        Generate API for given node and return as text.
        :param class_name: Name of class (e.g. "TnT.Gestures").
        :param client_name: Name of class in the client side.
        :param resource_type: Resource type of client object (e.g. "dut").
        :param node_path: Additional node path.
        :return: Node Python API as text.
        """
        api_node = generate_api_node(get_node_class(class_name), node_path, client_name, resource_type, True, None, None,
                                     None, None)

        writer = PythonWriter()

        api_node_to_python(api_node, writer)

        return writer.text.encode("utf-8")

    @json_out
    def put_generate(self, output_path, language="Python"):
        """
        Generate TnT Client API to given output path.
        :param output_path: Path where client files are written to. Can be relative path from server run directory.
        :param language: Programming language. Currently "Python" is supported.
        """

        config = {
            "output_path": output_path,
            "language": language,
            "clients": self.clients,
            "merge": self.merge
        }

        generate_client(config)
