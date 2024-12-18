@echo off
setlocal enabledelayedexpansion

set app_dir=C:\OptoFidelity\TnT Server\

rem Check that python exist in register.
set pythontest="C:\Windows\py.exe" --version
!pythontest!

if errorlevel == 1 (

    rem If python is not installed show popup to notify user.
    msg * /self /w "Python is not installed. Please generate client manually.") else (

    rem First start the server to generate the client.
    set server=TnT Server.exe
    set param=--generate-client=
    set execommand="!server!" !param!\configuration\client_config.yaml
    !execommand!

    rem Find pip location and install wheel in case it doesn't exist
    for /f "delims=" %%r in ('C:\Windows\py.exe -c "import os, sys; print(os.path.dirname(sys.executable))"') do (set path=%%r)
    set wheel_install="!path!\Scripts\pip.exe" install wheel
    !wheel_install!

    rem Move to client folder and create wheel.
    pushd !app_dir!client
    set setup="C:\Windows\py.exe" setup.py sdist bdist_wheel
    !setup!
    popd

    rem Move to client\dist folder and install the latest wheel in there.
    pushd !app_dir!client\dist
    for /f %%f in ('dir *.whl /b /od') do (SET latest=%%f)
    set wheel="C:\Windows\py.exe"  -m pip install !latest!
    !wheel!
    popd
    )