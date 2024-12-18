from tntserver.Nodes.Node import Node, json_out, text_out, get_node_class
from tntserver.client_generator.parser import generate_api_node
from tntserver.client_generator.python_writer import PythonWriter, api_node_to_python
from tntserver.client_generator.pdf_doc_writer import write_pdf_doc
import shutil
import os


def generate_client(config):
    merge = config["merge"]
    clients = config["clients"]
    language = config["language"]
    output_path = config["output_path"]

    api_nodes = {}

    # Create API for each node.
    for client_name, client_def in clients.items():
        class_name = client_def["cls"]
        node_path = client_def["node_path"]
        resource_type = client_def["resource_type"]
        mapping = client_def.get("map", None)
        name = client_def.get("name", None)
        include = client_def.get("include", None)
        exclude = client_def.get("exclude", None)

        api_node = generate_api_node(get_node_class(class_name), node_path, client_name, resource_type,
                                     mapping, name, include, exclude)

        api_nodes[client_name] = api_node

    # Merge APIs if specified.
    for key, value in merge.items():
        source = api_nodes[value]
        target = api_nodes[key]

        target.methods += source.methods
        target.properties += source.properties

    # Remove API that was merged to another.
    for value in merge.values():
        del api_nodes[value]

    # Manage writer for each client module. Each module may have several client classes.
    writers = {}

    # Transform APIs to code of target programming language.
    for client_name, client_def in clients.items():
        if client_name not in api_nodes:
            continue

        filename = client_def["filename"]

        if filename not in writers:
            if language == "Python":
                writers[filename] = PythonWriter(output_path, filename)
            else:
                raise Exception("Unknown client generator language {}.".format(language))

        api_node = api_nodes[client_name]
        api_node_to_python(api_node, writers[filename])

        api_node.module_name = filename

    for writer in writers.values():
        writer.to_file()

    # Copy the static client files.
    shutil.copy(os.path.join("client", "python", "__init__.py"), output_path)
    shutil.copy(os.path.join("client", "python", "logger.py"), output_path)
    shutil.copy(os.path.join("client", "python", "tnt_client.py"), output_path)

    # Copy example ecripts.
    if os.path.exists(os.path.join(output_path, "examples")):
        shutil.rmtree(os.path.join(output_path, "examples"))

    shutil.copytree(os.path.join("client", "python", "examples"), os.path.join(output_path, "examples"))

    # Write API documentation PDF file.
    if not os.path.exists(os.path.join(output_path, "doc")):
        os.mkdir(os.path.join(output_path, "doc"))

    write_pdf_doc(api_nodes.values(), os.path.join(output_path, "doc", "tnt_client_api.pdf"))
