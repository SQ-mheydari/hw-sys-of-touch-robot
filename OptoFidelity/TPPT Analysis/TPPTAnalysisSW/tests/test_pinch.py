# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

import cherrypy
import math
import numpy as np
import numpy.linalg as npl
from sqlalchemy.orm import joinedload
from genshi.template import MarkupTemplate
from functools import cmp_to_key

from TPPTAnalysisSW.testbase import TestBase, testclasscreator
from TPPTAnalysisSW.imagefactory import ImageFactory
from TPPTAnalysisSW.info.version import Version
from TPPTAnalysisSW.utils import Timer, exportcsv, str_to_float
from TPPTAnalysisSW.settings import get_setting
import TPPTAnalysisSW.measurementdb as db
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.plot_factory as plot_factory
import TPPTAnalysisSW.analyzers as analyzers

# Python 3 version of Python 2 built-in function cmp.
def cmp(a, b):
    return (a>b)-(a<b)

class PinchTest(TestBase):
    """ A dummy test class for use as a template in creating new test classes """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(16)
    def create_testclass(*args, **kwargs):
        return PinchTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.ddttest (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new SeparationTest class """
        super(PinchTest, self).__init__(ddtest_row, *args, **kwargs)

    # Override to make necessary analysis for test session success
    def runanalysis(self, *args, **kwargs):
        """ Runs the analysis, return a string containing the test result """
        results = self.read_test_results()
        verdict = None  ##todo, come back to this
        #if results['verdict'] is None:
        if verdict is None:
            verdict = 'N/A'
        elif results['verdict']:
            verdict = 'Pass'
        else:
            verdict = 'Fail'

        return verdict

    # Override to make necessary operations for clearing test results
    # Clearing the test result from the results table is done elsewhere
    def clearanalysis(self, *args, **kwargs):
        """ Clears analysis results """
        ImageFactory.delete_images(self.test_id)

    # Create CSV file from the results
    def createcsv(self, *args, **kwargs):
        """ Create csv file from the measurements """
        with db.get_database().session() as dbsession:
            test_results = dbsession.query(db.PinchTest).filter(db.PinchTest.test_id == self.test_id).\
                                                                    order_by(db.PinchTest.id).\
                                                                    options(joinedload('pinch_results'))

            return exportcsv(test_results, subtable='pinch_results')

    # Create the test report. Return the created HTML, or raise cherrypy.HTTPError
    def createreport(self, *args, **kwargs):
        
        # Create common template parameters (including test_item dictionary, testsession dictionary, test_id, test_type_name etc)
        templateParams = super(PinchTest, self).create_common_templateparams(**kwargs)
        #dbsession = get_database().session()

        # Add the image name and parameters to the report
        # Typically image is added like this:
        #
        t = Timer()

        # data for the report
        results = self.read_test_results()
        templateParams['results'] = results
        dutinfo = self.get_dutinfo()

        t.Time("Results")
        templateParams['figures'] = [ImageFactory.create_image_name(self.test_id, 'p2pdiff'),
                                    ImageFactory.create_image_name(self.test_id, 'timeseries')]


        t.Time("Results")

        # set the content to be used
        #templateParams['test_page'] = 'test_dummy.html'
        templateParams['test_page'] = 'test_pinch.html'
        templateParams['version'] = Version
        
        template = MarkupTemplate(open("templates/test_common_body.html"))
        stream = template.generate(**(templateParams))
        t.Time("Markup")
        return stream.render('xhtml'), results['verdict']

    # Create images for the report. If the function returns a value, it is used as the new image (including full path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        if image_name == 'p2pdiff':
            t = Timer(1)
            with db.get_database().session() as dbsession:
                dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
                results = self.read_test_results(dutinfo=dutinfo, dbsession=dbsession)
                t.Time("Results")
                title = 'Pinch - Maxoffset touch to line'
                print(results["failed_points"])
                plot_factory.plot_pinch_swipes_on_target(imagepath, dutinfo, results["passed_points"],results["failed_points"],results["lines"], *args, title=title, **kwargs)
                t.Time("Image")

        elif image_name == 'timeseries':
            t = Timer(1)
            with db.get_database().session() as dbsession:
                dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
                results = self.read_test_results(dutinfo=dutinfo, dbsession=dbsession)
            t = Timer(1)
            t.Time("Results")
            title = 'Preview: Time Series Plot'
            plot_factory.plot_pinch_timeseries(imagepath, dutinfo, results["all_points"],results["lines"], *args, title=title, **kwargs)
            t.Time("Image")

        return None

    def read_test_results(self, dutinfo=None, dbsession=None, **kwargs):
        if dbsession is None:
            with db.get_database().session() as dbsession:
                return self.read_test_results(dutinfo, dbsession, **kwargs)
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        s = Timer(2)
        tests = dbsession.query(db.PinchTest).filter(db.PinchTest.test_id == self.test_id).\
                                                   order_by(db.PinchTest.id).options(joinedload('pinch_results')).all()

        s.Time("DB Results")

        # Directory that contains the angles of the measurements
        locations = {}
        errors = set()
        lines = []
        passed_points = []
        failed_points = []
        all_points = []

        for test in tests:
            panel_points = [(p.panel_x, p.panel_y) for p in test.pinch_results]
            target_points = analyzers.panel_to_target(panel_points, dutinfo)
            start1_x, start1_y, end1_x, end1_y, start2_x, start2_y, end2_x, end2_y = self.calculate_start_end(test.center_x, test.center_y, test.robot_azimuth, test.start_separation, test.end_separation)
            swipe1_start, swipe1_end = analyzers.robot_to_target([(start1_x, start1_y), (end1_x, end1_y)], dutinfo)
            swipe2_start, swipe2_end = analyzers.robot_to_target([(start2_x, start2_y), (end2_x, end2_y)], dutinfo)
            lines.append((swipe1_start, swipe1_end))
            lines.append((swipe2_start, swipe2_end))##come back to this
            # swipe1_points = analyzers.target_to_swipe(target_points, swipe1_start, swipe1_end)
            # swipe2_points = analyzers.target_to_swipe(target_points, swipe2_start, swipe2_end)
            swipe1_target_points = self.calculate_target_swipe_points(swipe1_start, swipe1_end,0.1)
            swipe2_target_points = self.calculate_target_swipe_points(swipe2_start, swipe2_end,0.1)

            maxoffset = get_setting('maxoffset', dutinfo.sample_id)

            passfail_values = []
            for point in target_points:
                passed = False
                for p1 in swipe1_target_points:
                    if self.calculate_distance(point, p1) <  maxoffset:
                        passed = True
                for p2 in swipe2_target_points:
                    if self.calculate_distance(point, p2) <  maxoffset:
                        passed = True
                passfail_values.append(passed)

            passed = [target_points[i] for (i,t) in enumerate(passfail_values) if t]
            failed = [target_points[i] for (i,t) in enumerate(passfail_values) if not t]
            passed_points.extend(passed)
            failed_points.extend(failed)
            all_points.extend(target_points)

        print(failed_points)
        if len(failed_points)>0:
            verdict = 'Fail'
        else:
            verdict = 'Pass'

        results = {'lines': lines,
        'passed_points': passed_points,
        'failed_points': failed_points,
        'all_points': all_points,
        'verdict': verdict,
        'number_of_failed_points': len(failed_points), 
        'maxoffset': get_setting('maxoffset', dutinfo.sample_id)}

        return results
    
    def calculate_distance(self, point1, point2): 
        distance = math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)
        return distance


    def calculate_target_swipe_points(self, start, end, step_size):
        # Unpack start and end coordinates
        x1, y1 = start
        x2, y2 = end

        # Calculate the total distance between start and end points
        total_distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

        # Determine the number of steps required
        num_steps = int(total_distance / step_size)

        # Calculate the x and y increments for each step
        x_increment = (x2 - x1) / num_steps
        y_increment = (y2 - y1) / num_steps

        # Generate the points along the line
        points = []
        for step in range(num_steps + 1):
            x = x1 + step * x_increment
            y = y1 + step * y_increment
            points.append((x, y))

        return points
    
    def calculate_start_end(self, center_x, center_y, angle, start_separation, end_separation):
        #multiplying the angle by -1 because otherwise the angle was inverted compared to the angle for the gathered swipe
        
        y_diff = math.sin(math.radians(angle*-1))*.5*start_separation
        start1_y = (center_y+y_diff)
        start2_y = (center_y-y_diff)
        x_diff = math.cos(math.radians(angle*-1))*.5*start_separation
        start1_x = (center_x+x_diff)
        start2_x = (center_x-x_diff)
        y_end_diff = math.sin(math.radians(angle*-1))*.5*end_separation
        end1_y = (center_y+y_end_diff)
        end2_y = (center_y-y_end_diff)
        x_end_diff = math.cos(math.radians(angle)*-1)*.5*end_separation
        end1_x = (center_x+x_end_diff)
        end2_x = (center_x-x_end_diff)
        
        return start1_x, start1_y, end1_x, end1_y, start2_x, start2_y, end2_x, end2_y 
        

    def get_results(self) -> dict:
       ## I don't think this function is really used for anything at this moment
       ## Ideally the results should be split out by angle and location but that will require more development in the future
       dutinfo = self.get_dutinfo()
       all_results = self.read_test_results(dutinfo)

    #    results = {
    #        'summary': [],
    #    }
       
    #    angle_result = {
    #         'location': [0,0],
    #         'verdict': "Pass"
    #     }
    #    for angle, values in all_results['angles'].items():
    #        angle_result = {
    #            'angle': float(angle),
    #            'separation': str_to_float(values['separation']),
    #            'max_separation': values['maxseparation'],
    #            'verdict': "Pass" if values['verdict'] else "Fail"
    #        }
    #        results['summary'].append(angle_result)

    #    for angle_id in all_results['angle_ids']:
    #        for distance_id in all_results['angles'][angle_id]['distance_ids']:
    #            angle_result = {
    #                'angle': float(angle_id),
    #                'separation': float(distance_id),
    #                'verdict': all_results['angles'][angle_id]['distances'][distance_id]['verdict_text']
    #            }
    #            results['angles'].append(angle_result)

       return all_results
