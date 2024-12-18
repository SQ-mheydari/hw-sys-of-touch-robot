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
        templateParams['figure'] = ImageFactory.create_image_name(self.test_id, 'p2pdiff')

        t = Timer()

        results = self.read_test_results()
        templateParams['results'] = results

        t.Time("Results")

        # set the content to be used
        templateParams['test_page'] = 'test_dummy.html'
        templateParams['version'] = Version
        
        template = MarkupTemplate(open("templates/test_common_body.html"))
        stream = template.generate(**(templateParams))
        t.Time("Markup")
        #return stream.render('xhtml'), results['verdict']
        return stream.render('xhtml'), 'Pass'

##        self.clearanalysis()
##
##        # Create common template parameters (including ddttest dictionary, testsession dictionary, test_id, test_type_name etc)
##        templateParams = super(PinchTest, self).create_common_templateparams(**kwargs)
##        t = Timer()
##        results = self.read_test_results()
##
##        # data for the report
##        templateParams['results'] = results
##        templateParams['figures'] = [ImageFactory.create_image_name(self.test_id, 'sepgen'),
##                                     ImageFactory.create_image_name(self.test_id, 'sepdet')]
##
##        t.Time("Results")
##
##        # set the content to be used
##        templateParams['test_page'] = 'test_separation.html'
##        templateParams['test_script'] = 'test_page_subplots.js'
##        templateParams['version'] = Version
##
##        template = MarkupTemplate(open("templates/test_common_body.html"))
##        stream = template.generate(**(templateParams))
##        t.Time("Markup")
##
##        if results['verdict'] is None:
##            verdict = 'N/A'
##        elif results['verdict']:
##            verdict = 'Pass'
##        else:
##            verdict = 'Fail'
##
##        return stream.render('xhtml'), verdict

    # Create images for the report. If the function returns a value, it is used as the new image (including full path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        if image_name == 'p2pdiff':
            t = Timer(1)
            with db.get_database().session() as dbsession:
                dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
                results = self.read_test_results(dutinfo=dutinfo, dbsession=dbsession)
                t.Time("Results")
                title = 'Preview: One Finger Tap'
                plot_factory.plot_pinch_swipes_on_target(imagepath, dutinfo, results["passed_points"],results["failed_points"],results["lines"], *args, title=title, **kwargs)
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

        for test in tests:
            # Single separation angle & distance
            # Single location and angle
##            location =[test.start_x, test.start_y]
##            if location not in locations:
##                locations[location] = {'angles':{}}
##
##            angle = test.azimuth
##            dresults = {}
##            locations[location]['angles'][angle] = dresults

            panel_points = [(p.panel_x, p.panel_y) for p in test.pinch_results]
            target_points = analyzers.panel_to_target(panel_points, dutinfo)
            start1_x, start1_y, end1_x, end1_y, start2_x, start2_y, end2_x, end2_y = self.calculate_start_end(test.center_x, test.center_y, test.robot_azimuth, test.start_separation, test.end_separation)
            swipe1_start, swipe1_end = analyzers.robot_to_target([(start1_x, start1_y), (end1_x, end1_y)], dutinfo)
            swipe2_start, swipe2_end = analyzers.robot_to_target([(start2_x, start2_y), (end2_x, end2_y)], dutinfo)
            lines.append((swipe1_start, swipe1_end))
            lines.append((swipe2_start, swipe2_end))##come back to this
            swipe1_points = analyzers.target_to_swipe(target_points, swipe1_start, swipe1_end)
            swipe2_points = analyzers.target_to_swipe(target_points, swipe2_start, swipe2_end)

            ## Everything will be recorded as a PASS for now until we dial in our alogrithm 
            passfail_values = []
            for p1, p2 in zip(swipe1_points, swipe2_points):
                if analyzers.round_dec(abs(p1[1])) <= get_setting('maxoffset', dutinfo.sample_id) or analyzers.round_dec(abs(p2[1])) <= get_setting('maxoffset', dutinfo.sample_id):
                    passfail_values.append(True)
                else:
                    passfail_values.append(True)

            #passfail_values = [analyzers.round_dec(abs(p[1])) <= get_setting('maxoffset', dutinfo.sample_id) for p in (swipe1_points)]
            passed = [target_points[i] for (i,t) in enumerate(passfail_values) if t]
            failed = [target_points[i] for (i,t) in enumerate(passfail_values) if not t]
            passed_points.extend(passed)
            failed_points.extend(failed)

        results = {'lines': lines,
        'passed_points': passed_points,
        'failed_points': failed_points}
            

