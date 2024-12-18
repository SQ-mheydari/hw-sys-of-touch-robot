from tntclient.tnt_client import TnTClient
from tntclient.tnt_icon_client import TnTIconClient
import pytest
import os
from shutil import copyfile


def init():
    icon_name = 'star_blue'
    tntclient = TnTClient()
    icon_client = TnTIconClient(icon_name)
    tntclient.add_icon(icon_name)
    # check if icon png file does exist under data/icon/, because test remove() would delete icon file
    # if not exist, copy it from a backup file, test png() needs this file. This makes each test independent.
    icon_folder = os.path.abspath(os.path.join('data', 'icons'))
    icon_file = os.path.abspath(os.path.join(icon_folder, icon_name + '.png'))
    # this is the folder where all icon images are stored, client API tests would not delete any file from this folder
    # it is (project root)/tests/images/
    icon_src = os.path.abspath(os.path.join('..', '..', '..', '..', '..','tests', 'images', icon_name + '.png'))
    if not os.path.exists(icon_file):
        copyfile(icon_src, icon_file)

    return icon_name, tntclient, icon_client


@pytest.mark.skip(reason='No way to set icons folder to different location from client')
def test_remove():
    icon_name, tntclient, icon_client = init()
    tntclient.add_icon(icon_name)
    assert icon_client is not None
    result = icon_client.remove()
    assert result['status'].lower() == 'ok'


@pytest.mark.skip(reason='No way to set icons folder to different location from client')
def test_convert_png():
    icon_name, tntclient, icon_client = init()

    # only test png()
    # skip convert(), because it needs halcon which doesn't work in macOS
    # icon_file = os.path.abspath(os.path.join('..', '..', 'data', 'icons', 'star_blue.png'))
    # with open(icon_file, "rb") as file:
    #     data = file.read()
    # icon_client.convert(data)

    result = icon_client.png()
    assert result is not None
    assert isinstance(result, bytes)
