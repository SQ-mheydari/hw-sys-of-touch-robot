"""
Functionality for parsing metadata such as license type of packages contained in Python virtual environment.
"""
import os


def parse_metadata(metadata):
    """
    Parse relevant metadata from string to a dict.
    :param metadata: Metadata string.
    :return: Metadata as dict.
    """
    result = {}

    license = ""

    for line in metadata.splitlines():
        if "License" in line or "Name" in line or "Home-page" in line:
            try:
                name, value = line.split(": ", 2)
                result[name] = value
            except ValueError:
                pass  # Did not find correctly formatted line

        # License information can be stored as classifier.
        if "Classifier: License" in line:
            try:
                splits = line.split("::")

                if len(license) == 0:
                    license = splits[-1].strip()
                else:
                    license += ", " + splits[-1].strip()
            except ValueError:
                pass  # Did not find correctly formatted line

    if ("License" not in result or result["License"] == "" or result["License"] == "UNKNOWN" or
            result["License"] == "Dual License") and len(license) > 0:
        result["License"] = license

    return result


def get_venv_package_metadata(venv_dir):
    """
    Get metadata of packages in given virtual environment.
    :param venv_dir: Virtual environment directory.
    :return: Metadata as list of dicts.
    """
    metadata = []

    package_dir = os.path.join(venv_dir, "Lib", "site-packages")

    for file in os.listdir(package_dir):
        file_path = os.path.join(package_dir, file)

        if os.path.isdir(file_path) and file.endswith("dist-info"):
            print("Inspecting metadata: " + file_path)

            with open(os.path.join(file_path, "METADATA"), "r", encoding="utf-8") as f:
                file_content = f.read()
                metadata.append(parse_metadata(file_content))


    return metadata


def save_package_metadata(metadata, filename):
    """
    Save metadata to file.
    :param metadata: Metadata as list of dicts.
    :param filename: Name of file to save.
    """
    def write_package(package, file):
        print("Name: " + package.get("Name", ""), file=file)
        print("License: " + package.get("License", ""), file=file)
        print("Home-page: " + package.get("Home-page", ""), file=file)
        print("", file=file)

    with open(filename, "w") as f:
        for m in metadata:
            write_package(m, f)


def create_third_party_package_list(venv_path, filename):
    """
    Create a file that contains third-party packages with license info.
    Optofidelity propietary packages are removed and incorrect licenses are patched.
    :param venv_path: Path to virtual environment.
    :param filename: Name of file to write.
    """
    # Ignore OF proprietary packages in third party package list.
    ignore_packages = [
        "hsup",
        "pybasler",
        "pyfre",
        "pyhalcon",
        "rocktomotion",
        "optomotion",
        "toolbox",
        "socket-logger",
        "yasler",
        "baslerapi",
        "cwheel",
        "cwheel-hook",
        "optovision",
        "optofidelity-camera",
        "optofidelity-camera-allied",
        "optofidelity-camera-basler",
        "optofidelity-camera-hikvision",
        "pyinstaller",  # This is part of venv during installation but is not redistributed.
        "PyInstaller"
    ]

    # Allowed license types
    allowed_licenses = {
        "BSD",
        "BSD License",
        "MIT",
        "MIT License",
        "MIT license",
        "PSF",
        "Standard PIL License",
        "Apache 2.0",
        "Apache",
        "Apache Software License",
        "BSD or Apache License, Version 2.0",
        "BSD License, Apache Software License",
        "LGPLv3+",
        "Python Software Foundation License",
        "HPND",  # PIL license similar to MIT.
        "BSD-2-Clause"
    }

    metadata = get_venv_package_metadata(venv_path)

    # Remove ignored packages.
    metadata = [m for m in metadata if m["Name"] not in ignore_packages]

    # Add Simplemotion that is contained in rocktomotion in source form.
    metadata.append({"Name": "SimpleMotionV2", "License": "Apache 2.0", "Home-page": "https://github.com/GraniteDevices/SimpleMotionV2"})

    for m in metadata:
        # Incorrectly shows UNKNONW license although seems to be MIT.
        if m["Name"] == "PyAudio" and m["License"] == "UNKNOWN":
            m["License"] = "MIT"

        # PyMySQL has unconventional formatting.
        if m["Name"] == "PyMySQL" and m["License"] == '"MIT"':
            m["License"] = "MIT"

        # Tornado has license link instead of license name.
        if m["Name"] == "tornado" and m["License"] == "http://www.apache.org/licenses/LICENSE-2.0":
            m["License"] = "Apache 2.0"

            # Incorrectly shows UNKNONW license although seems to be MIT.
        if m["Name"] == "pefile" and m["License"] == "UNKNOWN":
            m["License"] = "MIT"

        # Screeninfo has no license info in the metadata but github site has MIT.
        if m["Name"] == "screeninfo" and m["License"] == "UNKNOWN":
            m["License"] = "MIT"

        # Pypylon seems to actually be 3-clause BSD.
        if m["Name"] == "pypylon" and m["License"] == "Other/Proprietary License":
            m["License"] = "BSD"

        #pyinstaller-hooks-contrib uses Apache 2.0
        if m["Name"] == "pyinstaller-hooks-contrib" and m["License"] == "UNKNOWN":
            m["License"] = "Apache 2.0"

    # If there is a license that is not recognized, exit with error code to make possible build fail.
    for m in metadata:
        if m["License"] not in allowed_licenses:
            print("ERROR: Package {} has unsupported license {}!".format(m["Name"], m["License"]))
            exit(-1)

    # Save third party package details to keep track of licenses.
    save_package_metadata(metadata, filename)


if __name__ == '__main__':
    create_third_party_package_list(os.environ['VIRTUAL_ENV'], os.path.join("..", "third_party_packages.txt"))