import TPPTcommon.containers as containers
#from TPPTcommon.TestStep import TestStep
from TPPTcommon.Node import *
from TPPTcommon.grid import *
from TPPTcommon.visualization import GridVisContainer
from MeasurementDB import *
from TPPTcommon.script_config import *

import logging
logger = logging.getLogger(__name__)

# Database table name for the test case.
DB_TEST_TABLE_NAME = 'pinch_test'

# Database table name for the test results.
DB_RESULTS_TABLE_NAME = 'pinch_results'

# Database table indices associated with test case.
DB_TABLE_INDICES = [[DB_TEST_TABLE_NAME, 'test_id'], [DB_RESULTS_TABLE_NAME, 'pinch_id']]

class PinchTest( Base ):

    __tablename__ = DB_TEST_TABLE_NAME

    id = Column( Integer, primary_key = True )
    test_id = Column( Integer, ForeignKey('test_item.id', ondelete='CASCADE'), nullable=False )
    test = relation( TestItem, backref = backref(DB_TEST_TABLE_NAME, order_by = id) )
    robot_azimuth = Column( Float )
    robot_tilt = Column( Float )

    #For straight lines, start and stop positions are defined
##    start_x = Column( Float )
##    start_y = Column( Float )
##    end_x = Column( Float )
##    end_y = Column( Float )
    center_x = Column( Float )
    center_y = Column( Float )
    start_separation = Column ( Float)
    end_separation = Column( Float )
    #panel_azimuth = Column( Float )

class PinchResults( Base ):

    __tablename__ = DB_RESULTS_TABLE_NAME

    id = Column( Integer, primary_key = True )
    pinch_id = Column( Integer, ForeignKey(DB_TEST_TABLE_NAME + '.id', ondelete='CASCADE'), nullable=False )
    pinch = relation( PinchTest, backref = backref(DB_RESULTS_TABLE_NAME, order_by = id) )

    panel_x = Column( Float )
    panel_y = Column( Float )
    panel_azimuth = Column( Float )
    sensitivity = Column( Float )
    delay = Column( Float )
    finger_id = Column( Integer )
    time = Column( Float )
    event = Column( Integer )


