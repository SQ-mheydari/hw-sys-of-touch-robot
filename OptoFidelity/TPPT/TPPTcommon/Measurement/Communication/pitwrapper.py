"""
Wrapper for PIT.

Useful information about dynamic attribute creation:
http://docs.python.org/reference/datamodel.html#customizing-attribute-access
"""

import logging
import socket
import time

# Own imports
try:
    from .clusterizer import Clusterizer
except ImportError:
    from clusterizer import Clusterizer

try:
    from .tunnelhandler import TunnelHandler
except ImportError:
    from tunnelhandler import TunnelHandler

LOGGER = logging.getLogger(__name__)

class PITWrapper():
    """Communicates with PIT.
    Note: This class implements magic with attribute lookup. If a non-existing
          attribute is accessed, it will be created dynamically. The new
          created object is callable. Therefore if you call a non-existing
          method in a method which is called from pit_func, it will cause an
          infinite recursive loop.

    You can use PIT's commands just by calling: PITWrapper.Command().
    Accessing a non-existing attribute of PITWrapper, e.g. P2P, will cause
    the __getattr__ method to dynamically create a callable, which sends the
    command and its parameters to PIT, and returns the received data to the
    caller.

    PITWrapper.P2P is callable, which sends command P2P with the same
    parameters that are given to the function.
    E.g. PITWrapper.P2P(1, 2) will send P2P command with parameters 1 and 2 to
    PIT and return the PIT's response to caller.

    That's how normal commands work. They give one response to one request.
    There are also separete generator command function.
    Generator command produces multiple responses to one request.
    They are explicitly defined in self.generator_commands dict.
    The returned generator will yield return values from PIT as long as the
    condition function returns True. Condition function is also defined in the
    self.generator_commands dict.
    """
    def __init__(self, tunnel=None, host=None, port=None, port2=5010, target=2, sender=4):
        """
        This class supports two types of constructing. Either with already
        initialized tunnel, or with host/port combination.

        Kwargs:
            tunnel: Handler to tunnelhandler.
            host: PIT's ip address.
            port: PIT's port.
            target: Target's id. Used to determine which module sent the
                    packet.
            sender: Sender's id.
        """
        self._tunnel = tunnel
        self._tunnel_data = None

        if self._tunnel is None:
            if host is None or port is None:
                raise NameError("Host and port are not defined!")

            self.pit_ip_address = host
            self.pit_port = port
            self.pit_port_data = port2
            # Initialize tunnel, tunnel handles the protocol between PIT
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            #self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
            self._sock.settimeout(3)
            try:
                self._sock.connect((self.pit_ip_address, self.pit_port))
            except socket.timeout:
                raise TimeoutError("Connection time out")

            self._tunnel = TunnelHandler(self._sock)
            self._tunnel.clear_tunnel()

            if self.pit_port_data != 0:
                # Initialize data socket from PIT
                self._sock_data = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock_data.settimeout(1)
                self._sock_data.connect((self.pit_ip_address, self.pit_port_data))
                self._tunnel_data = TunnelHandler(self._sock_data)
                self._tunnel_data.clear_tunnel()
        else:
            if host is not None or port is not None:
                raise NameError("Use only one type of constructing.")


        self.target = target
        self.sender = sender

        # Commands that causes PIT to send continuous data back until a
        # condition changes.
        # Format: {Casesensitive_name: callable}
        # The packets are received as long as the callable returns True
        # Callable should have one parameter, which is the packet received
        # from PIT.
        self.generator_commands = {'cline': self._cline_check}
        self.receiving = False
        self.stoprequest = False

    def __getattr__(self, name):
        """If class' attribute is accessed and it does not exist, this
        method will be called.

        Returns:
            A function that will call PIT's function named name.
        """
        def pit_func(*args):
            # Python gives arguments as a tuple, convert them to list.
            return self.send_command(name, list(args))
        return pit_func

    def close(self):
        """Closes the tunnel."""
        self._sock_data.close()
        self._sock.close()

    def _cline_check(self, xml_data):
        """Returns False, when CLine should be stopped."""
        # Old way: PIT returns timeout error at the end of CLine
        cluster = Clusterizer(xml_data)
        if cluster.command == 'Error' or cluster.command == 'stop' or cluster.command == 'Timeout':
            return [False, cluster.command]
        return [True, cluster.command]

    def _parse_return_data(self, xml_data):
        """Parses return data from the XML format that PIT outputs.
        Args:
            xml_data: str. XML format string that was received from PIT.
        Returns:
            Returns pythonic return values.
        """
        cluster = Clusterizer(xml_data)
        
        if cluster.command == 'Error':
            raise Exception(cluster.data)
        
        # Return data for CLine and P2P need to be converted to list type
        if cluster.command == "CLine" or cluster.command == "ReturnP2PArray" or cluster.command == "ReturnTimestamps":
            # CLine Data is in format: [str_repr_of_obj]. E.g. ['(1, 2)'] or ['2']
            try:
                # Remove possible python2 long type letter 'L' from timestamp 
                return_data = cluster.data[0].replace('L','')
                # Try to eval string to list
                return_data = eval(return_data)
            except NameError:
                # return string if eval fails.
                return_data = cluster.data
        else:
            # return string for other commands.
            return_data = cluster.data
        
        # If nothing is returned the return_data is '', make it more pythonic
        # by returning None
        if len(return_data) == 0:
            return None
        return return_data


    def _get_return_value(self, command, timeout=None):
        """Gets response from tunnel and returns it.
        Args:
            timeout: Timeout for receiving.
        """
        #xml_data = self._socket_receive(self._sock)
        xml_data = self._tunnel.get_packet(timeout=timeout)

        return self._parse_return_data(xml_data)

    def send_command(self, command, parameters):
        """Sends command to PIT.
        Args:
            command: PIT command.
            parameters: Parameters to command.
        Returns:
            PIT answer
        """
        # Format the XML data to be sent.
        signal = Clusterizer()
        signal.command = command
        signal.data = parameters
        signal.id = time.time()

        LOGGER.debug('Send command: %s' % command)
        xml_str = signal.tostring()
        data = str(len(xml_str)) + "\r" + xml_str
        self._tunnel.send_packet(data)

        return self._get_return_value(command)

    def receive_data_generator(self, command='CLine'):
        """ Read data from PIT2 and returns generator
        """
        self.receiving = True
        while True:
            xml_data = self._tunnel_data.get_packet(timeout=None)

            condition_func = self.generator_commands[command.lower()]
            if not condition_func(xml_data)[0]:
                if condition_func(xml_data)[1] != 'Error' and condition_func(xml_data)[1] != 'stop' and condition_func(xml_data)[1] != 'Timeout':
                    # We don't want to parse error string because error is generated always when listening
                    # for touch events and they stop coming even if they were coming successfully.
                    # Stop event provides empty string and we want to throw that away too.
                    yield self._parse_return_data(xml_data)
                break
            yield self._parse_return_data(xml_data)
        self.receiving = False

if __name__ == "__main__":
    pit = PITWrapper(host="172.22.11.2", port=5001)
    print("PIT SW version:", pit.PIT_FW_Version()[0])
    print("Set output:", pit.Output(1))
