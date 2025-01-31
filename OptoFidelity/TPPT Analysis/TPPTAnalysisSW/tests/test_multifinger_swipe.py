# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

import cherrypy
import math
import numpy as np
import numpy.linalg as npl
from sqlalchemy.orm import joinedload
from genshi.template import MarkupTemplate

from TPPTAnalysisSW.testbase import TestBase, testclasscreator
from TPPTAnalysisSW.imagefactory import ImageFactory
from TPPTAnalysisSW.measurementdb import get_database, MultifingerSwipeTest, MultifingerSwipeResults
from TPPTAnalysisSW.info.version import Version
from TPPTAnalysisSW.utils import Timer, exportcsv, verdict_to_str, max_not_none, is_swipe_diagonal, swipe_direction
from TPPTAnalysisSW.settings import get_setting
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.plot_factory as plot_factory
import TPPTAnalysisSW.analyzers as analyzers
from TPPTAnalysisSW.tests.utils import detect_incomplete_swipes

class MultiFingerSwipeTest(TestBase):
    """ A dummy test class for use as a template in creating new test classes """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(5)
    def create_testclass(*args, **kwargs):
        return MultiFingerSwipeTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.ddttest (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new MultiFingerSwipeTest class """
        super(MultiFingerSwipeTest, self).__init__(ddtest_row, *args, **kwargs)

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

    # Create CSV file from the results
    def createcsv(self, *args, **kwargs):
        """ Create csv file from the measurements """
        with get_database().session() as dbsession:
            test_results = dbsession.query(MultifingerSwipeTest).filter(MultifingerSwipeTest.test_id == self.test_id). \
                order_by(MultifingerSwipeTest.id). \
                options(joinedload('multi_finger_swipe_results'))

            return exportcsv(test_results, subtable='multi_finger_swipe_results')

    # Create the test report. Return the created HTML, or raise cherrypy.HTTPError
    def createreport(self, *args, **kwargs):
        self.clearanalysis()

        # Create common template parameters (including ddttest dictionary, testsession dictionary, test_id, test_type_name etc)
        templateParams = super(MultiFingerSwipeTest, self).create_common_templateparams(**kwargs)

        t = Timer()

        # data for the report
        results = self.read_test_results()
        templateParams['results'] = results

        t.Time("Results")

        # set the content to be used
        templateParams['test_page'] = 'test_multifinger_swipe.html'
        templateParams['test_script'] = 'test_page_subplots.js'
        templateParams['version'] = Version

        template = MarkupTemplate(open("templates/test_common_body.html"))
        stream = template.generate(**(templateParams))
        t.Time("Markup")

        return stream.render('xhtml'), results['verdict']

    # Create images for the report. If the function returns a value, it is used as the new image (including full path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        if image_name == 'swpgen':
            t = Timer(1)
            with get_database().session() as dbsession:
                dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
                results = self.read_test_results(dutinfo=dutinfo, dbsession=dbsession)
                passed_points = []
                failed_points = []
                lines = []
                for multiswipe in results['swipes']:
                    for finger in multiswipe['fingers']:
                        for points in finger['passed_points'].values():
                            passed_points.extend(points)
                        for points in finger['failed_points'].values():
                            failed_points.extend(points)
                        lines.append((finger['swipe_start'], finger['swipe_end']))
                pinfo = {'passed_points': passed_points,
                         'failed_points': failed_points,
                         'lines': lines}
                t.Time("Results")
                title = 'Preview: Multifinger swipe overview'
                plot_factory.plot_swipes_on_target(imagepath, pinfo, dutinfo, *args, title=title, **kwargs)
                t.Time("Image")
        elif image_name == 'swpdtls':
            t = Timer(1)
            with get_database().session() as dbsession:
                dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
                results = self.read_swipe_results(args[0], dbsession=dbsession, dutinfo=dutinfo, **kwargs)
                t.Time("Results")
                title = 'Preview: Multifinger swipe details ID:' + args[0]
                plot_factory.plot_multifinger_swipedetails(imagepath, results, dutinfo, title=title, **kwargs)
                t.Time("Image")
        else:
            raise cherrypy.HTTPError(message="No such image in the report")

        return None

    def read_test_results(self, dutinfo=None, dbsession=None, **kwargs):
        if dbsession is None:
            with get_database().session() as dbsession:
                return self.read_test_results(dutinfo, dbsession, **kwargs)
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        s = Timer(2)
        results = dbsession.query(MultifingerSwipeTest).filter(MultifingerSwipeTest.test_id == self.test_id). \
            order_by(MultifingerSwipeTest.id).options(joinedload('multi_finger_swipe_results')).all()

        s.Time("DB Results")
        swipes = []
        errors = set()
        max_offset = None
        max_jitter = None
        max_diagonal_offset = None
        max_diagonal_jitter = None
        missing_swipes = 0
        total_swipes = 0
        swipe_id = 0
        incomplete_swipes = 0
        diagonal_swipes = False
        nondiagonal_swipes = False

        for multiswipe in results:
            swipe = self.calculate_swipe_details(multiswipe, dutinfo, **kwargs)
            swipe_id += 1
            swipe['id'] = swipe_id
            swipes.append(swipe)

            # If each swipe has discontinuity in any of it's swiping fingers, count the swipe as incomplete.
            if swipe['swipe_gaps'] > 0:
                incomplete_swipes += 1

            # Calculate common parameters
            errors = errors.union(swipe['errors'])
            if swipe['diagonal']:
                diagonal_swipes = True
                max_diagonal_offset = max_not_none(swipe['max_offset'], max_diagonal_offset)
                max_diagonal_jitter = max_not_none(swipe['max_jitter'], max_diagonal_jitter)
            else:
                nondiagonal_swipes = True
                max_offset = max_not_none(swipe['max_offset'], max_offset)
                max_jitter = max_not_none(swipe['max_jitter'], max_jitter)
            missing_swipes += swipe['missing_swipes']
            total_swipes += swipe['num_fingers']

        diagonal_offset_verdict = None if max_diagonal_offset is None else max_offset <= get_setting('maxdiagoffset',
                                                                                                     dutinfo.sample_id)
        diagonal_jitter_verdict = None if max_diagonal_offset is None else max_offset <= get_setting('maxdiagjitter',
                                                                                                     dutinfo.sample_id)

        s.Time("Analysis")

        results = {'swipes': swipes,
                   'errors': errors,
                   'offset_verdict': None if max_offset is None else max_offset <= get_setting('maxoffset', dutinfo.sample_id),
                   'jitter_verdict': None if max_jitter is None else max_jitter <= get_setting('maxjitter', dutinfo.sample_id),
                   'max_offset': max_offset,
                   'max_jitter': max_jitter,
                   'use_diagonal_offset': get_setting('maxdiagoffset') > 0,
                   'max_diagonal_offset': max_diagonal_offset,
                   'diagonal_offset_verdict': diagonal_offset_verdict,
                   'use_diagonal_jitter': get_setting('maxdiagjitter') > 0,
                   'max_diagonal_jitter': max_diagonal_jitter,
                   'diagonal_jitter_verdict': diagonal_jitter_verdict,
                   'incomplete_swipes': incomplete_swipes,
                   'incomplete_swipes_verdict': incomplete_swipes <= get_setting('maxincompleteswipes', dutinfo.sample_id),
                   'edge_analysis_done': False,
                   'total_swipes': total_swipes,
                   'missing_swipes': missing_swipes,
                   'missing_swipes_verdict': (missing_swipes <= get_setting('maxmissingswipes', dutinfo.sample_id)),
                   'errors_verdict': len(errors) == 0,
                   'images': [(ImageFactory.create_image_name(self.test_id, 'swpgen'),
                               ImageFactory.create_image_name(self.test_id, 'swpgen', 'detailed')),
                              ],
                   'diagonal_swipes': diagonal_swipes,
                   'nondiagonal_swipes': nondiagonal_swipes
                   }

        def get_verdict(quantity):
            verdicts = []
            if results['nondiagonal_swipes'] or not results[f'use_diagonal_{quantity}']:
                verdicts.append(results[f'{quantity}_verdict'])
            if results['diagonal_swipes'] and results[f'use_diagonal_{quantity}']:
                verdicts.append(results[f'diagonal_{quantity}_verdict'])

            qty_verdict = True
            if None in verdicts:
                qty_verdict = None
            elif False in verdicts:
                qty_verdict = False

            return qty_verdict

        offset_verdict = get_verdict('offset')
        jitter_verdict = get_verdict('jitter')

        verdict = results['missing_swipes_verdict'] and results['errors_verdict']
        if verdict:
            if offset_verdict is None:
                verdict = None
            elif jitter_verdict is None:
                # what to do???
                verdict = results['offset_verdict']
            else:
                verdict = offset_verdict and jitter_verdict

        results['verdict'] = "N/A" if verdict is None else "Pass" if verdict else "Fail"

        return results

    def read_swipe_results(self, swipe_id, dbsession=None, dutinfo=None, **kwargs):
        if dbsession is None:
            with get_database().session() as dbsession:
                return self.read_swipe_results(swipe_id, dbsession, dutinfo, **kwargs)
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        multiswipe = dbsession.query(MultifingerSwipeTest).filter(MultifingerSwipeTest.id == swipe_id). \
            options(joinedload('multi_finger_swipe_results')).first()

        return self.calculate_swipe_details(multiswipe, dutinfo, **kwargs)

    def calculate_swipe_details(self, multiswipe, dutinfo, **kwargs):
        # Transfer swipe info to individual swipes
        start_point, end_point = analyzers.robot_to_target([(multiswipe.start_x, multiswipe.start_y),
                                                            (multiswipe.end_x, multiswipe.end_y)], dutinfo)
        separation_x = multiswipe.separation_distance * math.cos(math.radians(-multiswipe.separation_angle))
        separation_y = multiswipe.separation_distance * math.sin(math.radians(-multiswipe.separation_angle))
        start_points_x = [start_point[0] + i * separation_x for i in range(multiswipe.number_of_fingers)]
        start_points_y = [start_point[1] + i * separation_y for i in range(multiswipe.number_of_fingers)]
        end_points_x = [end_point[0] + i * separation_x for i in range(multiswipe.number_of_fingers)]
        end_points_y = [end_point[1] + i * separation_y for i in range(multiswipe.number_of_fingers)]
        startpoints = list(zip(start_points_x, start_points_y))
        endpoints = list(zip(end_points_x, end_points_y))

        allpoints = analyzers.panel_to_target([(p.panel_x, p.panel_y) for p in multiswipe.multi_finger_swipe_results],
                                              dutinfo)
        swipepoints = analyzers.target_to_swipe(allpoints, startpoints[0], endpoints[0])
        swipestarts = analyzers.target_to_swipe(startpoints, startpoints[0], endpoints[0])
        fingerids = np.array([p.finger_id for p in multiswipe.multi_finger_swipe_results])

        swipe_errors = set()
        # Check if we have the correct number of finger ids
        uniqids = np.unique(fingerids)
        if len(uniqids) > multiswipe.number_of_fingers:
            swipe_errors.add('Too many fingers were detected in input')

        pointsbyid = {}
        swipepointsbyid = {}
        for id in uniqids:
            pointsbyid[id] = [p for pid, p in zip(fingerids, allpoints) if pid == id]
            swipepointsbyid[id] = np.array([np.array(p) for pid, p in zip(fingerids, swipepoints) if pid == id])

        # Map the finger ids in the database to the id's in the points list
        max_jitter = None
        fingers = []
        finger_offsets = []
        missing_fingers = 0

        diagonal = is_swipe_diagonal(start_point, end_point)

        max_offset_limit = get_setting('maxoffset', dutinfo.sample_id)
        max_jitter_limit = get_setting('maxjitter', dutinfo.sample_id)
        if diagonal and get_setting('maxdiagoffset', dutinfo.sample_id) > 0:
            max_offset_limit = get_setting('maxdiagoffset', dutinfo.sample_id)
        if diagonal and get_setting('maxdiagjitter', dutinfo.sample_id) > 0:
            max_jitter_limit = get_setting('maxdiagjitter', dutinfo.sample_id)

        fingerids = self.find_fingerids(swipestarts, swipepointsbyid, swipe_errors)
        swipe_gaps = 0
        max_discontinuity = get_setting('maxswipediscontinuity', dutinfo.sample_id)

        for startpoint, endpoint, swipestart, ids_in_place in zip(startpoints, endpoints, swipestarts, fingerids):
            fingerpoints = {}
            swipepoints = {}
            passed = {}
            failed = {}
            jitters = {}
            results = []
            finger = {'swipe_start': startpoint,
                      'swipe_end': endpoint,
                      'points': fingerpoints,
                      'passed_points': passed,
                      'failed_points': failed,
                      'swipe_points': swipepoints,
                      'jitters': jitters,
                      'results': results,
                      'verdict': False}
            fingers.append(finger)
            if ids_in_place is None:
                # Missing finger
                # swipe_errors.add('Not all fingers were detected in input')
                finger_offsets.append(None)
                missing_fingers += 1
                continue

            max_finger_offset = None
            max_finger_jitter = None
            for id in ids_in_place:
                fingerpoints[id] = pointsbyid[id]
                swipepoints[id] = swipepointsbyid[
                                      id] - swipestart  # Transform coordinates to individual swipe coordinates

                gaps_count = len(detect_incomplete_swipes(swipepoints[id], max_discontinuity))

                # TODO: why sometimes we ids_in_place with size bigger than 1???? The extra Finger that is detected from
                #  test results always have just a few samples that breaks the analysis.
                if len(swipepoints[id]) < 2:  # Workaround
                    continue

                # if each finger in an individual swipe has discontinuity, count each of them as incomplete swipe.
                if gaps_count > 0 and id < multiswipe.number_of_fingers:
                    swipe_gaps += gaps_count

                results = analyzers.analyze_swipe_jitter(swipepointsbyid[id], float(get_setting('jittermask',
                                                                                                dutinfo.sample_id)))
                jitters[id] = results['jitters']
                offsets = np.abs(swipepointsbyid[id][:, 1] - swipestart[1])
                max_id_offset = analyzers.round_dec(np.max(offsets))
                results['max_offset'] = max_id_offset
                # Passed/failed points to visualization
                passfail_values = [analyzers.round_dec(o) <= max_offset_limit for p, o in zip(swipepoints[id], offsets)]
                passed[id] = [fingerpoints[id][i] for (i, t) in enumerate(passfail_values) if t]
                failed[id] = [fingerpoints[id][i] for (i, t) in enumerate(passfail_values) if not t]
                max_finger_offset = max_id_offset if max_finger_offset is None else max(max_id_offset,
                                                                                        max_finger_offset)
                max_id_jitter = analyzers.round_dec(results['max_jitter'])
                max_finger_jitter = max_id_jitter if max_finger_jitter is None else max(max_id_jitter,
                                                                                        max_finger_jitter)
            finger['max_offset'] = max_finger_offset
            finger_offsets.append(max_finger_offset)
            finger['max_jitter'] = max_finger_jitter
            if max_finger_jitter is not None:
                max_jitter = max_finger_jitter if max_jitter is None else max(max_jitter, max_finger_jitter)

            if max_finger_offset <= max_offset_limit:
                finger['verdict'] = True
            # else:
            # swipe_errors.add('Maximum offset exceeded')

        max_offset = None
        # Find max offset from non-None offsets
        if finger_offsets.count(None) < len(finger_offsets):
            max_offset = max([o for o in finger_offsets if o is not None])

        if max_offset is None:
            verdict = None
            verdict_text = 'N/A'
            verdict_class = ''
        else:
            verdict = (max_offset <= max_offset_limit and max_jitter <= max_jitter_limit and len(swipe_errors) == 0
                       and not swipe_gaps)

            verdict_text = 'Pass' if verdict else 'Fail'
            verdict_class = 'passed' if verdict else 'failed'

        direction = swipe_direction(start_point, end_point)

        swipe = {'num_fingers': multiswipe.number_of_fingers,
                 'startpoints': startpoints,
                 'endpoints': endpoints,
                 'missing_swipes': missing_fingers,
                 'offsets': finger_offsets,
                 'fingerids': fingerids,
                 'fingers': fingers,
                 'max_offset': max_offset,
                 'max_jitter': max_jitter,
                 'errors': swipe_errors,
                 'verdict': verdict,
                 'verdict_text': verdict_text,
                 'verdict_class': verdict_class,
                 'swipe_gaps': swipe_gaps,
                 'image': ImageFactory.create_image_name(self.test_id, 'swpdtls', str(multiswipe.id)),
                 'diagonal': diagonal,
                 'direction': direction}

        return swipe

    def find_fingerids(self, swipestarts, swipepointsbyid, swipe_errors):
        ''' Find finger ids for the points sorted by ids. Returns an array,
            where each id gives the finger_id for the specified point in targetpoints '''

        numids = len(swipepointsbyid.keys())
        numpoints = len(swipestarts)

        if numids == 0:
            # No measurements found
            return [None] * numpoints

        # Find the distances from each median point per id to each of the target points
        distances = {}
        # print str(targetpoints)
        for id in swipepointsbyid.keys():
            # For each fingerid check the closest target swipe - very easy in swipe coordinates
            median_offset = np.median([p[1] for p in swipepointsbyid[id]])
            dists = [np.abs(median_offset - p[1]) for p in swipestarts]
            distances[id] = dists

        return analyzers.find_closest_id_match(distances)

    def get_results(self) -> dict:
        dutinfo = self.get_dutinfo()
        all_results = self.read_test_results(dutinfo)
        results = {}

        if all_results['nondiagonal_swipes']:
            results['max_offset'] = all_results['max_offset']
            results['max_offset_verdict'] = verdict_to_str(all_results['offset_verdict'])
            results['max_jitter'] = all_results['max_jitter']
            results['max_jitter_verdict'] = verdict_to_str(all_results['jitter_verdict'])

        if all_results['diagonal_swipes']:
            results['max_diagonal_offset'] = all_results['max_diagonal_offset']
            results['max_diagonal_offset_verdict'] = verdict_to_str(all_results['diagonal_offset_verdict'])
            results['max_diagonal_jitter'] = all_results['max_diagonal_jitter']
            results['max_diagonal_jitter_verdict'] = verdict_to_str(all_results['diagonal_jitter_verdict'])

        results['missing_swipes'] = all_results['missing_swipes']
        results['missing_swipes_verdict'] = verdict_to_str(all_results['missing_swipes_verdict'])
        results['errors']: len(all_results['errors'])

        if all_results['errors']:
            results['error_descriptions'] = all_results['errors']

        results['swipes'] = []
        for swipe in all_results['swipes']:
            swipe_results = {
                'swipe_id': swipe['id'],
                'number_of_fingers': swipe['num_fingers'],
                'errors': len(swipe['errors']),
                'max_offset': swipe['max_offset'],
                'max_jitter': swipe['max_jitter'],
                'verdict': swipe['verdict_text'],
                'swipe_gaps': swipe['swipe_gaps'],
                'direction': swipe['direction']
            }
            results['swipes'].append(swipe_results)

        return results
