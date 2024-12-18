from tntclient.tnt_speaker_client import TnTSpeakerClient
import os
import sys
import pytest


# Speaker tests not working with Python 3.7 on macos build machine.
if not sys.platform.startswith("win"):
    pytest.skip("skipping windows-only tests", allow_module_level=True)


def init_speaker():
    speaker_name = 'speaker1'
    speaker_client = TnTSpeakerClient(speaker_name)
    return speaker_name, speaker_client


def test_chunk_size():
    speaker_name, speaker_client = init_speaker()
    size = speaker_client.chunk_size
    size_new = size + 1024
    speaker_client.chunk_size = size_new
    result = speaker_client.chunk_size
    assert result == size_new


@pytest.mark.skip(reason='fail in jenkins. Do not know if jenkins machine has speaker or not')
def test_device_name():
    speaker_name, speaker_client = init_speaker()
    device_name = speaker_client.device_name
    assert device_name is not None
    device_name_new = 'Built-in Output'
    speaker_client.device_name = device_name_new
    result = speaker_client.device_name
    assert result == device_name_new

    # set original name back, otherwise play wav file would fail
    speaker_client.device_name = device_name


def test_list_playback_devices():
    speaker_name, speaker_client = init_speaker()
    result = speaker_client.list_playback_devices()
    assert result is not None


@pytest.mark.skip(reason='fail in jenkins. Do not know if jenkins machine has speaker or not, and what device name is')
def test_play_wav_file():
    speaker_name, speaker_client = init_speaker()
    file_path = os.path.dirname(os.path.abspath(__file__))
    wav_file = os.path.abspath(os.path.join(file_path, 'data', 'test.wav'))

    result = speaker_client.play_wav_file(wav_file)
    assert result == 'ok'
