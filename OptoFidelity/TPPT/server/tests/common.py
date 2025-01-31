import json
import numpy as np


class ProgramArguments:
    def __init__(self):
        self.visual_simulation = False

def from_jsonout(jsonout_input):
    """
    Changes @json_out formatted input back to python form
    NOTE: might not handle for example None well
    :param input: @json_out formatted tuple
    :param jsonout_input: @json_out formatted tuple
    :return: the python form of the binary part
    """
    return json.loads(jsonout_input[1].decode('utf-8'))

def compare_axes(axes1, axes2):
    """
    Compare to axes dictionaries to make sure they match exactly.
    Errors are reported via assert.
    :param axes1: Axes dict e.g. {"x": [0, 1, 2], "y": [0, 0, 0]}.
    :param axes2: Axes dict e.g. {"x": [0, 1, 2], "y": [0, 0, 0]}.
    """
    keys1 = axes1.keys()
    keys2 = axes2.keys()

    assert len(keys1) == len(keys2)

    for key in keys1:
        assert key in keys2

        values1 = axes1[key]
        values2 = axes2[key]

        assert len(values1) == len(values2)

        for i in range(len(values1)):
            # Allow small deviations due to round-off errors.
            # Code refactoring can alter round-offs which should be acceptable.
            assert np.allclose(values1, values2, atol=1e-6)

