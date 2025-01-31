from tntserver.Nodes.TnT.Dut import Dut
from tntserver.Nodes.NodeSimulatorObject import NodeSimulatorObject
from tntserver.Nodes.Node import json_out
from threading import Thread
from toolbox.dut import DutCommunication, SvgRegion
import json
import cv2
import numpy as np
import time
import logging


log = logging.getLogger(__name__)


class DutSimulation(Dut):
    """
    Dut communication client
    & Dut visual simulator object
    """
    def __init__(self, name):
        super().__init__(name)
        self._xpos = 0
        self._svg = None
        self._terminate = False
        self._client = None
        self._client_thread = None
        self._simulator_object = None
        self._screen_size = None
        self.server_host = None
        self.server_port = None

    def _init(self, **kwargs):
        screen = kwargs.pop("screen")
        super()._init(**kwargs)

        screen_size = float(screen.get("width", 0)), float(screen.get("height", 0))
        ppmm = float(screen.get("ppmm", 1))

        # read and apply simulator object position
        position = [0, 0, 0, 0, 0, 0]
        pos = screen.get("position", None)
        if pos is not None:
            for i, v in enumerate(pos):
                position[i] = float(v)

        # create simulator object node for visualization
        obj = NodeSimulatorObject(self.name + "_object")
        obj_args = \
            {
            "type": "texture",
            "position": position,
            "ppmm": ppmm,
            "width": screen_size[0],
            "height": screen_size[1],
            "simulator_parent_object": "table",
            "draw": "color orange; rect 0 0 {} {} 0;".format(screen_size[0], screen_size[1])
            }
        obj._init_arguments = obj_args
        obj.transient = True

        # set the visualization object invisible for configuration yaml
        obj.transient = True

        # add the visualization node as a child
        self.add_child(obj)
        self._simulator_object = obj
        self._screen_size = screen_size

        # start dut communication client
        host = kwargs.get("host", "127.0.0.1")
        port = int(kwargs.get("port", 50008))
        self.server_host = host
        self.server_port = port

        self._start_communication_client()

    def __del__(self):
        if self._client is not None:
            self._client.socket.close()

        if self._client_thread is not None:
            self._client_thread.join()

    def _start_communication_client(self):
        t = Thread(target=self._communication_loop)
        self._client_thread = t
        t.start()

    def _communication_loop(self):
        def f(command, data):
            command, data = self._handle_command(command, data)
            return command, data

        client = DutCommunication(auth_key='pitaistoimia_lol')
        self._client = client
        client.start_client(self.server_host, self.server_port)
        while self._terminate == False:
            try:
                client.receive_and_respond(f)
                time.sleep(0.1)
            except Exception as e:
                log.error("client communication loop closed with reason {}".format(e))
                break

        client.close()

    def _handle_command(self, command, data):
        if command == "GINF":
            w = self._simulator_object._init_arguments["width"]
            h = self._simulator_object._init_arguments["height"]
            ppmm = self._simulator_object._init_arguments["ppmm"]
            w *= ppmm
            h *= ppmm
            w = int(w)
            h = int(h)
            info = {'display_resolution': {"width": w, "height": h},
                    'touch_resolution': {"width": w, "height": h},
                    'device_name': 'simulator', 'system_version': '1.0',
                    'system_name': 'simulation', "dut_name": self.name}
            info = json.dumps(info)
            return command, info.encode("ascii")

        if command =="SIMG":
            image = data # should be image in png or jpeg format; data that contains decodable image
            self._simulator_object.draw_image(image)
            return command, bytearray()

        if command == "GTCH":
            touch_coords = []
            r = {"fields": ["x", "y", "phase"], "touches": touch_coords}
            r = json.dumps(r)
            return command, r.encode("ascii")

        # Faking authentication
        if command == "CHAL":
            return command, "fake_challenge".encode("utf-8")
        if command == "AUTH":
            return command, "OK".encode("utf-8")
        # default response
        return command, bytearray()

