# Copyright (c) 2015 OptoFidelity Ltd. All Rights Reserved.

from cherrypy import *

from .base_page import BasePage
import TPPTAnalysisSW.measurementdb as measurementdb
from datetime import datetime
import TPPTAnalysisSW.test_refs as test_refs
from .info.version import Version
from genshi.template import MarkupTemplate
import TPPTAnalysisSW.testbase as testbase

class TestSessionReport(BasePage):

    exposed = True

    def GET(self, session_id=None, function=None, **kwargs):
        """ Generates one big summary report from all tests in a test session. """

        if session_id is None:
            raise HTTPError(status="500", message="Internal error - test session not found")
            return

        all_results = []
        summaries = []
        with measurementdb.get_database().session() as dbsession:
            session = dbsession.query(measurementdb.TestSession).filter(measurementdb.TestSession.id == session_id).first()

            if session is None:
                raise HTTPError(status="500", message="Internal error - test session not found")
                return

            for test in session.test_items:

                generator, cache = testbase.TestBase.create(test.id, **kwargs)
                summary = {"id": test.id}

                if cache:
                    all_results.append(test_refs.testclass_refs[str(test.id)].get_results_for_session_template())

                else:
                    html, result = generator.createreport(**kwargs)
                    with measurementdb.get_database().session() as session:
                        dbresult = measurementdb.TestResult()
                        dbresult.test_id = test.id
                        dbresult.result = result
                        dbresult.calculated = datetime.now()
                        session.query(measurementdb.TestResult).filter(measurementdb.TestResult.test_id == test.id).delete()
                        session.add(dbresult)
                        session.commit()
                    all_results.append(test_refs.testclass_refs[str(test.id)].get_results_for_session_template())

                summary['type'] = test_refs.testclass_refs[str(test.id)].results['test_type_name']
                results = dbsession.query(measurementdb.TestResult).filter(measurementdb.TestResult.test_id == test.id).first()
                summary['verdict'] = results.result
                summaries.append(summary)

            templateParams = {}
            templateParams['test_type_name'] = "Test Session #%s Report" % session_id
            templateParams['all_results'] = all_results
            templateParams['test_script'] = 'test_page_subplots.js'
            templateParams['test_page'] = 'test_session_report.html'
            templateParams['version'] = Version
            templateParams['summaries'] = summaries

            template = MarkupTemplate(open("templates/test_session_report_common.html"))
            stream = template.generate(**(templateParams))

            return stream.render('xhtml')
