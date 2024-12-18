SET PATH=%PATH:"=%

python -m venv venv
@IF NOT %ERRORLEVEL% == 0 EXIT /b %ERRORLEVEL%
call venv\\Scripts\\activate.bat
python -m pip install --upgrade pip==21.2.4
python -m pip cache purge


cd installer
pip install --extra-index-url https://artifactory.optofidelity.net/artifactory/api/pypi/legacy-pypi/simple -r requirements.txt
cd ..

pip install --extra-index-url https://artifactory.optofidelity.net/artifactory/api/pypi/legacy-pypi/simple -r requirements.txt

python customize_project.py --configuration-file="simulation_3axis.yaml"

SET PATH=%PATH:"=%
call venv\\Scripts\\activate.bat
