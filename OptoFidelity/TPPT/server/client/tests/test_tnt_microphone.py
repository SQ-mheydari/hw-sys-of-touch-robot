from tntclient.tnt_microphone_client import TnTMicrophoneClient
from tntclient.tnt_client import *


def init_nodes():
    microphone_name = 'microphone1'
    microphone_client = TnTMicrophoneClient(microphone_name)
    tntclient = TnTClient()
    return microphone_name, microphone_client, tntclient


def test_chunk_size():
    microphone_name, microphone_client, tntclient = init_nodes()
    size = microphone_client.chunk_size
    size_new = size + 1024
    microphone_client.chunk_size = size_new
    result = microphone_client.chunk_size
    assert result == size_new


def test_device_name():
    microphone_name, microphone_client, tntclient = init_nodes()
    device_name = microphone_client.device_name
    assert device_name is not None
    device_name_new = 'Built-in Output'
    microphone_client.device_name = device_name_new
    result = microphone_client.device_name
    assert result == device_name_new
