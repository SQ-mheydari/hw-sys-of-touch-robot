import json
import copy
import base64
from . import logger

try:
    import requests
except ImportError:
    raise ImportError(
        "TnT Client requires Python module 'requests'. This module can be installed with command 'pip install requests' or from here: https://pypi.python.org/pypi/requests/")

log = logger.get_logger(__name__)


class RequestError(Exception):
    """ Error occurred during the request to the TnT Server """

    def __init__(self, status, message):
        self.status = status
        self.message = message
        Exception.__init__(self, message)

    def __str__(self):
        if self.message:
            return "{} - {}".format(self.status, self.message)


class TnTDutPoint(object):
    """ Point used for DUT operations """

    def __init__(self, x, y, z, tilt=None, azimuth=None):
        self.x = x
        self.y = y
        self.z = z
        self.tilt = tilt
        self.azimuth = azimuth

    def __repr__(self):
        return "x: %s; y: %s; z %s; tilt: %s; azimuth: %s" % \
               (self.x, self.y, self.z, self.tilt, self.azimuth)

    def to_dict(self):
        """
        Convert TnTDutPoint object to dictionary.
        :return: Dictionary with keys that correspond to class members.
        """
        params = {
            "x": self.x,
            "y": self.y,
            "z": self.z,
        }
        if self.tilt is not None:
            params["tilt"] = self.tilt
        if self.azimuth is not None:
            params["azimuth"] = self.azimuth

        return params


def parameters_to_http_dict(parameters):
    """
    Convert TnT Client API parameters to a dict that can be passed through HTTP.
    :param parameters: Parameter dict.
    :return: New parameter dict that can be passed through HTTP.
    """

    if parameters is None:
        return None

    # Make sure we are not modifying the input dict.
    new_parameters = copy.deepcopy(parameters)

    for key, value in new_parameters.items():
        if isinstance(value, list):
            for i in range(len(value)):
                # List of TnTDutPoint objects are converted to dict.
                if isinstance(value[i], TnTDutPoint):
                    value[i] = value[i].to_dict()
        elif isinstance(value, bytes):
            # Bytes are passed as base64 encoded string.
            new_parameters[key] = base64.encodebytes(value).decode("ascii")

    return new_parameters


