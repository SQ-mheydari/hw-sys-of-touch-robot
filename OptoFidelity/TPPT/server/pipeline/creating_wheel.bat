SET PATH=%PATH:"=%
call venv\\Scripts\\activate.bat

SET PYTHONPATH=%cd%

python main.py --generate-client=configuration/client_config.yaml
copy installer\\version.txt .
cd client
python setup.py sdist bdist_wheel
copy tntclient tests\\
cd dist
FOR %%I IN (*.whl) DO python -m pip install "%%I"
