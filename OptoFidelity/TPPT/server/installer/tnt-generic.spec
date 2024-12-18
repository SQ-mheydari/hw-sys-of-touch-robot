# -*- mode: python -*-

import os
import sys
import json
import importlib

# This is generic spec
install_data_file = sys.argv[-1]
with open(install_data_file, 'r') as fp:
    install_data = json.load(fp)

hiddenimports = install_data["hiddenimports"]

# Add cwheel_hook to hiddenimports to enable pyc file decryption at run time.
hiddenimports.append("cwheel_hook")

block_cipher = None

dlls = []

for i in os.listdir('bin'):
    if "140" in i:
        dlls.append(('bin/%s' % i, '.'))

def add_dlls(module_name, sub_directory=''):
    module = importlib.import_module(module_name)
    module_dir = os.path.dirname(module.__file__)

    found = False
    for i in os.listdir(module_dir + sub_directory):
        if i.endswith(".dll"):
            dlls.append(('%s%s/%s' % (module_dir, sub_directory, i), '.'))
            found = True
    if not found:
        raise Exception("Could not find drivers from {}".format(module_name))


for dll_info in install_data["add_dlls"]:
    add_dlls(dll_info["module"], dll_info.get("subdir", ""))

a = Analysis([install_data["entry"]],
             pathex=[''],
             binaries=dlls,
             datas=install_data["datas"],
             hiddenimports=hiddenimports,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=True)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name=install_data["exe_name"],
          debug=False,
          strip=False,
          upx=True,
          console=True,
          icon='server_icon.ico')

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='start')
