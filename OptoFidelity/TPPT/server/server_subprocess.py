import subprocess
import os
import sys

if len(sys.argv) > 1:
    if 'windows' in sys.argv[1]:
        server_location = os.path.abspath(os.path.join(os.getcwd(), 'installer', 'dist', 'start', 'TnT Server.exe'))
    elif 'macos' in sys.argv[1]:
        # for mac
        server_location = os.path.abspath(os.path.join(os.getcwd(), 'installer', 'dist', 'tnt_server', 'TnT Server'))

config_path = os.path.abspath(os.path.join(os.getcwd(), 'configuration', 'simulation_3axis.yaml'))
server_cmd = [server_location, "--configuration="+config_path,
              "--visual-simulation=false"]

with open("srv_output.txt", "w") as output_file:
    try:
        print('Start TnT Server.')
        subprocess.run(server_cmd, timeout=240, stdout=output_file)
    except subprocess.TimeoutExpired:
        print('TnT Server timeout.')
        pass

with open("srv_output.txt", "r") as file:
    print('TnT Server output start')
    print(file.read())
    print('TnT Server output end')
