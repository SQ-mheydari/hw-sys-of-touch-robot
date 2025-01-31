"""
Implements writing TnT Client to Python package.
"""
import os


class PythonWriter:
    """
    Helper class to write Python code with given indentations.
    """
    PREAMBLE = """
from .tnt_client import *
from . import logger

log = logger.get_logger(__name__)

            """
    def __init__(self, directory=None, filename=None):
        self.indent_width = 4
        self.line_ending = "\n"
        self.text = ""
        self.level = 0
        self.path = os.path.join(directory, filename + ".py") if directory is not None and filename is not None else None

    def write_line(self, line, new_line=True):
        """
        Write a line of Python code.
        Uses current indentation state.
        :param line: Line as string.
        :param new_line: Add new line character?
        """
        self.text += " " * self.indent_width * self.level + line

        if new_line:
            self.text += self.line_ending

    def write(self, text):
        """
        Write text with no extra processing (appended to the end of previous line).
        :param text: Text to write.
        """
        self.text += text

    def write_doc(self, doc):
        """
        Write Python docstring.
        :param doc: Docstring as string.
        """
        self.write_line('"""')
        self.write_line(doc)
        self.write_line('"""')

    def to_file(self):
        """
        Dump Python code to file.
        """

        # Create directory if it doesn't exist.
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

        with open(self.path, "w") as file:
            text = PythonWriter.PREAMBLE + self.line_ending + self.text

            # Change encoding to simple ascii to avoid problems with encodings.
            file.write(bytes(text, 'utf-8').decode('ascii', 'ignore'))


def api_node_to_python(api_node, writer):
    """
    Write node API as Python code.
    :param api_node: ApiNode object.
    :param writer: PythonWriter object. This object can already have some content in it.
    """
    writer.write_line("class {}(TnTClientObject):".format(api_node.client_name))
    writer.level += 1

    if api_node.doc is not None:
        writer.write_doc(api_node.doc)

    if api_node.object_name is None:
        writer.write_line('def __init__(self, name, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):')
    else:
        writer.write_line(
            'def __init__(self, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):')

    writer.level += 1

    if api_node.object_name is None:
        if api_node.resource_type is None:
            writer.write_line(
                'TnTClientObject.__init__(self, host, port, workspace, None, name)')
        else:
            writer.write_line(
                'TnTClientObject.__init__(self, host, port, workspace, "{}", name)'.format(api_node.resource_type))

    else:
        if api_node.resource_type is None:
            writer.write_line('TnTClientObject.__init__(self, host, port, workspace, None, "{}")'.format(api_node.object_name))
        else:
            writer.write_line(
                'TnTClientObject.__init__(self, host, port, workspace, "{}", "{}")'.format(api_node.resource_type,
                                                                                           api_node.object_name))

    writer.write_line('')
    writer.level -= 1

    if api_node.deletable:
        writer.write_line("def remove(self):")
        writer.level += 1

        writer.write_line('"""')
        writer.write_line('Remove the resource.')
        writer.write_line('After the resource has been removed, the client object is no longer valid.')
        writer.write_line('"""')

        writer.write_line("return self._DELETE('', {})")
        writer.level -= 1

        writer.write_line("")

    # Methods
    for api_method in api_node.methods:
        writer.write_line("def " + api_method.client_name + "(self, ", False)

        for p in api_method.parameters:
            # TODO: Parameter type.
            writer.write(p.name)

            if p.has_default:
                if isinstance(p.default, str):
                    writer.write("='{}'".format(str(p.default)))
                else:
                    writer.write("={}".format(str(p.default)))

            if p != api_method.parameters[-1]:
                writer.write(", ")

        writer.write("):")
        writer.write_line("")

        writer.level += 1

        if api_method.doc is not None:
            writer.write_doc(api_method.doc)

        # Create params dict.
        # Mandatory parameters.
        # If the request has content, it has no parameters.
        if not api_method.content:
            writer.write_line("params = {")
            writer.level += 1

            for p in api_method.parameters:
                if not p.has_default or p.default is not None:
                    writer.write_line("'{}': {},".format(p.name, p.name))

            writer.level -= 1
            writer.write_line("}")
            writer.write_line("")

        # Optional parameters.
        for p in api_method.parameters:
            if p.has_default and p.default is None:
                writer.write_line("if {} is not None:".format(p.name))
                writer.level += 1
                writer.write_line("params['{}'] = {}".format(p.name, p.name))
                writer.level -= 1

        writer.write_line("")

        request_type = api_method.request_type

        # Create API command.
        if api_method.node_path is None:
            if api_method.content:
                writer.write_line("return self._PUT('{}', parameters=None, content_type='{}', content=value)".format(api_method.name, api_method.content_type))
            else:
                writer.write_line("return self._{}('{}', params)".format(request_type.upper(), api_method.name))
        else:
                writer.write_line(
                    "return self._{}('{}/{}', params)".format(request_type.upper(), api_method.node_path, api_method.name))
        writer.write_line("")

        writer.level -= 1

    # Properties
    for api_property in api_node.properties:
        writer.write_line("@property")
        writer.write_line("def " + api_property.name + "(self):")

        writer.level += 1

        if api_property.doc is not None:
            writer.write_doc(api_property.doc)

        writer.write_line("return self.get_property('{}')".format(api_property.name))
        writer.write_line("")

        writer.level -= 1

        if api_property.settable:
            writer.write_line("@{}.setter".format(api_property.name))
            writer.write_line("def " + api_property.name + "(self, value):")

            writer.level += 1

            if api_property.doc is not None:
                writer.write_doc(api_property.doc)

            writer.write_line("self.set_property('{}', value)".format(api_property.name))
            writer.write_line("")

            writer.level -= 1

    writer.level -= 1
