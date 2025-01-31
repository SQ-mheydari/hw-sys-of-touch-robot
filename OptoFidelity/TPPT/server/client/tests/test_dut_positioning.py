from tntclient.tnt_dut_positioning_client import TnTDUTPositioningClient
from tntclient.tnt_dut_client import TnTDUTClient
import pytest

@pytest.mark.skip(reason='start() fail, as simulation camera is used')
def test_all():
    # group testing all dut positioning methods, because many of them requiring start() running first

    simu_dut = 'simu_dut'
    simu_dut_client = TnTDUTClient(simu_dut)
    simu_dut_client.tl = {'x': 110, 'y': 309, 'z': -70}
    simu_dut_client.tr = {'x': 160, 'y': 309, 'z': -70}
    simu_dut_client.bl = {'x': 110, 'y': 409, 'z': -70}
    dut_positioning_name = 'dutpositioning'
    dut_positioning_client = TnTDUTPositioningClient(dut_positioning_name)

    dut_positioning_client.start(dut_name=simu_dut, camera_exposure=3,
                                            camera_gain=3, position_image_params=None,
                                            show_positioning_image=True)

    result = dut_positioning_client.dut_positioning_image(150, 215, 11)
    assert result is not None

    x, y, z = 50, 70, -30
    dut_positioning_client.add_robot_plane_point([x, y, z])

    result = dut_positioning_client.positioning_image_parameters(150, 215, 11)
    assert len(result) > 0

    result = dut_positioning_client.calculate()
    assert result is not None

    dut_positioning_client.center_to_blob_in_image(dut_name=simu_dut, camera_exposure=3, camera_gain=3)

    dut_positioning_client.clear_plane_points()

    dut_positioning_client.locate_next_blob()
