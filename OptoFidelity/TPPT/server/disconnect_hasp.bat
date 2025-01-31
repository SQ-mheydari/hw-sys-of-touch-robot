@ECHO OFF
SET /A "index = 1"
SET /A "retries = 3"
:while
Rem 3 in the following command is a hard coded HASP port in dongle server
"C:\Program Files\SEH Computertechnik GmbH\SEH UTN Manager\utnm.exe" /c "deactivate 10.118.240.211 4"
if %index% leq %retries% (
    SET /A "index = index + 1"
    if %ERRORLEVEL% == 24 (
        echo HASP already deactivated
        ping localhost -n 3 > nul
        goto :return
    )
    if %ERRORLEVEL% == 29 (
        echo No USB device with given vendor id and device id found
        ping localhost -n 3 > nul
        goto :while
    )
    if %ERRORLEVEL% == 21 (
        echo Deactivation failed for unknown reason
        ping localhost -n 3 > nul
        goto :while
    )
    if %ERRORLEVEL% == 0 (
        echo HASP disconnected
        goto :return
    )
    goto :while
    
)
:return
