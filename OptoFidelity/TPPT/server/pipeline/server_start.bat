SET PATH=%PATH:"=%
call venv\\Scripts\\activate.bat
set OF_LICENSE_PATH=installer\\licenses\\license_indefinite
python server_subprocess.py windows
findstr /c:"Server ready at port 8000" srv_output.txt
if %errorlevel% neq 0 exit /b %errorlevel%
