# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

import cherrypy
from genshi.template import MarkupTemplate
import numpy as np
from sqlalchemy.orm import joinedload

from ..testbase import TestBase, testclasscreator
from ..imagefactory import ImageFactory
from ..settings import get_setting, precision
from ..utils import Timer, exportcsv, verdict_to_str
from ..info.version import Version
import TPPTAnalysisSW.measurementdb as db
import TPPTAnalysisSW.analyzers as analyzers
import TPPTAnalysisSW.plot_factory as plot_factory
import TPPTAnalysisSW.plotinfo as plotinfo


class OneFingerTapTest(TestBase):
    """ A dummy test class for use as a template in creating new test classes """

    # This is the generator function for the class - it must exist in all derived classes
    # Just update the id (dummy=99) and class name
    @staticmethod
    @testclasscreator(0)
    def create_testclass(*args, **kwargs):
        return OneFingerTapTest(*args, **kwargs)

    # Init function: make necessary initializations.
    # Parent function initializes: self.test_id, self.test_item (dictionary, contains test_type_name) and self.testsession (dictionary)
    def __init__(self, ddtest_row, *args, **kwargs):
        """ Initializes a new OneFingerTapTest class """
        return super(OneFingerTapTest, self).__init__(ddtest_row, *args, **kwargs)

    # Create CSV file from the results
    def createcsv(self, *args, **kwargs):
        ''' Create csv file from the measurements '''
        with db.get_database().session() as dbsession:
            query = dbsession.query(db.OneFingerTapTest).filter(db.OneFingerTapTest.test_id == self.test_id). \
                order_by(db.OneFingerTapTest.id)

            return exportcsv(query, initialstring='one_finger_tap_test\n')

    # Override to make necessary analysis for test session success
    def runanalysis(self, *args, **kwargs):
        """ Runs the analysis, return a string containing the test result """
        results = self.read_test_results()
        verdict = "Pass" if (results['max_input_verdict'] and results['missing_inputs_verdict']) else "Fail"
        dutinfo = self.get_dutinfo()
        if get_setting('edgelimit', dutinfo.sample_id) >= 0:
            if not results['missing_edge_inputs_verdict']:
                verdict = "Fail"

        return verdict

    # Override to make necessary operations for clearing test results
    # Clearing the test result from the results table is done elsewhere
    def clearanalysis(self, *args, **kwargs):
        """ Clears analysis results """
        ImageFactory.delete_images(self.test_id)

    # Create the test report. Return the created HTML, or raise cherrypy.HTTPError
    def createreport(self, *args, **kwargs):

        self.clearanalysis()

        # Create common template parameters (including test_item dictionary, testsession dictionary, test_id, test_type_name etc)
        templateParams = super(OneFingerTapTest, self).create_common_templateparams(**kwargs)

        t = Timer()

        # data for the report
        results = self.read_test_results()
        templateParams['results'] = results
        dutinfo = self.get_dutinfo()

        t.Time("Results")

        # set the content to be used
        templateParams['test_page'] = 'test_one_finger_tap.html'
        templateParams['version'] = Version
        azimuth_angles, tilt_angles = self.read_test_angles()
        templateParams['azimuth_angles'] = azimuth_angles
        templateParams['tilt_angles'] = tilt_angles

        template = MarkupTemplate(open("templates/test_common_body.html"))
        stream = template.generate(**(templateParams))
        t.Time("Markup")

        verdict = "Pass" if (results['max_input_verdict'] and results['missing_inputs_verdict']) else "Fail"
        if get_setting('edgelimit', dutinfo.sample_id) >= 0:
            if not results['missing_edge_inputs_verdict']:
                verdict = "Fail"

        return stream.render('xhtml'), verdict

    # Create images for the report. If the function returns a value, it is used as the new image (including full path)
    def createimage(self, imagepath, image_name, *args, **kwargs):

        if image_name == 'p2pdiff':
            t = Timer(1)
            with db.get_database().session() as dbsession:
                dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
                results = self.read_test_results(dutinfo=dutinfo, dbsession=dbsession)
                t.Time("Results")
                title = 'Preview: One Finger Tap'
                plot_factory.plot_taptest_on_target(imagepath, results, dutinfo, *args, title=title, **kwargs)
                t.Time("Image")
        elif image_name == 'p2pdxdy':
            t = Timer(1)
            results = self.read_test_results(**kwargs)
            t.Time("Results")
            plot_factory.plot_dxdy_graph(imagepath, results, 0.0, *args, **kwargs)
            t.Time("Image")
        elif image_name == 'p2pdxdyltd':
            t = Timer(1)
            results = self.read_test_results(**kwargs)
            t.Time("Results")
            plot_factory.plot_dxdy_graph(imagepath, results, 1.0, *args, **kwargs)
            t.Time("Image")
        elif image_name == 'p2pdxdyltdc':
            t = Timer(1)
            results = self.read_test_results(center_only=True)
            t.Time("Results")
            plot_factory.plot_dxdy_graph(imagepath, results, 1.0, *args, center_only=True, **kwargs)
            t.Time("Image")
        elif image_name == 'p2pdxdyltde':
            t = Timer(1)
            results = self.read_test_results(edge_only=True)
            t.Time("Results")
            plot_factory.plot_dxdy_graph(imagepath, results, 1.0, *args, edge_only=True, **kwargs)
            t.Time("Image")
        elif image_name == 'p2phistogram':
            t = Timer(1)
            results = self.read_test_results()
            t.Time("Results")
            plot_factory.plot_p2p_err_histogram(imagepath, results, 1.0, *args, edge_only=False, **kwargs)
            t.Time("Image")
        elif image_name == 'p2phistogramc':
            t = Timer(1)
            results = self.read_test_results(center_only=True)
            t.Time("Results")
            plot_factory.plot_p2p_err_histogram(imagepath, results, 1.0, *args, center_only=True, **kwargs)
            t.Time("Image")
        elif image_name == 'p2phistograme':
            t = Timer(1)
            results = self.read_test_results(edge_only=True)
            t.Time("Results")
            plot_factory.plot_p2p_err_histogram(imagepath, results, 1.0, *args, edge_only=True, **kwargs)
            t.Time("Image")

        return None

    def read_test_angles(self):
        # Use sets to only pick unique values
        azimuth_angles = set()
        tilt_angles = set()

        dbsession = db.get_database().session()
        query = dbsession.query(db.OneFingerTapTest).filter(db.OneFingerTapTest.test_id == self.test_id)

        for point in query:
            if point.robot_azimuth is not None:
                azimuth_angles.add(float(point.robot_azimuth))
            if point.robot_tilt is not None:
                tilt_angles.add(float(point.robot_tilt))

        dbsession.close()

        return sorted(list(azimuth_angles)), sorted(list(tilt_angles))

    def read_test_results(self, dutinfo=None, dbsession=None, **kwargs):
        if dbsession is None:
            with db.get_database().session() as dbsession:
                return self.read_test_results(dutinfo, dbsession, **kwargs)
        if dutinfo is None:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)

        query = dbsession.query(db.OneFingerTapTest).filter(db.OneFingerTapTest.test_id == self.test_id). \
            order_by(db.OneFingerTapTest.id)

        passed_points = []  # These are tuple-tuples: ((target_x, target_y), (hit_x, hit_y))
        failed_points = []
        targets = []
        hits = []  # target points: ((target_x, target_y), radius)
        missing = []  # target points ((target_x, target_y), radius)
        missing_edge = []
        edge_points = 0
        max_input_error = analyzers.round_dec(0.0)
        max_edge_error = analyzers.round_dec(0.0)
        distances = []

        for point in query:
            target = analyzers.robot_to_target((point.robot_x, point.robot_y), dutinfo)
            targets.append(target)

            edge_point = False
            if analyzers.is_edge_point(target, dutinfo):
                edge_point = True
                edge_points += 1
                if 'center_only' in kwargs:
                    continue
            else:
                if 'edge_only' in kwargs:
                    continue

            if point.panel_x is None or point.panel_y is None:
                missing.append((target, analyzers.get_max_error(target, dutinfo)))
                if edge_point:
                    missing_edge.append((target, analyzers.get_max_error(target, dutinfo)))

            else:
                max_error = analyzers.round_dec(analyzers.get_max_error(target, dutinfo))
                hits.append((target, max_error))
                hit = analyzers.panel_to_target((point.panel_x, point.panel_y), dutinfo)
                distance = analyzers.round_dec(np.linalg.norm((hit[0] - target[0], hit[1] - target[1])))
                distances.append(float(distance))
                if distance > max_error:
                    failed_points.append((target, hit))
                else:
                    passed_points.append((target, hit))
                if edge_point:
                    if distance > max_edge_error:
                        max_edge_error = distance
                else:
                    if distance > max_input_error:
                        max_input_error = distance

        max_input_verdict = (max_input_error < get_setting('maxposerror', dutinfo.sample_id))
        if get_setting('edgelimit', dutinfo.sample_id) >= 0:
            max_input_verdict = max_input_verdict and max_edge_error < get_setting('edgepositioningerror', dutinfo.sample_id)

        sorted_acc_errors = np.sort(distances)
        index_85_0 = round(0.85 * len(distances)) - 1
        limit_85_0 = sorted_acc_errors[index_85_0] if index_85_0 != -1 else None
        index_99_7 = round(0.997 * len(distances)) - 1
        limit_99_7 = sorted_acc_errors[index_99_7] if index_99_7 != -1 else None

        results = {'max_input_error': max_input_error,
                   'edge_analysis_done': (get_setting('edgelimit', dutinfo.sample_id) >= 0),
                   'max_edge_error': max_edge_error,
                   'max_input_verdict': max_input_verdict,
                   'total_points': len(targets),
                   'edge_points': edge_points,
                   'missing_inputs': len(missing),
                   'missing_inputs_verdict': (len(missing) - len(missing_edge) <= get_setting('maxmissing', dutinfo.sample_id)),
                   'missing_edge_inputs': len(missing_edge),
                   'missing_edge_inputs_verdict': (len(missing_edge) <= get_setting('maxedgemissing', dutinfo.sample_id)),
                   'passed_points': passed_points,
                   'failed_points': failed_points,
                   'targets': targets,
                   'maxposerror': get_setting('maxposerror', dutinfo.sample_id),
                   'hits': hits,
                   'missing': missing,
                   'distances': distances,
                   'limit_85_0': limit_85_0,
                   'limit_99_7': limit_99_7
                   }

        if get_setting('edgelimit', dutinfo.sample_id) >= 0:
            # Edge analysis
            results['edgepositioningerror'] = get_setting('edgepositioningerror', dutinfo.sample_id)
            results['images'] = [(ImageFactory.create_image_name(self.test_id, 'p2pdiff'),
                                  ImageFactory.create_image_name(self.test_id, 'p2pdiff', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2pdxdy'),
                                  ImageFactory.create_image_name(self.test_id, 'p2pdxdy', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2pdxdyltdc'),
                                  ImageFactory.create_image_name(self.test_id, 'p2pdxdyltdc', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2pdxdyltde'),
                                  ImageFactory.create_image_name(self.test_id, 'p2pdxdyltde', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2phistogram'),
                                  ImageFactory.create_image_name(self.test_id, 'p2phistogram', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2phistogramc'),
                                  ImageFactory.create_image_name(self.test_id, 'p2phistogramc', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2phistograme'),
                                  ImageFactory.create_image_name(self.test_id, 'p2phistograme', 'detailed'))]
        else:
            results['images'] = [(ImageFactory.create_image_name(self.test_id, 'p2pdiff'),
                                  ImageFactory.create_image_name(self.test_id, 'p2pdiff', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2pdxdy'),
                                  ImageFactory.create_image_name(self.test_id, 'p2pdxdy', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2pdxdyltd'),
                                  ImageFactory.create_image_name(self.test_id, 'p2pdxdyltd', 'detailed')),
                                 (ImageFactory.create_image_name(self.test_id, 'p2phistogram'),
                                  ImageFactory.create_image_name(self.test_id, 'p2phistogram', 'detailed'))]

        return results

    def get_results(self) -> dict:
        dutinfo = self.get_dutinfo()
        all_results = self.read_test_results(dutinfo)
        results = {}
        if all_results['edge_analysis_done']:
            results['max_center_accuracy_error'] = all_results['max_input_error']
            results['max_center_accuracy_error_verdict'] = verdict_to_str(all_results['max_input_verdict'])
            results['max_edge_accuracy_error'] = all_results['max_edge_error']
            results['max_edge_accuracy_error_verdict'] = verdict_to_str(
                all_results['max_edge_error'] >= all_results['edgepositioningerror'])
            results['missing_center_inputs'] = all_results['missing_inputs'] - all_results['missing_edge_inputs']
            results['missing_center_inputs_verdict'] = verdict_to_str(all_results['missing_inputs_verdict'])
            results['missing_edge_inputs'] = all_results['missing_edge_inputs']
            results['missing_edge_inputs_verdict'] = verdict_to_str(all_results['missing_edge_inputs_verdict'])
        else:
            results['max_accuracy_error'] = all_results['max_input_error']
            results['max_accuracy_error_verdict'] = verdict_to_str(all_results['max_input_verdict'])
            results['missing_inputs'] = all_results['missing_inputs']
            results['missing_inputs_verdict'] = verdict_to_str(all_results['missing_inputs_verdict'])
        results['limit_85_0'] = all_results['limit_85_0']
        results['limit_99_7'] = all_results['limit_99_7']

        return results
