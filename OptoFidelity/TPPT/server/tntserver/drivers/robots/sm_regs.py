"""
Simplemotion constant definitions.
These can be used to set and get specific axis parameter values.
"""
import enum


def BV(bit):
    return 1 << bit


SMP_MIN_VALUE_MASK = 0x4000
SMP_MAX_VALUE_MASK = 0x8000

# NORMAL SM PARAMS
SMP_CUMULATIVE_STATUS = 13
SMP_ABSOLUTE_SETPOINT = 551
SMP_TRAJ_PLANNER_ACCEL = 800
SMP_TRAJ_PLANNER_VEL = 802
SMP_SYSTEM_CONTROL_RESET_FB_AND_SETPOINT = 512

SMP_SET_GPIO_PROPERTIES = 145

SMP_DIGITAL_OUT_VALUE_1 = 136
SMP_DIGITAL_OUT_VALUE_2 = 137

# set IO pin direction: 0=input, 1=output. May not be supported by HW.
SMP_DIGITAL_IO_DIRECTION_1 = 140
SMP_DIGITAL_IO_DIRECTION_2 = 141
SMP_DIGITAL_IO_DIRECTION_3 = 142
SMP_DIGITAL_IO_DIRECTION_4 = 143

SMP_FAULTS = 552
SMP_STATUS = 553
SMP_STAT_TARGET_REACHED = BV(1)
SMP_STAT_ENABLED = BV(4)
SMP_STAT_SERVO_READY = BV(8)
SMP_STAT_HOMING = BV(11)
SMP_STAT_INITIALIZED = BV(12)

SMP_ABSOLUTE_POS_TARGET = 551
SMP_ACTUAL_POSITION_FB = 903
SMP_TORQUELIMIT_CONT = 410
SMP_TORQUELIMIT_PEAK = 411

# SMP_SPRING_CONSTANT is the spring constant of sensor in micrograms per encoder count
SMP_SPRING_CONSTANT = 8130  #

# SMP_FORCE_FEEDBACK_VALUE is read-only variable of force feedback reading in milligrams
SMP_FORCE_FEEDBACK_VALUE = 8131

# SMP_FORCE_FAULT_LIMIT is the threshold for over force fault in mg
SMP_FORCE_FAULT_LIMIT = 8132

# Force controller PID gains
SMP_FORCE_P = 8133
SMP_FORCE_I = 8134
SMP_FORCE_D = 8135

# SMP_FORCE_TARE_THRESHOLD is the maximum allowed variations in force reading during the stabilize time (mg)
SMP_FORCE_TARE_THRESHOLD = 8136

# SMP_FORCE_TARE_STABILIZE_TIME is the time (in ms) for force to stay within +/-SMP_FORCE_TARE_THRESHOLD to finish taring
SMP_FORCE_TARE_STABILIZE_TIME = 8137

# SMP_FORCE_TOUCH_THRESHOLD is the threshold in mg where touch probe mode stops motion
SMP_FORCE_TOUCH_THRESHOLD = 8138

# SMP_FORCE_CTR_OUT_RAW is read-only value of force controller PID
SMP_FORCE_CTR_OUT_RAW = 8139

# SMP_FORCE_CTR_OUT_FILTERED is placeholder, not used currently
SMP_FORCE_CTR_OUT_FILTERED = 8140

""" SMP_FORCE_MODE
 * sets operating mode.
 * -normal position mode
 * -touch probing mode
 * -force control mode
 * -tare
 *
 * TOUCH PROBING MODE:
 * this mode will differ from normal position control mode by
 * -using mode specific acceleration/velocity limits SMP_VEL_LIMIT_IN_TOUCH_PROBING and SMP_ACCEL_LIMIT_IN_TOUCH_PROBING
 * -motion (of any direction) will stop when 20hz low pass filtered force (of any polarity) exceeds SMP_FORCE_TOUCH_THRESHOLD
 * usage:
 * 1) set relevant parameters (touch probing threshold, touch probing accel/vel limits). also suggest doing tare before next step.
 * 2) write SMP_FORCE_MODE=FORCE_MODE_SET_TOUCH_PROBE_CTRL
 * 3) send setpoint command far enough to cause collision
 * 4) poll SMP_FORCE_FUNCTIONS_STATUS - touch has happened when FFS_TOUCH_PROBE_SUCCESS goes true
 * 5) set SMP_FORCE_MODE to desired mode
 *
 * TARE MODE:
 * this mode will wait until force sensor has stabilized within +/-SMP_FORCE_TARE_THRESHOLD for time
 * of SMP_FORCE_TARE_STABILIZE_TIME and then reset force readout to zero.
 * usage:
 * 1) write SMP_FORCE_MODE=FORCE_MODE_START_TARE (mode must not be in force control mode before setting to avoid axis motion during taring)
 * 2) poll for FFS_TARE_SUCCESS in SMP_FORCE_FUNCTIONS_STATUS
 * 3) done, set mode to something else
 *
 * FORCE CONTROL MODE:
 * this mode will use force sensor as feedback to control motor velocity.
 * when setting this mode, the setpoint of force mode will be the force that was present during mode change.
 * i.e. if finger touches table at 12.345g force and force mode is set, then force mode initial setpoint becomes
 * 12.345g to avoid bouncing off the table.
 *
 * Notes:
 * -In all modes, travel limits set by homing will restrict motion range.
 * -Use Disable torque [LFS] to limit motion range after homing. This works properly in force control mode too.
 *
 """
