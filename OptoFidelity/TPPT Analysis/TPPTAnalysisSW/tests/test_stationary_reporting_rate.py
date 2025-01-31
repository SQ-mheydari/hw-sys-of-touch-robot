# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

import cherrypy
import numpy
from genshi.template import MarkupTemplate
from sqlalchemy.orm import joinedload

from TPPTAnalysisSW.testbase import TestBase, testclasscreator
from TPPTAnalysisSW.imagefactory import ImageFactory
from TPPTAnalysisSW.measurementdb import get_database, OneFingerStationaryReportingRateTest
from TPPTAnalysisSW.settings import get_setting
from TPPTAnalysisSW.utils import Timer, exportcsv, get_total_verdict, get_limit_verdict
from TPPTAnalysisSW.info.version import Version
import TPPTAnalysisSW.plot_factory as plot_factory
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.analyzers as analyzers

class StationaryReportingRateTest(TestBase):
    """ A dummy test class for use as a template in creating new test classes """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(11)
    def create_testclass(*args, **kwargs):
        return StationaryReportingRateTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.test_item (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new StationaryReportingRateTest class """
        super(StationaryReportingRateTest, self).__init__(ddtest_row, *args, **kwargs)

    # Create CSV file from the results
    def createcsv(self, *args, **kwargs):
        ''' Create csv file from the measurements '''
        with get_database().session() as dbsession:
            test_results = dbsession.query(OneFingerStationaryReportingRateTest).filter(OneFingerStationaryReportingRateTest.test_id == self.test_id).\
                                                                                 order_by(OneFingerStationaryReportingRateTest.id).\
                                                                                 options(joinedload('one_finger_stationary_reporting_rate_results'))

            return exportcsv(test_results, subtable='one_finger_stationary_reporting_rate_results')

    # Override to make necessary analysis for test session success
    def runanalysis(self, *args, **kwargs):
        """ Runs the analysis, return a string containing the test result """
        results = self.read_test_results()

        return results["verdict"]

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
        templateParams = super(StationaryReportingRateTest, self).create_common_templateparams(**kwargs)

        s.Time("Init")

        # Read test results
        results = self.read_test_results()

        s.Time("Results")

        templateParams['total_verdict'] = results['verdict']
        templateParams['slowest_verdict'] = results['slowest_verdict']
        templateParams['avg_verdict'] = results['avg_verdict']
        templateParams['slowest_reporting_rate'] = results['slowest_reporting_rate']
        templateParams['average_slowest_reporting_rate'] = results['average_slowest_reporting_rate']
        templateParams['fastest_reporting_rate'] = results['fastest_reporting_rate']
        templateParams['average_reporting_rate'] = results['average_reporting_rate']
        templateParams['detailed_data'] = zip(results['point_ids'], results['max_reporting_rates'],
                                              results['min_reporting_rates'], results['average_reporting_rates'], results['verdicts'], results['images'])

        # Add the image name and parameters to the report
        templateParams['figure'] = ImageFactory.create_image_name(self.test_id, 'strr')
        templateParams['detailed_figure'] = ImageFactory.create_image_name(self.test_id, 'strr', 'detailed')

        # set the content to be used
        templateParams['test_page'] = 'test_stationary_reporting_rate.html'
        templateParams['test_script'] = 'test_page_subplots.js'
        templateParams['version'] = Version
        s.Time("Parameters")

        template = MarkupTemplate(open("templates/test_common_body.html"))
        stream = template.generate(**(templateParams))
        s.Time("Generate")

        return stream.render('xhtml'), results["verdict"]

    # Create images for the report. If the function returns a value, it is used as the new image name (without image path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        if image_name == 'strr':
            with get_database().session() as dbsession:
                dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
                results = self.read_test_results()
                title = 'Preview: Stationary reporting rate'
                plot_factory.plot_passfail_labels_on_target(imagepath, results, dutinfo, *args, title=title, **kwargs)
        elif image_name == 'strrdtls':
            with get_database().session() as dbsession:
                dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
                results = self.read_point_info(args[0], dutinfo=dutinfo, dbsession=dbsession)
                title = 'Preview: Stationary reporting rate'
                plot_factory.plot_reporting_rate(imagepath, results, title=title, **kwargs)
        else:
            raise cherrypy.HTTPError(message = "No such image in the report")

        return None

    def read_test_results(self, dutinfo = None, dbsession = None):

        t = Timer(2)

        if dbsession is None:
            with get_database().session() as dbsession:
                return self.read_test_results(dutinfo, dbsession)
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        test_results = dbsession.query(OneFingerStationaryReportingRateTest).filter(OneFingerStationaryReportingRateTest.test_id == self.test_id).\
                                                                             order_by(OneFingerStationaryReportingRateTest.id).\
                                                                             options(joinedload('one_finger_stationary_reporting_rate_results')).all()

        t.Time("DB")

        max_reporting_rates = []
        min_reporting_rates = []
        average_reporting_rates = []
        verdicts = []
        point_id = 0
        point_ids = []
        passed_points = []
        failed_points = []
        images = []

        if get_setting('minreportingrate', dutinfo.sample_id) > 0.0:
            accept_delay = (1000.0 / float(get_setting('minreportingrate', dutinfo.sample_id)))
        else:
            accept_delay = 0.0

        for test_result in test_results:
            results = test_result.one_finger_stationary_reporting_rate_results
            max_reporting_rate = 0.0
            min_reporting_rate = 0.0
            previous_timestamp = 0.0
            max_delay = 0.0
            min_delay = 0.0
            delays = []
            verdict = "N/A" # No points
            for result in results:
                if previous_timestamp == 0.0:
                    previous_timestamp = result.time
                else:
                    delay = result.time - previous_timestamp
                    delays.append(delay)
                    if delay >= max_delay:
                        max_delay = delay
                    if min_delay == 0.0:
                        min_delay = delay
                    elif delay > 0.0 and delay < min_delay:
                        min_delay = delay
                    previous_timestamp = result.time

                    if delay > accept_delay:
                        verdict = "Fail"
                    elif verdict == "N/A":
                        verdict = "Pass" # At least one accepted point exists -> Pass (if not later set to fail)

            min_reporting_rate = analyzers.round_dec(1.0/(max_delay/1000.0)) if max_delay != 0.0 else None
            max_reporting_rate = analyzers.round_dec(1.0/(min_delay/1000.0)) if min_delay != 0.0 else None

            avg_delay = numpy.average(delays) if len(delays) > 0 else 0.0
            average_reporting_rate = analyzers.round_dec(1.0/(avg_delay/1000)) if avg_delay != 0.0 else None

            if average_reporting_rate is None:
                verdict = "Fail"

            min_reporting_rates.append(min_reporting_rate)
            max_reporting_rates.append(max_reporting_rate)
            average_reporting_rates.append(average_reporting_rate)
            point_id += 1
            point_ids.append(point_id)
            if verdict == "Pass":
                point = analyzers.robot_to_target((test_result.robot_x, test_result.robot_y), dutinfo)
                passed_points.append((point[0], point[1], point_id, verdict))
            else:
                point = analyzers.robot_to_target((test_result.robot_x, test_result.robot_y), dutinfo)
                failed_points.append((point[0], point[1], point_id, verdict))
            verdicts.append(verdict)
            images.append(ImageFactory.create_image_name(self.test_id, 'strrdtls', str(test_result.id)))

        t.Time("Analysis")

        results = {}
        results['point_ids'] = point_ids
        results['max_reporting_rates'] = max_reporting_rates
        results['min_reporting_rates'] = min_reporting_rates
        results['average_reporting_rates'] = average_reporting_rates
        results['failed_points'] = failed_points
        results['passed_points'] = passed_points
        results['verdicts'] = verdicts
        results['images'] = images

        try:
            results['slowest_reporting_rate'] = numpy.min([f for f in results['min_reporting_rates'] if f is not None])
        except ValueError:
            results['slowest_reporting_rate'] = None
        try:
            values = [f for f in results['min_reporting_rates'] if f is not None]
            results['average_slowest_reporting_rate'] = numpy.mean(values) if len(values) != 0 else None
        except ValueError:
            results['average_slowest_reporting_rate'] = None
        try:
            results['fastest_reporting_rate'] = numpy.max([f for f in results['max_reporting_rates'] if f is not None])
        except ValueError:
            results['fastest_reporting_rate'] = None

        results['slowest_verdict'] = get_limit_verdict(results['slowest_reporting_rate'],
                                                       get_setting('minreportingrate', dutinfo.sample_id),
                                                       lower_bound=True)

        try:
            values = [f for f in results['average_reporting_rates'] if f is not None]
            results['average_reporting_rate'] = numpy.mean(values) if len(values) != 0 else None
            results['avg_verdict'] = get_limit_verdict(results['average_reporting_rate'],
                                                       get_setting('minavgreportingrate', dutinfo.sample_id),
                                                       lower_bound=True)
        except (ValueError, TypeError):
            results['average_reporting_rate'] = None
            results['avg_verdict'] = "N/A"

        results['verdict'] = get_total_verdict(results['slowest_verdict'], results['avg_verdict'])

        return results

    def read_point_info(self, point_id, dutinfo = None, dbsession = None):

        s = Timer(2)

        if dbsession is None:
            with get_database().session() as dbsession:
                return self.read_point_info(point_id, dutinfo, dbsession)
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        point = dbsession.query(OneFingerStationaryReportingRateTest).filter(OneFingerStationaryReportingRateTest.id == point_id).\
                                                                             options(joinedload('one_finger_stationary_reporting_rate_results')).first()

        points = []
        pindex = 0
        passed = []
        failed = []
        delays = []
        max_delay = None
        min_delay = None
        previous_timestamp = 0.0

        if get_setting('minreportingrate', dutinfo.sample_id) > 0.0:
            accept_delay = (1000.0 / float(get_setting('minreportingrate', dutinfo.sample_id)))
        else:
            accept_delay = 0.0

        for result in point.one_finger_stationary_reporting_rate_results:
            if previous_timestamp == 0.0:
                previous_timestamp = result.time
            else:
                delay = result.time - previous_timestamp
                if delay > 0.0:
                    delays.append(delay)
                    previous_timestamp = result.time

                    if max_delay is None or max_delay < delay:
                        max_delay = delay

                    if min_delay is None or min_delay > delay:
                        min_delay = delay

                    if delay > accept_delay:
                        failed.append((pindex, delay))
                    else:
                        passed.append((pindex, delay))
                    pindex += 1

        results = {'passed': passed,
                   'failed': failed,
                   'max_allowed_delay': analyzers.round_dec(1.0/(float(get_setting('minreportingrate', dutinfo.sample_id))/1000.0)),
                   #'points': points,
                   'delays': delays,
                   'max_delay': max_delay,
                   'min_delay': min_delay
                   }

        return results

    def get_results(self) -> dict:
        dutinfo = self.get_dutinfo()
        all_results = self.read_test_results(dutinfo)
        results = {
            'minimum_reporting_rate': all_results['slowest_reporting_rate'],
            'minimum_reporting_rate_verdict': all_results['slowest_verdict'],
            'average_minimum_reporting_rate': all_results['average_slowest_reporting_rate'],
            'average_reporting_rate': all_results['average_reporting_rate'],
            'average_reporting_rate_verdict': all_results['avg_verdict'],
            'points': []
        }

        points = zip(all_results['point_ids'], all_results['max_reporting_rates'], all_results['min_reporting_rates'],
                     all_results['average_reporting_rates'], all_results['verdicts'])
        for point in points:
            point_results = {
                'point_id': point[0],
                'max_reporting_rate': point[1],
                'min_reporting_rate': point[2],
                'avg_reporting_rate': point[3],
                'verdict': point[4]
            }
            results['points'].append(point_results)

        return results
