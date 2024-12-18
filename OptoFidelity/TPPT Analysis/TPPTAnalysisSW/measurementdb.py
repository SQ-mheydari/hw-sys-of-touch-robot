# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.
import traceback
import argparse
import json
import time
import sqlite3

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relation, backref, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy import event
from .measurementdb_sqlite import create_sqlite_indices

Base = declarative_base()

parser = argparse.ArgumentParser()
parser.add_argument('--check', action="store_true", default=False, help='Startup check for CI usage')
parser.add_argument('--database', type=str, default='C:/OptoFidelity/TPPT/database.sqlite', help='Path to used database file')
parser.add_argument('--config', type=str, default='C:/OptoFidelity/TPPT/config.json', help='Path to used configuration file')
args = parser.parse_args()

database = args.database
config = args.config


def on_connect(conn, record):
    conn.execute('pragma foreign_keys=ON')


def saveLastPath(path):
    # Update path to existing config
    with open(config, 'r') as f:
        conf_data = f.read()
    try:
        conf = json.loads(conf_data)
    except Exception as e:
        conf = {}
    conf["lastDB"] = path

    with open(config, 'w') as f:
        f.write(json.dumps(conf, indent=4))


def getLastPath():
    try:
        f = open(config, 'r')
        data = json.load(f)

        if "lastDB" in data:
            return data['lastDB']
        else:
            return database

    except Exception as e:
        print(str(e))
        return database