SMP_FORCE_MODE = 8141
FORCE_MODE_POS_CTRL = 1
FORCE_MODE_TOUCH_PROBE_CTRL = 2
FORCE_MODE_FORCE_CTRL = 3
FORCE_MODE_TARE = 4

"""status bits for force features. see FFS_ defs below"""
SMP_FORCE_FUNCTIONS_STATUS = 8142

# FFS_TARE_BUSY is 1 during taring (at least time of SMP_FORCE_TARE_STABILIZE_TIME)
FFS_TARE_BUSY = 0

# FFS_TARE_SUCCESS goes 1 after taring is complete and user may switch to other modes
FFS_TARE_SUCCESS = 1

# FFS_OVER_FORCE fault becomes 1 if force sensor (tared value) reads higher than SMP_FORCE_FAULT_LIMIT value.
# to recover from fault, write SMP_CB1_CLEARFAULTS|SMP_CB1_ENABLE (both bits 1) to SMP_CONTROL_BITS1.
# recovering sets mode into FORCE_MODE_POS_CTRL and setpoint to 0 so axis will move up to safe level on clearfaults command.
# after that remember to set desired mode & setpoint again.
FFS_OVER_FORCE = 3

# FFS_TOUCH_PROBE_SUCCESS turns 1 after touch probe has stopped motion due to force value exceeding user set threshold
FFS_TOUCH_PROBE_SUCCESS = 5

# FFS_RECOVERING_FROM_OVER_FORCE is 1 when device is performing recovery from over force error
FFS_RECOVERING_FROM_OVER_FORCE = 8

# Acceleration and velocity limits in different modes. Same scale as drives CAL and CVL.
SMP_VEL_LIMIT_IN_TOUCH_PROBING = 8143
SMP_ACCEL_LIMIT_IN_TOUCH_PROBING = 8144
SMP_VEL_LIMIT_IN_FORCE_CONTROL = 8145
SMP_ACCEL_LIMIT_IN_FORCE_CONTROL = 8146

"""FILTERS
 * force feedback value is processed like this:
 *
 * force=raw_encoder_value*spring_constant+tare_offset
 * forceForTare=filter(3,force) #fixed 3Hz bandwidth
 * forceForDGain=filter(SMP_FORCE_D_FILTER_FREQ,force)
 * forceFilteredGeneral=filter(SMP_FORCE_FILTER_FREQ,force)
 *
 * forceFilteredGeneral is used for:
 * - PI control as feedback
 * - touch probe mode feedback
 * - Debug2 scope signal (i.e. use with Granity)
 """

# Force D controller filter frequency (1-1000 Hz, or 0 to disable (infinite bandwidth))
SMP_FORCE_D_FILTER_FREQ = 8148
# Force feedback filter frequency (1-1000 Hz, or 0 to disable (infinite bandwidth))
SMP_FORCE_FILTER_FREQ = 8149

SMP_DEBUGPARAM1 = 8100
SMP_DEBUGPARAM2 = 8101

"""Scope capture parameters
"""
SMP_CAPTURE_SOURCE = 5020
# bitfield values (shift these with BV())
CAPTURE_TORQUE_TARGET = 1
CAPTURE_TORQUE_ACTUAL = 2
CAPTURE_VELOCITY_TARGET = 3
CAPTURE_VELOCITY_ACTUAL = 4
CAPTURE_POSITION_TARGET = 5
CAPTURE_POSITION_ACTUAL = 6
CAPTURE_FOLLOW_ERROR = 7
CAPTURE_OUTPUT_VOLTAGE = 8
CAPTURE_BUS_VOLTAGE = 9
CAPTURE_STATUSBITS = 10
CAPTURE_FAULTBITS = 11
CAPTURE_P_OUT = 12
CAPTURE_I_OUT = 13
CAPTURE_D_OUT = 14
CAPTURE_FF_OUT = 15
CAPTURE_RAW_POS = 25
# 8 bit signed values combined, only for return data, not for scope
CAPTURE_TORQ_AND_FERROR = 26

# rest are availalbe in debug/development firmware only:
CAPTURE_PWM1 = 16
CAPTURE_PWM2 = 17
CAPTURE_PWM3 = 18
CAPTURE_DEBUG1 = 19
CAPTURE_DEBUG2 = 20
CAPTURE_CURRENT1 = 21
CAPTURE_CURRENT2 = 22
CAPTURE_ACTUAL_FLUX = 23
CAPTURE_OUTPUT_FLUX = 24

