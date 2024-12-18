# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

from .base_page import BasePage
from cherrypy import *
from genshi.template import MarkupTemplate
from genshi.filters import HTMLFormFiller
from .measurementdb import *
from .plotinfo import TestSessionInfo
from .info.version import Version

import json
import TPPTAnalysisSW.plotinfo as plotinfo
import TPPTAnalysisSW.test_session as test_session
import copy

#Settings controller for settings-view
class SummaryController(BasePage):
    exposed = True
    
    def GET(self, testsession_id = None):

        if (testsession_id == None):
            raise HTTPError("404")

        with get_database().session() as dbsession:
            sessioninfo = TestSessionInfo(testsession_id=testsession_id, dbsession=dbsession)
            test_query = dbsession.query(TestItem).filter(TestItem.testsession_id==testsession_id).values(TestItem.id)
            test_ids = [id[0] for id in test_query]

            templateparams = copy.copy(sessioninfo.__dict__)

            template = MarkupTemplate(open("templates/test_summary.html"))
            stream = template.generate(test_ids=test_ids, version=Version, **(templateparams))
            return stream.render('xhtml')
    