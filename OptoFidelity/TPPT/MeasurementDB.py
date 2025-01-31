# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

import traceback

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relation, backref, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy import event
import json
import time
import sqlite3
from scriptpath import join_script_root_directory
import logging

Base = declarative_base()

logger = logging.getLogger(__name__)


def on_connect(conn, record):
    conn.execute('pragma foreign_keys=ON')


def getConfig():

    with open(join_script_root_directory('config.json'), 'r') as f:
        conf_data = f.read()
    try:
        conf = json.loads(conf_data)
    except Exception as e:
        conf = {}
        logger.warning("Failed to load config.json: {}".format(str(e)))

    return conf


def saveLastPath(path):
    # Update path to existing config
    conf = getConfig()
    conf["lastDB"] = path

    with open(join_script_root_directory('config.json'), 'w') as f:
        f.write(json.dumps(conf, indent=4))


def getLastPath():
    return getConfig()["lastDB"]


def create_sqlite_indices(database_file, indices):
    """ Creates indices to the SQLite database """
    db = sqlite3.connect(database_file)

    curindices = get_current_indices(db)

    for index_values in indices:
        # For some reason curindices has '_fkey' appended to names

        index_name = index_values[0] + '_fkey'

        if index_name not in curindices:
            logging.info("Creating database index %s" % index_name)
            create_index(db, index_name, index_values)

    db.close()

def get_current_indices(database):
    """ Returns an array of currently declared indices in the database """

    c = database.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
    indices = [r[0] for r in c.fetchall()]

    return indices

def create_index(database, index_name, index_values):
    """ Creates the specified index in the database """
    database.execute('CREATE INDEX IF NOT EXISTS %s ON %s ( %s )' % (index_name, index_values[0], index_values[1]))

