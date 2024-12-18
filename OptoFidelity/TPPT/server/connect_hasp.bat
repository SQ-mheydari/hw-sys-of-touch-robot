@ECHO OFF
SET /A "index = 1"
SET /A "retries = 10"
:while
Rem 3 in the following command is a hard coded HASP port in dongle server
"C:\Program Files\SEH Computertechnik GmbH\SEH UTN Manager\utnm.exe" /c "activate 10.118.240.211 4"
if %index% leq %retries% (
    SET /A "index = index + 1"
    if %ERRORLEVEL% == 25 (
        echo HASP already activated, waiting 30s...
        ping localhost -n 2 > nul
        goto :while
    )
    if %ERRORLEVEL% == 29 (
        echo No USB device with given vendor id and device id found
        ping localhost -n 11 > nul
        goto :while
    )
    if %ERRORLEVEL% == 0 (
        echo HASP connected
        goto :return
    )
    goto :while
    
)
:return
