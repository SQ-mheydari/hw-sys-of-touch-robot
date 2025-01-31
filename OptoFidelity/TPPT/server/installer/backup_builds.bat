@echo off
setlocal enabledelayedexpansion

rem App is given in parameter 1
set app_dir="C:\OptoFidelity\"%1
set backup_dir="C:\OptoFidelity\Backups\"

rem Check if there is a previous installation.  If not skip back up.
if not exist %app_dir% (goto :eof)

rem Create backup directory if not exist
if not exist backup_dir%"\NUL"% (mkdir backup_dir)

rem Date is given in parameter 2
set date=%2

rem Construct the back up directory and remove unnecessary quotations.
set dir=!%backup_dir%%1 %2-!
set dir=!dir:"=%!

rem Loop through all folders in backup directory and count all that contain app name (param 1) in their name,
set /A count=0
for /d %%f in ("C:%dir%*") do (
  set name=%%f
  if not !x!name!:%1=%==x!name!! (
        set /A count=!count!+1
    )
)

rem Finally copy existing installation to backup folder.
set newname="%dir%!count!"
mkdir !newname!
xcopy %app_dir% !newname! /E /y

rem Delete old installation
rmdir /s %app_dir% /q

rem sleep for a moment so that deleting the folder has time to finish before continuing.
timeout 2