class ResultDatabase:

    def __init__(self, filename, test_case_modules):
        self.db = None
        self.session = None
        self.dbpath = None
        self.test_case_modules = test_case_modules

        # curved line test contains different tests
        # define new ones here
        self.CURVED_LINE_TESTS = {1: "Handwriting"}

        self.CURVED_ANALYSIS_TYPES = {1: ["path_accuracy",
                                          "curved_path_linearity",
                                          "reported_pos_proximity_to_robot_pos",
                                          "path_length_comparison"]
                                      }

        self.initialize(filename)
        saveLastPath(filename)

    def initialize(self, filename):

        self.dbpath = filename
        self.db = create_engine('sqlite:///' + filename)
        event.listen(self.db, 'connect', on_connect)
        self.session = sessionmaker(bind=self.db, autoflush=False)
        Base.metadata.create_all(self.db)
        
        # TODO: Some explanation is in order.
        # These are database indices for various test and test result tables.
        indices = [
            ['dut_parameters', 'dut_id'],
            ['test_item', 'testsession_id']
            ]

        # Insert database indices defined by test case modules.
        for module in self.test_case_modules:
            # If test case module has no table index definition, it does not use the database.
            if not hasattr(module, 'DB_TABLE_INDICES'):
                continue

            for module_indices in module.DB_TABLE_INDICES:
                indices.append(module_indices)

        create_sqlite_indices(filename, indices)

        # Check if ResultDatabase already contains test types below.
        try:
            # TODO: It would be nice if these test type names were defined in respective test case Python files.
            # However, do we wan't the ID values to be unique if test case order or number changes? Perhaps hash from name?
            # Note: TestType integer IDs must match the ones used in analysis.
            session = self.session()
            session.add( TestType( 0, 'One Finger Tap Test' ) )
            session.add( TestType( 1, 'One Finger Swipe Test' ) )
            session.add( TestType( 2, 'One Finger First Contact Latency Test' ) )
            session.add( TestType( 5, 'MultiFinger Swipe Test'))
            session.add( TestType( 8, 'MultiFinger Tap Test'))
            session.add( TestType( 9, 'One Finger Stationary Jitter'))
            session.add( TestType( 10, 'One Finger Tap Repeatability'))
            session.add( TestType( 11, 'One Finger Stationary Reporting Rate Test'))
            session.add( TestType( 12, 'One Finger Non Stationary Reporting Rate Test'))
            session.add( TestType( 14, 'Separation Test'))
            session.add( TestType( 16, 'Pinch Test'))
            session.commit()
            session.close()
        except:
            # Already created
            pass
        try:
            # Create settings for analysis if not created already. Analysis expects these to exist in database.
            self.checksetting(Setting('maxjitter',1.0,"mm","Maximum allowed non stationary jitter"))
            self.checksetting(Setting('maxstationaryjitter',1.0,"mm","Maximum allowed stationary jitter"))
            self.checksetting(Setting('jittermask',10.0,"mm","Non stationary jitter search mask"))
            self.checksetting(Setting('maxactiveresponselatency',25.0,"ms","Maximum allowed response latency from an active state for the initial input"))
            self.checksetting(Setting('maxidleresponselatency',50.0,"ms","Maximum allowed response latency from an idle state"))
            self.checksetting(Setting('minreportingrate',120.0,"Hz","Minimum allowed reporting rate"))
            self.checksetting(Setting('minavgreportingrate', 120.0, "Hz", "Minimum allowed average reporting rate"))
            self.checksetting(Setting('maxposerror',1.0,"mm","Maximum allowed accuracy error"))
            self.checksetting(Setting('maxmissing',0.0,"pcs","Maximum allowed missing inputs"))
            self.checksetting(Setting('maxoffset',1.0, "mm","Maximum allowed offset"))
            self.checksetting(Setting('maxseparation',12.0,"mm","Maximum allowed finger separation distance (vertical and horizontal)"))
            self.checksetting(Setting('maxdiagseparation',15.0,"mm","Maximum allowed finger separation distance (diagonal)"))
            self.checksetting(Setting('minppi',200.0,"ppi","Minimum display resolution"))
            self.checksetting(Setting('maxrepeaterror',1.0,"mm","Maximum tap repeatability error"))
            self.checksetting(Setting('edgelimit',-1.0,"mm","Edge area distance from edge in Tap test"))
            self.checksetting(Setting('edgepositioningerror',1.5,"mm","Maximum allowed accuracy error in edge area"))
            self.checksetting(Setting('maxedgemissing',0.0,"pcs","Maximum allowed missing edge inputs"))
            self.checksetting(Setting('maxmissingswipes',0.0,"pcs","Maximum allowed missing swipes in swipe test"))
            self.checksetting(Setting('maxbrokenswipes', 0.0, "pcs", "Maximum allowed broken swipes in linearity test"))
            self.checksetting(Setting('maxdiagoffset', 0.0, "mm", "Maximum allowed offset for diagonal swipes (0 to disable)"))
            self.checksetting(Setting('maxdiagjitter', 0.0, "mm", "Maximum allowed jitter for diagonal swipes (0 to disable)"))
            # When adding settings, remember to add them to settings.py categories
        except: #IntegrityError:
            logging.info(traceback.format_exc())
            # Already created
            pass

    def changeDatabase(self, path):
        self.initialize(path)
        saveLastPath(path)

    def add( self, data, commit = True, expire_on_commit=True ):
        session = self.session(expire_on_commit=expire_on_commit)
        session.add( data )
        if commit == True:
            self.session_commit(session)
        _id = data.id
        session.close()
        return _id

    def addAll( self, data, commit = True ):
        session = self.session()
        session.add_all( data )
        if commit == True:
            self.session_commit(session)
        session.close()

    def getEngine(self):
        return self.db

    def update(self, data):
        session = self.session()
        session.merge(data)
        self.session_commit(session)
        session.close()

    def commit(self):
        session = self.session()
        self.session_commit(session)
        session.close()

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
            dbsession = self.session()
        try:
            return dbsession.query( TestSession ).all()
        finally:
            dbsession.close()

    def get_test_session( self, session_id ):
        session = self.session()
        try:
            return session.query( TestSession ).filter_by( id=session_id ).first()
        finally:
            session.close()

    def get_TestType( self, type_id ):
        session = self.session()
        try:
            return session.query(TestType).filter_by( id=type_id ).all()
        finally:
            session.close()

    def get_TestTypes( self ):
        session = self.session()
        try:
            return session.query(TestType).all()
        finally:
            session.close()

    def get_programs( self ):
        session = self.session()
        try:
            return session.query( TestSession.program).order_by(TestSession.program)
        finally:
            session.close()

    def get_manufacturers( self, Program ):
        session = self.session()
        try:
            return session.query( TestSession.manufacturer).order_by(TestSession.manufacturer).all()
        finally:
            session.close()

    def checksetting( self, setting ):
        session = self.session()
        dbsetting = session.query(Setting).filter_by(name=setting.name, dut=setting.dut).first()
        if dbsetting is None:
            # Setting does not exist
            session.add(setting)
            self.session_commit(session)
        session.close()

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
