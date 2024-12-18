# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

# Test class for testing test generation (phew...)

import unittest
import testbase
import time

# Result generation time threshold for acceptance
# Analysis should run in 500 ms
_report_time_threshold = 0.5

def setUpModule():
    import start_webserver

class VerdictTest(unittest.TestCase):
    
    # addTestId - runTest pattern enables us to read test id's from database
    # and run each test id as a separate test
    @staticmethod
    def addTestId(test_id):
        def subtest(self):
            self.runTest(test_id)
        
        test_method = "test_testid_%s" % test_id
        setattr(VerdictTest, test_method, subtest)
        return test_method

    def runTest(self, test_id):
        import testbase
        testclass = testbase.TestBase.create(test_id)
        self.assertIsNotNone(testclass, "None testclass for test id %s" % str(test_id))
        start = time.clock()
        verdict = testclass.runanalysis()       
        end = time.clock()
        self.assertIn(verdict, ["Pass", "Fail", "N/A"], "Invalid response for test id %s: %s" % (test_id, verdict))
        self.assertLessEqual(end-start, _report_time_threshold, "The execution of verdict took too long: %.1f seconds" % (end-start))

def suite():
    import measurementdb
    dbsession = measurementdb.get_database().session()
    test_ids = dbsession.query(measurementdb.TestItem).order_by(measurementdb.TestItem.id).\
                                                       values(measurementdb.TestItem.id)

    tests = []
    for test_id in test_ids:
        tests.append(VerdictTest.addTestId(str(test_id[0])))

    suite = unittest.TestSuite()
    for test in tests:
        suite.addTest(VerdictTest(test))
    return suite
