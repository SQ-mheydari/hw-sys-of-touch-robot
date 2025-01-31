import tntserver.globals
from .comm import *
import os
import importlib


class RobotSimulator:
    def __init__(self, model: str, kinematic, host:str = '127.0.0.1', port: int = 4001, visualize: bool = True):

        # collect simulator names and axis specs
        self.simulators = {}

        # get all simulators;
        # all files in simulator folder that start with "simulator_"
        """
        simulators = {}
        files = os.listdir(os.path.dirname(__file__))
        for filename in files:
            if "simulator_" in filename:
                importname = "." + filename
                importname = ".".join(importname.split('.')[:-1])

                parts = filename.split("_")
                project_id = parts[1] # Simulator_xxxx_something
                classname = "Simulator_" + project_id

                module = importlib.import_module(importname, self.__class__.__module__)

                cls = getattr(module, classname)

                simulator_name = getattr(cls, "name")
                simulators[simulator_name] = cls

        model = str(model).lower()
        simulator_model = simulators[model]
        """
        module = importlib.import_module(".simulator_{}".format(model), "tntserver.drivers.robots.goldenmov.simulator")
        cls = getattr(module, "Simulator_{}".format(model))

        simulator_model = cls

        simulator_title = getattr(simulator_model, "title")

        if simulator_model is not None:
            if visualize:
                self.connection = WebGoldenSimulatorComm(host, port, axis_info=simulator_model.axis)

                self.connection.setTitle(simulator_title)

                # instantiate simulator
                self.model = simulator_model(self.connection, kinematic)
                self.model.create_model()
                tntserver.globals.simulator_model = self.model
            else:
                self.connection = NumericGoldenSimulatorComm(axis_info=simulator_model.axis)

            tntserver.globals.simulator_instance = self.connection

        else:
            raise(Exception("could not load simulator robot model {}".format(model)))



    def registerSimulator(self, simulator):
        self.simulators[simulator.name] = simulator
