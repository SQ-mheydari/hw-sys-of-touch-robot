# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

import TPPTAnalysisSW.measurementdb
import TPPTAnalysisSW.plotters

#Every page inherits this class
class BasePage(object):
	def __init__(self):
		super(BasePage, self).__init__()