class Pinch(TestStep):
    """
    In this test case we perform pinches in various orientations in the center of the DUT.
    """
    def __init__(self, context):
        super().__init__('Pinch')

        self.context = context

        # Tips for the two fingers are defined in test properties.
        tip_names = [node.name for node in context.tips_node.children]

        if tip_names:
            self.controls.tip1 = tip_names[0]
            self.controls.info['tip1'] = {'label': 'Finger 1 tip', 'items': tip_names,
                                          'tooltip': self.context.tooltips['Tip 1']}

            self.controls.tip2 = tip_names[0]
            self.controls.info['tip2'] = {'label': 'Finger 2 tip', 'items': tip_names,
                                          'tooltip': self.context.tooltips['Tip 2']}

        self.controls.test_locations = 'Center'
        self.controls.info['test_locations'] = {'label': 'Test Locations', 'items': {'Center', 'Center Line', 'Quadrants', 'All Locations'}}
        
        self.controls.pinch_direction = 'Both'
        self.controls.info['pinch_direction'] = {'label': 'Pinch Direction', 'items': {'Both', 'Pinch In', 'Pinch Out'}}
            
        # It is possible that separation test is loaded with robot that doesn't support it (e.g. 3axis simulator).
        try:
            separation_limits = self.context.robot.finger_separation_limits()
        except:
            separation_limits = [10.0, 140.0]
            self.context.html_warning("Could not fetch separation limits from robot, using values {}"
                                      .format(str(separation_limits)))

        # Default min separation is maximum robot's minimum separation and 10 mm which is the typical tip hull diameter.
        self.controls.min_separation = max(separation_limits[0], 10.0)

        if get_config_value("azimuth_angles"):
            self.controls.azimuth_angles = "-45, 0, 45"
            self.controls.info["azimuth_angles"] = {"label": "Azimuth angles [°]",
                                                    "tooltip": self.context.tooltips["Azimuth angles"]}

        self.controls.speed = 30.0
        self.controls.info['speed'] = {'label': 'Speed of Pinch movement'}

        self.controls.pinch_length = 10.0
        self.controls.info['pinch_length'] = {'label': 'Length of Pinch Gesture'}

    def execute(self):
        """
        The 'execute' method contains the actual work that the
        test step is doing.
        """
        dut = self.context.get_active_dut()

        #Locations Definitions
        dut_center = [[(dut.width/2), (dut.height/2)]]
        center_line = [[(dut.width/2), (dut.height/3)], dut_center[0], [(dut.width/2), (dut.height/3)*2]]
        quadrants = [[(dut.width/3), (dut.height/3)], [(dut.width/3)*2, (dut.height/3)], [(dut.width/3)*2, (dut.height/3)*2], [(dut.width/3), (dut.height/3)*2]]
        all_locations = center_line+quadrants

        self.locations_dict = {"Center":dut_center, "Center Line":center_line, "Quadrants":quadrants, "All Locations":all_locations}
        self.locations = self.locations_dict[self.controls.test_locations]

        #clearance = float(self.controls.clearance)

        test_item = self.context.create_db_test_item("Pinch Test")  #todo

        for location in self.locations:
            pinch_paths = self.create_grid(dut, location)  #create the pinch measurement 

            for index, pinch in enumerate(pinch_paths):

                    # Create database entry for the pinch.
                    pinch_id = self.create_pinch_id(pinch, test_item)  #todo, pinch isn't right here 

                    # Jump with default speed over the start point of the pinch
                    self.context.set_robot_default_speed()
                    dut.jump(pinch.center_x, pinch.center_y, dut.base_distance, dut.base_distance)

                    # set Azimuth Line
                    dut.move(pinch.center_x, pinch.center_y, dut.base_distance, azimuth=pinch.azimuth)

                    #set the distance between the fingers before it starts the pinch gesture
                    self.context.robot.set_finger_separation(pinch.start_separation)
                    
                    ## Setting the speed we will use to perforn the pinch
                    self.context.set_robot_speed(self.controls.speed)  

                    # Start capturing a continuous stream of touch events.
                    continuous_measurement = self.context.create_continuous_measurement(pinch)   ##unsure whethere pinch works here or if it should be None
                    continuous_measurement.start(timeout=0.5)  ## This is a default value. see function get_continuous_measurement_timeout() if you want it to be dynamic but I don't quite understand it yet

                    ### Draw expected line to UI
                    #self.context.draw_dut_expected_line(pinch.start_x, pinch.start_y, pinch.end_x, pinch.end_y)

                    dut.pinch(pinch.center_x, pinch.center_y, pinch.start_separation, pinch.end_separation, pinch.azimuth, clearance=-.1)

                    # End measuring touch events.
                    continuous_measurement.end()

                    # Parse touch event data.
                    touchlist = continuous_measurement.parse_data()

                    # Save results to database.
                    self.save_measurement_data(pinch_id, touchlist)

                    # Check if test should pause or stop.
                    self.context.breakpoint()

            self.context.close_db_test_item(test_item)

        self.context.close_db_test_item(test_item)
        
    def create_grid(self, dut, location):
        # min_separation = self._get_finger_separation(self.controls.min_finger_clearance,
        #                                              float(self.controls.finger_size))
        max_separation = self.controls.min_separation + self.controls.pinch_length * 2
        if max_separation > dut.width or max_separation > dut.height:
            raise Exception("Pinch is too wide for DUT")

        azimuth_angles = [0,45,90]

        if hasattr(self.controls, "azimuth_angles"):
            azimuths = parse_numbers(self.controls.azimuth_angles)
        else:
            azimuths = azimuth_angles

        grid = []
        for azimuth in azimuths: ## These are the angles around the center point that the pinches will happen
            if self.controls.pinch_direction == 'Both' or self.controls.pinch_direction == 'Pinch Out':
                grid.append(containers.Pinch(location[0], location[1], self.controls.min_separation, max_separation, azimuth))
            if self.controls.pinch_direction == 'Both' or self.controls.pinch_direction == 'Pinch In':
                grid.append(containers.Pinch(location[0], location[1], max_separation, self.controls.min_separation, azimuth))
        return grid

    def visualize_grid(self, dut):
        """
        Construct a visualization of the test case grid.
        :param dut: DUT where the grid is evaluated on.
        """

        #Locations Definitions
        dut_center = [[(dut.width/2), (dut.height/2)]]
        center_line = [[(dut.width/2), (dut.height/3)], dut_center[0], [(dut.width/2), (dut.height/3)*2]]
        quadrants = [[(dut.width/3), (dut.height/3)], [(dut.width/3)*2, (dut.height/3)], [(dut.width/3)*2, (dut.height/3)*2], [(dut.width/3), (dut.height/3)*2]]
        all_locations = center_line+quadrants

        locations_dict = {"Center":dut_center, "Center Line":center_line, "Quadrants":quadrants, "All Locations":all_locations}
        locations = locations_dict[self.controls.test_locations]

        test_pattern = []

        for location in locations:
            test_pattern += self.create_grid(dut, location)  #create the pinch measurement

        return GridVisContainer(self.__class__.__name__, (dut.width, dut.height), test_pattern, dut.name)
    
    def create_pinch_id(self, pinch, test_item):
        """
        Create gesture and add to database.
        :return: id of created gesture.
        """
    
        test = PinchTest()
        test.center_x = pinch.center_x
        test.center_y = pinch.center_y
        test.robot_azimuth = pinch.azimuth
        test.start_separation = pinch.start_separation
        test.end_separation = pinch.end_separation
        test.test_id = test_item.id
        #test.finger_size = float(self.controls.finger_size)
        test.speed = self.controls.speed
        self.context.db.add(test)
        return test.id
    

    def save_measurement_data(self, pinch_id, touchlist):
        """
        This is the touch measurement reported back to us from the DUT. 
        """

        dblist = []

        for testresult in touchlist:
            test_results = PinchResults()
            print(testresult)

            test_results.panel_x = float(testresult[0])
            test_results.panel_y = float(testresult[1])
            test_results.sensitivity = float(testresult[2])
            test_results.finger_id = int(testresult[3])
            test_results.delay = testresult[4]
            test_results.time = testresult[5]
            test_results.event = testresult[6]
            test_results.panel_azimuth = float(testresult[7])
            test_results.panel_tilt = float(testresult[8])
            test_results.pinch_id = pinch_id
            dblist.append(test_results)

            self.context.add_dut_point(float(testresult[0]), float(testresult[1]), False, False)

        self.context.db.addAll(dblist)