class ResultDatabase:

    def __init__(self, filename):
        self.db = None
        self.session = None
        self.dbpath = None

        self.initialize(filename)
        saveLastPath(filename)

    def initialize(self, filename):

        self.dbpath = filename
        self.db = create_engine('sqlite:///' + filename)
        event.listen(self.db, 'connect', on_connect)
        self.session = sessionmaker(bind=self.db, autoflush=False)
        Base.metadata.create_all(self.db)
        create_sqlite_indices(filename)

        # Check if ResultDatabase already contains test types below.
        try:
            with self.session() as session:
                session.add( TestType( 0, 'One Finger Tap Test' ) )
                session.add( TestType( 1, 'One Finger Swipe Test' ) )
                session.add( TestType( 2, 'One Finger First Contact Latency Test' ) )
                session.add( TestType( 5, 'MultiFinger Swipe Test' ) )
                session.add( TestType( 8, 'MultiFinger Tap Test'))
                session.add( TestType( 9, 'One Finger Stationary Jitter'))
                session.add( TestType( 10, 'One Finger Tap Repeatability'))
                session.add( TestType( 11, 'One Finger Stationary Reporting Rate Test'))
                session.add( TestType( 12, 'One Finger Non Stationary Reporting Rate Test'))
                session.add( TestType( 14, 'Separation Test'))
                session.add( TestType( 16, 'Pinch Test'))
                session.commit()
        except:
            # Already created
            pass
        try:
            self.checksetting(Setting('maxjitter',1.0,"mm","Maximum allowed non stationary jitter"))
            self.checksetting(Setting('maxstationaryjitter',0.0,"mm","Maximum allowed stationary jitter"))
            self.checksetting(Setting('jittermask',10.0,"mm","Non stationary jitter search mask"))
            self.checksetting(Setting('maxactiveresponselatency',25.0,"ms","Maximum allowed response latency from an active state for the initial input"))
            self.checksetting(Setting('maxidleresponselatency',50.0,"ms","Maximum allowed response latency from an idle state"))
            self.checksetting(Setting('minreportingrate',100.0,"Hz","Minimum allowed reporting rate"))
            self.checksetting(Setting('minavgreportingrate', 120.0, "Hz", "Minimum allowed average reporting rate"))
            self.checksetting(Setting('maxposerror',1.0,"mm","Maximum allowed accuracy error"))
            self.checksetting(Setting('maxmissing',0.0,"pcs","Maximum allowed missing inputs"))
            self.checksetting(Setting('maxoffset', 1.0, "mm","Maximum allowed offset"))
            self.checksetting(Setting('maxseparation',12.0,"mm","Maximum allowed finger separation distance (vertical and horizontal)"))
            self.checksetting(Setting('maxdiagseparation',15.0,"mm","Maximum allowed finger separation distance (diagonal)"))
            self.checksetting(Setting('minppi',200.0,"ppi","Minimum display resolution"))
            self.checksetting(Setting('maxrepeaterror',1.0,"mm","Maximum tap repeatability error"))
            self.checksetting(Setting('edgelimit',-1.0,"mm","Edge area distance from edge in Tap test"))
            self.checksetting(Setting('edgepositioningerror',1.0,"mm","Maximum allowed accuracy error in edge area"))
            self.checksetting(Setting('maxedgemissing',0.0,"pcs","Maximum allowed missing edge inputs"))
            self.checksetting(Setting('maxmissingswipes',0.0,"pcs","Maximum allowed missing swipes in swipe test"))
            self.checksetting(Setting('maxbrokenswipes', 0.0, "pcs", "Maximum allowed broken swipes in linearity test"))
            self.checksetting(Setting('maxincompleteswipes', 0.0, "pcs", "Maximum allowed incomplete swipes in swipe test"))
            self.checksetting(Setting('maxswipediscontinuity', 5.0, "mm", "Maximum allowed gap between consecutive swipe points"))
            self.checksetting(Setting('maxdiagoffset', 0.0, "mm", "Maximum allowed offset for diagonal swipes (0 to disable)"))
            self.checksetting(Setting('maxdiagjitter', 0.0, "mm", "Maximum allowed jitter for diagonal swipes (0 to disable)"))
            # When adding settings, remember to add them to settings.py categories
        except: #IntegrityError:
            print(traceback.format_exc())
            # Already created
            pass

    def changeDatabase(self, path):
        self.initialize(path)
        saveLastPath(path)

    def add( self, data, commit = True ):
        with self.session() as session:
            session.add( data )
            if commit == True:
                self.session_commit(session)

    def addAll( self, data, commit = True ):
        with self.session() as session:
            session.add_all( data )
            if commit == True:
                self.session_commit(session)

    def getEngine(self):
        return self.db

    def update(self, data):
        with self.session() as session:
            session.merge(data)
            self.session_commit(session)

    def commit(self):
        with self.session() as session:
            self.session_commit(session)

    def session_commit(self, session):
        # If database is locked, try again until timeout occurs
        max_wait_time = 15
        start = time.time()
        while(True):
            try:
                session.commit()
                break
            except sqlite3.OperationalError as e:
                if time.time() - start > max_wait_time:
                    raise e
                else:
                    pass

    def get_test_sessions( self, dbsession=None ):
        if dbsession is None:
            with self.session() as dbsession:
                return dbsession.query( TestSession ).all()

        return dbsession.query( TestSession ).all()

    def get_test_session( self, session_id ):
        with self.session() as session:
            print("#########GET TEST SESSION")
            return session.query( TestSession ).filter_by( id=session_id ).first()

    def get_test_results( self, test_id ):
        with self.session() as session:
            retval = session.query(OneFingerTapTest).filter_by( test_id=test_id ).all()
            return retval

    def get_TestType( self, type_id ):
        with self.session() as session:
            return session.query(TestType).filter_by( id=type_id ).all()

    def get_TestTypes( self ):
        with self.session() as session:
            return session.query(TestType).all()

    def get_programs( self ):
        with self.session() as session:
            return session.query( TestSession.program).order_by(TestSession.program)

    def get_manufacturers( self, Program ):
        with self.session() as session:
            return session.query( TestSession.manufacturer).order_by(TestSession.manufacturer).all()

    def checksetting( self, setting ):
        with self.session() as session:
            dbsetting = session.query(Setting).filter_by(name=setting.name, dut=setting.dut).first()
            if dbsetting is None:
                # Setting does not exist
                session.add(setting)
                self.session_commit(session)

# Define database tables

class TestSession( Base ):

# TestSession is constant to all test cases

    __tablename__ = 'test_session'

    id = Column( Integer, primary_key=True )
    operator = Column( String )
    starttime = Column( String )
    endtime = Column( String )
    invalid = Column( Boolean )
    notes = Column( String )

class TestDUT( Base ):

    # A DUT that is tested in one or multiple test sessions and referenced to in Test Items
    __tablename__ = 'test_dut'
    id = Column( Integer, primary_key=True )

    # Dut parameters
    program = Column( String )
    manufacturer = Column( String )
    batch = Column( String )
    serial = Column( String )
    sample_id = Column( String )


class TestType( Base ):

    #Device digitizer touch test types stored here

    __tablename__ = 'test_type'

    id = Column( Integer, primary_key = True )
    name = Column( String )

    def __init__( self, id, name ):
        self.id = id
        self.name = name

