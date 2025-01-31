import subprocess
import os
import sys
import time
import requests
import json

"""
- This script is used to run client API test cases for Jenkinsfile stage (Client API tests)
- First tnt server is launched by subprocess without timeout
- Wait 30s so server starts correctlly, then run pytest for client APIs
- After test is done, subprocess (tnt server) will be terminated
"""
# have a different name as test server start, for debugging purpose
output_file_name = "srv_output_client.txt"
output_file = open(output_file_name, "w")
config_file = 'simulation_synchro.yaml'

# this value will be set by return code of pytest
error_level = 1

# for mac
# this is the director for server in the builds
root_dir = os.path.abspath(os.path.join(os.getcwd(), 'installer', 'dist', 'tnt_server'))
server_app_name = 'TnT Server'

# for windows
if len(sys.argv) > 1:
    if 'windows' in sys.argv[1]:
        root_dir = os.path.abspath(os.path.join(os.getcwd(), 'installer', 'dist', 'start'))
        server_app_name = 'TnT Server.exe'

config_path = os.path.abspath(os.path.join(os.getcwd(), 'configuration', config_file))
# cd to server root in order for server easily access data or others
os.chdir(root_dir)

server_location = os.path.abspath(os.path.join(os.getcwd(), server_app_name))
print(server_location)
server_cmd = [server_location, "--configuration="+config_path,
              "--visual-simulation=false"]


def wait_for_server_init(interval, max_time):
    """
    Wait for server to start in another process. Checks for successful GET request.
    Blocks until server has initialized.
    Raises exception if server does not start within max_time.
    :param interval: Check interval in seconds.
    :param max_time: Maximum time for server initialization in seconds.
    """
    start_time = time.time()

    session = requests.Session()

    url = "http://127.0.0.1:8000/tnt/version"

    while time.time() - start_time < max_time:
        try:
            response = session.get(url, headers={"content-type": "application/json"})

            if response.status_code != 200:
                raise Exception("GET request returned with status code {}.".format(response.status_code))

            data = json.loads(response.content.decode())
            print("Got TnT Server version {}.".format(data["tnt_version"]))
            return
        except Exception:
            # Pass any exceptions that may happen until server is ready.
            pass

        # Sleep some time to avoid too frequent file access.
        time.sleep(interval)

    raise Exception("Server did not initialize within {} seconds.".format(max_time))


try:
    print('start...')
    # launch tnt server which doesn't block executing following codes
    proc1 = subprocess.Popen(server_cmd, stdout=output_file)

    wait_for_server_init(interval=10.0, max_time=600.0)

    # change to client test path, so pytest can find client test scripts
    test_directory = os.path.abspath(os.path.join(os.getcwd(), 'client', 'tests'))
    try:
        os.chdir(test_directory)
    except:
        pass

    # launch tests
    error_level = os.system('pytest -Wdefault --ignore=test_scripts')
    print('error level is: ' + str(error_level))

    # terminate tnt server after tests are done
    subprocess.Popen.kill(proc1)

except Exception as e:
    print(e)
    # kill subprocess to stop server
    subprocess.Popen.kill(proc1)

# if pytest fails, raise error level to jenkins
if error_level != 0:
    sys.exit(1)

