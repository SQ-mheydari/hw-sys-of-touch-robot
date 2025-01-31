from tntclient.tnt_motherboard_client import TnTMotherboardClient
import pytest

def init_motherboard():
    # this has been already defined in server config file
    mother_board_name = 'Motherboard1'
    mother_board_client = TnTMotherboardClient(mother_board_name)
    motherboard_parameter_name = "light1"
    return motherboard_parameter_name, mother_board_client

@pytest.mark.skip(reason='fail, TOUCH5705-')
def test_set_output_state():
    motherboard_parameter_name, mother_board_client = init_motherboard()
    result = mother_board_client.set_output_state(name_or_number=motherboard_parameter_name, state=1)
    assert result['status'].lower() == 'ok'