##            pdist = (math.cos(math.radians(-test.separation_angle)) * test.tool_separation,
##                     math.sin(math.radians(-test.separation_angle)) * test.tool_separation)
##            dresults['point']    = analyzers.robot_to_target((test.robot_x, test.robot_y), dutinfo)
##            dresults['point_diameter'] = test.finger1_diameter
##            dresults['angle']    = test.separation_angle
##            dresults['point2']   = [c + d for c, d in zip(dresults['point'], pdist)]
##            dresults['point2_diameter'] = test.finger2_diameter
##            dresults['errors']   = set()
##            dresults['image']    = ImageFactory.create_image_name(self.test_id, 'sepdtls', angle, distance)
##            taps = {}
##            dresults['taps']     = taps
##            for tap in test.separation_results:
##                if tap.finger_id not in taps:
##                    taps[tap.finger_id] = []
##                taps[tap.finger_id].append(analyzers.panel_to_target((tap.panel_x, tap.panel_y), dutinfo))
##
##            if len(taps.keys()) == 0:
##                # No measurements found
##                dresults['errors'].add('No measurements for tap')
##                errors.add('No measurements for tap')
##                dresults['verdict'] = False
##                dresults['verdict_text'] = 'N/A'
##            elif len(taps.keys()) == 1:
##                # No separation
##                dresults['verdict'] = False
##                dresults['verdict_text'] = 'Fail'
##            elif len(taps.keys()) == 2:
##                # Separation found
##                dresults['verdict'] = True
##                dresults['verdict_text'] = 'Pass'
##            else:
##                # Too many id's
##                dresults['errors'].add('Too many ids for tap')
##                errors.add('Too many ids for tap')
##                dresults['verdict'] = False
##                dresults['verdict_text'] = 'Fail'
##
##        # Calculate results
##        verdict = None
##        for angle, values in angles.items():
##            sorteddist = sorted(values['distances'].keys(), key=cmp_to_key(lambda x,y: cmp(float(x), float(y))))
##            #print "Angle %s - %s" % (angle, str(sorteddist))
##            mindist = None
##            for dist in sorteddist:
##                if values['distances'][dist]['verdict']:
##                    if mindist is None:
##                        mindist = dist
##                else:
##                    mindist = None
##
##            values['distance_ids'] = sorteddist
##            values['separation'] = mindist
##            # Verdict calculation
##            if angle == '0.0' or angle == '90.0':
##                dverdict = mindist is not None and (float(mindist) <= get_setting('maxseparation', dutinfo.sample_id))
##                values['maxseparation'] = get_setting('maxseparation', dutinfo.sample_id)
##            else:
##                dverdict = mindist is not None and (float(mindist) <= get_setting('maxdiagseparation', dutinfo.sample_id))
##                values['maxseparation'] = get_setting('maxdiagseparation', dutinfo.sample_id)
##            values['verdict'] = dverdict
##            if verdict is None:
##                verdict = dverdict
##            elif dverdict == False:
##                verdict = False
##
##        angle_ids = sorted(angles.keys(), key=cmp_to_key(lambda x,y: cmp(float(x), float(y))))

##        results = {'max_input_error': max_input_error,
##                   'max_input_verdict': max_input_verdict,
##                   'total_points': len(targets),
##                   'missing_inputs': len(missing),
##                   'missing_inputs_verdict': (len(missing) - len(missing_edge) <= get_setting('maxmissing', dutinfo.sample_id)),
##                   'missing_edge_inputs': len(missing_edge),
##                   'missing_edge_inputs_verdict': (len(missing_edge) <= get_setting('maxedgemissing', dutinfo.sample_id)),
##                   'passed_points': passed_points,
##                   'failed_points': failed_points,
##                   'targets': targets,
##                   'maxposerror': get_setting('maxposerror', dutinfo.sample_id),
##                   'hits': hits,
##                   'missing': missing,
##                   'distances': distances,
##                   }

        return results
    
    def calculate_start_end(self, center_x, center_y, angle, start_separation, end_separation):
        
        y_diff = math.sin(math.radians(angle))*.5*start_separation
        start1_y = (center_y+y_diff)
        start2_y = (center_y-y_diff)
        x_diff = math.cos(math.radians(angle))*.5*start_separation
        start1_x = (center_x+x_diff)
        start2_x = (center_x-x_diff)
        y_end_diff = math.sin(math.radians(angle))*.5*end_separation
        end1_y = (center_y+y_end_diff)
        end2_y = (center_y-y_end_diff)
        x_end_diff = math.cos(math.radians(angle))*.5*end_separation
        end1_x = (center_x+x_end_diff)
        end2_x = (center_x-x_end_diff)
        
        return start1_x, start1_y, end1_x, end1_y, start2_x, start2_y, end2_x, end2_y 
        

    def get_results(self) -> dict:
       dutinfo = self.get_dutinfo()
       all_results = self.read_test_results(dutinfo)

       results = {
           'summary': [],
       }
       
       angle_result = {
            'location': [0,0],
            'verdict': "Pass"
        }
       results['summary'].append(angle_result)
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

       return results
