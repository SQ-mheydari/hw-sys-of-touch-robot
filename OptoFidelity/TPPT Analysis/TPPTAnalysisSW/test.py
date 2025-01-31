# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.
import json
from decimal import Decimal

from cherrypy import *

from .base_page import BasePage
import TPPTAnalysisSW.testbase as testbase
from .measurementdb import get_database, TestItem, TestResult
from datetime import datetime
import TPPTAnalysisSW.test_refs as test_refs
from TPPTAnalysisSW.utils import dict_to_json_string


#Controller for test
class Test(BasePage):
    SAVEPATH = ""
    exposed = True


    def GET(self, test_id=None, function=None, **kwargs):
        #print "Test GET, testid", test_id
        if (test_id==None):
            raise HTTPError("404")

        generator, cache = testbase.TestBase.create(test_id, **kwargs)
        if 'refresh' in kwargs and kwargs['refresh'] == "yes":
            cache = False

        if generator:

            if function == 'csv':
                response.headers['Content-type'] = 'text/csv'
                response.headers['Content-disposition'] = 'attachment;filename=testdata_%s.csv' % test_id
                return generator.createcsv(**kwargs)

            if function == 'json':
                response.headers['Content-type'] = 'application/json'
                response.headers['Content-disposition'] = 'attachment;filename=testdata_%s.json' % test_id
                report = {"metadata": generator.get_metadata(),
                          "limits": generator.get_limits(),
                          "results": generator.get_results()}
                return dict_to_json_string(report)

            if function == 'raw_csv':
                response.headers['Content-type'] = 'text/csv'
                response.headers['Content-disposition'] = 'attachment;filename=testdata_raw_%s.csv' % test_id
                kwargs['raw'] = True
                return generator.createcsv(**kwargs)

            if cache:
                html, result = test_refs.testclass_refs[test_id].createreport(cache=True, **kwargs)
                return html

            else:
                html, result = generator.createreport(**kwargs)

                with get_database().session() as session:
                    dbresult = TestResult()
                    dbresult.test_id = test_id
                    dbresult.result = result
                    dbresult.calculated = datetime.now()
                    session.query(TestResult).filter(TestResult.test_id == test_id).delete()
                    session.add(dbresult)
                    session.commit()

                return html
        else:
            print("unknown test type (test id %s)" % test_id)
            raise HTTPError(status="500", message="Internal error - test type not found")

    def PUT(self,**kwargs):
        pass

