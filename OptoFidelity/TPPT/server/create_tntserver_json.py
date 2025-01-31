import json
import os
import ruamel.yaml
import sys

"""
Installer cannot automatically find all files
Installer needs tntserver.json to tell missing files
This script creates the tntserver.json automatically
This script should be run in installer directory to get paths right
    (or any path one level higher than root)
"""



def recursive_dir(path, files = []):
    filenames = os.listdir(os.path.relpath(path))
    for filename in filenames:
        if filename.startswith("__") or filename.startswith("."):
            continue

        f = "{}/{}".format(path, filename)

        files.append(f)

        if os.path.isdir(os.path.relpath(f)):
            recursive_dir(f, files)

    return files




if __name__ == '__main__':

    print("running Create_tntserver_json.py")
    print("at path ", os.getcwd())

    current_path = os.getcwd()
    if not current_path.endswith("installer"):
        os.chdir("installer")

    # the output file
    outfile = os.path.relpath('../tntserver.json')

    # first constant defaults:

    j = {
        "encrypted_packages":
            [
            "tntserver",
            "yasler",
            "hsup",
            "toolbox",
            "optomotion",
            "optovision",
            "optocamera"
            ],

        "hiddenimports":
            [
            "scipy.linalg",
            "scipy.integrate",
            "scipy.special",
            "scipy.special._ufuncs",
            "numpy.core",
            "colorlog",
            "tkinter",
            "serial",
            "tntserver.loggingfilters"
            ],

        "add_dlls": [
            {
                "module": "optomotion",
            },
            {
                "module": "tntserver.drivers.sensors"
            }
        ],
        "entry": "../main.py",
        "datas": [
            [
                "version.txt",
                "."
            ],
            [
                "../CHANGELOG.md",
                "."
            ],
            [
                "../configuration/start.yaml",
                "configuration"
            ],
            [
                "../configuration/logging.yaml",
                "configuration"
            ],
            [
                "../tntserver/drivers/cameras/ximea/windows/libs/x32/*",
                "."
            ],
            [
                "../tntserver/drivers/cameras/ximea/windows/libs/x64/*",
                "."
            ],
            [
                "../client/",
                "client"
            ],
            [
                "../tntserver/client_generator/data/",
                "tntserver/client_generator/data"
            ],
            [
                "../data/image_filters/",
                "data/image_filters"
            ],
            [
                "../generate_client.bat",
                "."
            ],
            [
                "../venv/Lib/site-packages/matplotlib/mpl-data/",
                "matplotlib/mpl-data"
            ],
        ],
        "exe_name": "TnT Server",
        "app_name": "TnT Server",
        "app_id": "1D759111-E177-4D96-8B8F-95C1913B9E9B",
        "version_module": "tntserver",
        "configuration_directories": [
            "configuration"
        ]
        }

    try:
        import yasler

        j["datas"].append([os.path.join(os.path.dirname(yasler.__file__), "pylon"), os.path.join("yasler", "pylon")])
    except ImportError:
        pass

    j['hidden_files'] = []

    files = recursive_dir("../tntserver", [])
    files = [f.replace('/', '.')[3:-3] for f in files if f.endswith('.py')]
    j['hiddenimports'] += files

    # Add simulator framework data. Don't add model files.
    datas = []
    datas += recursive_dir("../tntserver/web/img", [])
    datas += recursive_dir("../tntserver/web/js", [])
    datas += ["../tntserver/web/simu.html"]

    # might be in windows world but still the paths must be unix-style for the install to work
    d = [[os.path.relpath(p).replace('\\', '/'), os.path.dirname(p).replace('\\', '/').strip('../')] for p in datas]

    j['datas'] += d

    p = json.dumps(j, sort_keys=True, indent=4, separators=(',', ': '))

    file = open(outfile, 'w')
    file.write(p)
    file.close()
