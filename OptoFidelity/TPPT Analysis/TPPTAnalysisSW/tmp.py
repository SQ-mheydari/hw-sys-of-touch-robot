# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

from .utils import Timer

#import matplotlib.pyplot as plt
#import plot_factory
#import transform2d 
#import math
#import threading

#import measurementdb
#import sqlite3
#import time

def test_line_transformation():
    #line = [(-1, -1), (1, 2)]
    line = [(1, 1), (0, 0.9), (-1, 1.1)]

    direction = (line[-1][0] - line[0][0], line[-1][1] - line[0][1])
    angle = math.atan2(direction[1], direction[0])
    print "Angle: %.3f*pi" % (angle / math.pi)
    transform = transform2d.Transform2D.offset(-line[0][0], -line[0][1]) + transform2d.Transform2D.rotate_radians(-angle)
    line2 = transform.transform(line)

    plt.figure(1)
    plt.axis('equal')
    plt.plot([p[0] for p in line], [p[1] for p in line])
    plt.plot([p[0] for p in line2], [p[1] for p in line2])
    plt.show()

def run_tap_test():
    """ Simulate a tap test by creating a test and adding new taps repeatedly """

    testsession_id = 2 # Measurement will be added to this session
    original_test_id = 15 # Measurements will be copied from this test id

    db = measurementdb.get_database()
    session = db.session()

    test = {'testsession_id': testsession_id, 
            'starttime': '2014-01-31 16:27:17', 
            'endtime' : '2014-01-31 16:28:07', 
            'sample_id': None, 
            'slot_id': 1, 
            'invalid': 0, 
            'testtype_id': 0}
    test = measurementdb.TestItem(**test)
    session.add(test)
    session.flush()
    print "New test id: %d" % test.id 

    taps = session.query(measurementdb.OneFingerTapTest).filter(measurementdb.OneFingerTapTest.test_id == original_test_id).\
                                                         order_by(measurementdb.OneFingerTapTest.id)

    #oft_columns = ['jitter', 'robot_x', 'robot_y', 'robot_z', 'point_number', 'panel_x', 'panel_y', 'sensitivity', 'finger_id', 'delay', 'time']
    oft_columns = [c.name for c in measurementdb.OneFingerTapTest.__table__.columns]
    print str(oft_columns)
    for tap in taps:
        dbtap = measurementdb.OneFingerTapTest()
        for column in oft_columns:
            setattr(dbtap, column, getattr(tap, column))
        dbtap.test = test
        session.add(dbtap)
        session.commit()
        print "Added tap id %d" % dbtap.id
        time.sleep(0.5)

def create_image(index):
    plot_factory.plot_dummy_image('static/img/generated/dummy%d.png' % index, {'points':[(0,index), (1,2*index), (2*index,4)]}, str="Test %d" % index)

def run_synchro_test():
    import utils
    utils.Timer.do_timing = True
    for i in range(1, 10):
        t = threading.Thread(target=create_image, args=(i,))
        t.start()

def copy_testsessions(conn_src, conn_dst):
    c = conn_src.cursor()
    for row in c.execute("select * from test_sessions order by id"):
        # Create new test session
        conn_dst.execute("insert into test_session values(?, ?, ?, ?, ?, ?)", (row['id'], row['operator'], row['starttime'], row['endtime'], row['invalid'], row['notes']))
        # Create a new DUT
        conn_dst.execute("insert into test_dut values(?, ?, ?, ?, ?)", (row['id'], row['program'], row['manufacturer'], row['batch'], 'Sample'))
    # Copy test items
    for row in c.execute("select * from ddt_test order by id"):
        conn_dst.execute("insert into test_item values(?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                         (row['id'], row['testsession_id'], row['testsession_id'], row['starttime'], row['endtime'], 
                          row['slot_id'], 'OF', row['invalid'], row['testtype_id']))


def copy_db(src, dest): 
    conn_src = sqlite3.connect(src)
    conn_src.row_factory = sqlite3.Row
    conn_dst = sqlite3.connect(dest)

    copy_testsessions(conn_src, conn_dst)
    conn_src.close()
    conn_dst.commit()
    conn_dst.close()

import tests.test_multifinger_tap
from testbase import TestBase

def test_multifinger_tap(test_id):
    Timer.do_timing = True
    testclass = TestBase.create(test_id)
    results = testclass.read_test_results()
    print str(results)

if __name__ == '__main__':
    #copy_db(r'c:\Work\database_old.sqlite', r'c:\Work\database.sqlite')
    test_multifinger_tap('4')