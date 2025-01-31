# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

import TPPTAnalysisSW.transform2d as transform2d
import TPPTAnalysisSW.measurementdb as db


def format_parameter_name(name):
    """
    Format parameter name to more readable form.
    Converts e.g. "my_parameter" to "My parameter".
    """
    name = name.replace("_", " ")

    if len(name) > 0:
        name = name[0].upper() + name[1:]

    return name


class TestSessionInfo:
    """ Information class that holds test session information contents """

    def __init__(self, testsession=None, testsession_id=None, dbsession=None):
        """ Initializes the session info """

        if testsession is None:
            if dbsession is None:
                with db.get_database().session() as dbsession:
                    self.__init__(testsession, testsession_id, dbsession)
                    return
            testsession = dbsession.query(db.TestSession).filter(db.TestSession.id == testsession_id).first()

        self.id = testsession.id
        
        self.operator = testsession.operator
        self.starttime = testsession.starttime
        self.endtime = testsession.endtime
        self.notes = testsession.notes
        
        # Fetch the session parameters
        self.parameters = {}
        for param in testsession.session_parameters:
            name = format_parameter_name(param.name)

            if param.isFloat:
                self.parameters[name] = param.valueFloat
            else:
                self.parameters[name] = param.valueString

class TestDUTInfo:
    """ Information class that holds test session information contents """

    def __init__(self, testdut=None, testdut_id=None, dbsession=None):
        """ Initializes the DUT info """

        if testdut is None:
            if dbsession is None:
                with db.get_database().session() as dbsession:
                    self.__init__(testdut, testdut_id, dbsession)
                    return
            testdut = dbsession.query(db.TestDUT).filter(db.TestDUT.id == testdut_id).first()

        self.id = testdut.id
        
        self.program = testdut.program
        self.manufacturer = testdut.manufacturer
        self.batch = testdut.batch
        self.sample_id = testdut.sample_id
        
        # Fetch the session parameters
        self.parameters = {}
        for param in testdut.dut_parameters:
            if param.isFloat:
                self.parameters[param.name] = param.valueFloat
            else:
                self.parameters[param.name] = param.valueString

        # Handle the parameters

        # Digitizer resolution
        self.digitizer_resolution = [float(s) for s in self.parameters['DUT resolution [x;y, p.c.]'].split(';')]
        # Physical dimensions
        self.dimensions = [float(s) for s in self.parameters['DUT dimensions [x;y, mm]'].split(';')]
        # Offset to be added to the measurements
        self.offset = [float(s) for s in self.parameters['DUT offset [x;y, mm]'].split(';')]
        
        # Flip x-coordinates
        self.flipx = False
        if 'Flip X coordinates' in self.parameters:
            if self.parameters['Flip X coordinates'] is None or self.parameters['Flip X coordinates'] != "0":
                self.flipx = True

        # Flip x-coordinates
        self.flipy = False
        if 'Flip Y coordinates' in self.parameters:
            if self.parameters['Flip Y coordinates'] is None or self.parameters['Flip Y coordinates'] != "0":
                self.flipy = True

        # Switch X->Y
        self.switchxy = False
        if '(X,Y) --> (Y,X)' in self.parameters:
            if self.parameters['(X,Y) --> (Y,X)'] is None or self.parameters['(X,Y) --> (Y,X)'] != "0":
                self.switchxy = True
    
    def save(self, dbsession=None):
        if dbsession is None:
            with db.get_database().session() as dbsession:
                return self.save(dbsession)

        testdut = dbsession.query(db.TestDUT).filter(db.TestDUT.id == self.id).first()
        saveparams = {
                      'DUT resolution [x;y, p.c.]': ";".join(str(f) for f in self.digitizer_resolution),
                      'DUT dimensions [x;y, mm]': ';'.join(str(f) for f in self.dimensions),
                      'DUT offset [x;y, mm]': ';'.join(str(f) for f in self.offset),
                      'Flip X coordinates': '1' if self.flipx else '0',
                      'Flip Y coordinates': '1' if self.flipy else '0',
                      '(X,Y) --> (Y,X)': '1' if self.switchxy else '0',
                      }

        testdut.manufacturer = self.manufacturer
        testdut.program = self.program
        testdut.batch = self.batch
        testdut.sample_id = self.sample_id

        for param in testdut.dut_parameters:
            if param.name in saveparams:
                # Update existing value
                param.valueString = saveparams[param.name]
                param.isFloat = None
                del saveparams[param.name]

        for key, value in saveparams.items():
            # Add non-existing values (a strange situation...)
            dbsession.add(db.DutParameters(dut_id=self.id, name=key, valueString=value))

        dbsession.commit()
