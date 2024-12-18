# Configuration

This section instructs how to use and modify TnT Server configuration file for use
for different robots and use cases.

# Overview

TnT Server is a software component which is deployed from master branch to many different customers.
Each customer may have somewhat different robot HW and other requirements from the software.
All the software is developed in TnT Server master and the features that are applicable to given
project are defined in configuration file.

The configuration file is a YAML file located under `configuration` directory.

Usually the included features are configured to include some of following:

- Robot (3-axis, synchro finger, voicecoil)
- Cameras (Gige or USB)
- Functional testing: OCR and icon detection
- Performance testing: camera trigger, analyzers
- Various detectors, analyzers and sensors

# Base configuration

There are two full configuration files under `configuration` directory that can be directly used without modifications:

- `simulation_3axis.yaml` - Standard 3-axis one finger (no voicecoil) simulator.
- `simulation_synchro.yaml` - Standard Synchrofinger simulator.

These files contain all possible pieces of configuration that might be used in a project delivery.
Everything that is not applicable to given project should be removed. Especially simulator specific configurations
should be removed from robot delivery. See the configuration files for explanation for each piece of configuration.

When setting up development environment, these configurations can be used as they are.

Both configuration files contain additional simulation content such as DUTs and calibration targets.
These can be used for testing purposes. The DUTs and tips in these configs should be maintained to be
valid if any code changes are done.

When any code changes are done such as adding new nodes or modifying existing nodes, these two
configuration files should be updated accordingly. One should add comments that are necessary for
understanding when the node needs to be used and how to configure it.

# Simulation vs. real robot

Robot can be configured to be ran as real robot or in simulation mode. This is controlled by Robot argument `simulator`.
Change this to `true` in given configuration file to control a real robot.

Camera can also be ran in simulation mode. This is controlled by Camera `driver` argument. Change this to appropriate
driver in given configuration file when controlling a real camera. The default value is `simulator`.

# Specific configurations

Standard or "close to standard" robot configurations are maintained in `configuration/robots` directory.
Because the configurations would contain a lot of the same content as e.g. `simulation_3axis.yaml`, only Robot configuration
part is maintained in these files. Hence to obtain a complete configuration for these cases, you need to replace the
Robot and Camera configurations in `simulation_3axis.yaml` by the corresponding parts in the specific configuration.
Note that DUT and tip positioning may then be invalid depending on the robot geometry.

# Client configuration

TnT Server runs a REST API server. This is not used directly by customers. Instead they use TnT Client (Python) to
send commands to TnT Server via the REST API. This client is also project specific because only parts of the
entire API that are applicable to the projects should be exposed. For example, if the project does not include
icon detection the related API should not be exposed because the feature would not work without valid license.

TnT Client is automatically generated from the REST API definition and the parts to be included in the client
are determined by a configuration file. In `configuration` directory there is `client_config.yaml` which contains
the most frequently used API. Remove what is not applicable to specific project.

See `client/README.md` for more information on generating the client. The document is contained in that directory
because it should be bundled in with the TnT Server build.
