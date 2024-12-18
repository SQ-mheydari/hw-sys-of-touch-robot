"""
This Python file must be located at the root TPPT directory.
"""
import os

def get_script_root_directory():
    """
    :return: TPPT script root directory. Use this instead of relative path because
    scripts are usually executed by TnT UI which is located under different path.
    """
    return os.path.dirname(os.path.realpath(__file__))

def join_script_root_directory(ending):
    """
    Join script root directory with given ending.
    :param ending: Path ending appended to script root directory.
    :return: Joined path.
    """
    return os.path.join(get_script_root_directory(), ending)