SMP_CAPTURE_TRIGGER = 5011
# choices:
TRIG_NONE = 0
TRIG_INSTANT = 1
TRIG_FAULT = 2
TRIG_TARGETCHANGE = 3
TRIG_TARGETCHANGE_POS = 4
TRIG_EXTERNAL_INPUT = 5

SMP_CAPTURE_SAMPLERATE = 5012
# Read only

SMP_CAPTURE_BUF_LENGHT = 5013
# SMP_CAPTURE_BEFORE_TRIGGER_PERCENTS sets how much samples will be preserved before trigger event. Value 0 is
# traditional, +n starts capture n percents before trigger (relative to whole capture length), -n after trigger.
# Value range -1000000%..+100%.
SMP_CAPTURE_BEFORE_TRIGGER_PERCENTS = 5014

# SMP_CAPTURE_STATE, states: 0=idle (capture complete or not started), 1=waiting for trigger, 2=capturing. To start
# capture, write value 1 here starting from IONI FW V1110.
SMP_CAPTURE_STATE = 5015

# This is looped 0-n to make samples 0-n readable from SMP_CAPTURE_BUFFER_GET_VALUE
SMP_CAPTURE_BUFFER_GET_ADDR = 5333
SMP_CAPTURE_BUFFER_GET_VALUE = 5334


# Scope variables
class ScopeVariables(enum.Enum):
    CAPTURE_TORQUE_TARGET = 1
    CAPTURE_TORQUE_ACTUAL = 2
    CAPTURE_VELOCITY_TARGET = 3
    CAPTURE_VELOCITY_ACTUAL = 4
    CAPTURE_POSITION_TARGET = 5
    CAPTURE_POSITION_ACTUAL = 6
    CAPTURE_FOLLOW_ERROR = 7
    CAPTURE_OUTPUT_VOLTAGE = 8
    CAPTURE_BUS_VOLTAGE = 9
    CAPTURE_STATUSBITS = 10
    CAPTURE_FAULTBITS = 11
    CAPTURE_P_OUT = 12
    CAPTURE_I_OUT = 13
    CAPTURE_D_OUT = 14
    CAPTURE_FF_OUT = 15
    CAPTURE_PWM1 = 16
    CAPTURE_PWM2 = 17
    CAPTURE_PWM3 = 18
    CAPTURE_DEBUG1 = 19
    CAPTURE_DEBUG2 = 20
    CAPTURE_RAW_POS = 25


# Scope triggers
class ScopeTriggers(enum.Enum):
    TRIG_NONE = 0
    TRIG_INSTANT = 1
    TRIG_FAULT = 2
    TRIG_TARGETCHANGE = 3
    TRIG_TARGETCHANGE_POS = 4
    TRIG_EXTERNAL_INPUT = 5


# Homing stuff
# Starting and stopping homing:
SMP_HOMING_CONTROL = 7532


SMP_CONTROL_BITS1 = 2533

# Control bitfield values

SMP_CB1_ENABLE = BV(0)  # software enable
SMP_CB1_CLEARFAULTS = BV(1)  # clear faults


# Scaling values
SMP_ENCODER_PPR = 565
SMP_AXIS_SCALE = 491

SMP_POSITION_TRACKING_ERROR_THRESHOLD = 555
SMP_VELOCITY_TRACKING_ERROR_THRESHOLD = 556
SMP_SYSTEM_CONTROL = 554

SMP_POSITION_SOFT_HIGH_LIMIT = 835
SMP_POSITION_SOFT_LOW_LIMIT = 836

SMP_CONTROL_MODE = 559

CM_TORQUE = 3
CM_VELOCITY = 2
CM_POSITION = 1
CM_NONE = 0

SMP_INPUT_MULTIPLIER = 560
SMP_INPUT_DIVIDER  = 561

# IO Registers, read more at
# https://git.optofidelity.net/tnt/OptoMotion/blob/OFMD2_V02_master/OFIC_FW/docs/OFMD2_SM_control.pdf
SMP_DIGITAL_PIN_MODES_1 = 142
SMP_ENCODER_TRIGGER_POS = 155
SMP_ENCODER_TRIGGER_PARAMS = 156
SMP_ENCODER_TRIGGER_START = 157
SMP_ENCODER_RESET = 158
SMP_ENCODER_VALUE = 159

SMP_HOME_SWITCH_SOURCE_SELECT = 100

SMP_DIG_IN1_GPI1 = BV(0)
SMP_DIG_IN1_GPI2 = BV(1)

SMP_TRAJ_PLANNER_HOMING_BITS = 806

HOMING_POS_HOME_SWITCH_POLARITY = BV(2)