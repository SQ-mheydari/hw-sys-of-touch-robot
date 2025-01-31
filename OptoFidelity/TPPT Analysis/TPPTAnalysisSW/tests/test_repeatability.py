# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

import cherrypy
import numpy as np
import numpy.linalg
from genshi.template import MarkupTemplate

from TPPTAnalysisSW.testbase import TestBase, testclasscreator
from TPPTAnalysisSW.imagefactory import ImageFactory
from TPPTAnalysisSW.settings import get_setting
from TPPTAnalysisSW.utils import Timer, exportcsv, max_not_none, verdict_to_str, get_limit_verdict, get_total_verdict
import TPPTAnalysisSW.plot_factory as plot_factory
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.analyzers as analyzers
from TPPTAnalysisSW.measurementdb import *
from TPPTAnalysisSW.info.version import Version

class RepeatabilityTest(TestBase):
    """ A dummy test class for use as a template in creating new test classes """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(10)
    def create_testclass(*args, **kwargs):
        return RepeatabilityTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.test_item (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new RepeatabilityTest class """
        super(RepeatabilityTest, self).__init__(ddtest_row, *args, **kwargs)

    # Create CSV file from the results
    def createcsv(self, *args, **kwargs):
        ''' Create csv file from the measurements '''
        with get_database().session() as dbsession:
            test_results = dbsession.query(OneFingerTapRepeatabilityTest).filter(OneFingerTapRepeatabilityTest.test_id == self.test_id).\
                                                                          order_by(OneFingerTapRepeatabilityTest.point_number)

            return exportcsv(test_results, initialstring='one_finger_tap_repeatability_test\n')

    # Override to make necessary analysis for test session success
    def runanalysis(self, *args, **kwargs):
        """ Runs the analysis, return a string containing the test result """
        results = self.read_test_results()
        points_verdict = verdict_to_str(len(results['failed_points']) == 0)
        return get_total_verdict(points_verdict, results['verdict_x'], results['verdict_y'])

    # Override to make necessary operations for clearing test results
    # Clearing the test result from the results table is done elsewhere
    def clearanalysis(self, *args, **kwargs):
        """ Clears analysis results """
        ImageFactory.delete_images(self.test_id)

    # Create the test report. Return the created HTML, or raise cherrypy.HTTPError
    def createreport(self, *args, **kwargs):

        t = Timer(1)

        self.clearanalysis()

        # Create common template parameters (including test_item dictionary, testsession dictionary, test_id, test_type_name etc)
        templateParams = super(RepeatabilityTest, self).create_common_templateparams(**kwargs)
        verdict = "Pass"
        results = self.read_test_results()
        dutinfo = self.get_dutinfo()

        t.Time("Results")
        # Add the image name and parameters to the report
        templateParams['figure'] = ImageFactory.create_image_name(self.test_id, 'rept')
        templateParams['detailed_figure'] = ImageFactory.create_image_name(self.test_id, 'rept', 'detailed')

        templateParams['results'] = results
        templateParams['repeatability_errors'] = results['repeatability_errors']
        templateParams['max_x_repeatability_error'] = results['max_x_repeatability_error']
        templateParams['verdict_x'] = results['verdict_x']
        templateParams['max_y_repeatability_error'] = results['max_y_repeatability_error']
        templateParams['verdict_y'] = results['verdict_y']
        templateParams['max_repeatability_error'] = results['max_repeatability_error']

        templateParams['test_page'] = 'test_repeatability.html'
        templateParams['test_script'] = 'test_page_subplots.js'
        templateParams['version'] = Version

        azimuth_angles, tilt_angles = self.read_test_angles()
        templateParams['azimuth_angles'] = azimuth_angles
        templateParams['tilt_angles'] = tilt_angles

        # Create individual plot image names
        subfigures = [None] # Use one-based indexing
        for result in results['repeatability_errors']:
            subfigures.append(ImageFactory.create_image_name(self.test_id, "repinfo", str(result[4])))
        templateParams['pointPlots'] = subfigures
        #print str(templateParams['pointPlots'])

        t.Time("Params")

        template = MarkupTemplate(open("templates/test_common_body.html"))
        stream = template.generate(**(templateParams))
        t.Time("Markup")

        if len(results['failed_points']) > 0:
            verdict = "Fail"

        return stream.render('xhtml'), verdict


    # Create images for the report. If the function returns a value, it is used as the new image name (without image path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        if image_name == 'rept':
            # Overview image
            t = Timer(1)
            with get_database().session() as dbsession:
                dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

                results = self.read_test_results(dutinfo=dutinfo, dbsession=dbsession)
                # Modify the labels to show the range of IDs in a cluster
                # Otherwise the labels would overlap
                azimuth_angles, tilt_angles = self.read_test_angles()
                n_angles = len(azimuth_angles) * len(tilt_angles)
                if n_angles > 1:
                    for points in [results['passed_points'], results['failed_points']]:
                        for i, point in enumerate(points):
                            point_id = int(point[2])
                            label = ''
                            if point_id % n_angles == 0:
                                label = f'{point_id - n_angles + 1} - {point_id}'
                            points[i] = (point[0], point[1], label)

                t.Time("DB")
                title = 'Preview: One Finger Tap Repeatability'
                plot_factory.plot_passfail_labels_on_target(imagepath, results, dutinfo, *args, title=title, **kwargs)
                t.Time("Image")
        elif image_name == 'repinfo':
            # Individual point image
            t = Timer(1)
            point_id = int(args[0])
            results = self.read_point_details(point_id)
            t.Time("DB")
            title = 'Preview: One Finger Tap Repeatability details'
            plot_factory.plot_repeatability_details(imagepath, results, *args, **kwargs)
            t.Time("Image")
        else:
            raise cherrypy.HTTPError(message = "No such image in the report")

        return None

    def read_test_angles(self):
        # Use sets to only pick unique values
        azimuth_angles = set()
        tilt_angles = set()

        dbsession = get_database().session()
        columns = OneFingerTapRepeatabilityTest.__table__.columns
        test_results = dbsession.query(OneFingerTapRepeatabilityTest).filter(
            OneFingerTapRepeatabilityTest.test_id == self.test_id). \
            order_by(OneFingerTapRepeatabilityTest.point_number).values(*columns)

        for point in test_results:
            if point.robot_azimuth is not None:
                azimuth_angles.add(float(point.robot_azimuth))
            if point.robot_tilt is not None:
                tilt_angles.add(float(point.robot_tilt))

        dbsession.close()

        return sorted(list(azimuth_angles)), sorted(list(tilt_angles))

    def read_test_results(self, dutinfo = None, dbsession = None):
        if dbsession is None:
            with get_database().session() as dbsession:
                return self.read_test_results(dutinfo, dbsession)
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        columns = OneFingerTapRepeatabilityTest.__table__.columns
        test_results = dbsession.query(OneFingerTapRepeatabilityTest).filter(OneFingerTapRepeatabilityTest.test_id == self.test_id).\
                                                                      order_by(OneFingerTapRepeatabilityTest.point_number).values(*columns)

        # Group the results by the point_id for easier handling
        # At the same time add a running point id as the first member of the array
        results = {}
        point_counter = 0
        for result in test_results:
            if result.panel_x is not None and result.panel_y is not None:
                if result.point_number in results:
                    results[result.point_number].append(result)
                else:
                    results[result.point_number] = [point_counter, result]
                    point_counter += 1

        x_repeatability_errors = [None] * point_counter # Initialize lists for the correct length
        y_repeatability_errors = [None] * point_counter
        verdicts = [None] * point_counter
        point_ids = [None] * point_counter
        passed_points = []
        failed_points = []
        robot_x = [None] * point_counter
        robot_y = [None] * point_counter
        robot_azimuth = [None] * point_counter
        robot_tilt = [None] * point_counter

        for point_id, measurements in results.items():
            x_coordinates = []
            y_coordinates = []
            point_nbr = measurements[0]

            for result in measurements[1:]:
                point = analyzers.panel_to_target((result.panel_x, result.panel_y), dutinfo)
                x_coordinates.append(point[0])
                y_coordinates.append(point[1])

            # Arrays must have at least one coordinate - otherwise they won't exist in db
            x_error = analyzers.round_dec(np.ptp(x_coordinates))
            y_error = analyzers.round_dec(np.ptp(y_coordinates))
            x_repeatability_errors[point_nbr] = x_error
            y_repeatability_errors[point_nbr] = y_error
            point_ids[point_nbr] = point_id

            result = measurements[1]
            robot_x[point_nbr] = analyzers.round_dec(result.robot_x)
            robot_y[point_nbr] = analyzers.round_dec(result.robot_y)
            if result.robot_azimuth is not None:
                robot_azimuth[point_nbr] = float(result.robot_azimuth)
            if result.robot_tilt is not None:
                robot_tilt[point_nbr] = float(result.robot_tilt)

            if (x_error > analyzers.round_dec(get_setting('maxrepeaterror', dutinfo.sample_id))
                    or y_error > analyzers.round_dec(get_setting('maxrepeaterror', dutinfo.sample_id))):
                failed_points.append((measurements[1].robot_x, measurements[1].robot_y, point_nbr + 1))
                verdicts[point_nbr] = "Fail"
            else:
                passed_points.append((measurements[1].robot_x, measurements[1].robot_y, point_nbr + 1))
                verdicts[point_nbr] = "Pass"

        results = {}
        results['x_repeatability_errors'] = x_repeatability_errors
        results['y_repeatability_errors'] = y_repeatability_errors
        if len(x_repeatability_errors) > 0:
            results['max_x_repeatability_error'] = np.max(x_repeatability_errors)
        else:
            results['max_x_repeatability_error'] = None
        if len(y_repeatability_errors) > 0:
            results['max_y_repeatability_error'] = np.max(y_repeatability_errors)
        else:
            results['max_y_repeatability_error'] = None

        # Result tuple for the generator
        results['repeatability_errors'] = list(
            zip(range(1, len(x_repeatability_errors) + 1), x_repeatability_errors, y_repeatability_errors, verdicts,
                point_ids, robot_x, robot_y, robot_azimuth, robot_tilt))
        results['max_repeatability_error'] = max_not_none(results['max_x_repeatability_error'],
                                                          results['max_y_repeatability_error'])

        # For plotting
        results['passed_points'] = passed_points
        results['failed_points'] = failed_points

        results['verdict_x'] = get_limit_verdict(results['max_x_repeatability_error'],
                                                 get_setting('maxrepeaterror', dutinfo.sample_id))
        results['verdict_y'] = get_limit_verdict(results['max_y_repeatability_error'],
                                                 get_setting('maxrepeaterror', dutinfo.sample_id))

        return results

    def read_point_details(self, point_id, dutinfo = None, dbsession = None):
        if dbsession is None:
            with get_database().session() as dbsession:
                return self.read_point_details(point_id, dutinfo, dbsession)
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        points = dbsession.query(OneFingerTapRepeatabilityTest).filter(OneFingerTapRepeatabilityTest.test_id == self.test_id,
                                                                       OneFingerTapRepeatabilityTest.point_number == point_id).all()

        results = {}
        points_arr = []
        passed = []
        passed_count = []
        failed = []
        failed_count = []
        results['robot_point'] = (0,0)

        for point in points:
            results['robot_point'] = [point.robot_x, point.robot_y] # This will be overwritten in each round
            if point.panel_x is not None and point.panel_y is not None:
                points_arr.append(analyzers.panel_to_target((point.panel_x, point.panel_y), dutinfo))

        if len(points_arr) > 0:
            average_point = np.average(points_arr, axis=0)
            results['average_point'] = average_point
            top_left = np.min(points_arr, axis=0)

            for point in points_arr:
                distance = max([point[0] - top_left[0], point[1] - top_left[1]])
                if distance > get_setting('maxrepeaterror', dutinfo.sample_id):
                    if point in failed:
                        failed_count[failed.index(point)] += 1
                    else:
                        failed.append(point)
                        failed_count.append(1)
                else:
                    if point in passed:
                        passed_count[passed.index(point)] += 1
                    else:
                        passed.append(point)
                        passed_count.append(1)

        results['passed_points'] = passed
        results['passed_points_count'] = passed_count
        results['failed_points'] = failed
        results['failed_points_count'] = failed_count
        if len(points_arr) > 0:
            # Top-left has been declared before
            reference = top_left
            x_range = np.ptp([p[0] for p in points_arr])
            y_range = np.ptp([p[1] for p in points_arr])
            if x_range < get_setting('maxrepeaterror', dutinfo.sample_id):
                reference[0] = top_left[0] + ((x_range - float(get_setting('maxrepeaterror', dutinfo.sample_id))) / 2)
            if y_range < get_setting('maxrepeaterror', dutinfo.sample_id):
                reference[1] = top_left[1] + ((y_range - float(get_setting('maxrepeaterror', dutinfo.sample_id))) / 2)

            results['reference_point'] = reference
            results['distance'] = get_setting('maxrepeaterror', dutinfo.sample_id)

        return results

    def get_results(self) -> dict:
        dutinfo = self.get_dutinfo()
        all_results = self.read_test_results(dutinfo)
        azimuth_angles, tilt_angles = self.read_test_angles()

        x_verdict = all_results['verdict_x']
        y_verdict = all_results['verdict_y']
        results = {
            'repeatability_error_x':  all_results['max_x_repeatability_error'],
            'repeatability_error_x_verdict': x_verdict,
            'repeatability_error_y': all_results['max_y_repeatability_error'],
            'repeatability_error_y_verdict': y_verdict,
            'points': []
        }

        for point in all_results['repeatability_errors']:
            point_results = {
                'point_id': point[0],
                'x': point[5],
                'y': point[6],
                'dx': point[1],
                'dy': point[2],
                'verdict': point[3]
            }
            if azimuth_angles:
                point_results['azimuth'] = point[7]
            if tilt_angles:
                point_results['tilt'] = point[8]
            results['points'].append(point_results)

        return results
