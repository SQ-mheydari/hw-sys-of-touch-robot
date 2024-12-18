# TnT Client

Client for interacting with TnT Server via REST API.

## Generating wheel

Place your client generation config file under following directory:

    configuration/

See example config file

    configuration/client_config.yaml

Start TnT Server with command:

    TnT Server.exe --generate-client=configuration/client_config.yaml

The client will be generated under following directory:

    client/

In that directory there is `setup.py` that can be used to generate a wheel with system installation of Python:

    python setup.py sdist bdist_wheel

In case you get an error about `wheel` package not found, you need to install it with command:

    pip install wheel

If you can't install packages due to limited privilege, use option `--user` as `pip install --user wheel`.

A wheel will be generated under following directory:

    client/dist/

To install the client to the system Python environment, execute following command under `client/dist`:

    python -m pip install tntclient-x.x.x.x.x-py3-none-any.whl

where `x.x.x.x.x` should be replaced by the specific version number. In built version of TnT Server the client wheel version will match the server version.

## Usage

Import package `tntclient` and create client objects to communicate with the server. Example:

```
from tntclient.tnt_robot_client import TnTRobotClient

robot = TnTRobotClient("Robot1")
```
