"""
DeviceSocket is the connection between a script and device under test.
DeviceSocket is basically the same as TCPSocket module in PST.
"""

import logging
import queue
import select
import socket
import threading
import os
import os.path
import time

log = logging.getLogger(__name__)

CONNECTION_LIST = []
PORT = 50007

class DeviceSocket(threading.Thread):    

    def __init__(self):
        self.queue = queue.Queue()
        self.server_thread = threading.Thread(target=self.server, args =(self.queue,))
        self.server_thread.start()

    def server(self, queue):
                # List to keep track of socket descriptors

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # this has no effect, why ?
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("0.0.0.0", PORT))
        self.server_socket.listen(10)

        # Add server socket to the list of readable connections
        CONNECTION_LIST.append(self.server_socket)
        
        input = ""

        while True:
            # Get the list sockets which are ready to be read through select
            read_sockets,write_sockets,error_sockets = select.select(CONNECTION_LIST,[],[])

            for sock in read_sockets:
                #New connection
                if sock == self.server_socket:
                    # Handle the case in which there is a new connection recieved through server_socket
                    sockfd, addr = self.server_socket.accept()
                    CONNECTION_LIST.append(sockfd)
                    log.debug("Client ({}, {}) connected".format(addr[0], addr[1]))

                    #self.broadcast_data(sockfd, "[%s:%s] entered room\n" % addr)
                 
                #Some incoming message from a client
                else:
                    # Data recieved from client, process it
                    try:
                        #In Windows, sometimes when a TCP program closes abruptly,
                        # a "Connection reset by peer" exception will be thrown
                        
                        # input must have at least '4' characters
                        while len(input) < 4:
                            input += sock.recv(4).decode("utf-8")
                            # Test that client is still connected to avoid forever loop; if recv returns 0, the client has disconnected
                            if len(input) == 0:
                                break
                        length = int(input[:4])
                        input = input[4:]

                        # input must have at least 'length' characters
                        while len(input) < length:
                            input += sock.recv(length).decode("utf-8")
                        
                        # store extra characters if any, cut input to length
                        restInput = input[length:]
                        input = input[:length]

                        results = eval(input)
                        #log.debug("Put touch event to queue: {}".format(results))
                        queue.put(results)

                         # put the rest of the characters back to input
                        input = restInput
                        
                    except Exception as e:
                        log.info(e)
                        #self.broadcast_data(sock, "Client (%s, %s) is offline" % addr)
                        log.debug("Client ({}, {}) is offline".format(addr[0], addr[1]))
                        sock.close()
                        CONNECTION_LIST.remove(sock)
                        continue

        server_socket.close()
    def close_server(self):
        self.server_thread.join()

    def broadcast_data(self,sock, message):
        #Do not send the message to master socket and the client who has send us the message
        for socket in CONNECTION_LIST:
            if socket != self.server_socket and socket != sock :
                try :
                    socket.send(message.encode("utf-8"))
                except :
                    # broken socket connection may be, chat client pressed ctrl+c for example
                    socket.close()
                    CONNECTION_LIST.remove(socket)
    def handle_queue(self):
            while not self.queue.empty():
                result = self.queue.get()
                self.queue.task_done()
                log.debug(result)
    def clear_queue(self):
        while not self.queue.empty():
            self.queue.get()
            self.queue.task_done()
    def ReturnP2PArray(self, timeout = 2.0):
        try:
            retval = self.queue.get(timeout=timeout)
            self.queue.task_done()
            return retval
        except:
            return []
    def CLine(self, timeout = 2.0):
        while True:
            item = self.queue.get(timeout=timeout)
            self.queue.task_done()
            if item is None:
                break
            yield item

    def update_line(self,x_array, y_array, hl):
        hl.set_ydata(y_array)
        hl.set_xdata(x_array)
        plt.draw()
    
    def print_touch_data(self,input_results,draw_touches, hl):
        results = input_results
        touchlist = []
        
        if len(results) > 0:
            if "OK" in results:
                for point in range(results.index("OK")):  # Read all data points before "OK"
                    touchlist.append([results[point][0], results[point][1], results[point][2],
                                      results[point][3], results[point][4], results[point][5], results[point][6]])
            x_array = []
            y_array = []
            for touch in touchlist:
                
                event = int(touch[6])
                if event == 0:
                    event_name = "MOVE_DOWN"
                elif event == 1:
                    event_name = "MOVE_UP  "
                elif event == 2:
                    event_name = "ACTION_MOVE"
                elif event == 9:
                    event_name = "HOVER_DOWN "
                elif event == 10:
                    event_name = "HOVER_UP  "
                elif event == 7:
                    event_name = "HOVER_MOVE"
                else:
                    event_name = "Unknown event: " + str(event)
                log.debug("IP: " + str(sock.getpeername()[0]) +"\tEvent: "+ event_name + "\tPressure: " + str(touch[2]) +"\tX: " + str(touch[0]) + "\t Y: " + str(touch[1])+ "\t Finger: " + str(touch[3])+ "\t Timestamp: " + str(touch[5]))
                if draw_touches:
                    x_array.append(touch[0])
                    y_array.append(touch[1])
            if draw_touches:    
                self.update_line(x_array,y_array, hl)
