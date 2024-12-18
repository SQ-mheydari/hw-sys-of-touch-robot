import asyncio
import select
import socket
import threading
import time
import webbrowser
import logging
import websockets
import json

from tntserver.Nodes.Node import *
import tntserver.globals
import math

log = logging.getLogger(__name__)


STAFF_PORT = 4001
WEBSOCKET_PORT = 9876


class NodeSimulator(Node):

    def _init(self, **kwargs):
        # Only initialize if using visual simulation.
        if "program_arguments" in kwargs:
            if not kwargs["program_arguments"].visual_simulation:
                return

        t = threading.Timer(1, self.start)
        t.start()
        #self.start()

        self.listen_channel("tips")
        self.listen_channel("tools")

    def message(self, message:str):
        parts = message.split(" ")

        cmd = parts[0]
        params = parts[1:]

        if cmd == "attach_tip":
            tip_name = params[0]
            kinematic_name = params[1]
            s = tntserver.globals.simulator_model
            s.attach_tip(tip_name, kinematic_name)
        elif cmd == "detach_tip":
            tip_name = params[0]
            s = tntserver.globals.simulator_model
            s.detach_tip(tip_name)
        elif cmd == "set_tip_slot_in":
            tip_name = params[0]
            slot_in = [float(params[1]), float(params[2]), float(params[3])]
            s = tntserver.globals.simulator_model
            s.set_tip_slot_in(tip_name, slot_in)
        elif cmd == "attach_tool":
            tool_name = params[0]
            kinematic_name = params[1]
            s = tntserver.globals.simulator_model
            s.attach_tool(tool_name, kinematic_name)
        elif cmd == "detach_tool":
            tool_name = params[0]
            s = tntserver.globals.simulator_model
            s.detach_tool(tool_name)

    def start(self):
        log.info("Starting simulator")

        logging.getLogger("websockets.protocol").setLevel(logging.WARNING)

        simulator = StaffSimulator()
        webbrowser.open("http://127.0.0.1:8010/simu.html")
        self.__simulator = simulator

        asyncio.set_event_loop(asyncio.new_event_loop())
        start_server = websockets.serve(websocketloop, 'localhost', WEBSOCKET_PORT)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

    @json_out
    def get_set_tip(self, tip_name):
        s = tntserver.globals.simulator_model
        s.set_tip(tip_name)

    @json_out
    def get_move_object(self, name, p):
        p = json.loads(p)
        x, y, z = p[0], p[1], p[2]
        a = math.radians(p[3]) if len(p) > 3 else 0
        b = math.radians(p[4]) if len(p) > 4 else 0
        c = math.radians(p[5]) if len(p) > 5 else 0

        sc = tntserver.globals.simulator_instance
        sc.moveObject(name, [x, y, z, a, b, c])

    @json_out
    def put_send_and_receive(self, msg: str):
        c = tntserver.globals.simulator_instance
        result = c.send_and_receive(msg)

        return result


class WebInterface():
    __instance = None
    websocket = None

    def __init__(self):
        self.socket = WebInterface.websocket
        self.out_queue = []
        self.in_queue = []
        self.out_queue_cv = threading.Condition()
        self.response_cv = threading.Condition()

    def message(self, message):
        msg = [message, None]

        # send message and notify
        self.out_queue.append(msg)
        self.out_queue_cv.acquire()
        self.out_queue_cv.notify()
        self.out_queue_cv.release()

        # wait for response
        while msg[1] is None:
            self.response_cv.acquire()
            self.response_cv.wait()
            self.response_cv.release()

        result = msg[1]

        return result

    @staticmethod
    def instance():
        if WebInterface.__instance is None:
            WebInterface.__instance = WebInterface()
        return WebInterface.__instance


async def websocketloop(websocket, path):
    WebInterface.websocket = websocket

    try:
        name = await websocket.recv()
        log.info("websocket is now open and simulator is ready to operate")

        while (True):
            wi = WebInterface.instance()
            try:
                if len(wi.out_queue) > 0:
                    msg = wi.out_queue[0]
                    wi.out_queue = wi.out_queue[1:]
                    await websocket.send(msg[0])
                    response = await websocket.recv()

                    # send response and notify
                    msg[1] = response
                    wi.response_cv.acquire()
                    wi.response_cv.notify()
                    wi.response_cv.release()

            except Exception as e:
                log.error("websocketloop exception {}".format(e))
                if wi.socket._connection_lost:
                    break
                pass

            wi.out_queue_cv.acquire()
            wi.out_queue_cv.wait()
            wi.out_queue_cv.release()
    except Exception as e:
        log.error("Exception while waiting for websocket {}".format(e))
    log.warning("websocket closed")


class StaffSimulator():
    def __init__(self, port=STAFF_PORT):
        self.lock = threading.Lock()
        self._terminate = False

        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("localhost", port))
                break
            except Exception as e:
                s.close()
                log.error("Exception creating simulator socket {}".format(e))
                time.sleep(1)


        s.listen(10)
        self.listensocket = s

        thread = threading.Thread(None, self.listenLoop, "connectionlistener")
        thread.start()
        self.connectionlistenerthread = thread

    def close(self):
        self._terminate = True
        self.listensocket.close()
        self.connectionlistenerthread.join()

    def listenLoop(self):
        while self._terminate == False:
            try:
                client, addr = self.listensocket.accept()
            except Exception as e:
                log.error("Simulator thread exited with message {}".format(e))
            t = threading.Thread(None, self.clientLoop, name="clientconnection", args=(client, addr))
            t.start()

    def clientLoop(self, client, addr):
        log.info("new client {} {}".format(client, addr))
        buffer = ""

        client.setblocking(1)

        while self._terminate == False:
            try:
                rlist, wlist, elist = select.select([client], [], [], 1)
                if len(rlist) > 0:
                    socket = rlist[0]
                    d = socket.recv(100000)
                    if len(d) == 0:
                        time.sleep(0.5)
                    s = d.decode()
                    buffer += s

                    p = buffer.find("\n")

                    if p >= 0:
                        msg = buffer[0:p + 1]
                        buffer = buffer[p + 1:]

                        webinterface = WebInterface.instance()
                        res = webinterface.message(msg)
                        client.send(res.encode())
                else:
                    time.sleep(0.5)
            except Exception as e:
                log.error("simulator communication error {}".format(e))
                break
        log.error("connection to client lost", client, addr)

