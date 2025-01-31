import logging
log = logging.getLogger(__name__)


class LicenseError(Exception):
    pass


def check_license_feature(feature_name: str):
    """
    Check that the currently active license has given feature.
    This is intended to have an effect in the built version where cwheel_hook is installed.
    :param feature_name: Name of feature to check.
    :return: True if feature is enabled, otherwise False.
    """
    try:
        # In build version cwheel_hook is installed so that this import will succeed.
        # If for some reason cwheel_hook would not be bundled with build, the decryption would fail before this stage.
        import cwheel_hook
    except ImportError:
        # In development version, cwheel_hook is not present but all features must be enabled.
        return True

    return cwheel_hook.check_feature(feature_name)
