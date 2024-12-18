:: STAGE ---------- Prepare environment ----------
echo Stage: Preparing build environment.

echo Python version
python --version

echo Python bitness
FOR /F "tokens=* USEBACKQ" %%F IN (`python -c "import struct;print( 8 * struct.calcsize('P'))"`) DO (
SET BITNESS=%%F
)
ECHO %BITNESS%

:: TODO: This is currently set for installer because venv is not working in cloud machine for some reason.
SET VIRTUAL_ENV=c:\Python3

:: Need to use pip version 18 as newer version lead to an error when installing Pyinstaller on build slave.
python -m pip install --upgrade pip==18

echo Pip version
pip --version

cd installer
pip --default-timeout=1000 --retries=10 install --extra-index-url https://common:b3atsab3rany0n3@pypi-azure.optofidelity.net/common/oldpypi -r requirements.txt
cd ..
pip --default-timeout=1000 --retries=10 install --extra-index-url https://common:b3atsab3rany0n3@pypi-azure.optofidelity.net/common/oldpypi -r requirements.txt

python customize_project.py --configuration-file="simulation_3axis.yaml"


:: STAGE ---------- Unit tests ----------
echo Stage: Running unit tests.

pytest -Wdefault --ignore=test_scripts
@IF NOT %ERRORLEVEL% == 0 EXIT /b %ERRORLEVEL%


:: STAGE ---------- Create installer ----------
echo Stage: Creating installer.

python create_tntserver_json.py

SET PYTHONPATH=%cd%
cd installer
python package_parser.py
@IF NOT %ERRORLEVEL% == 0 EXIT /b %ERRORLEVEL%

:: Use project number 0 and project version 0 for platform.
python setup_installer.py setup-generic.in.iss ..\tntserver.json %MASTER_BUILD_NUMBER%
python -m PyInstaller --clean -y tnt-generic.spec ..\tntserver.json

:: Encrypt python files. TODO: HASP connection may sometimes fail. Make more robust.
call ..\connect_hasp.bat
ping 127.0.0.1 -n 11 > nul
python encrypt_packages.py ..\tntserver.json
@IF NOT %ERRORLEVEL% == 0 EXIT /b %ERRORLEVEL%
call ..\disconnect_hasp.bat
ping 127.0.0.1 -n 6 > nul

"C:\Program Files (x86)\Inno Setup 6\iscc.exe" setup-generic.iss
cd ..


:: STAGE ---------- Test installer ----------
echo Stage: Testing installer.

for /r %%x in (installer\\Output\\*.exe) do set INSTALLER="%%x"

%INSTALLER% /VERYSILENT /LOG=%BITNESS%bit_install.log /DIR=installation


:: Stage ---------- Test license key ----------
echo Stage: Testing license key.

set OF_LICENSE_PATH=%cd%\\installer\\licenses\\license_expired
installation\\"TnT Server.exe" > output.txt

:: Make sure that the application is unable to run the code. findstr returns error code that makes build fail.
findstr "bad marshal data" output.txt
@IF NOT %ERRORLEVEL% == 0 EXIT /b %ERRORLEVEL%


:: STAGE ---------- Test uninstaller ----------
echo Stage: Testing uninstaller.

"installation\\unins000.exe" /VERYSILENT
@IF NOT %ERRORLEVEL% == 0 EXIT /b %ERRORLEVEL%


:: STAGE ---------- TnT Client ----------
echo Stage: Building TnT Client.

python main.py --generate-client=configuration/client_config.yaml
@IF NOT %ERRORLEVEL% == 0 EXIT /b %ERRORLEVEL%
copy installer\\version.txt .
cd client
python setup.py sdist bdist_wheel
@IF NOT %ERRORLEVEL% == 0 EXIT /b %ERRORLEVEL%
cd ..


:: STAGE ---------- Test Server start ----------
::echo Stage: Testing server start.

::set OF_LICENSE_PATH=%cd%\\installer\\licenses\\license_indefinite

::call connect_hasp.bat
::ping 127.0.0.1 -n 6 > nul

:: start tnt server in subprocess with timeout
:: TODO: Would be better to run the installed version before uninstaller stage.
:: TODO: It seems that server start takes a long time and the timeout in server_subprocess.py is not enough.
:: TODO: Server can't start with the default config unless Halcon and possibly ABBYY are installed to the system.

::python server_subprocess.py windows

:: check from server log, if server starts without error

::findstr /c:"Server ready at port 8000" srv_output.txt
::@IF NOT %ERRORLEVEL% == 0 EXIT /b %ERRORLEVEL%

:: Disconnect HASP.
::call disconnect_hasp.bat
::ping 127.0.0.1 -n 6 > nul
