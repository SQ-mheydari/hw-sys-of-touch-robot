from tntserver.drivers.robots.goldenmov.mbmemory import *
import numpy as np
import pytest


def test_mbmemory_read_write():
    """
    Test basic read and write using MotherboardMemorySimulator.
    """
    mbmem = MotherboardMemorySimulator(None, motherboard_address="IO7")

    # This is not necessary for simulator but test that it is successful.
    mbmem.set_address()

    data = bytearray([1, 2, 3, 4, 5])

    mbmem.write_memory(0, data)

    # Read entire buffer.
    result = mbmem.read_memory(0, 5)
    assert np.allclose(result, data)

    # Read partial buffer.
    result = mbmem.read_memory(2, 3)
    assert np.allclose(result, data[2:])


def test_mbmemory_write_entire_buffer():
    """
    Test writing entire buffer using MotherboardMemorySimulator.
    """
    mbmem = MotherboardMemorySimulator(None, motherboard_address="IO7")

    # Check that maximum buffer size can be written.
    data = bytearray([0] * MotherboardMemoryBase.MEM_MAX_SIZE)
    mbmem.write_memory(0, data)

    # Check that we get exception if maximum size is exceeded.
    with pytest.raises(Exception):
        data = bytearray([0] * (MotherboardMemoryBase.MEM_MAX_SIZE + 1))
        mbmem.write_memory(0, data)


def test_mbmemory_erase():
    """
    Test erasing memory using MotherboardMemorySimulator.
    """
    mbmem = MotherboardMemorySimulator(None, motherboard_address="IO7")

    size = MotherboardMemoryBase.MEM_MAX_SIZE
    mbmem.erase_memory(42, 0, size)

    result = mbmem.read_memory(0, size)
    assert np.allclose(result, [42] * size)


def test_mbmemory_dict():
    """
    Test writing and reading dict with varying memory offsets using MotherboardMemorySimulator.
    """
    d = {
        "name": "opto",
        "age": 34,
        "height": 179.47038,
        "values": ["ok", "go boldly"]
    }

    mbmem = MotherboardMemorySimulator(None, motherboard_address="IO7")

    # Use different offsets to write and read dict.
    for offset in [0, 2, 5]:
        mbmem.write_dict(offset, d)

        result = mbmem.read_dict(offset)
        print(result)

        assert result["name"] == "opto"
        assert result["age"] == 34
        assert result["height"] == 179.47038
        assert result["values"][0] == "ok"
        assert result["values"][1] == "go boldly"
