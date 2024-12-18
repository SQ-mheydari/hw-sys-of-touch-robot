import os


def verify_attribute(obj, attr_name):
    value = getattr(obj, attr_name)
    if value is not None:
        value_new = getattr(obj, attr_name) + 3
    else:
        value_new = 5

    setattr(obj, attr_name, value_new)
    assert getattr(obj, attr_name) == value_new