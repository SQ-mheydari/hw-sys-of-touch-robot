# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

import cherrypy
from genshi.template import MarkupTemplate
from sqlalchemy.orm import joinedload
import TPPTAnalysisSW.measurementdb as measurementdb
from .plotinfo import *
import TPPTAnalysisSW.analyzers as analyzers
from .settings import settings
from datetime import datetime
import math
import json

import time
import traceback
import TPPTAnalysisSW.plotinfo as plotinfo
from .utils import Timer
from .testbase import TestBase
from .base_page import BasePage
from .info.version import Version
import TPPTAnalysisSW.imagefactory as imagefactory

#Controller for testsession
class TestSession(BasePage):
    exposed = True

    def GET(self,testSessionId=None, command=None):
        # Command is here in case we need to create e.g. session-wide settings
        if command is None:
            if (testSessionId==None):
                raise cherrypy.HTTPError("404", "No testsession given")

            with measurementdb.get_database().session() as dbsession:
                testsession = dbsession.query(measurementdb.TestSession).filter(measurementdb.TestSession.id==testSessionId).first()
                sessioninfo = plotinfo.TestSessionInfo(testsession=testsession)

                tests, results, curved = self.sessionResultsFromDB(testsession, dbsession)
                tests_results = zip(tests,results)

                # Categorize tests by DUTs
                duts = [] # list of tuples: (dut, [(test, result), ...])
                dut_indices = {} # Dut id -> duts list index map
                for test_result in tests_results:
                    dut = test_result[0].dut
                    if dut.id in dut_indices:
                        # Append to an older dut
                        dut_index = dut_indices[dut.id]
                        duts[dut_index][1].append(test_result)
                    else:
                        # Add new dut
                        dut_index = len(duts)
                        dut_indices[dut.id] = dut_index
                        duts.append((dut, [test_result]))

                with open("templates/testsession.html") as f:
                    tmpl = MarkupTemplate(f)
                    stream = tmpl.generate(duts=duts, session=sessioninfo, version=Version)
                    return stream.render('xhtml')
        else:
            raise cherrypy.HTTPError("404", "Command not found")

    def POST(self,testSessionId=None, command=None, **kwargs):
        if 'data' not in kwargs:
            print("No data in kwargs")
            raise cherrypy.HTTPError("400", "Expected data not received")

        data = json.loads(kwargs['data'])
        if 'command' not in data:
            print("No command in data")
            raise cherrypy.HTTPError("400", "Expected command not received")

        return_data = 'No such command'

        if data['command'] == 'set_notes':
            with measurementdb.get_database().session() as dbsession:
                testsession = dbsession.query(measurementdb.TestSession).filter(measurementdb.TestSession.id==testSessionId).first()
                testsession.notes = data['value']
                dbsession.commit()
                return_data = testsession.notes

        return return_data

    @staticmethod
    def session_samples_progs_manus(testsession, dbsession):

        sample_names = set()
        sample_prog = set()
        sample_manu = set()
        sample_ver = set()

        for test in testsession.test_items:

            sample = test.dut.sample_id
            manu = test.dut.manufacturer
            prog = test.dut.program
            ver = test.dut.batch

            if sample is None or len(sample) == 0:
                sample = "[Empty]"
            sample_names.add(sample)

            if manu is None or len(manu) == 0:
                manu = "[Empty]"
            sample_manu.add(manu)

            if prog is None or len(prog) == 0:
                prog = "[Empty]"
            sample_prog.add(prog)

            if ver is None or len(ver) == 0:
                ver = "[Empty]"
            sample_ver.add(ver)

        return ", ".join(sorted(sample_names)), \
               ", ".join(sorted(sample_prog)), \
               ", ".join(sorted(sample_manu)), \
               ", ".join(sorted(sample_ver))

    @staticmethod
    def sessionResultsFromDB(testsession, dbsession):

        tests = []
        results = []
        test_types = []

        for test in testsession.test_items:
            if len(test.test_results) == 0:
                # Run analysis
                result = TestBase.evaluateresult(test.id)
            else:
                result = test.test_results[0].result

            tests.append(test)
            test_types.append(test.testtype_id)
            results.append(result)

        curved = False
        if len(set(test_types)) == 1:
            if test_types[0] == 15:
                curved = True

        return (tests, results, curved)

    @classmethod
    def eval_tests_results(caller, dbsession, testSessionId, recalculate=True):
        try:
            return TestSession.do_evaluation(dbsession, testSessionId, recalculate=recalculate)
        except Exception as e:
            print("Error in analysis!", e)

    @classmethod
    def do_evaluation(caller, dbsession, testSessionId, recalculate=True):
        '''
        Analyzes all test results in test session.
        '''

        tests = dbsession.query(measurementdb.TestItem).options(joinedload('type')).\
                                filter(measurementdb.TestItem.testsession_id == testSessionId).all()
        results = []

        s = Timer(2)

        for idx, t in enumerate(tests):
            imagefactory.ImageFactory.delete_images(str(t.id))
            result = TestBase.evaluateresult(t.id, recalculate=recalculate)
            results.append(result)
            s.Time("Analyzed test %d - result %s" % (t.id, result))

        return tests, results
