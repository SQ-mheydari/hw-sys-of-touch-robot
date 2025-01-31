# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

# Test class for testing test generation (phew...)

import unittest
import time
import re

# Report generation time threshold for acceptance
_report_time_threshold = 1.0

def setUpModule():
    import start_webserver

class ReportTest(unittest.TestCase):
    
    # addTestId - runTest pattern enables us to read test id's from database
    # and run each test id as a separate test
    @staticmethod
    def addTestId(test_id):
        def subtest(self):
            self.runTest(test_id)
        
        test_method = "test_testid_%s" % test_id
        setattr(ReportTest, test_method, subtest)
        return test_method

    def runTest(self, test_id):
        import start_webserver
        #print "Test id %s" % test_id
        start = time.clock()
        html = start_webserver.root.tests.GET(test_id)
        end = time.clock()
        self.assertLessEqual(end-start, _report_time_threshold, "The execution of report took too long: %.1f seconds" % (end-start))

        if ReportTest.check_images:
            images = re.findall('/img/.*?\.png', html)
            for image in images:
                # Strip /img/ from the start
                name = image[5:]
                #print "Test id %s - image %s" % (test_id, name)
                start_webserver.root.img.GET(name)

def suite(check_images=False):
    import measurementdb
    dbsession = measurementdb.get_database().session()
    test_ids = dbsession.query(measurementdb.TestItem).order_by(measurementdb.TestItem.id).\
                                                       values(measurementdb.TestItem.id)

    ReportTest.check_images = check_images

    tests = []
    for test_id in test_ids:
        tests.append(ReportTest.addTestId(str(test_id[0])))

    suite = unittest.TestSuite()
    for test in tests:
        suite.addTest(ReportTest(test))
    return suite
