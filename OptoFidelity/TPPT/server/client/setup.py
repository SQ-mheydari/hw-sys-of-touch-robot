from setuptools import setup
import os


def get_version_number():
    """ Returns TnT Server's version number string including Jenkins build number from version.txt exists.
    If version.txt doesn't exist, build number is set to 'x'.

    :return Version number.
    """

    # These are used when client is generated in development version.
    build_number = "0"
    version_number = "0.0.0"

    # Read build number from version.txt
    path = os.path.dirname(os.path.abspath(__file__))
    version_file_name = os.path.join(path, "..", "version.txt")

    # Get build version.
    if os.path.exists(version_file_name):
        with open(version_file_name, 'r') as file:
            # Read all "key: value" pairs into a dict
            version_info = dict(line.split(':', 1) for line in file)
            if 'Build' in version_info:
                build_number = version_info['Build'].strip()
            if 'Version' in version_info:
                version_number = version_info['Version'].strip()

    return version_number + "." + build_number


setup(name='tntclient',
      version=get_version_number(),
      description='TnT Server Client',
      packages=['tntclient'],
      url="www.optofidelity.com",
      author="Optofidelity",
      author_email="support@optofidelity.com",
      include_package_data=True,
      setup_requires=['wheel'],
      package_data={'tntclient': ['doc/*.pdf', 'examples/*.py']},
      install_requires=['requests'])
