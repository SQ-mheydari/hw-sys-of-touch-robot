py -3.7-64 -m venv venv && (
  echo Virtual environment created
) || (
  echo WARNING: Python Launcher doesn't support -X.Y-64 option, verify if it's really 64-bit environment
  py -3.7 -m venv venv
)
call venv\Scripts\activate.bat
python -m pip install --upgrade pip==21.2.4
python -m pip install -U pip setuptools wheel
pip install --extra-index-url https://artifactory.optofidelity.net/artifactory/api/pypi/legacy-pypi/simple --trusted-host artifactory.optofidelity.net -r requirements.txt
