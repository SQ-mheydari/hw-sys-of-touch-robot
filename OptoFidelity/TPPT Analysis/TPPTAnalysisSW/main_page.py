# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.
import genshi

from genshi.template import MarkupTemplate
import sqlalchemy.sql.default_comparator
import sqlalchemy.ext.baked

import shutil
import json
import cherrypy
import os.path

import TPPTAnalysisSW.measurementdb as db
from .base_page import BasePage
from .test_session import TestSession
from .info.version import Version
from .settings import settings
import TPPTAnalysisSW.progressstatus as progressstatus
import TPPTAnalysisSW.test_refs as test_refs
import TPPTAnalysisSW.imagefactory as imagefactory
from .utils import database_files


#Main page controller
class MainPage(BasePage):

    def __init__(self):
        super(MainPage, self).__init__()

    exposed = True

    def GET(self, *args, **kwargs):

        if "event" in kwargs:
            cherrypy.response.headers["Content-Type"] = "text/event-stream"
            cherrypy.response.headers["Transfer-Encoding"] = "identity"
            return "data: " + str(progressstatus.progress) + "\ndata:\nretry:500\n\n"

        if os.path.isfile("static/AnalysisSoftwareUserGuide.pdf") and os.path.isfile("../../Docs/AnalysisSoftwareUserGuide.pdf"):
            if os.path.getmtime("static/AnalysisSoftwareUserGuide.pdf") < os.path.getmtime("../../Docs/AnalysisSoftwareUserGuide.pdf"):
                try:
                    shutil.copy("../../Docs/AnalysisSoftwareUserGuide.pdf", "static/AnalysisSoftwareUserGuide.pdf")
                except IOError:
                    print("Copying user guide failed.")
        else:
            try:
                shutil.copy("../../Docs/AnalysisSoftwareUserGuide.pdf", "static/AnalysisSoftwareUserGuide.pdf")
            except IOError:
                print("Copying user guide failed.")

        with db.get_database().session() as dbsession:
            testsessions = dbsession.query(db.TestSession).order_by(db.TestSession.id)

            sessions = []

            for ts in testsessions:

                tests, results, curved = TestSession.sessionResultsFromDB(ts, dbsession)
                if "Error" in results:
                    result = "Error"
                elif "Fail" in results and "Requires recalculate" not in results:
                    result = "Fail"
                elif ("N/A" in results or len(results) == 0):
                    result = "N/A"
                elif "Requires recalculate" in results:
                    result = "Requires recalculate"
                else:
                    result = "Pass"

                sessions.append((ts, result, TestSession.session_samples_progs_manus(ts, dbsession), curved))

            # Show test sessions
            pagenumber = 1
            if ('page' in kwargs):
                pagenumber = max(1, int(kwargs['page']))
            sessions_per_page = 30
            if len(sessions) >= sessions_per_page:
                latest = sessions[(-1 - sessions_per_page * (pagenumber - 1)):(-sessions_per_page - sessions_per_page * (pagenumber - 1)):-1]
            else:
                latest = sessions[::-1]

            # Tree: Manufacturers - Program
            manufacturers = self.manufacturers_tree(dbsession, sessions)

            with open("templates/testsessions_index.html") as f:
                template = MarkupTemplate(f)

                stream = template.generate(latest=latest,
                                           manufacturers=manufacturers,
                                           version=Version,
                                           pagenumber=pagenumber,
                                           dbfiles=database_files())

                return stream.render('xhtml', doctype='html5')

    def POST(self, filepath=None, *args, **kwargs):
        with db.get_database().session() as dbsession:
            param = ""

            if 'params' in kwargs:
                param = kwargs['params']
            elif filepath:
                test_refs.testclass_refs.clear()
                imagefactory.ImageFactory.delete_all_images()
                db.get_database().changeDatabase(filepath)
                return self.GET()

            if param == "recalculate":

                # clear cache
                test_refs.testclass_refs.clear()
                imagefactory.ImageFactory.delete_all_images()
                dbsessions = dbsession.query(db.TestSession).values(db.TestSession.id)
                sessionids = [ts[0] for ts in dbsessions]
                length = len(sessionids)
                for idx, ts in enumerate(sessionids):
                    TestSession.eval_tests_results(dbsession, ts)
                    if idx == 0:
                        progressstatus.progress = 0
                    else:
                        progressstatus.progress = round(idx / float(length), 2)

                progressstatus.progress = 0

                return "Analysis recalculated."

            if param == "delete":
                print ("Deleting test session id %s and all related data..." % (kwargs['id'],))
                session = dbsession.query(db.TestSession).filter(db.TestSession.id == kwargs['id']).first()
                for item in session.test_items:
                    if str(item.id) in test_refs.testclass_refs:
                        imagefactory.ImageFactory.delete_images(str(item.id))
                        test_refs.testclass_refs.pop(str(item.id))
                dbsession.query(db.TestSession).filter(db.TestSession.id == kwargs['id']).delete()
                dbsession.commit()

                return "Deletion successful."

    def manufacturers_tree(self, dbsession, sessions):

        # Structure of the list.
        # [(manufacturer_name, [(program_name, [testsession1, testsession2, ...]), ...]), ...]
        manufacturers = []

        for dut in dbsession.query(db.TestDUT):
            # Manufacturer
            man = dut.manufacturer
            if man is None or len(man) == 0:
                man = "[Empty]"

            p_list = None
            for m in manufacturers:
                if m[0] == man:
                    p_list = m[1]
            if p_list is None:
                p_list = []
                manufacturers.append((man, p_list))

            # Program
            prog = dut.program
            if prog is None or len(prog) == 0:
                prog = "[Empty]"

            prog_set = None
            for p in p_list:
                if p[0] == prog:
                    prog_set = p[1]
            if prog_set is None:
                prog_set = []
                p_list.append((prog, prog_set))

            # Append the test id's to the program set
            for test in dut.test_items:
                if test.testsession_id not in prog_set:
                    prog_set.append(test.testsession_id)

        # Replace testsession id's with test session lists
        testsessions = {ts[0].id: ts for ts in sessions}
        for man in manufacturers:
            for prog in man[1]:
                for i in range(len(prog[1])):
                    prog[1][i] = testsessions[prog[1][i]]

        return manufacturers

