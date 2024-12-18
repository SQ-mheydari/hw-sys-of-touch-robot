from tntclient.tnt_audio_analyzer_client import TnTAudioAnalyzerClient
import os


def init_audio_analyzer():
    # this has been already defined in server config file
    audio_analyzer_name = 'audio_analyzer'
    audio_analyzer_client = TnTAudioAnalyzerClient(audio_analyzer_name)
    return audio_analyzer_client


def test_find_frequency_peaks():
    audio_analyzer_client = init_audio_analyzer()
    file_path = os.path.dirname(os.path.abspath(__file__))
    wav_file = os.path.abspath(os.path.join(file_path, 'data', 'test.wav'))

    with open(wav_file, 'rb') as f:
        value = f.read()
    result = audio_analyzer_client.find_frequency_peaks(value)
    assert len(result) > 0
