from tntserver.Nodes.Node import Node, json_out
from toolbox.dut import DutAPI, DutPositioning
from tntserver.Nodes.TnT.Dut import Dut
import socket
import threading
import queue
import time
import errno

import logging
log = logging.getLogger(__name__)


class DutServer(Node):
    """
    Dut communication server
    """
    static = None

    def __init__(self, name):
        super().__init__(name)
        DutServer.static = self
        self.dutapi = None

    def _init(self, **kwargs):
        """
        Classic server port has been 50007
        New protocol port should be classic+1, thus here 50008
        :param kwargs:
        :return:
        """
        host = kwargs.get("host", "127.0.0.1")
        port = int(kwargs.get("port", 50008))
        self.dutapi = DutAPI(host, port, auth_key="pitaistoimia_lol")

    def __del__(self):
        if self.dutapi is not None:
            self.dutapi.close()

    def _dut_name_to_client_name(self, dut_name: str):
        """
        Map TnT Dut Name to Dut communication client name
        for example "Dut1" -> "Client1"
        All the communication with physical DUT is done using Client Name
        :return: mapped client name
        """
        client_names = [name for name in self.dutapi.clients]
        for client_name in client_names:
            info = self.info(client_name = client_name)
            name = info.get("dut_name", None)
            if name is not None and name == dut_name:
                return client_name
        raise(Exception("communication client not found for dut name {}".format(dut_name)))

    def clients(self):
        """
        List connected clients.
        :return: List of communication client names.
        """
        client_names = [name for name in self.dutapi.clients]
        return client_names

    def is_dut_connected(self, dut_name: str):
        try:
            # will raise exception if not found
            client_name = self._dut_name_to_client_name(dut_name)
        except:
            return False
        return client_name in self.clients()

    def info(self, dut_name: str=None, client_name: str=None):
        """
        Read raw info dict from DUT using DUT Name or Client Name
        :param dut_name: name of the DUT. (optional)
        :param client_name: name of the connected dut client. (optional)
        :return:
        """
        client_name = self._dut_name_to_client_name(dut_name) if client_name is None else client_name
        info = self.dutapi.get_info(client_name)
        return info

    def touches(self, dut_name: str=None, client_name: str=None):
        """
        Read touches from the connected DUT using either Dut Name or Client Name
        :param dut_name: name of the DUT (optional)
        :param client_name: name of the connected Client (optional)
        :return: dictionary containing all the touches since las 'touches' call, for example:
                 {
                 "touch_fields", ["x", "y", "force"],
                 "touches", [[10, 10, 1], [100, 10, 1], [100, 100, 1]]
                 }
        """
        client_name = self._dut_name_to_client_name(dut_name) if client_name is None else client_name
        touches = self.dutapi.get_touches(client_name)
        return touches

    def show_image(self, dut, image):
        """
        Show image on DUT screen using
        :param image: image as numpy array, bytes, or filename
        :param dut: Dut Node
        :return: "ok" / error
        """
        dut_name = dut.name
        client_name = self._dut_name_to_client_name(dut_name)
        self.dutapi.show_image(client_name, image)
        return "ok"

    def show_positioning_image(self, dut):
        """
        Show positioning image on DUT screen
        :param dut: Dut Node
        :return: dictionary containing positions of drawn markers, display size in mm, display size in pixels
        """
        dut_name = dut.name
        r = dut._svgregion

        client_name = self._dut_name_to_client_name(dut_name)
        info = self.dutapi.get_info(client_name)

        pixel_size = info["display_resolution"]
        pixel_size = pixel_size["width"], pixel_size["height"]

        if r is not None:
            draw_region = r.region.get("analysis_region", None)
            mm_size = r.bounding_box[2], r.bounding_box[3]
            ppmm = pixel_size[0] / mm_size[0]
        else:
            # simulated defaults, ppmm=10 is a good approximation that should work with most displays
            draw_region = None
            ppmm = 10
            mm_size = pixel_size[0] / ppmm, pixel_size[1] / ppmm

        image, blob_positions = DutPositioning.positioning_image(r, draw_region, pixel_size, ppmm)

        self.dutapi.show_image(client_name, image)

        rv = {"blobs": blob_positions,
              "display_size_mm": mm_size,
              "display_size_px": pixel_size}
        return rv

    def create_duts(self):
        """
        Physical DUTs communicating through this server should have dut_name in their info.
        When you connect such DUT to this server, it might be that there isn't corresponding Dut Node
        At those situations, do call this function to create missing Dut Nodes
        Such situatuons are
        - in user interface you enter to Duts view

        in short: for each connected physical dut, create a Dut Node if needed.
        :return:

        """
        duts = Node.find_class("Duts")[0]
        dut_names = [name for name in duts.children]

        changes = False
        client_names = self.clients()
        for client_name in client_names:
            info = self.info(client_name=client_name)
            name = info.get("dut_name", None)
            if name not in dut_names:
                # create the missing dut
                new_dut = Dut(name=name)
                duts.add_child(new_dut)
                new_dut._init()
                changes = True

        if changes:
            duts.save()

    @json_out
    def get_create_duts(self):
        """
        Update list of DUTs with new connected DUT clients.
        Call this function always if you need list of DUTs and new DUT might have been connected
        :return: "ok" / error
        """
        self.create_duts()
        return "ok"

    @json_out
    def get_clients(self):
        """
        Read list of connected clients
        :return: list of Dut Communication Client Names, for example ["Client1", "Client2"]
        """
        return self.clients()

    @json_out
    def get_info(self, dut_name: str):
        """
        Get raw info dictionary from connected DUT
        :param dut_name: name of the DUT
        :return: dictionary containing DUT info, like screen pixel size, DUT model.
        """
        return self.info(dut_name)

    @json_out
    def get_touches(self, dut_name: str):
        """
        Read touches from connected DUT
        Reading will clear current list of touches from the device.
        :param dut_name: name of the DUT
        :return: dictionary containing touch fields and touches, for example:
                 {
                 "touch_fields", ["x", "y", "force"],
                 "touches", [[10, 10, 1], [100, 10, 1], [100, 100, 1]]
                 }

        """
        return self.touches(dut_name)

    @json_out
    def put_show_positioning_image(self, dut_name: str):
        """
        Show positioning image on connected DUT's display.
        :param dut_name: name of the DUT
        :return: dictionary containing positions of drawn markers, display size in mm, display size in pixels
        """
        rv = self.show_positioning_image(Node.find(dut_name))
        return rv