class TestItem( Base ):

    #A single test related to device digitizer touch is defined here
    __tablename__ = 'test_item'

    id = Column( Integer, primary_key= True )
    testsession_id = Column( Integer, ForeignKey('test_session.id', ondelete='CASCADE'), nullable=False )
    testsession = relation( TestSession, backref = backref('test_items', order_by =  id) )
    dut_id = Column( Integer, ForeignKey('test_dut.id'), nullable=False )
    dut = relation( TestDUT, backref = backref('test_items', order_by =  id) )
    starttime = Column( String )
    speed = Column( Float )
    endtime = Column( String )
    slot_id = Column( Integer )
    finger_type = Column( String )
    invalid = Column( Boolean )
    testtype_id = Column( Integer, ForeignKey('test_type.id', ondelete='CASCADE'), nullable=False )
    type = relation( TestType, backref = backref('test_items', order_by = id) )

class SessionParameters( Base ):

    #Session parameters are defined here
    __tablename__ = 'session_parameters'

    id = Column( Integer, primary_key = True )
    testsession_id = Column( Integer, ForeignKey('test_session.id', ondelete='CASCADE'), nullable=False )
    testsession = relation(TestSession, backref = backref('session_parameters', order_by = id ) )
    name = Column( String )
    valueFloat = Column( Float )
    valueString = Column( String )
    isFloat = Column( Boolean )

class DutParameters( Base ):

    #DUT parameters are defined here
    __tablename__ = 'dut_parameters'

    id = Column( Integer, primary_key = True )
    dut_id = Column( Integer, ForeignKey('test_dut.id', ondelete='CASCADE'), nullable=False )
    dut = relation(TestDUT, backref = backref('dut_parameters', order_by = id ) )
    name = Column( String )
    valueFloat = Column( Float )
    valueString = Column( String )
    isFloat = Column( Boolean )

class DUTInformationTest( Base ):

    __tablename__ = 'dut_information_test'

    id = Column(Integer, primary_key=True)
    testsession_id = Column( Integer, ForeignKey('test_session.id', ondelete='CASCADE'), nullable=False )
    testsession = relation( TestSession, backref = backref('dut_information_test', order_by =  id) )

    name = Column( String )
    valueFloat = Column( Float )
    valueString = Column( String )
    isFloat = Column( Boolean )

class OneFingerTapTest( Base ):

    #One-finger tap results are defined here
    __tablename__ = 'one_finger_tap_test'

    id = Column(Integer, primary_key=True)
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref=backref('one_finger_tap_test', order_by=id) )

    #Are results single tap or jitter
    jitter = Column( Boolean )

    #Common parameters
    robot_x = Column( Float )
    robot_y = Column( Float )
    robot_z = Column( Float )
    robot_azimuth = Column( Float )
    robot_tilt = Column( Float )
    point_number = Column( Integer )

    #Results
    panel_x = Column( Float )
    panel_y = Column( Float )
    panel_azimuth = Column( Float )
    panel_tilt = Column( Float )
    sensitivity = Column( Float )
    finger_id = Column( Integer )
    delay = Column( Float )
    time = Column( Float )

class OneFingerTapRepeatabilityTest( Base ):

    #One-finger tap results are defined here
    __tablename__ = 'one_finger_tap_repeatability_test'

    id = Column(Integer, primary_key=True)
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref=backref('one_finger_tap_repeatability_test', order_by=id) )

    #Common parameters
    robot_x = Column( Float )
    robot_y = Column( Float )
    robot_z = Column( Float )
    robot_azimuth = Column( Float )
    robot_tilt = Column( Float )
    point_number = Column( Integer )

    #Results
    panel_x = Column( Float )
    panel_y = Column( Float )
    panel_azimuth = Column( Float )
    panel_tilt = Column( Float )
    sensitivity = Column( Float )
    finger_id = Column( Integer )
    delay = Column( Float )
    time = Column( Float )
    event = Column( Integer )

class OneFingerSwipeTest( Base ):

    #One-finger swipe test is defined here
    __tablename__ = 'one_finger_swipe_test'

    id = Column( Integer, primary_key = True )
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref('one_finger_swipe_test', order_by = id) )

    robot_azimuth = Column( Float )
    robot_tilt = Column( Float )

    #For straight lines, start and stop positions are defined
    start_x = Column( Float )
    start_y = Column( Float )
    end_x = Column( Float )
    end_y = Column( Float )

    #For circular lines, also through position and radius in x and y directions are defined
    through_x = Column( Float )
    through_y = Column( Float )
    radius_x = Column( Float )
    radius_y = Column( Float )

