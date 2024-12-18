# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.
from typing import Dict

from _decimal import Decimal
from sqlalchemy.orm import joinedload
from datetime import datetime

import time
import traceback
import TPPTAnalysisSW.plotinfo as plotinfo

from .measurementdb import get_database, TestItem, TestResult
from .settings import get_setting, setting_categories
import TPPTAnalysisSW.test_refs as test_refs

# generator functions for the different images - will be filled by the decorator
# This is a directory id -> generating function
_test_generators = {}

#decorator class
class testclasscreator(object):
    """ Creates test reports and images for the test. Gets the test type id as parameter """

    _generators = {}

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        pass

    def __call__(self, f):
        global _test_generators
        for arg in self.args:
            _test_generators[arg] = f
        return f


class TestBase(object):
    """Base class for all test objects. """

    def __init__(self, test_item_row, *args, **kwargs):
        """ Initialize the common report parameters """

        # Create dictionary for testsession parameters
        self.test_item = {column.name: getattr(test_item_row, column.name) for column in test_item_row.__table__.columns}
        self.test_item['test_type_name'] = test_item_row.type.name
        self.test_item['speed'] = test_item_row.speed
        self.test_id = self.test_item['id']
        # Create dictionary for test session parameters
        session = test_item_row.testsession
        self.testsession = {column.name: getattr(session, column.name) for column in session.__table__.columns}
        dut = test_item_row.dut
        self.dut = {column.name: getattr(dut, column.name) for column in dut.__table__.columns}

    @staticmethod
    def create(test_id, dbsession=None, **kwargs):
        """ Create a correct subclass for given test id """
        global _test_generators

        if dbsession is None:
            with get_database().session() as dbsession:
                return TestBase.create(test_id, dbsession, **kwargs)

        test = dbsession.query(TestItem).options(joinedload(TestItem.testsession)).\
                                                 options(joinedload(TestItem.type)).\
                                                 filter(TestItem.id==test_id).first()

        cache = True
        test_id = str(test_id)

        if test.testtype_id in _test_generators:
            if test_id not in test_refs.testclass_refs:
                generator = _test_generators[test.testtype_id](test, **kwargs)
                test_refs.testclass_refs[test_id] = generator
                cache = False

        if test.testtype_id != 15:  #THIS USED TO BE 15 BUT CASEY CHANGED TO 16 SINCE PINCH TEST IS NUMBER 16, NOT TOTALLY SURE WHAT IT DOES
            cache = False
            
        return test_refs.testclass_refs[test_id], cache

    def get_test_item(self, dbsession=None):
        if dbsession is None:
            with get_database().session() as dbsession:
                return self.get_test_item(dbsession)

        test = dbsession.query(TestItem).options(joinedload(TestItem.testsession)). \
            options(joinedload(TestItem.type)). \
            filter(TestItem.id == self.test_id).first()

        return test

    def get_test_session(self, dbsession=None):
        if dbsession is None:
            with get_database().session() as dbsession:
                return self.get_test_session(dbsession)

        test = dbsession.query(TestItem).options(joinedload(TestItem.testsession)). \
            options(joinedload(TestItem.testsession)). \
            filter(TestItem.id == self.test_id).first()

        return test.testsession

    def get_dutinfo(self):
        """ Get dutinfo object. """

        with get_database().session() as dbsession:
            dutinfo = plotinfo.TestDUTInfo(testdut_id=self.dut['id'], dbsession=dbsession)
            return dutinfo

    # These functions must be implemented in the child classes

    def runanalysis(self, *args, **kwargs):
        raise NotImplementedError("Method not implemented")

    def clearanalysis(self, *args, **kwargs):
        raise NotImplementedError("Method not implemented")

    def createreport(self, *args, **kwargs):
        raise NotImplementedError("Method not implemented")

    def createimage(self, *args, **kwargs):
        raise NotImplementedError("Method not implemented")

    def createcsv(self, *args, **kwargs):
        return '"This feature is not implemented yet"'
        #raise NotImplementedError("Method not implemented")

    def create_common_templateparams(self, *args, **kwargs):
        templateParams = {}
        templateParams["test_item"] = self.test_item
        templateParams["testsession"] = self.testsession
        templateParams["dut"] = self.dut
        templateParams["test_id"] = self.test_item['id']
        templateParams["test_type_name"] = self.test_item['test_type_name']
        templateParams["curtime"] = time.time()
        templateParams["speed"] = self.test_item['speed']
        templateParams["azimuth_angles"] = []
        templateParams["tilt_angles"] = []

        templateParams["get_setting"] = get_setting

        templateParams["kwargs"] = kwargs

        return templateParams

    @staticmethod
    def evaluateresult(test_id, dbsession=None, recalculate=True):

        if dbsession is None:
            with get_database().session() as dbsession:
                return TestBase.evaluateresult(test_id, dbsession, recalculate)
        else:
            session = dbsession

        result = None

        if recalculate:
            testclass = TestBase.create(test_id, dbsession=session)[0]

        try:

            if recalculate:
                if testclass is not None:
                    result = testclass.runanalysis()
                else:
                    # Test class not found!
                    print("Test class not found for test " + str(test_id))
                    result = "Error"

            dbresult = TestResult()
            dbresult.test_id = test_id

            if recalculate:
                dbresult.result = result
            else:
                result = "Requires recalculate"
                dbresult.result = result

            dbresult.calculated = datetime.now()
            session.query(TestResult).filter(TestResult.test_id == test_id).delete()
            session.add(dbresult)
            session.commit()

        except Exception as e:
            print(traceback.format_exc())
            result = "Error"

        if dbsession is None:
            session.close()

        return result

    def get_metadata(self) -> dict:
        """
        Get common test metadata for report. The fields are in the same order as on the test page.
        :return: Metadata as a dict.
        """

        metadata = {}

        def add_if_valid(key, value):
            """
            Add key to metadata if value evaluates to True (not None, "" or []).
            """
            if value:
                metadata[key] = value

        metadata["test_type"] = self.test_item['test_type_name']
        metadata["test_id"] = self.test_item['id']
        add_if_valid("test_session_id", self.testsession["id"])
        add_if_valid("start_time", self.test_item["starttime"])
        if self.test_item["starttime"] and self.test_item["endtime"]:
            date_format = '%Y-%m-%d %H:%M:%S'
            metadata["total_execution_time"] = str(datetime.strptime(self.test_item["endtime"], date_format) -
                                                   datetime.strptime(self.test_item["starttime"], date_format))
        add_if_valid("dut", self.dut["sample_id"])
        add_if_valid("manufacturer", self.dut["manufacturer"])
        add_if_valid("model/version", self.dut["batch"])
        add_if_valid("serial", self.dut["serial"])
        metadata["test_equipment"] = "OptoFidelity TOUCH, Analysis SW version 2.0"
        add_if_valid("test_finger", self.test_item["finger_type"])
        add_if_valid("notes", self.testsession["notes"])
        add_if_valid("operator", self.testsession["operator"])
        add_if_valid("line_drawing_speed", self.test_item["speed"])
        if hasattr(self, "read_test_angles"):
            # FIXME: are these really common metadata?
            azimuth_angles, tilt_angles = self.read_test_angles()
            add_if_valid("azimuth_angles", azimuth_angles)
            add_if_valid("tilt_angles", tilt_angles)

        return metadata

    def get_results(self) -> dict:
        """
        Get contents of the test results tables. This should correspond roughly one-to-one with what's visible in the
        GUI. Does not contain any images.
        :return: Results as a dict.
        """
        raise NotImplementedError

    def get_limits(self) -> Dict[str, Decimal]:
        """
        Get limits corresponding to DUT name and test type. Will return default limits if DUT does not exist.
        :return: Limits dict {name: value}.
        """

        dut = self.dut["sample_id"]
        test_type = self.test_item['test_type_name']

        if test_type not in setting_categories:
            return {}

        limits = {}
        for name in setting_categories[test_type]:
            limits[name] = get_setting(name, dut)

        return limits
