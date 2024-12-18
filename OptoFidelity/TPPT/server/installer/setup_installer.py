"""
Usage:

setup_installer.py setup_file conf_file [build_number]
"""

import sys
import importlib
import json
import struct
from subprocess import check_output
import os


def get_version(known_module):
    try:
        module = importlib.import_module(known_module)
        return module.__version__
    except ImportError:
        pass
    except AttributeError:
        pass

    print("Warning: could not determine version number.")

    return "0.0.0"

def git_commit():
    return check_output(["git", "-C", "..", "rev-parse", "HEAD"]).decode().strip()


def git_branch():
    branch = check_output(["git", "-C", "..", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()

    if branch == "HEAD":
        branch = check_output(["git", "-C", "..", "name-rev", "--name-only", "HEAD"]).decode().strip()

    return branch


def get_arg(index, default = None):
    if len(sys.argv) > index:
        return sys.argv[index]
    else:
        if callable(default):
            return default()
        else:
            return default


def get_platform():
    platform = "x"

    # Determine platform name that makes sense and is short enough for installer name.
    if sys.platform == "win32":
        platform = "win"
    elif sys.platform == "darwin":
        platform = "macos"
    elif sys.platform == "linux":
        platform = "linux"
    else:
        print("Warning: unknown platform {}.".format(sys.platform))

    return platform


def get_architecture():
    architecture = "x"

    if struct.calcsize('P') == 4:
        architecture = "x86"
    elif struct.calcsize('P') == 8:
        architecture = "amd64"
    else:
        print("Warning: unknown architecture.")

    return architecture


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    setup_file = get_arg(1)
    conf_file = get_arg(2)
    build_number = os.getenv("CI_JOB_ID")

    commit = git_commit()
    branch = os.getenv("CI_COMMIT_BRANCH")

    with open(conf_file, 'r') as f:
        conf = json.load(f)

    version = str(get_version(conf["version_module"]))

    architecture = get_architecture()
    platform = get_platform()

    with open("version.txt", 'w') as f:
        f.write("Build: " + build_number + "\n")
        f.write("Version: " + version + "\n")
        f.write("Commit: " + commit + "\n")
        f.write("Branch: " + branch + "\n")
        f.write("Platform: " + platform + "\n")
        f.write("Architecture: " + architecture + "\n")
        f.close()

    with open(setup_file, 'r') as f:
        setup = f.read()

    postfix = platform + "_" + architecture

    # For build from master, use proper version number. For build from other branches, use abbreviated commit hash.
    # For candidate builds the hash is usually more meaningful.
    if branch == "master":
        build_version = '{}.{}'.format(version, build_number)
    else:
        build_version = commit[:7]

    setup_name = '"{}_{}_{}_Setup"'.format(conf["app_name"].replace(" ", "_"), build_version, postfix)

    setup = setup.replace('app_name', '"{}"'.format(conf["app_name"]))
    setup = setup.replace('exe_name', '"{}.exe"'.format(conf["exe_name"]))
    setup = setup.replace('app_id', '"{}"'.format(conf["app_id"]))
    setup = setup.replace('version_string', '"{}"'.format(build_version,))
    setup = setup.replace('setup_name', setup_name)

    conf_dir_install = r"""Source: "dist\start\CONF_DIR\*"; DestDir: "{app}\CONF_DIR"; Permissions: everyone-full; Flags: confirmoverwrite recursesubdirs createallsubdirs"""
    root_dir_install = r"""Source: "dist\start\*"; Excludes: "CONF_DIRS,log"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs"""

    install_lines = []
    conf_dirs = conf["configuration_directories"]
    for conf_dir in conf_dirs:
        install_lines.append(conf_dir_install.replace("CONF_DIR", conf_dir))
    install_lines.append(root_dir_install.replace("CONF_DIRS", ",".join(conf_dirs)))

    setup = setup.replace("configuration_install_lines", "\n".join(install_lines))

    with open(setup_file.replace(".in", ""), 'w') as f:
        f.write(setup)