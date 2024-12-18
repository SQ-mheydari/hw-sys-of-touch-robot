#!/bin/bash

python3.7 -m venv venv
source venv/bin/activate
curl https://bootstrap.pypa.io/2.7/get-pip.py -o get-pip.py
python get-pip.py
python -m pip install --upgrade pip
python -m pip install -U pip setuptools wheel
pip install --extra-index-url http://jenkins-master.optofidelity.net:8081 --trusted-host jenkins-master.optofidelity.net -r requirements.txt
