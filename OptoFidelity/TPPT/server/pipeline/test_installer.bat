for /r %%x in (installer\\Output\\*.exe) do set INSTALLER="%%x" %INSTALLER% /VERYSILENT /LOG=install.log /DIR=installation
timeout /t 15 /nobreak
set OF_LICENSE_PATH=installer/licenses/license_expired
installation\\"TnT Server.exe" > output.txt

findstr "bad marshal data" output.txt

"installation\\unins000.exe" /VERYSILENT
