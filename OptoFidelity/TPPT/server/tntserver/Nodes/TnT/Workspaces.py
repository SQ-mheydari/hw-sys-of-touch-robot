from tntserver.Nodes.Node import *


class Workspaces(Node):
    """
    is a container for NodeWorkspace resources
    """

    @json_out
    def get_self(self):
        workspaces = {}

        for workspace in self.children.values():
            workspaces[workspace.name] = {
                "name": workspace.name,
                "description": "",
                "title": ""
            }

        r = {
            "workspaces": workspaces
        }
        return r
