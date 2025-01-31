# Copyright (c) 2014 OptoFidelity Ltd. All Rights Reserved.

import traceback
import json

import cherrypy
from cherrypy import HTTPError
from genshi.template import MarkupTemplate

from .base_page import BasePage
from .measurementdb import get_database, Setting, ResultDatabase
import TPPTAnalysisSW.test_session as test_session
import TPPTAnalysisSW.imagefactory as imagefactory
from .settings import setting_categories, loadSettings, get_setting
from .info.version import Version
import TPPTAnalysisSW.progressstatus as progressstatus
import TPPTAnalysisSW.test_refs as test_refs
from .utils import database_files


#Settings controller for settings-view
class SettingsController(BasePage):

    SAVEPATH = ""

    def __init__(self):
        super().__init__()
        self.current_dut = ""
        self.duts = []
        self.get_duts()

    def GET(self, *args, **kwargs):

        if "event" in kwargs:
            cherrypy.response.headers["Content-Type"] = "text/event-stream"
            cherrypy.response.headers["Transfer-Encoding"] = "identity"
            return "data: " + str(progressstatus.progress) + "\ndata:\nretry:500\n\n"

        with get_database().session() as dbsession:
            with open("templates/settings.html") as f:

                tmpl = MarkupTemplate(f)
                settings = dbsession.query(Setting).filter(Setting.dut == self.current_dut).all()
                self.get_duts()
                groups = self.settings_by_group(settings)
                loadSettings(dbsession)
                stream = tmpl.generate(groups=groups, version=Version, duts=self.duts, current_dut=self.current_dut,
                                       get_setting=get_setting, dbfiles=database_files())

                return stream.render('xhtml')

    def POST(self, *args, mode: str = "", dut_name: str = "", db_path: str = "", params: str = None,
             **kwargs) -> str:
        """
        Handle POST event from GUI.
        :param mode: What action to perform:
            change_dut: Load settings for another DUT from database.
            remove_dut: Remove settings for current DUT from database.
            add_dut: Add settings for new DUT to database.
            recalculate: Save settings for current DUT and recalculate all limits.
            norecalculate: Only save settings.
            import: Import settings from another database.
        :param dut_name: DUT name from input field or DUT dropdown selection in the case of change/remove/add_dut.
        :param db_path: Path to database file.
        :param params: Values from input fields in settings table. List of dicts with keys 'name' and 'value' formatted
            as a JSON string.
        :return: Message to display at the top of the settings menu.
        """

        if mode == "change_dut":
            self.current_dut = dut_name
            return f"Loading settings for {self.current_dut}..."

        if mode == "remove_dut":
            self.remove_current_dut()
            return f"Removing DUT {dut_name}..."

        if mode == "add_dut":
            self.copy_current_dut()
            return f"Adding DUT {self.current_dut}..."

        if mode == "import":
            self.import_settings(db_path)
            return f"Importing settings from database {db_path}"

        with get_database().session() as dbsession:
            data = json.loads(params)

            for setting_input in data:
                setting = dbsession.query(Setting).filter(Setting.name == setting_input['name'],
                                                          Setting.dut == self.current_dut).first()
                try:
                    setting.dut = dut_name  # Rename DUT
                    strvalue = setting_input['value']
                    strvalue = strvalue.replace(',', '.') # Allow comma decimal separator
                    setting.value = float(strvalue)
                except ValueError:
                    print(traceback.format_exc())
                    dbsession.rollback()
                    raise HTTPError("500", "Float value required for %s" % setting.desc)

            self.current_dut = dut_name

            dbsession.commit()
            loadSettings(dbsession) # from settings.py

            # clear cache
            test_refs.testclass_refs.clear()
            imagefactory.ImageFactory.delete_all_images()

            if mode == "recalculate":

                testsessions = get_database().get_test_sessions(dbsession)
                length = len(testsessions)

                for idx, ts in enumerate(testsessions):
                    test_session.TestSession.eval_tests_results(dbsession, ts.id)
                    if idx == 0:
                        progressstatus.progress = 0
                    else:
                        progressstatus.progress = round(idx / float(length), 2)

                progressstatus.progress = 0

                return "Settings saved and analyses recalculated."

            testsessions = get_database().get_test_sessions(dbsession)

            for ts in testsessions:
                test_session.TestSession.eval_tests_results(dbsession, ts.id, recalculate=False)

        return "Settings saved but analyses were not recalculated."

    def copy_current_dut(self):
        """
        Copy current DUT settings to database with a new name.
        Set copy as current DUT.
        """
        base_name = "default" if self.current_dut == "" else self.current_dut.rstrip(" - copy")
        # Find unused name for new DUT.
        dut_name = f"{base_name} - copy"
        i = 2
        while dut_name in self.duts:
            dut_name = f"{base_name} - copy ({i})"
            i += 1

        with get_database().session() as dbsession:
            # Add new DUT setting to database with values copied from current DUT.
            default_settings = dbsession.query(Setting).filter(Setting.dut == self.current_dut).all()
            for setting in default_settings:
                setting_copy = Setting(setting.name, setting.value, setting.unit, setting.desc, dut_name)
                dbsession.add(setting_copy)
                print(f"Added setting {setting.name} for DUT {dut_name}")

            dbsession.commit()
            loadSettings(dbsession)  # from settings.py

        self.current_dut = dut_name

    def remove_current_dut(self):
        """
        Remove all settings for current DUT from database.
        Set current DUT to be the default one.
        """
        with get_database().session() as dbsession:
            setting = dbsession.query(Setting).filter(Setting.dut == self.current_dut)
            setting.delete()
            dbsession.commit()
            loadSettings(dbsession)  # from settings.py
            self.current_dut = ""

    def get_duts(self):
        """
        Load saved DUT values from database.
        """
        self.duts = []
        with get_database().session() as dbsession:
            for dut in dbsession.query(Setting.dut).distinct():
                self.duts.append(dut[0])
        if self.current_dut not in self.duts:
            self.current_dut = ""

    def settings_by_group(self, settings):
        # Copy settings to safety
        settings = list(settings)
        groups, groups_settings = self.parse_groups()

        # Replace setting_id with given setting
        for group_settings in groups_settings:
            for i, setting_name in enumerate(group_settings):
                setting = [s for s in settings if s.name == setting_name]
                if len(setting) == 0:
                    raise HTTPError(status="500", message=f"Internal error: setting {setting_name} not found in "
                                                          f"database for DUT {self.current_dut}")
                else:
                    settings.remove(setting[0])
                    group_settings[i] = setting[0]

        if len(settings) > 0:
            # There are non-categorized settings
            groups.append(None)
            groups_settings.append(settings)

        # Note: this will break if some of the settings given in settings_categories
        # is not found in the database. This should be rare condition, as missing
        # settings are inserted in the startup sequence

        return zip(groups, groups_settings)

    def parse_groups(self):
        """
        Parses the group to list of categories. Creates separate categories
        for settings that are in multiple categories
        """

        settings_dict = {}

        # Create settings list (reverse: setting_id -> categories)
        # Note: generated lists are equal if they are included in the same categories
        for name, settings_list in setting_categories.items():
            for setting_id in settings_list:
                if setting_id in settings_dict:
                    settings_dict[setting_id].append(name)
                else:
                    settings_dict[setting_id] = [name]

        # List of different categories
        groups = []
        # Settings in each category
        groups_settings = []

        for setting_id, groups_list in settings_dict.items():
            if groups_list in groups:
                # Append setting to the specific group
                groups_settings[groups.index(groups_list)].append(setting_id)
            else:
                # Create a new group in list and add the settings to it
                # order groups by number of categories in group and alphabetically
                for index_to in range(len(groups)):
                    if len(groups[index_to]) < len(groups_list):
                        continue
                    elif (len(groups[index_to]) > len(groups_list) or
                          groups[index_to][0] > groups_list[0]):
                        groups.insert(index_to, groups_list)
                        groups_settings.insert(index_to, [setting_id])
                        break
                else:
                    # Append
                    groups.append(groups_list)
                    groups_settings.append([setting_id])

        return (groups, groups_settings)

    exposed = True

    def import_settings(self, db_path: str):
        """
        Import all settings from given database to current database. This deletes all existing settings from the current
        database!
        :param db_path: Path to .sqlite database file.
        """

        db = ResultDatabase(db_path)
        with db.session() as dbsession:
            imported_settings = dbsession.query(Setting)

        duts = set()
        with get_database().session() as dbsession:
            dbsettings = dbsession.query(Setting)
            dbsettings.delete()
            for setting in imported_settings:
                duts.add(setting.dut)
                dbsession.add(Setting(setting.name, setting.value, setting.unit, setting.desc, setting.dut))
            dbsession.commit()

            loadSettings(dbsession)

            if self.current_dut not in duts:
                self.current_dut = ""

            testsessions = get_database().get_test_sessions(dbsession)

            for ts in testsessions:
                test_session.TestSession.eval_tests_results(dbsession, ts.id, recalculate=False)
