
SET PATH="C:\\Program Files\\MVTec\\HALCON-13.0\\bin\\x64-win64";%PATH%
SET PATH=%PATH:"=%
call venv\\Scripts\\activate.bat

SET PYTHONPATH=%cd%

python create_tntserver_json.py
cd installer

python package_parser.py

python setup_installer.py setup-generic.in.iss ..\\tntserver.json %BUILD_NUMBER%
python -m PyInstaller --clean -y tnt-generic.spec ..\\tntserver.json
python encrypt_packages.py ..\\tntserver.json

iscc setup-generic.iss
cd ..