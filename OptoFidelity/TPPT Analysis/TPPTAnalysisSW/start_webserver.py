# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

import cherrypy
from .main_page import MainPage
from .all_test_results import AllResultsController
from .test_session import TestSession
from .test import Test
from .test_session_report import TestSessionReport
from .imagefactory import ImageFactory
from .settings_page import SettingsController
from .test_session_settings import TestSessionSettingsController
from .settings import *
from .test_summary import SummaryController
from .utils import Timer
import TPPTAnalysisSW.test_refs as test_refs
import TPPTAnalysisSW.measurementdb as measurementdb
import TPPTAnalysisSW.progressstatus as progressstatus

# We need to import the different test types somewhere - a small kludge
import TPPTAnalysisSW.tests.test_multifinger_swipe
import TPPTAnalysisSW.tests.test_multifinger_tap
import TPPTAnalysisSW.tests.test_separation
import TPPTAnalysisSW.tests.test_dutinformation
import TPPTAnalysisSW.tests.test_one_finger_tap
import TPPTAnalysisSW.tests.test_one_finger_swipe
import TPPTAnalysisSW.tests.test_repeatability
import TPPTAnalysisSW.tests.test_non_stationary_reporting_rate
import TPPTAnalysisSW.tests.test_stationary_reporting_rate
import TPPTAnalysisSW.tests.test_stationary_jitter
import TPPTAnalysisSW.tests.test_first_contact_latency
import TPPTAnalysisSW.tests.test_one_finger_tap
import TPPTAnalysisSW.tests.test_pinch

import os
import sys
import webbrowser


def start(address, port):

    conf = {
        '/': {
              'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
              'response.timeout': 3600,
        },
        '/static' : {
            'tools.staticdir.root': os.getcwd(),
            'tools.staticdir.on' : True,
            'tools.staticdir.dir' : 'static',
        }
    }

    test_refs.init()
    progressstatus.initProgress()

    with measurementdb.get_database().session() as dbsession:
        loadSettings(dbsession) # from settings.py

    root = MainPage()
    root.testsessions = TestSession()
    root.tests = Test()
    root.testsessionreports = TestSessionReport()

    # create generated image path if none exists
    if not os.path.isdir('static/img/generated'):
        os.mkdir('static/img/generated')

    root.img = ImageFactory()
    root.img.configuration['root_dir'] = os.getcwd()
    root.settings = SettingsController()
    root.testsessionsettings = TestSessionSettingsController()
    root.summary = SummaryController()
    root.allresults = AllResultsController()

    if "--timer" in sys.argv:
        # Used in Plotinfo
        Timer.do_timing = True

    web_address = 'http://%s:%s/' % (address, port)

    def browse():
        webbrowser.open(web_address)

    cherrypy.engine.subscribe('start', browse, priority=90)

    cherrypy.config.update({'server.socket_host': address,})
    cherrypy.config.update({'server.socket_port': port,})

    cherrypy.quickstart(root,'/',conf)
