py -3.7-32 -m venv venv
call venv\Scripts\activate.bat
python -m pip install --upgrade pip==21.2.4
python -m pip install -U pip setuptools wheel
pip install --extra-index-url http://jenkins-master.optofidelity.net:8081 --trusted-host jenkins-master.optofidelity.net -r requirements.txt