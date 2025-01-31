# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

import cherrypy
import threading
from genshi.template import MarkupTemplate
from sqlalchemy.orm import joinedload
from numpy import mean

from TPPTAnalysisSW.testbase import TestBase, testclasscreator
from TPPTAnalysisSW.imagefactory import ImageFactory
from TPPTAnalysisSW.settings import get_setting
from TPPTAnalysisSW.utils import Timer, exportcsv, verdict_to_str, is_swipe_diagonal, swipe_direction
from TPPTAnalysisSW.info.version import Version
import TPPTAnalysisSW.measurementdb as measurementdb
import TPPTAnalysisSW.analyzers as analyzers
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.plot_factory as plot_factory
from TPPTAnalysisSW.tests.utils import detect_incomplete_swipes

class OneFingerSwipeTest(TestBase):
    """ A dummy test class for use as a template in creating new test classes """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(1)
    def create_testclass(*args, **kwargs):
        return OneFingerSwipeTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.test_item (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new OneFingerSwipeTest class """
        super(OneFingerSwipeTest, self).__init__(ddtest_row, *args, **kwargs)

    # Create CSV file from the results
    def createcsv(self, *args, **kwargs):
        """ Create csv file from the measurements """
        with measurementdb.get_database().session() as dbsession:
            dbswipes = dbsession.query(measurementdb.OneFingerSwipeTest).filter(measurementdb.OneFingerSwipeTest.test_id==self.test_id).\
                                                                         join(measurementdb.OneFingerSwipeResults).\
                                                                         order_by(measurementdb.OneFingerSwipeTest.id, measurementdb.OneFingerSwipeResults.id)

            return exportcsv(dbswipes, subtable='one_finger_swipe_results')

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

        self.clearanalysis()

        # Create common template parameters (including test_item dictionary, testsession dictionary, test_id, test_type_name etc)
        templateParams = super(OneFingerSwipeTest, self).create_common_templateparams(**kwargs)

        s = Timer()
        s.Time("START")

        results = self.read_test_results()

        s.Time("Results")

        templateParams['results'] = results
        templateParams['figure'] = ImageFactory.create_image_name(self.test_id, "swipes")
        templateParams['detailed_figure'] = ImageFactory.create_image_name(self.test_id, "swipes", "detailed")
        templateParams['test_page'] = 'test_one_finger_swipe.html'
        templateParams['test_script'] = 'test_page_subplots.js'
        templateParams['version'] = Version
        azimuth_angles, tilt_angles = self.read_test_angles()
        templateParams['azimuth_angles'] = azimuth_angles
        templateParams['tilt_angles'] = tilt_angles

        template = MarkupTemplate(open("templates/test_common_body.html"))
        stream = template.generate(**(templateParams))
        s.Time("READY")

        # Start creating the preview image already - the call will probably come soon
        # NOTE: this is not necessary in summary tests
        if 'noimages' not in kwargs:
            threading.Thread(target = self.createpreviewimage, args = (results,)).start()

        return stream.render('xhtml'), results['verdict']

    def createpreviewimage(self, results):
        """ Creates a swipe preview image with the specified results """
        imagepath = ImageFactory.create_image_path(self.test_id, "swipes")
        with measurementdb.get_database().session() as dbsession:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            title = 'Preview: One Finger Swipe'
            plot_factory.plot_swipes_on_target(imagepath, results, dutinfo, title=title)

    # Create images for the report. If the function returns a value, it is used as the new image (including full path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        if image_name == 'swipes':
            # See above: preview image is normally generated after the report creation
            with measurementdb.get_database().session() as dbsession:
                dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
                pinfo = self.read_test_results(dbsession=dbsession, dutinfo=dutinfo)
                title = 'Preview: One Finger Swipe'
                plot_factory.plot_swipes_on_target(imagepath, pinfo, dutinfo, *args, title=title, **kwargs)
        elif image_name == 'jittdtls':
            with measurementdb.get_database().session() as dbsession:
                dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
                results = self.read_swipe_details(args[0], dbsession=dbsession, dutinfo=dutinfo)
                title = 'Preview: One Finger Swipe details'
                plot_factory.plot_one_finger_swipe_with_linear_fit(imagepath, results, dutinfo, title=title, **kwargs)
        else:
            raise cherrypy.HTTPError(message = "No such image in the report")

        return None

    def read_test_angles(self):
        # Use sets to only pick unique values
        azimuth_angles = set()
        tilt_angles = set()

        dbsession = measurementdb.get_database().session()
        dbswipes = dbsession.query(measurementdb.OneFingerSwipeTest).filter(
            measurementdb.OneFingerSwipeTest.test_id == self.test_id). \
            options(joinedload('one_finger_swipe_results')). \
            order_by(measurementdb.OneFingerSwipeTest.id)

        for swipe in dbswipes:
            if swipe.robot_azimuth is not None:
                azimuth_angles.add(float(swipe.robot_azimuth))
            if swipe.robot_tilt is not None:
                tilt_angles.add(float(swipe.robot_tilt))

        dbsession.close()

        return sorted(list(azimuth_angles)), sorted(list(tilt_angles))

    def read_test_results(self, dutinfo = None, dbsession = None):

        s = Timer(2)
        if dbsession is None:
            with measurementdb.get_database().session() as dbsession:
                return self.read_test_results(dutinfo, dbsession)
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        dbswipes = dbsession.query(measurementdb.OneFingerSwipeTest).filter(measurementdb.OneFingerSwipeTest.test_id==self.test_id).\
                                                                     options(joinedload('one_finger_swipe_results')).\
                                                                     order_by(measurementdb.OneFingerSwipeTest.id)

        s.Time('DB')

        max_jitter = None
        jitter_verdict = "N/A"
        max_offset = None
        offset_verdict = "N/A"
        max_offsets_from_linear_fit = []
        swipes = []
        missing_swipes = []
        swipe_id = 1
        lines = []
        passed_points = []
        failed_points = []
        incomplete_swipes = 0
        max_discontinuity = get_setting('maxswipediscontinuity', dutinfo.sample_id)
        max_diagonal_jitter = None
        diagonal_jitter_verdict = "N/A"
        max_diagonal_offset = None
        diagonal_offset_verdict = "N/A"

        use_diagonal_offset = get_setting("maxdiagoffset", dutinfo.sample_id) > 0
        use_diagonal_jitter = get_setting("maxdiagjitter", dutinfo.sample_id) > 0

        diagonal_swipes = False
        nondiagonal_swipes = False

        for swipe in dbswipes:
            assert(swipe.start_x is not None)
            assert(swipe.start_y is not None)
            assert(swipe.end_x is not None)
            assert(swipe.end_y is not None)

            swipe_gaps_count = 0

            panel_points = [(p.panel_x, p.panel_y) for p in swipe.one_finger_swipe_results]
            # Transform panel -> robot -> swipe
            target_points = analyzers.panel_to_target(panel_points, dutinfo)
            swipe_start, swipe_end = analyzers.robot_to_target([(swipe.start_x, swipe.start_y), (swipe.end_x, swipe.end_y)], dutinfo)
            lines.append((swipe_start, swipe_end))
            swipe_points = analyzers.target_to_swipe(target_points, swipe_start, swipe_end)
            swipe_results = analyzers.analyze_swipe_jitter(swipe_points, float(get_setting('jittermask', dutinfo.sample_id)))
            linearity_results = analyzers.analyze_swipe_linearity(swipe_points)

            diagonal = is_swipe_diagonal(swipe_start, swipe_end)
            if diagonal:
                diagonal_swipes = True
            else:
                nondiagonal_swipes = True

            # Check is NaN
            if linearity_results['lin_error_max'] == linearity_results['lin_error_max']:
                max_offsets_from_linear_fit.append(linearity_results['lin_error_max'])

            passfail_values = [analyzers.round_dec(abs(p[1])) <= get_setting('maxoffset', dutinfo.sample_id) for p in swipe_points]
            passed = [target_points[i] for (i,t) in enumerate(passfail_values) if t]
            failed = [target_points[i] for (i,t) in enumerate(passfail_values) if not t]
            passed_points.extend(passed)
            failed_points.extend(failed)

            swipe_verdict = "N/A"

            max_offset_limit = get_setting('maxoffset', dutinfo.sample_id)
            max_jitter_limit = get_setting('maxjitter', dutinfo.sample_id)
            if diagonal:
                if use_diagonal_offset:
                    max_offset_limit = get_setting("maxdiagoffset", dutinfo.sample_id)
                if use_diagonal_jitter:
                    max_jitter_limit = get_setting("maxdiagjitter", dutinfo.sample_id)

            def update_max_value_and_verdict(value, max_value, value_limit, verdict):
                nonlocal swipe_verdict
                if max_value is None or value > max_value:
                    max_value = value
                if value > value_limit:
                    verdict = "Fail"
                    swipe_verdict = "Fail"
                else:
                    if swipe_verdict != "Fail":
                        swipe_verdict = "Pass"
                    if verdict == "N/A":
                        verdict = "Pass"
                return max_value, verdict

            offset = None
            average_offset = None
            jitter = None
            average_jitter = None
            if len(swipe_points) > 0:

                swipe_gaps_count = len(detect_incomplete_swipes(swipe_points, max_discontinuity))
                offset = analyzers.round_dec(max([abs(p[1]) for p in swipe_points]))
                average_offset = analyzers.round_dec(mean([abs(p[1]) for p in swipe_points]))
                if diagonal and use_diagonal_offset:
                    max_diagonal_offset, diagonal_offset_verdict = update_max_value_and_verdict(
                        offset, max_diagonal_offset, max_offset_limit, diagonal_offset_verdict)
                else:
                    max_offset, offset_verdict = update_max_value_and_verdict(offset, max_offset, max_offset_limit,
                                                                              offset_verdict)

                jitter = analyzers.round_dec(swipe_results['max_jitter']) if 'max_jitter' in swipe_results else None
                average_jitter = analyzers.round_dec(swipe_results['average_jitter']) if 'jitters' in swipe_results \
                    else None
                if jitter is not None:
                    if diagonal and use_diagonal_jitter:
                        max_diagonal_jitter, diagonal_jitter_verdict = update_max_value_and_verdict(
                            jitter, max_diagonal_jitter, max_jitter_limit, diagonal_jitter_verdict)
                    else:
                        max_jitter, jitter_verdict = update_max_value_and_verdict(jitter, max_jitter, max_jitter_limit,
                                                                                  jitter_verdict)

                if swipe_gaps_count > 0:
                    incomplete_swipes += 1
                    swipe_verdict = "Fail"

            else:
                swipe_verdict = "Fail"
                missing_swipes.append(swipe.id)

            azimuth = float(swipe.robot_azimuth) if swipe.robot_azimuth is not None else None
            tilt = float(swipe.robot_tilt) if swipe.robot_tilt is not None else None
            direction = swipe_direction(swipe_start, swipe_end)

            swipes.append((swipe_id, jitter, offset, swipe_verdict,
                           ImageFactory.create_image_name(self.test_id, "jittdtls", str(swipe.id)),
                           azimuth, tilt, swipe_gaps_count, average_jitter, average_offset, direction))
            swipe_id += 1

        s.Time('Analysis')
        if len(max_offsets_from_linear_fit) > 0:
            linear_fit_avg = float(sum(max_offsets_from_linear_fit)) / len(max_offsets_from_linear_fit)
        else:
            linear_fit_avg = None

        results = {'max_jitter': max_jitter,
                   'average_max_jitter': analyzers.round_dec(analyzers.mean([swipe[1] for swipe in swipes])),
                   'average_jitter': analyzers.round_dec(analyzers.mean([swipe[7] for swipe in swipes])),
                   'jitter_verdict': jitter_verdict,
                   'max_offset': max_offset,
                   'average_max_offset': analyzers.round_dec(analyzers.mean([swipe[2] for swipe in swipes])),
                   'average_offset': analyzers.round_dec(analyzers.mean([swipe[8] for swipe in swipes])),
                   'offset_verdict': offset_verdict,
                   'use_diagonal_jitter': use_diagonal_jitter,
                   'max_diagonal_jitter': max_diagonal_jitter,
                   'diagonal_jitter_verdict': diagonal_jitter_verdict,
                   'use_diagonal_offset': use_diagonal_offset,
                   'max_diagonal_offset': max_diagonal_offset,
                   'diagonal_offset_verdict': diagonal_offset_verdict,
                   'incomplete_swipes': incomplete_swipes,
                   'swipes': swipes,
                   'swipe_count': len(swipes),
                   'missing_swipes': missing_swipes,
                   'missing_count': len(missing_swipes),
                   'lines': lines,
                   'passed_points': passed_points,
                   'failed_points': failed_points,
                   'max_offset_from_linear_fit': max(max_offsets_from_linear_fit) if max_offsets_from_linear_fit != [] else 0,
                   'avg_of_offsets_from_linear_fit': linear_fit_avg,
                   'diagonal_swipes': diagonal_swipes,
                   'nondiagonal_swipes': nondiagonal_swipes
                   }

        # This case can happen if swipes have less than two points so that jitter or offset can't be calculated.
        # In that case swipe verdict can't be given. But if number of missing swipes exceeds limit, the test verdict
        # is Fail even if jitter and offset can't be calculated.
        verdict = "N/A"

        dutinfo = self.get_dutinfo()

        def get_verdict(quantity):
            verdicts = []
            if results['nondiagonal_swipes'] or not results[f'use_diagonal_{quantity}']:
                verdicts.append(results[f'{quantity}_verdict'])
            if results['diagonal_swipes'] and results[f'use_diagonal_{quantity}']:
                verdicts.append(results[f'diagonal_{quantity}_verdict'])

            qty_verdict = "Pass"
            if "N/A" in verdicts:
                qty_verdict = "N/A"
            elif "Fail" in verdicts:
                qty_verdict = "Fail"

            return qty_verdict

        jitter_verdict = get_verdict('jitter')
        offset_verdict = get_verdict('offset')
        missing_passed = results['missing_count'] <= get_setting('maxmissingswipes', dutinfo.sample_id)

        if jitter_verdict == "Pass" and offset_verdict == "Pass" and missing_passed:
            verdict = "Pass"
        elif jitter_verdict == "Fail" or offset_verdict == "Fail" or not missing_passed:
            verdict = "Fail"

        results['verdict'] = verdict

        return results

    def read_swipe_details(self, swipe_id, dbsession=None, dutinfo=None):
        if dbsession is None:
            with measurementdb.get_database().session() as dbsession:
                return self.read_swipe_details(swipe_id, dbsession, dutinfo)
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(self.testsession['id'], dbsession)

        line = dbsession.query(measurementdb.OneFingerSwipeTest).filter(measurementdb.OneFingerSwipeTest.id == swipe_id).\
                                                                 order_by(measurementdb.OneFingerSwipeTest.id).\
                                                                 options(joinedload('one_finger_swipe_results')).first()

        panel_points = [(point.panel_x, point.panel_y) for point in line.one_finger_swipe_results]
        target_points = analyzers.panel_to_target(panel_points, dutinfo)
        line_start, line_end = analyzers.robot_to_target([(line.start_x, line.start_y), (line.end_x, line.end_y)], dutinfo)
        swipe_points = analyzers.target_to_swipe(target_points, line_start, line_end)
        jitterinfo = analyzers.analyze_swipe_jitter(swipe_points, float(get_setting('jittermask', dutinfo.sample_id)))
        linearity_results = analyzers.analyze_swipe_linearity(swipe_points)

        passfail_values = [abs(p[1]) <= get_setting('maxoffset', dutinfo.sample_id) for p in swipe_points]
        passed = [target_points[i] for (i,t) in enumerate(passfail_values) if t]
        failed = [target_points[i] for (i,t) in enumerate(passfail_values) if not t]

        return {'passed_points': passed, 'failed_points': failed, 'swipe_points': swipe_points,
                'line_start': line_start, 'line_end': line_end, 'jitters': jitterinfo['jitters'],
                'linear_error': linearity_results['linear_error'], 'lin_error_max': linearity_results['lin_error_max'],
                'lin_error_rms': linearity_results['lin_error_rms'], 'lin_error_avg': linearity_results['lin_error_avg']}

    def get_results(self) -> dict:
        dutinfo = self.get_dutinfo()
        all_results = self.read_test_results(dutinfo)
        azimuth_angles, tilt_angles = self.read_test_angles()
        results = {}

        if all_results['nondiagonal_swipes'] or not all_results['use_diagonal_jitter']:
            results['max_digitizer_jitter'] = all_results['max_jitter']
            results['max_digitizer_jitter_verdict'] = all_results['jitter_verdict']
        if all_results['nondiagonal_swipes'] or not all_results['use_diagonal_offset']:
            results['max_digitizer_offset'] = all_results['max_offset']
            results['max_digitizer_offset_verdict'] = all_results['offset_verdict']

        if all_results['diagonal_swipes'] and all_results['use_diagonal_jitter']:
            results['max_diagonal_jitter'] = all_results['max_diagonal_jitter']
            results['max_diagonal_jitter_verdict'] = all_results['diagonal_jitter_verdict']
        if all_results['diagonal_swipes'] and all_results['use_diagonal_offset']:
            results['max_diagonal_offset'] = all_results['max_diagonal_offset']
            results['max_diagonal_offset_verdict'] = all_results['diagonal_offset_verdict']

        results['average_max_digitizer_jitter'] = all_results['average_max_jitter']
        results['average_digitizer_jitter'] = all_results['average_jitter']
        results['average_max_digitizer_offset'] = all_results['average_max_offset']
        results['average_digitizer_offset'] = all_results['average_offset']

        results['missing_swipes'] = all_results['missing_count']
        results['missing_swipes_verdict'] = verdict_to_str(
            all_results['missing_count'] <= get_setting('maxmissingswipes', dutinfo.sample_id))
        results['incomplete_swipes'] = all_results['incomplete_swipes']
        results['incomplete_swipes_verdict'] = verdict_to_str(
            all_results['missing_count'] <= get_setting('maxincompleteswipes', dutinfo.sample_id))
        results['max_error'] = all_results['max_offset_from_linear_fit']
        results['mean_of_max_errors'] = all_results['avg_of_offsets_from_linear_fit']

        swipes = []
        for swipe in all_results['swipes']:
            swipe_results = {
                'swipe_id': swipe[0],
                'max_jitter': swipe[1],
                'max_offset': swipe[2],
                'verdict': swipe[3],
                'swipe_gaps': swipe[7],
                'avg_jitter': swipe[8],
                'avg_offset': swipe[9],
                'direction': swipe[10]
            }
            if azimuth_angles:
                swipe_results['azimuth'] = swipe[5]
            if tilt_angles:
                swipe_results['tilt'] = swipe[6]
            swipes.append(swipe_results)
        results['swipes'] = swipes

        return results