class TnTClientObject(object):
    """ This class provides (low level) access to TnT Server and its resources acting as a base class for all resources. """
    default_workspace = "ws"

    def __init__(self, host, port, workspace, resource_type=None, resource_name=None):

        self._host = host
        self._port = port

        # Using sessions is faster than opening new connection every time sending request with request.get/post/put/delete
        self._session = requests.Session()
        self._resource_type = resource_type
        self._resource_name = resource_name

        self._workspace = "http://{}:{}/tnt/workspaces/{}".format(host, port, workspace)

        if self._resource_type is not None:
            if self._resource_name:
                self._url = "http://{}:{}/tnt/workspaces/{}/{}/{}".format(host, port, workspace, self._resource_type,
                                                                          self._resource_name)
            else:
                self._url = "http://{}:{}/tnt/workspaces/{}/{}".format(host, port, workspace, self._resource_type)

        elif self._resource_name is not None:
            self._url = "http://{}:{}/tnt/workspaces/{}/{}".format(host, port, workspace, self._resource_name)

        else:
            self._url = "http://{}:{}/tnt/workspaces/{}".format(host, port, workspace)

    def __str__(self):
        if self._resource_name is None:
            return self._url
        else:
            return self._resource_name

    @property
    def host(self):
        """ Host IP address """
        return self._host

    @property
    def port(self):
        """ Host IP port """
        return self._port

    @property
    def resource_type(self):
        """ Resource type e.g. 'robots', 'duts', etc. """
        return self._resource_type

    @property
    def name(self):
        """ Resource name """
        return self._resource_name

    @property
    def connection(self):
        """ Resource connection """
        return self._GET('connection')

    def _GET(self, target, parameters=None):
        return self._send_request("GET", target, parameters)

    def _POST(self, target, parameters):
        return self._send_request("POST", target, parameters)

    def _PUT(self, target, parameters, content_type=None, content=None):
        return self._send_request("PUT", target, parameters, content_type=content_type, content=content)

    def _DELETE(self, target, parameters):
        return self._send_request("DELETE", target, parameters)

    def _POST_ADVANCED(self, target, data=None, json=None, files=None):
        """
        allow to send json and data in request
        """
        url = '{base}/{t}'.format(base=self._url, t=target)
        # log.debug('post to {u}, data type {d}, json {j}'.format(u=url, d=type(data), j=json))
        response = self._session.post(url, data=data, json=json, files=files)
        log.debug('response {}'.format(str(response.content)))
        return self._get_response_content(response)

    def _send_request(self, method, target, parameters, base_url=None, content=None, content_type=None):
        """
        send request with content-type = application/json as default. PUT command also works with other
        content types.
        :param method: the http request type
        :param target: destination of the request
        :param parameters: possible request parameters in a dict (will be ignored if content_type is not None)
        :param base_url: base url
        :param content: if content_type is defined, this is used as data, otherwise ignored
        :param content_type: content type, currently only works with PUT
        """
        # Sanity check for parameters
        if parameters is not None:
            if type(parameters) != dict:
                raise ValueError("Parameters must be provided in dictionary instead of " + str(type(parameters)))

        # Convert parameters to a dictionary that can be passed through HTTP request.
        parameters = parameters_to_http_dict(parameters)

        url = self._url if base_url is None else base_url

        if target is not None and len(target) > 0:
            url += "/" + target

        if method == "GET":
            if parameters is not None:
                url += "?"

                for key, value in parameters.items():
                    url += "{}={}&".format(key, value)

                # Remove trailing ampersand
                if url[-1] == "&":
                    url = url[:-1]

            response = self._session.get(url)

        elif method == "POST":
            response = self._session.post(url, data=json.dumps(parameters),
                                          headers={"content-type": "application/json"})

        elif method == "PUT":
            # If content type is defined, it will be used instead of application/json. In that case also parameters
            # are ignored and content is used as request content
            if content_type is None:
                response = self._session.put(url, data=json.dumps(parameters),
                                             headers={"content-type": "application/json"})
            else:
                response = self._session.put(url, data=content, headers={"content-type": content_type})

        elif method == "DELETE":
            response = self._session.delete(url, data=json.dumps(parameters),
                                            headers={"content-type": "application/json"})

        else:
            raise ValueError("Unknown or unsupported HTTP method -- " + method)

        return self._get_response_content(response)

    def _get_response_content(self, response):
        """
        Return response content on success or raise RequestError
        :param response:
        :return:
        """
        # If request was completed successfully
        if 200 <= response.status_code < 300:

            if response.headers["Content-Type"] == "application/octet-stream":
                return response.content

            if response.headers["Content-Type"] == "image/jpeg":
                return response.content

            if response.headers["Content-Type"] == "image/png":
                return response.content

            if response.headers["Content-Type"] == "audio/x-wav":
                return response.content

            content = self._decode_content(response.content)

            if response.headers["Content-Type"] == "application/json":
                return json.loads(content)

        else:
            content = self._decode_content(response.content)

            json_error = json.loads(content)
            log.debug('json {s} - {m}'.format(s=json_error["status"], m=json_error["message"]))
            raise RequestError(json_error["status"], json_error["message"])

    def _decode_content(self, content):
        """
        currently decode only if expecting json
        :param content: response.content
        :return:
        """
        if isinstance(content, bytes):
            content = content.decode()
        return content

    @staticmethod
    def change_type(data_type: str, value: str):
        """
        Changes the type of a string variable
        :param data_type: the new type of the variable
        :param value: value of the variable
        :return: value in correct type
        """

        assert isinstance(data_type, str)
        assert isinstance(value, str)

        if data_type == "str":
            return value
        elif data_type == "int":
            return int(value)
        elif data_type == "float":
            return float(value)
        elif data_type == "bool":
            return value == "True"
        elif data_type == "list":
            return json.loads(value)
        elif data_type == "NoneType":
            return None
        else:
            raise TypeError("Unknown data type: {}".format(data_type))

    @staticmethod
    def change_type_recursively(data):
        """
        Change type of data returned by HTTP call.
        The returned data is a dict of form {"type": type, "value": value} or a dict of such dicts.
        :param data: Data dictionary.
        :return: Data in correct type.
        """
        if "type" in data and "value" in data:
            return TnTClientObject.change_type(data["type"], data["value"])

        return {key: TnTClientObject.change_type_recursively(value) for key, value in data.items()}

    def get_properties(self) -> dict:
        """
        Get all available properties
        :return: dictionary containing all properties
        """
        return self._GET("properties")

    def get_property(self, name):
        """
        Get client property value.
        :param name: Property name.
        :return: Property value.
        """
        params = {"name": name}
        data = self._GET("property", params)

        return self.change_type_recursively(data)

    def set_properties(self, properties: dict):
        """
        set properties
        :param properties: dictionary with {name: value} for properties
        :return: "" - empty string
        """
        return self._PUT("properties", parameters=properties)

    def set_property(self, name, value):
        """
        Set client property value.
        :param name: Property name.
        :param value: Property value.
        """
        params = {name: value}

        self._PUT("properties", params)


