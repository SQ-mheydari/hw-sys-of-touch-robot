
from tntclient.tnt_client import *
from tntclient.tnt_robot_client import TnTRobotClient
from tntclient.tnt_icon_client import TnTIconClient
from tntclient.tnt_image_client import TnTImageClient
from tntclient.tnt_physical_button_client import TnTPhysicalButtonClient
from tntclient.tnt_tip_client import TnTTipClient
from tntclient.tnt_dut_client import TnTDUTClient
from tntclient.tnt_audio_analyzer_client import TnTAudioAnalyzerClient
from tntclient.tnt_camera_client import TnTCameraClient
from tntclient.tnt_microphone_client import TnTMicrophoneClient
from tntclient.tnt_motherboard_client import TnTMotherboardClient
from tntclient.tnt_speaker_client import TnTSpeakerClient


import pytest
import os

def init_nodes():
    tntclient = TnTClient()
    dut_name = 'dut1'
    icon_name = 'icon1'
    image_name = 'image1'
    physical_button_name = 'physical_button1'
    tip_name = 'tip1'
    audio_analyzer_name = 'audio_analyzer'
    camera_name = 'camera1'
    microphone_name = 'microphone1'
    motherboard_name = 'motherboard1'
    robot_name = 'Robot1'
    speaker_name = 'speaker1'
    nodes = {}
    nodes['tntclient'] = tntclient
    nodes['dut_name'] = dut_name
    nodes['icon_name'] = icon_name
    nodes['image_name'] = image_name
    nodes['physical_button_name'] = physical_button_name
    nodes['tip_name'] = tip_name
    nodes['audio_analyzer_name'] = audio_analyzer_name
    nodes['camera_name'] = camera_name
    nodes['microphone_name'] = microphone_name
    nodes['motherboard_name'] = motherboard_name
    nodes['robot_name'] = robot_name
    nodes['speaker_name'] = speaker_name
    return nodes



def test_add_dut():
    nodes = init_nodes()
    result = nodes['tntclient'].add_dut("client_test_dut")
    assert isinstance(result, TnTDUTClient)
    assert result.name == "client_test_dut"
    result.remove()


def test_add_icon():
    nodes = init_nodes()
    result = nodes['tntclient'].add_icon("client_test_icon")
    assert isinstance(result, TnTIconClient)
    assert result.name == "client_test_icon"
    result.remove()


def test_add_image():
    nodes = init_nodes()
    result = nodes['tntclient'].add_image("client_test_image")
    assert isinstance(result, TnTImageClient)
    assert result.name == "client_test_image"
    result.remove()


def test_add_physical_button():
    nodes = init_nodes()
    result = nodes['tntclient'].add_physical_button("client_test_button")
    assert isinstance(result, TnTPhysicalButtonClient)
    assert result.name == "client_test_button"
    result.remove()


def test_add_tip():
    nodes = init_nodes()
    result = nodes['tntclient'].add_tip("client_test_tip")
    assert isinstance(result, TnTTipClient)
    assert result.name == "client_test_tip"
    result.remove()


def test_audio_analyzer():
    nodes = init_nodes()
    result = nodes['tntclient'].audio_analyzer(nodes['audio_analyzer_name'])
    assert isinstance(result, TnTAudioAnalyzerClient)
    assert result.name == nodes['audio_analyzer_name']


def test_camera():
    nodes = init_nodes()
    result = nodes['tntclient'].camera(nodes['camera_name'])
    assert isinstance(result, TnTCameraClient)
    assert result.name == nodes['camera_name']


def test_cameras():
    nodes = init_nodes()
    result = nodes['tntclient'].cameras()
    for c in result:
        assert isinstance(c, TnTCameraClient)


def test_detectors():
    nodes = init_nodes()
    result = nodes['tntclient'].detectors()


def test_dut():
    nodes = init_nodes()
    result = nodes['tntclient'].dut(nodes['dut_name'])
    assert isinstance(result, TnTDUTClient)
    assert result.name == nodes['dut_name']
    print(result.name)
    print(nodes['dut_name'])


def test_duts():
    nodes = init_nodes()
    result = nodes['tntclient'].duts()
    for d in result:
        assert isinstance(d, TnTDUTClient)


def test_icon():
    nodes = init_nodes()
    result = nodes['tntclient'].icon(nodes['icon_name'])
    assert isinstance(result, TnTIconClient)
    assert result.name == nodes['icon_name']


def test_icons():
    nodes = init_nodes()
    result = nodes['tntclient'].icons()
    for i in result:
        assert isinstance(i, TnTIconClient)


def test_image():
    nodes = init_nodes()
    result = nodes['tntclient'].image(nodes['image_name'])
    assert isinstance(result, TnTImageClient)
    assert result.name == nodes['image_name']

def test_images():
    nodes = init_nodes()
    result = nodes['tntclient'].images
    pass

def test_microphone():
    nodes = init_nodes()
    result = nodes['tntclient'].microphone(nodes['microphone_name'])
    assert isinstance(result, TnTMicrophoneClient)
    assert result.name == nodes['microphone_name']


def test_motherboard():
    nodes = init_nodes()
    result = nodes['tntclient'].motherboard(nodes['motherboard_name'])
    assert isinstance(result, TnTMotherboardClient)
    assert result.name == nodes['motherboard_name']


def test_motherboards():
    nodes = init_nodes()
    result = nodes['tntclient'].motherboards()
    for m in result:
        assert isinstance(m, TnTMotherboardClient)


def test_physical_button():
    nodes = init_nodes()
    result = nodes['tntclient'].physical_button(nodes['physical_button_name'])
    assert isinstance(result, TnTPhysicalButtonClient)
    assert result.name == nodes['physical_button_name']


def test_physical_buttons():
    nodes = init_nodes()
    result = nodes['tntclient'].physical_buttons()
    for p in result:
        assert isinstance(p, TnTPhysicalButtonClient)


def test_robot():
    nodes = init_nodes()
    result = nodes['tntclient'].robot(nodes['robot_name'])
    assert isinstance(result, TnTRobotClient)
    assert result.name == nodes['robot_name']

def test_robots():
    nodes = init_nodes()
    result = nodes['tntclient'].robots()
    for r in result:
        assert isinstance(r, TnTRobotClient)


def test_speaker():
    nodes = init_nodes()
    result = nodes['tntclient'].speaker(nodes['speaker_name'])
    assert isinstance(result, TnTSpeakerClient)


def test_speakers():
    nodes = init_nodes()
    result = nodes['tntclient'].speakers()
    for s in result:
        assert isinstance(s, TnTSpeakerClient)

def test_tip():
    nodes = init_nodes()
    result = nodes['tntclient'].tip(nodes['tip_name'])
    assert isinstance(result, TnTTipClient)
    assert result.name == nodes['tip_name']

def test_tips():
    nodes = init_nodes()
    result = nodes['tntclient'].tips()
    for t in result:
        assert isinstance(t, TnTTipClient)


def test_version():
    nodes = init_nodes()
    result = nodes['tntclient'].version()
    file_path = os.path.dirname(os.path.abspath(__file__))

    version_file = os.path.abspath(os.path.join('..', '..', 'version.txt'))
    version_lines = []
    with open(version_file, 'r') as f:
        version_lines = f.readlines()

        for l in version_lines:
            if 'Version' in l:
                assert result == l.split(':')[1].strip()

    f.close()
