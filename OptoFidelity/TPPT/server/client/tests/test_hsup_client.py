from tntclient.tnt_hsup_client import *
import os
import pytest


def init():
    watchdog_client = TnTHsupWatchdogClient()
    spa_client = TnTHsupSpaClient()
    P2I_client = TnTHsupP2IClient()
    file_path = os.path.dirname(os.path.abspath(__file__))
    settings_path = os.path.abspath(os.path.join(file_path, 'data', 'watchdog.yaml'))
    return watchdog_client, spa_client, P2I_client, settings_path

@pytest.mark.skip(reason='hsup start() not working with simulated camera, dut')
def test_watchdog():
    watchdog_client, spa_client, P2I_client, settings_path = init()
    watchdog_client.start(settings_path=settings_path)
    result = watchdog_client.get_status()
    assert len(result) > 0
    result = watchdog_client.get_results(timeout=3)
    assert len(result) > 0


@pytest.mark.skip(reason='hsup start() not working with simulated camera, dut')
def test_spa():
    watchdog_client, spa_client, P2I_client, settings_path = init()
    spa_client.start(settings_path=settings_path)
    result = spa_client.get_status()
    assert len(result) > 0
    result = spa_client.get_results(timeout=3)
    assert len(result) > 0

@pytest.mark.skip(reason='hsup start() not working with simulated camera, dut')
def test_P2I():
    watchdog_client, spa_client, P2I_client, settings_path = init()
    P2I_client.start(settings_path=settings_path)
    result = P2I_client.get_status()
    assert len(result) > 0
    result = P2I_client.get_results(timeout=3)
    assert len(result) > 0
