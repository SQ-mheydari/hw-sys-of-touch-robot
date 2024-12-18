In Pyinstaller 3.4 there is a bug in

PyInstaller/utils/misc.py

that results in errors when building packages that have namespaces (some standard packages have these).

Replace

venv/Lib/site-packages/PyInstaller/utils/misc.py

by the provided misc.py file.
