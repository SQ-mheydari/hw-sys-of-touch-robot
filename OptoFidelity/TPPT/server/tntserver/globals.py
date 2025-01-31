"""
Storage for global variables that are available to all Nodes
"""

import os

# the HTTP port for API
server_port = 8001

# simulator connection ( GoldenSimulatorComm )
simulator_instance = None

# simulator model ( selected model of robots.goldenmov.simulator.simulator_xxxx.py )
simulator_model = None

# root path
root_path = os.path.dirname(__file__)

