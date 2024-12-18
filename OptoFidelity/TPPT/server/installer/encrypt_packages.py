from cwheel import compile_file, encrypt_file
import glob
import sys
import json

def encrypt_package(package_name):
    file_paths = glob.glob("dist/start/" + package_name + "/**", recursive=True)

    for file_path in file_paths:
        if not file_path.endswith(".pyc"):
            continue

        encrypt_file(file_path, hasp=True)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    conf_file = sys.argv[1]

    with open(conf_file, 'r') as f:
        conf = json.load(f)

    for package_name in conf['encrypted_packages']:
        encrypt_package(package_name)

