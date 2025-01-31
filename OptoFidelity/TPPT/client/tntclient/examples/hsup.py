"""
Examples for using Human Simulated User Performance (HSUP) Python API.
"""
from tntclient.tnt_hsup_client import TnTHsupP2IClient, TnTHsupSpaClient
from tntclient.tnt_client import TnTClient
import time


def hsup_analysis():
    """
    This example shows how to use analysis when it's stopped from the script after robot movement.
    """
    client = TnTClient()
    analysis = TnTHsupP2IClient()
    dut = client.dut("Dut1")

    analysis.start(settings_path=r"C:\p2i_config.yaml")

    dut.swipe(50, 10, 50, 100)

    results = analysis.get_results()

    print("Analysis results: {}".format(results))


def hsup_analysis_timeout():
    """
    This example shows how to use analysis when timeout is configured into YAML file
    and that stops the measurement.
    """

    analysis = TnTHsupSpaClient()

    analysis.start(settings_path=r"C:\spa_config.yaml")

    while True:
        status = analysis.get_status()

        print("Analysis status: {}".format(status))

        if status['status_analysis'] == 'stopped':
            break

        time.sleep(1)

    results = analysis.get_results()

    print("Analysis results: {}".format(results))
