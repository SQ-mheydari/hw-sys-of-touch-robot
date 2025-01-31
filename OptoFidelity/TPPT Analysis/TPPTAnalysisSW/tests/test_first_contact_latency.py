# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

import cherrypy
import numpy
from genshi.template import MarkupTemplate
from sqlalchemy.orm import joinedload

from TPPTAnalysisSW.testbase import TestBase, testclasscreator
from TPPTAnalysisSW.imagefactory import ImageFactory
from TPPTAnalysisSW.measurementdb import get_database, OneFingerFirstContactLatencyTest
from TPPTAnalysisSW.settings import get_setting, precision
from TPPTAnalysisSW.utils import Timer, exportcsv
from TPPTAnalysisSW.info.version import Version
import TPPTAnalysisSW.plot_factory as plot_factory
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.analyzers as analyzers

class FirstContactLatencyTest(TestBase):
    """ A dummy test class for use as a template in creating new test classes """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(2)
    def create_testclass(*args, **kwargs):
        return FirstContactLatencyTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.test_item (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new FirstContactLatencyTest class """
        super(FirstContactLatencyTest, self).__init__(ddtest_row, *args, **kwargs)

    # Create CSV file from the results
    def createcsv(self, *args, **kwargs):
        ''' Create csv file from the measurements '''
        with get_database().session() as dbsession:
            query = dbsession.query(OneFingerFirstContactLatencyTest).filter(
                OneFingerFirstContactLatencyTest.test_id == self.test_id).order_by(OneFingerFirstContactLatencyTest.id)
            return exportcsv(query, initialstring='one_finger_first_contact_latency_test\n')

    # Override to make necessary analysis for test session success
    def runanalysis(self, *args, **kwargs):
        """ Runs the analysis, return a string containing the test result """
        verdict = "N/A"
        result = self.read_test_results()
        if (result['active_response_latency_verdict'] == "Fail" or 
            result['idle_response_latency_verdict'] == "Fail"):
             verdict = "Fail"
        elif (result['active_response_latency_verdict'] == "Pass" and 
              result['idle_response_latency_verdict'] == "Pass"):
            verdict = "Pass"
        return verdict

    # Override to make necessary operations for clearing test results
    # Clearing the test result from the results table is done elsewhere
    def clearanalysis(self, *args, **kwargs):
        """ Clears analysis results """
        ImageFactory.delete_images(self.test_id)

    # Create the test report. Return the created HTML, or raise cherrypy.HTTPError
    def createreport(self, *args, **kwargs):

        s = Timer(1)

        # clear analysis data
        self.clearanalysis()

        # Create common template parameters (including test_item dictionary, testsession dictionary, test_id, test_type_name etc)
        templateParams = super(FirstContactLatencyTest, self).create_common_templateparams(**kwargs)

        s.Time("Init")

        # Read test results
        results = self.read_test_results()

        s.Time("Results")
          
        templateParams['active_response_latency'] = results['active_response_latency']
        templateParams['idle_response_latency'] = results['idle_response_latency']
        templateParams['active_response_latency_verdict'] = results['active_response_latency_verdict']
        templateParams['idle_response_latency_verdict'] = results['idle_response_latency_verdict']
        templateParams['measurements'] = results['measurements']

        # Add the image name and parameters to the report
        templateParams['figure'] = ImageFactory.create_image_name(self.test_id, 'fcl') 
        templateParams['detailed_figure'] = ImageFactory.create_image_name(self.test_id, 'fcl', 'detailed') 

        # set the content to be used
        templateParams['test_page'] = 'test_first_contact_latency.html'
        templateParams['version'] = Version
        s.Time("Parameters")

        template = MarkupTemplate(open("templates/test_common_body.html"))
        stream = template.generate(**(templateParams))
        s.Time("Generate")

        verdict = "Pass"
        if results['active_response_latency_verdict'] == "Fail" or results['idle_response_latency_verdict'] == "Fail":
            verdict = "Fail"
        elif results['active_response_latency_verdict'] == "N/A" or results['idle_response_latency_verdict'] == "N/A":
            verdict = "N/A"

        return stream.render('xhtml'), verdict

    # Create images for the report. If the function returns a value, it is used as the new image name (without image path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        if image_name == 'fcl':
            with get_database().session() as dbsession:
                dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
                results = self.read_test_results()
                title = 'Preview: First contact latency'
                plot_factory.plot_passfail_labels_on_target(imagepath, results, dutinfo, *args, title=title, **kwargs)
        else:
            raise cherrypy.HTTPError(message = "No such image in the report")
            
        return None

    def read_test_results(self, dbsession = None):

        t = Timer(2)

        if dbsession is None:
            with get_database().session() as dbsession:
                return self.read_test_results(dbsession)

        test_results = dbsession.query(OneFingerFirstContactLatencyTest).filter(OneFingerFirstContactLatencyTest.test_id == self.test_id).\
                                                                         order_by(OneFingerFirstContactLatencyTest.id).all()

        t.Time("Database")

        measurements = []
        passed_points = []
        failed_points = []
        point_id = 1
        previous_point = None
        active_response_latency = None
        idle_response_latency = None
        dutinfo = self.get_dutinfo()

        for result in test_results:
            if previous_point is None:
                previous_point = (result.robot_x, result.robot_y, result.robot_z)
            elif (result.robot_x != previous_point[0] or result.robot_y != previous_point[1] or 
                    result.robot_z != previous_point[2]):
                # Check verdict of previous point id
                verdict = "Pass"
                for msmt in measurements:
                    if msmt[0] == point_id and msmt[4] != "Pass":
                        verdict = msmt[4]
                if verdict == "Pass":
                    passed_points.append((previous_point[0], previous_point[1], point_id))
                else:
                    failed_points.append((previous_point[0], previous_point[1], point_id))

                point_id += 1
                previous_point = (result.robot_x, result.robot_y, result.robot_z)

            type = "N/A"
            threshold = 0.0
            if result.powerstate == 1:
                type = "Active"
                threshold = get_setting('maxactiveresponselatency', dutinfo.sample_id)
            elif result.powerstate == 2:
                type = "Idle"
                threshold = get_setting('maxidleresponselatency', dutinfo.sample_id)

            verdict = "N/A"
            try:
                latency = analyzers.round_dec(result.time - result.delay + result.system_latency)
                verdict = "Pass" if latency <= threshold else "Fail"
            except TypeError:
                latency = None

            if latency is not None:
                if type == "Active":
                    active_response_latency = max(active_response_latency, latency) if active_response_latency is not None else latency
                else:
                    idle_response_latency = max(idle_response_latency, latency) if idle_response_latency is not None else latency

            measurements.append((point_id, type, latency, threshold, verdict))

        if previous_point is not None:
            # Check verdict of previous point id
            verdict = "Pass"
            for msmt in measurements:
                if msmt[0] == point_id and msmt[4] != "Pass":
                    verdict = msmt[4]
            if verdict == "Pass":
                passed_points.append((previous_point[0], previous_point[1], point_id))
            else:
                failed_points.append((previous_point[0], previous_point[1], point_id))

        active_response_latency_verdict = "N/A"
        if active_response_latency is not None:
            active_response_latency_verdict = "Pass" if active_response_latency < get_setting('maxactiveresponselatency', dutinfo.sample_id) else "Fail"
        idle_response_latency_verdict = "N/A"
        if idle_response_latency is not None:
            idle_response_latency_verdict = "Pass" if idle_response_latency < get_setting('maxidleresponselatency', dutinfo.sample_id) else "Fail"
  
        results = {'active_response_latency': active_response_latency,
                   'active_response_latency_verdict': active_response_latency_verdict,
                   'idle_response_latency': idle_response_latency,
                   'idle_response_latency_verdict': idle_response_latency_verdict,
                   'passed_points': passed_points,
                   'failed_points': failed_points,
                   'measurements': measurements}

        t.Time("End of analysis")

        return results

    def get_results(self) -> dict:
        all_results = self.read_test_results()
        results = {
            'active_response_latency': all_results['active_response_latency'],
            'active_response_latency_verdict': all_results['active_response_latency_verdict'],
            'idle_response_latency': all_results['idle_response_latency'],
            'idle_response_latency_verdict': all_results['idle_response_latency_verdict'],
            'measurements': []
        }

        for result in all_results['measurements']:
            point = {
                'point_id': result[0],
                'sleep_mode': result[1],
                'value': result[2],
                'maximum_allowed': result[3],
                'verdict': result[4]
            }
            results['measurements'].append(point)

        return results