class OneFingerSwipeResults( Base ):

    #One-finger swipe results are defined here
    __tablename__ = 'one_finger_swipe_results'

    id = Column( Integer, primary_key = True )
    swipe_id = Column( Integer, ForeignKey('one_finger_swipe_test.id', ondelete='CASCADE'), nullable=False )
    swipe = relation( OneFingerSwipeTest, backref = backref('one_finger_swipe_results', order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    panel_azimuth = Column( Float )
    panel_tilt = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )

class OneFingerStationaryReportingRateTest( Base ):

    #One Finger Stationary Reporting Rate Test is defined here
    __tablename__ = 'one_finger_stationary_reporting_rate_test'

    id = Column( Integer, primary_key = True )
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref('one_finger_stationary_reporting_rate_test', order_by = id) )

    #For straight lines, start and stop positions are defined
    robot_x = Column( Float )
    robot_y = Column( Float )

class OneFingerStationaryReportingRateResults( Base ):

    #One Finger Stationary Reporting Rate results are defined here
    __tablename__ = 'one_finger_stationary_reporting_rate_results'

    id = Column( Integer, primary_key = True )
    point_id = Column( Integer, ForeignKey('one_finger_stationary_reporting_rate_test.id', ondelete='CASCADE'), nullable=False )
    point = relation( OneFingerStationaryReportingRateTest, backref = backref('one_finger_stationary_reporting_rate_results', order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )

class OneFingerNonStationaryReportingRateTest( Base ):

    #One Finger Non Stationary Reporting Rate Test is defined here
    __tablename__ = 'one_finger_non_stationary_reporting_rate_test'

    id = Column( Integer, primary_key = True )
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref('one_finger_non_stationary_reporting_rate_test', order_by = id) )

    #For straight lines, start and stop positions are defined
    start_x = Column( Float )
    start_y = Column( Float )
    end_x = Column( Float )
    end_y = Column( Float )

class OneFingerNonStationaryReportingRateResults( Base ):

    #One Finger Non Stationary Reporting Rate results are defined here
    __tablename__ = 'one_finger_non_stationary_reporting_rate_results'

    id = Column( Integer, primary_key = True )
    swipe_id = Column( Integer, ForeignKey('one_finger_non_stationary_reporting_rate_test.id', ondelete='CASCADE'), nullable=False )
    swipe = relation( OneFingerNonStationaryReportingRateTest, backref = backref('one_finger_non_stationary_reporting_rate_results', order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )

class OneFingerStationaryJitterTest( Base ):

    #One Finger Non Stationary Reporting Rate Test is defined here
    __tablename__ = 'one_finger_stationary_jitter_test'

    id = Column( Integer, primary_key = True )
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref('one_finger_stationary_jitter_test', order_by = id) )

    #For straight lines, start and stop positions are defined
    robot_x = Column( Float )
    robot_y = Column( Float )
    robot_azimuth = Column( Float )
    robot_tilt = Column( Float )


class OneFingerStationaryJitterResults( Base ):

    #One Finger Non Stationary Reporting Rate results are defined here
    __tablename__ = 'one_finger_stationary_jitter_results'

    id = Column( Integer, primary_key = True )
    point_id = Column( Integer, ForeignKey('one_finger_stationary_jitter_test.id', ondelete='CASCADE'), nullable=False )
    point = relation( OneFingerStationaryJitterTest, backref = backref('one_finger_stationary_jitter_results', order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    panel_azimuth = Column( Float )
    panel_tilt = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )

class OneFingerFirstContactLatencyTest( Base ):

    #One-finger latency test is defined here

    __tablename__ = 'one_finger_first_contact_latency_test'

    id = Column(Integer, primary_key=True)
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref=backref('one_finger_first_contact_latency_test', order_by=id) )

    #One-finger Latency test results
    powerstate = Column( Integer )
    system_latency = Column( Float )
    delay = Column( Float )
    time = Column( Float )
    robot_x = Column( Float )
    robot_y = Column( Float )
    robot_z = Column( Float )

