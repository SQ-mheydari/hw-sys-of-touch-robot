from tntclient.tnt_tip_client import TnTTipClient
from tntclient.tnt_client import TnTClient
import pytest
from toolbox import robotmath


def init_nodes():
    tip_name = 'tip1'
    tip_client = TnTTipClient(tip_name)
    tntclient = TnTClient()
    return tip_name, tip_client, tntclient


def define_tip():
    """
    All these (need to connect to server) now are put into the method. Otherwise, jenkins would try to connect to server
    during loading test cases before server starts.
    Returns: none
    -------

    """
    tip_name, tip_client, tntclient = init_nodes()
    tips = tntclient.tips()

    if tips is not None:
        if len(tips) > 0:
            tip_names = [tip.name for tip in tips]
            if tip_name not in tip_names:
                tntclient.add_tip(tip_name)
    else:
        tntclient.add_tip(tip_name)


def verify_attribute(obj, attr_name):
    define_tip()
    value = getattr(obj, attr_name)
    if value is not None:
        value_new = getattr(obj, attr_name) + 3
    else:
        value_new = 5

    setattr(obj, attr_name, value_new)
    assert getattr(obj, attr_name) == value_new


def test_attributes():
    tip_name, tip_client, tntclient = init_nodes()
    define_tip()
    attributes = ('diameter', 'first_finger_offset', 'length', 'num_tips', 'separation', 'tip_distance',
                  'model', 'slot_in', 'slot_out', 'is_multifinger')
    models = ("Standard", "Multifinger")
    slot_list = [[1.0, 0.0, 0.0, 62.151], [0.0, 1.0, 0.0, 322.536], [-0.0, 0.0, 1.0, -81.001], [0.0, 0.0, 0.0, 1.0]]
    for a in attributes:
        if a == 'model':
            m = tip_client.model
            index = models.index(m)
            m_new = models[abs(index - 1)]
            tip_client.model = m_new
            assert tip_client.model == m_new
        elif a == 'slot_in' or a == 'slot_out':
            slot = getattr(tip_client, a)
            if slot is not None:
                slot_new = robotmath.xyz_to_frame(slot[0][3], slot[1][3], slot[2][3]).tolist()
            else:
                slot_new = slot_list

            setattr(tip_client, a, slot_new)
            result = getattr(tip_client, a)
            for i in range(len(result)):
                assert result[i] == pytest.approx(slot_new[i])

        elif a == 'is_multifinger':
            result = tip_client.is_multifinger
            assert isinstance(result, bool)
        else:
            verify_attribute(tip_client, a)


def test_remove():
    tip_name, tip_client, tntclient = init_nodes()
    define_tip()
    result = tip_client.remove()
    assert result['status'] == 'ok'
    assert tip_name not in tntclient.tips()
