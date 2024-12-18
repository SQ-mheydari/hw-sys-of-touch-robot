# Copyright (c) 2020 OptoFidelity Ltd. All Rights Reserved.

from cherrypy import *
from genshi import Markup

from .base_page import BasePage
import TPPTAnalysisSW.measurementdb as measurementdb
from datetime import datetime
import TPPTAnalysisSW.test_refs as test_refs
from .info.version import Version
from genshi.template import MarkupTemplate
import TPPTAnalysisSW.testbase as testbase


# Controller for sessiontest to show all test results in one page
from TPPTAnalysisSW.settings import get_settings_by_dut
from TPPTAnalysisSW.utils import dict_to_json_string


class AllResultsController(BasePage):
    exposed = True

    def GET(self, session_id=None, function=None, **kwargs):
        """ Generates one big summary report from all tests in a test session.
            :param session_id: Id for test session which results are shown.
            :param function: Tells if csv, json, raw csv or a html page is wanted.
            :returns: Html page, csv file or json file.
        """

        if session_id is None:
            raise HTTPError(status="500", message="Internal error - test session not found")

        with measurementdb.get_database().session() as dbsession:
            session = dbsession.query(measurementdb.TestSession).filter(measurementdb.TestSession.id == session_id).first()

            if session is None:
                raise HTTPError(status="500", message="Internal error - test session not found")

            test_html = ''
            csv = ''
            json_dict = {}
            error_string = ''

            if function == 'json':
                total_time = str(datetime.strptime(session.endtime, '%Y-%m-%d %H:%M:%S') -
                                 datetime.strptime(session.starttime, '%Y-%m-%d %H:%M:%S'))
                json_dict['session'] = {
                    'start_time': session.starttime,
                    'total_execution_time': total_time,
                    'test_session_id': session.id,
                    'parameters': {param.name: param.valueFloat if param.isFloat else param.valueString
                                   for param in session.session_parameters}
                }
                json_dict['tests'] = []

            # Loop through tests and create the html/csv string or JSON dict. In the case of error save test ids to
            # error_string so that they can be displayed to user.
            for test in session.test_items:
                generator, cache = testbase.TestBase.create(test.id, **kwargs)

                try:
                    if function == 'csv':
                        csv += generator.createcsv(**kwargs) + '\n'
                    elif function == 'json':
                        report = {"metadata": generator.get_metadata(),
                                  "limits": generator.get_limits(),
                                  "results": generator.get_results()}
                        json_dict['tests'].append(report)
                    elif function == 'raw_csv':
                        kwargs['raw'] = True
                        csv += generator.createcsv(**kwargs) + '\n'
                    else:
                        # Every html document created by createreport contains two '<!--split-->' tags. First one is given
                        # to each test in test_common_body.html. This removes the part with logo, buttons etc. This part is
                        # the index 0 of the split result. The second one is given in the end of the template for each test.
                        # The purpose of this one is to remove the closing tags related to the parts that were removed by
                        # the first one. This is index 2 of the split result. Therefore index 1 contains the content that we
                        # actually want to show.
                        test_html += generator.createreport(test.id)[0].split('<!--split-->')[1]
                except TypeError:
                    if error_string == '':
                        error_string += 'Failed to load following test reports because error: {}'.format(test.id)
                    else:
                        error_string += ', {}'.format(test.id)

        # Add '.' to error_string so that it is a proper sentence.
        if error_string != '':
            error_string += '.'

        # Return csv or html based on the used function.
        if function == 'csv':
            response.headers['Content-type'] = 'text/csv'
            response.headers['Content-disposition'] = 'attachment;filename=test_session_data_%s.csv' % session_id
            return csv
        elif function == 'json':
            response.headers['Content-type'] = 'text/json'
            response.headers['Content-disposition'] = 'attachment;filename=test_session_data_%s.json' % session_id
            return dict_to_json_string(json_dict)
        elif function == 'raw_csv':
            response.headers['Content-type'] = 'text/csv'
            response.headers['Content-disposition'] = 'attachment;filename=test_session_data_raw_%s.csv' % session_id
            return csv
        else:
            templateParams = {}

            templateParams['test_type_name'] = "Test Session #%s Report" % session_id
            templateParams['session_id'] = session_id
            templateParams['error_string'] = error_string
            templateParams['content'] = Markup(test_html)
            templateParams['version'] = Version

            template = MarkupTemplate(open("templates/all_test_results.html"))
            stream = template.generate(**(templateParams))

            return stream.render('xhtml')
