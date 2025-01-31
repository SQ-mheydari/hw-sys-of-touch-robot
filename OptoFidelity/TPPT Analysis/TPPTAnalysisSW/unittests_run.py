# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

import unittest
import TPPTAnalysisSW.unittests as unittests

if __name__ == '__main__':
    print "Running analysis verdicts test"
    tests = unittests.verdicts_test.suite()
    unittest.TextTestRunner().run(tests)
    print "Running test report generation test"
    tests = unittests.tests_test.suite(check_images=True)
    unittest.TextTestRunner().run(tests)