class SeparationTest( Base ):

    #Separation results are defined here
    __tablename__ = 'separation_test'

    id = Column(Integer, primary_key=True)
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref=backref('separation_test', order_by=id) )

    #Is measurement 2-, 3-, 4-, or 5-finger
    number_of_fingers = Column( Integer )

    robot_x = Column( Float )
    robot_y = Column( Float )
    robot_z = Column( Float )
    separation_distance = Column( Float )
    separation_angle = Column( Float )
    first_finger_offset = Column( Float )
    tool_separation = Column( Float )
    finger1_diameter = Column( Float )
    finger2_diameter = Column( Float )

class SeparationResults( Base ):

    #Separation results are defined here
    __tablename__ = 'separation_results'

    id = Column( Integer, primary_key = True )
    point_id = Column( Integer, ForeignKey('separation_test.id', ondelete='CASCADE') )
    point = relation( SeparationTest, backref = backref('separation_results', order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )

class PinchTest( Base ):

    __tablename__ = 'pinch_test'

    id = Column( Integer, primary_key = True )
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref('pinch_test', order_by = id) )
    robot_azimuth = Column( Float )
    robot_tilt = Column( Float )

    #For straight lines, start and stop positions are defined
    center_x = Column( Float )
    center_y = Column( Float )
    start_separation = Column ( Float)
    end_separation = Column( Float )

class PinchResults( Base ):

    __tablename__ = 'pinch_results'

    id = Column( Integer, primary_key = True )
    pinch_id = Column( Integer, ForeignKey('pinch_test.id', ondelete='CASCADE'))
    pinch = relation( PinchTest, backref = backref('pinch_results', order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    panel_azimuth = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )

class MultifingerTapTest( Base ):

    #Multifinger tap results are defined here
    __tablename__ = 'multi_finger_tap_test'

    id = Column(Integer, primary_key=True)
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref=backref('multi_finger_tap_test', order_by=id) )

    #Is measurement 2-, 3-, 4-, or 5-finger
    number_of_fingers = Column( Integer )

    robot_x = Column( Float )
    robot_y = Column( Float )
    robot_z = Column( Float )
    separation_distance = Column( Float )
    separation_angle = Column( Float )
    first_finger_offset = Column( Float )

class MultifingerTapResults( Base ):

    #Multifinger Tap results are defined here
    __tablename__ = 'multi_finger_tap_results'

    id = Column( Integer, primary_key = True )
    point_id = Column( Integer, ForeignKey('multi_finger_tap_test.id', ondelete='CASCADE') )
    point = relation( MultifingerTapTest, backref = backref('multi_finger_tap_results', order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )

class MultifingerSwipeTest( Base ):

    #One-finger swipe test is defined here
    __tablename__ = 'multi_finger_swipe_test'

    id = Column( Integer, primary_key = True )
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref('multi_finger_swipe_test', order_by = id) )

    #Is measurement 2-, 3-, 4-, or 5-finger
    number_of_fingers = Column( Integer )

    #For straight lines, start and stop positions are defined
    start_x = Column( Float )
    start_y = Column( Float )
    end_x = Column( Float )
    end_y = Column( Float )
    separation_distance = Column( Float )
    separation_angle = Column( Float )
    first_finger_offset = Column( Float )

    #Is test zoom, pinch or swipe
    test_type = Column( String )


class MultifingerSwipeResults( Base ):

    #Multifinger pinch results are defined here
    __tablename__ = 'multi_finger_swipe_results'

    id = Column( Integer, primary_key = True )
    swipe_id = Column( Integer, ForeignKey('multi_finger_swipe_test.id', ondelete='CASCADE'), nullable=False )
    swipe = relation( MultifingerSwipeTest, backref = backref('multi_finger_swipe_results', order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )


class Setting(Base):

    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String)
    desc = Column(String)
    dut = Column(String)

    def __init__(self, name, value, unit, desc, dut=""):
        self.name = name
        self.value = value
        self.unit = unit
        self.desc = desc
        self.dut = dut


class TestResult(Base):
    __tablename__ = 'test_result'
    id = Column(Integer, primary_key = True)
    test_id = Column(Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref('test_results') )
    result = Column(String)
    calculated = Column(DateTime)


# The global database singleton instance
db = None

""" Returns the global database instance """
# If there is an existing database given as config, let's use that one
# If not, a database with that name is created, if there is no config
# the last used datapath is used
def get_database():
    global db
    if db is None and database is None:
        db = ResultDatabase(getLastPath())
    elif db is None and database is not None:
        db = ResultDatabase(database)
    return db
