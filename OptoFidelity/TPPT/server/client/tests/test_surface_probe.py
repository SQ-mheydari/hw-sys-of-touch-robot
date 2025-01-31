from tntclient.tnt_surface_probe_client import TnTSurfaceProbeClient
from tntclient.tnt_dut_client import TnTDUTClient
import pytest


@pytest.mark.skip(reason='fail, not working with simulations for robot, dut, camera')
def test_probe_z_surface():
    surface_probe_name = 'surfaceprobe'
    surface_probe_client = TnTSurfaceProbeClient(surface_probe_name)
    dut_name = 'dut1'
    dut_client = TnTDUTClient(dut_name)
    dut_client.move(dut_client.width /2, dut_client.height/2, 1)
    result = surface_probe_client.probe_z_surface()

