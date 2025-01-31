# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

import cherrypy
from genshi.template import MarkupTemplate
from sqlalchemy.orm import joinedload
import numpy

from TPPTAnalysisSW.testbase import TestBase, testclasscreator
from TPPTAnalysisSW.imagefactory import ImageFactory
from TPPTAnalysisSW.measurementdb import *
from TPPTAnalysisSW.utils import Timer, exportcsv, verdict_to_str, get_total_verdict
from TPPTAnalysisSW.settings import get_setting
from TPPTAnalysisSW.info.version import Version
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.plot_factory as plot_factory
import TPPTAnalysisSW.analyzers as analyzers


class NonStationaryReportingRateTest(TestBase):
    """ A dummy test class for use as a template in creating new test classes """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(12)
    def create_testclass(*args, **kwargs):
        return NonStationaryReportingRateTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.test_item (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new NonStationaryReportingRateTest class """
        super(NonStationaryReportingRateTest, self).__init__(ddtest_row, *args, **kwargs)

    # Create CSV file from the results
    def createcsv(self, *args, **kwargs):
        """ Create csv file from the measurements """
        with get_database().session() as dbsession:
            test_results = dbsession.query(OneFingerNonStationaryReportingRateTest).filter(
                OneFingerNonStationaryReportingRateTest.test_id == self.test_id). \
                order_by(OneFingerNonStationaryReportingRateTest.id). \
                options(joinedload('one_finger_non_stationary_reporting_rate_results'))

            return exportcsv(test_results, subtable='one_finger_non_stationary_reporting_rate_results')

    # Override to make necessary analysis for test session success
    def runanalysis(self, *args, **kwargs):
        """ Runs the analysis, return a string containing the test result """
        results = self.read_test_results()
        return results['verdict']

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
        templateParams = super(NonStationaryReportingRateTest, self).create_common_templateparams(**kwargs)

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
        templateParams['missing_lines'] = results['missing_lines']
        templateParams['detailed_data'] = zip(results['swipe_ids'], results['max_reporting_rates'],
                                              results['min_reporting_rates'], results['average_reporting_rates'],
                                              results['verdicts'], results['images'])

        # Add the image name and parameters to the report
        templateParams['figure'] = ImageFactory.create_image_name(self.test_id, 'nonstrr')
        templateParams['detailed_figure'] = ImageFactory.create_image_name(self.test_id, 'nonstrr', 'detailed')

        # set the content to be used
        templateParams['test_page'] = 'test_non_stationary_reporting_rate.html'
        templateParams['test_script'] = 'test_page_subplots.js'
        templateParams['version'] = Version
        s.Time("Parameters")

        template = MarkupTemplate(open("templates/test_common_body.html"))
        stream = template.generate(**(templateParams))
        s.Time("Generate")
        return stream.render('xhtml'), results['verdict']

    # Create images for the report. If the function returns a value, it is used as the new image name (without image path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        if image_name == 'nonstrr':
            with get_database().session() as dbsession:
                dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
                results = self.read_test_results()
                title = 'Preview: Non-stationary reporting rate'
                plot_factory.plot_swipes_on_target_with_labels(imagepath, results, dutinfo, *args, title=title,
                                                               **kwargs)
        elif image_name == 'nonstrdtl':
            with get_database().session() as dbsession:
                dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
                results = self.read_swipe_info(args[0], dutinfo=dutinfo, dbsession=dbsession)
                title = 'Preview: Non-stationary reporting rate'
                plot_factory.plot_reporting_rate(imagepath, results, title=title, **kwargs)
        else:
            raise cherrypy.HTTPError(message="No such image in the report")

        return None

    def read_test_results(self, dutinfo=None, dbsession=None):

        s = Timer(2)

        if dbsession is None:
            with get_database().session() as dbsession:
                return self.read_test_results(dutinfo, dbsession)
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        test_results = dbsession.query(OneFingerNonStationaryReportingRateTest).filter(
            OneFingerNonStationaryReportingRateTest.test_id == self.test_id). \
            order_by(OneFingerNonStationaryReportingRateTest.id). \
            options(joinedload('one_finger_non_stationary_reporting_rate_results')).all()

        s.Time("DB")

        max_reporting_rates = []
        min_reporting_rates = []
        average_reporting_rates = []
        verdicts = []
        swipe_id = 0
        swipe_ids = []
        passed_points = []
        failed_points = []
        images = []
        lines = []
        missing_lines = 0
        if get_setting('minreportingrate', dutinfo.sample_id) > 0.0:
            accept_delay = (1000.0 / float(get_setting('minreportingrate', dutinfo.sample_id)))
        else:
            accept_delay = 0.0

        for test_result in test_results:
            max_reporting_rate = 0.0
            min_reporting_rate = 0.0
            previous_timestamp = 0.0
            max_delay = 0.0
            min_delay = 0.0
            delays = []
            verdict = "N/A"  # No points
            for result in test_result.one_finger_non_stationary_reporting_rate_results:
                if previous_timestamp == 0.0:
                    previous_timestamp = result.time
                    passed_points.append((result.panel_x, result.panel_y))
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
                        failed_points.append((result.panel_x, result.panel_y))
                        verdict = "Fail"
                    else:
                        passed_points.append((result.panel_x, result.panel_y))
                        if verdict == "N/A":
                            verdict = "Pass"  # At least one point exists -> Pass (if not later set to fail)

            if len(test_result.one_finger_non_stationary_reporting_rate_results) == 0:
                verdict = "Fail"  # If no points in the measurement -> missing line
                missing_lines += 1

            min_reporting_rate = analyzers.round_dec(1.0 / (max_delay / 1000.0)) if max_delay != 0.0 else None
            max_reporting_rate = analyzers.round_dec(1.0 / (min_delay / 1000.0)) if min_delay != 0.0 else None

            avg_delay = numpy.average(delays) if len(delays) > 0 else 0.0
            average_reporting_rate = analyzers.round_dec(1.0 / (avg_delay / 1000)) if avg_delay != 0.0 else None

            if average_reporting_rate is None:
                verdict = "Fail"

            min_reporting_rates.append(min_reporting_rate)
            max_reporting_rates.append(max_reporting_rate)
            average_reporting_rates.append(average_reporting_rate)
            lines.append(((test_result.start_x, test_result.start_y), (test_result.end_x, test_result.end_y)))
            verdicts.append(verdict)
            swipe_id += 1
            swipe_ids.append(swipe_id)
            images.append(ImageFactory.create_image_name(self.test_id, 'nonstrdtl', str(test_result.id)))

        s.Time("Analysis")

        results = {}
        results['swipe_ids'] = swipe_ids
        results['max_reporting_rates'] = max_reporting_rates
        results['min_reporting_rates'] = min_reporting_rates
        results['average_reporting_rates'] = average_reporting_rates
        results['verdicts'] = verdicts
        results['images'] = images
        results['passed_points'] = analyzers.panel_to_target(passed_points, dutinfo)
        results['failed_points'] = analyzers.panel_to_target(failed_points, dutinfo)
        results['lines'] = analyzers.robot_to_target(lines, dutinfo)
        results['missing_lines'] = missing_lines

        try:
            results['slowest_reporting_rate'] = numpy.min([f for f in results['min_reporting_rates'] if f is not None])
            results['slowest_verdict'] = "Pass" \
                if (results['slowest_reporting_rate'] > get_setting('minreportingrate', dutinfo.sample_id)
                                                                   and results['missing_lines'] == 0) else "Fail"
        except ValueError:
            results['slowest_reporting_rate'] = None
            results['slowest_verdict'] = "N/A"
        try:
            values = [f for f in results['min_reporting_rates'] if f is not None]
            results['average_slowest_reporting_rate'] = numpy.mean(values) if len(values) != 0 else None
        except ValueError:
            results['average_slowest_reporting_rate'] = None
        try:
            results['fastest_reporting_rate'] = numpy.max([f for f in results['max_reporting_rates'] if f is not None])
            if results['fastest_reporting_rate'] is numpy.nan:
                results['fastest_reporting_rate'] = None
        except ValueError:
            results['fastest_reporting_rate'] = None
        try:
            values = [f for f in results['average_reporting_rates'] if f is not None]
            results['average_reporting_rate'] = numpy.mean(values) if len(values) != 0 else None
            results['avg_verdict'] = "Pass" if \
                results['average_reporting_rate'] > get_setting('minavgreportingrate', dutinfo.sample_id) else "Fail"
        except (ValueError, TypeError):
            results['average_reporting_rate'] = None
            results['avg_verdict'] = "N/A"

        lines_verdict = verdict_to_str(results['missing_lines'] == 0)
        results['verdict'] = get_total_verdict(lines_verdict, results['slowest_verdict'], results['avg_verdict'])

        return results

    def read_swipe_info(self, swipe_id, dutinfo=None, dbsession=None):

        s = Timer(2)

        if dbsession is None:
            with get_database().session() as dbsession:
                return self.read_swipe_info(swipe_id, dutinfo, dbsession)
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        swipe = dbsession.query(OneFingerNonStationaryReportingRateTest).filter(
            OneFingerNonStationaryReportingRateTest.id == swipe_id). \
            order_by(OneFingerNonStationaryReportingRateTest.id). \
            options(joinedload('one_finger_non_stationary_reporting_rate_results')).first()

        points = []
        pindex = 0
        passed = []
        failed = []
        delays = []
        max_delay = None
        min_delay = None
        previous_timestamp = 0.0
        # start = analyzers.robot_to_target((swipe.start_x, swipe.start_y), dutinfo)
        # end = analyzers.robot_to_target((swipe.end_x, swipe.end_y), dutinfo)
        # transform = analyzers.panel_to_target_transform(dutinfo) + analyzers.target_to_swipe_transform(start, end)

        if get_setting('minreportingrate', dutinfo.sample_id) > 0.0:
            accept_delay = (1000.0 / float(get_setting('minreportingrate', dutinfo.sample_id)))
        else:
            accept_delay = 0.0

        for result in swipe.one_finger_non_stationary_reporting_rate_results:
            # point = transform.transform(((result.panel_x, result.panel_y)))
            # points.append(point)
            if previous_timestamp == 0.0:
                previous_timestamp = result.time
                # passed.append((pindex, 0,0))
                # delays.append(None)
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
                   'max_allowed_delay': analyzers.round_dec(
                       1.0 / (float(get_setting('minreportingrate', dutinfo.sample_id)) / 1000.0)),
                   # 'points': points,
                   'delays': delays,
                   'max_delay': max_delay,
                   'min_delay': min_delay
                   }

        return results

    def get_results(self) -> dict:
        all_results = self.read_test_results()
        results = {
            'minimum_reporting_rate': all_results['slowest_reporting_rate'],
            'minimum_reporting_rate_verdict': all_results['slowest_verdict'],
            'average_minimum_reporting_rate': all_results['average_slowest_reporting_rate'],
            'average_reporting_rate': all_results['average_reporting_rate'],
            'average_reporting_rate_verdict': all_results['avg_verdict'],
            'missing_lines': all_results['missing_lines'],
            'missing_lines_verdict': verdict_to_str(all_results['missing_lines'] == 0),
            'swipes': []
        }

        for result in zip(all_results['swipe_ids'], all_results['max_reporting_rates'],
                          all_results['min_reporting_rates'], all_results['average_reporting_rates'],
                          all_results['verdicts']):
            point = {
                'swipe_id': result[0],
                'max_reporting_rate': result[1],
                'min_reporting_rate': result[2],
                'avg_reporting_rate': result[3],
                'verdict': result[4]
            }
            results['swipes'].append(point)

        return results
