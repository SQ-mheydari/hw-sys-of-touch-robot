# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

import cherrypy
import json

from genshi.template import MarkupTemplate
from genshi.filters import HTMLFormFiller

import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.test_session as test_session
import TPPTAnalysisSW.plotters as plotters
import TPPTAnalysisSW.imagefactory as imagefactory
import TPPTAnalysisSW.measurementdb as db
import TPPTAnalysisSW.test_session as test_session

from .base_page import BasePage

from .info.version import Version

# Settings controller for settings-view
class TestSessionSettingsController(BasePage):
    """ These are actually DUT-specific settings """

    def GET(self, testsession_id, dut_id):
        if dut_id is None:
            raise HTTPError("404")

        with db.get_database().session() as dbsession:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=dut_id, dbsession=dbsession)

            template = MarkupTemplate(open("templates/test_dut_settings.html"))
            stream = template.generate(version=Version, testsessionid=testsession_id, dutinfo=dutinfo)
            return stream.render('xhtml')

    def POST(self, testsession_id, dut_id, **kwargs):
        if 'data' not in kwargs:
            raise cherrypy.HTTPError("400", "Expected data not received")

        saveFields = ["size_x", "size_y", "digitizer_resolution_x", "digitizer_resolution_y",
                      "flipx", "flipy", "switchxy",
                      "dut_manufacturer", "dut_program", "dut_batch", "dut_sample_id"]
        data = json.loads(kwargs['data'])

        # Check that each save field exists in the data
        for key in saveFields:
            if key not in data:
                print("Missing key from input: " + key)
                raise cherrypy.HTTPError("400", "Invalid key/value pairs in POST data")
        # Check that no extra fields exists in the data
        for key in data.keys():
            if key not in saveFields:
                print ("Unrecognized key: " + key)
                raise cherrypy.HTTPError("400", "Unrecognized key/value pairs in POST data")

        # Assume that the data is of correct format -> save to DB
        with db.get_database().session() as dbsession:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=dut_id, dbsession=dbsession)
            dutinfo.dimensions = [float(data['size_x']), float(data['size_y'])]
            dutinfo.digitizer_resolution = [float(data['digitizer_resolution_x']), float(data['digitizer_resolution_y'])]
            dutinfo.offset = [0.0, 0.0]
            dutinfo.flipx = (data['flipx'] == '1')
            dutinfo.flipy = (data['flipy'] == '1')
            dutinfo.switchxy = (data['switchxy'] == '1')

            dutinfo.manufacturer = data['dut_manufacturer']
            dutinfo.program = data['dut_program']
            dutinfo.batch = data['dut_batch']
            dutinfo.sample_id = data['dut_sample_id']

            dutinfo.save(dbsession=dbsession)

            # Recalculate analysis results
            test_session.TestSession.do_evaluation(dbsession, testsession_id)

        cherrypy.response.headers['Content-Type']= 'text/plain'
        return "Saved"

    exposed = True

