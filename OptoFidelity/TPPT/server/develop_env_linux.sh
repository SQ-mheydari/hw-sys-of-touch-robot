#!/bin/bash

pyenv version 3.7.9
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -U pip setuptools wheel
pip install --extra-index-url http://jenkins-master.optofidelity.net:8081 --trusted-host jenkins-master.optofidelity.net -r requirements.txt