class TnTClient(TnTClientObject):
    """ This class provides high level access to TnT Server and its resources.
    :example:
    client = TnTClient()

    robot = client.robot("MyRobotName")
    dut = client.dut("MyDutName")
    camera = client.camera("MyCameraName")

    robot.some_method()
    """

    def __init__(self, host="127.0.0.1", port=8000, workspace=TnTClientObject.default_workspace):
        self.workspace = workspace
        TnTClientObject.__init__(self, host, port, workspace=workspace)

    def robot(self, name):
        """
        Create a new robot client object with a given name.
        :param name: Name of robot to create client for.
        :return: TnTRobotClient object.
        """

        try:
            from .tnt_robot_client import TnTRobotClient

            return TnTRobotClient(name, host=self.host, port=self.port, workspace=self.workspace)
        except ImportError:
            log.error("Robot client not found.")
            raise

    def robots(self):
        """
        Get a list of all available robots from TnT Server as robot clients.
        :return: List of TnTRobotClient objects corresponding to all robots in server.
        """
        robots = []

        for r in self._GET("robots")["robots"]:
            robots.append(self.robot(r["name"]))

        return robots

    def dut(self, name):
        """
        Create a new DUT client object with a given name.
        :param name: Name of DUT.
        :return: TnTDUTClient object corresponding to DUT with given name.
        """

        try:
            from .tnt_dut_client import TnTDUTClient

            return TnTDUTClient(name, host=self.host, port=self.port, workspace=self.workspace)
        except ImportError:
            log.error("DUT client not found.")
            raise

    def add_dut(self, name):
        """
        Add new DUT resource.
        :param name: Name of the resource.
        :return: TnTDUTClient object corresponding to the added resource.
        """
        client = TnTClientObject(self.host, self.port, self.workspace, "duts", "")

        client._POST("", {"name": name, "type": "Dut"})

        return self.dut(name)

    def duts(self):
        """
        Get a list of all available DUTs from TnT Server as DUT clients.
        :return: List of TnTDUTClient objects corresponding to all DUTs in server.
        """
        duts = []

        for d in self._GET("duts")["duts"]:
            duts.append(self.dut(d["name"]))

        return duts

    def tip(self, name):
        """
        Create a new tip client object with a given name.
        :param name: Name of tip.
        :return: TnTTipClient object corresponding to tip with given name.
        """

        try:
            from .tnt_tip_client import TnTTipClient

            return TnTTipClient(name, host=self.host, port=self.port, workspace=self.workspace)
        except ImportError:
            log.error("Tip client not found.")
            raise

    def add_tip(self, name):
        """
        Add new tip resource.
        :param name: Name of the resource.
        :return: TnTTipClient object corresponding to the added resource.
        """
        client = TnTClientObject(self.host, self.port, self.workspace, "tips", "")

        client._POST("", {"name": name, "type": "Tip"})

        return self.tip(name)

    def tips(self):
        """
        Get a list of all available tips from TnT Server as tip clients.
        :return: List of TnTTipClient objects corresponding to all tips in server.
        """
        tips = []

        for t in self._GET("tips")["tips"]:
            tips.append(self.tip(t["name"]))

        return tips

    def camera(self, name):
        """
        Create a new camera client object with a given name.
        :param name: Name of camera.
        :return: TnTCameraClient object corresponding to camera with given name.
        """

        try:
            from .tnt_camera_client import TnTCameraClient

            return TnTCameraClient(name, host=self.host, port=self.port, workspace=self.workspace)
        except ImportError:
            log.error("Camera client not found.")
            raise

    def cameras(self):
        """
        Get a list of all available cameras from TnT Server.
        :return: List of TnTCameraClient objects corresponding to all cameras in server.
        """
        cameras = []

        for i in self._GET("cameras")["cameras"]:
            cameras.append(self.camera(i["name"]))

        return cameras

    def physical_button(self, name):
        """
        Create a new physical button client object with a given name.
        :param name: Name of DUT physical button.
        :return: TnTPhysicalButtonClient object corresponding to DUT physical button with given name.
        """

        try:
            from .tnt_physical_button_client import TnTPhysicalButtonClient

            return TnTPhysicalButtonClient(name, host=self.host, port=self.port, workspace=self.workspace)
        except ImportError:
            log.error("Physical button client not found.")
            raise

    def add_physical_button(self, name):
        """
        Add new physical button resource.
        :param name: Name of the resource.
        :return: TnTPhysicalButtonClient object corresponding to the added resource.
        """
        client = TnTClientObject(self.host, self.port, self.workspace, "physical_buttons", "")

        client._POST("", {"name": name, "type": "PhysicalButton"})

        return self.physical_button(name)

    def physical_buttons(self):
        """
        Get a list of all available physical buttons from TnT Server.
        :return: List of TnTPhysicalButtonClient objects corresponding to all DUT physical buttons in server.
        """
        physical_buttons = []

        for button in self._GET("physical_buttons")["physical_buttons"]:
            physical_buttons.append(self.physical_button(button["name"]))

        return physical_buttons

    def microphone(self, name):
        """
        Create a new microphone client with the microphone that has the given name in server.
        :param name: name of the microphone
        :return: TnTMicrophoneClient object corresponding to microphone with given name
        """

        try:
            from .tnt_microphone_client import TnTMicrophoneClient

            return TnTMicrophoneClient(name, host=self.host, port=self.port, workspace=self.workspace)
        except ImportError:
            log.error("Microphone client not found.")
            raise

    def detectors(self):
        """
        Get list of all available detectors from TnT Server that have client implemented
        :return: objects that are of correct type with given names
        """
        detectors = []
        for d in self._GET("detectors")["detectors"]:
            # the detectors can be of different types
            if d["type"] == "NodeMicrophone":
                detectors.append(self.microphone(d["name"]))

        return detectors

    def speaker(self, name):
        """
        Create a new speaker client with the speaker that has the given name in server.
        :param name: name of the speaker
        :return: TnTSpeakerClient object corresponding to speaker with given name
        """

        try:
            from .tnt_speaker_client import TnTSpeakerClient

            return TnTSpeakerClient(name, host=self.host, port=self.port, workspace=self.workspace)
        except ImportError:
            log.error("Speaker client not found.")
            raise

    def speakers(self):
        """
        Get a list of all available speakers from TnT Server.
        :return: List of TnTSpeakerClient objects corresponding to all speakers in TnT server
        """
        speakers = []
        for d in self._GET("speakers")["speakers"]:
            speakers.append(self.speaker(d["name"]))

        return speakers

    def audio_analyzer(self, name):
        """
        Create a new audio analyzer client with the analyzer that has the given name in server.
        :param name: analyzer name
        :return: TnTAudioAnalyzerClient object
        """

        try:
            from .tnt_audio_analyzer_client import TnTAudioAnalyzerClient

            return TnTAudioAnalyzerClient(name, host=self.host, port=self.port, workspace=self.workspace)
        except ImportError:
            log.error("Audio analyzer client not found.")
            raise

    def image(self, name):
        """
        Create a new image client with the image that has the given name in server.
        :param name: name of the image
        :return: TnTImageClient object corresponding to image with given name
        """
        try:
            from .tnt_image_client import TnTImageClient

            return TnTImageClient(name, host=self.host, port=self.port, workspace=self.workspace)
        except ImportError:
            log.error("Image client not found.")
            raise

    def add_image(self, name):
        """
        Add new image resource.
        :param name: Name of the resource.
        :return: TnTImageClient object corresponding to the added resource.
        """
        client = TnTClientObject(self.host, self.port, self.workspace, "images", "")

        client._POST("", {"name": name, "type": "Image"})

        return self.image(name)

    def images(self):
        """
        Get a list of all available images from TnT Server.
        :return: List of TnTImageClient objects corresponding to all images in TnT server
        """
        images = []
        for i in self._GET("images")["images"]:
            images.append(self.image(i["name"]))

        return images

    def icon(self, name):
        """
        Create a new icon client with the icon that has the given name in server.
        :param name: Name of the icon.
        :return: TnTIconClient object corresponding to icon with given name.
        """
        try:
            from .tnt_icon_client import TnTIconClient

            return TnTIconClient(name, host=self.host, port=self.port, workspace=self.workspace)
        except ImportError:
            log.error("Icon client not found.")
            raise

    def add_icon(self, name):
        """
        Add new icon resource.
        :param name: Name of the resource.
        :return: TnTIconClient object corresponding to the added resource.
        """
        client = TnTClientObject(self.host, self.port, self.workspace, "icons", "")

        client._POST("", {"name": name, "type": "Icon"})

        return self.icon(name)

    def icons(self):
        """
        Get a list of all available icons from TnT Server.
        :return: List of TnTIconClient objects corresponding to all icons in server.
        """
        icons = []
        for i in self._GET("icons")["icons"]:
            icons.append(self.icon(i["name"]))

        return icons

    def motherboard(self, name):
        """
        Create a new motherboard client object with a given name.
        :param name: Name of motherboard.
        :return: TnTMotherboardClient object corresponding to camera with given name.
        """
        try:
            from .tnt_motherboard_client import TnTMotherboardClient

            return TnTMotherboardClient(name, host=self.host, port=self.port, workspace=self.workspace)
        except ImportError:
            log.error("Motherboard client not found.")
            raise

    def motherboards(self):
        """
        Get a list of all available motherboards from TnT Server.
        :return: List of TnTMotherboardClient objects corresponding to all motherboards in server.
        """
        motherboards = []

        for i in self._GET("motherboards")["motherboards"]:
            motherboards.append(self.motherboard(i["name"]))

        return motherboards

    def version(self):
        """
        Get TnT Server version.
        :return: Version string.
        """
        base_url = "http://{}:{}/tnt".format(self._host, self._port)
        return self._send_request("GET", "version", parameters=None, base_url=base_url)["tnt_version"]

    def futek(self, name):
        """
        Create a new Futek client object with a given name.
        :param name: Name of Futek object.
        :return: created Futek object
        """
        try:
            from .tnt_futek_client import TnTFutekClient

            return TnTFutekClient(name, host=self.host, port=self.port, workspace=self.workspace)
        except ImportError:
            log.error("Futek client not found.")
            raise
