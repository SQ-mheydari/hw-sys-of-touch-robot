@echo off
setlocal enabledelayedexpansion

rem App is given in parameter 1
set app=%1
set unquoted_app=%app:"=%
set app_dir=C:\OptoFidelity\%unquoted_app%
set backup_dir=C:\OptoFidelity\Backups\
set config_folder=\configuration
set data_folder=\data

rem Find the most recent backup.
for /f "delims=" %%a in ('dir %backup_dir%%app%* /ad-h /b /od') do (set recent=%%a)

rem Copy configs from newest backup to the current installation.
rem The variables with "bu" inform about the config location in backup folder and the variables with "new"
rem tell the location in the newly installed server folder.
set buconfigfolder=!backup_dir!!recent!!config_folder!
set newconfigfolder=!app_dir!!config_folder!
robocopy "!buconfigfolder!" "!newconfigfolder!" /e

rem In server also copy the contents of the data folder.
if not %app% == "TnT UI" (
    set budatafolder=!backup_dir!!recent!!data_folder!
    set newdatafolder=!app_dir!!data_folder!
    robocopy "!budatafolder!" "!newdatafolder!" /e
)
