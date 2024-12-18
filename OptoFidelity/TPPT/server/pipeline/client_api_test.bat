SET PATH=%PATH:"=%
call venv\\Scripts\\activate.bat
set OF_LICENSE_PATH=%cd%\\installer\\licenses\\license_indefinite
python run_client_test.py windows