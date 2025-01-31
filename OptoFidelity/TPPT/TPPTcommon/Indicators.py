class Indicators:
    """
    Indicators to show in UI.
    Indicators consist of name-value-pairs that are shown in UI with some fixed style.
    """

    def __init__(self, ui):
        self._ui = ui
        self._status = ""
        self._dut_name = ""
        self._tip_name = ""
        self._test_details = []
        self.X = ""
        self.Y = ""

    def set_dut_name(self, dut_name):
        self._dut_name = dut_name
        self.update_ui()

    def set_tip_name(self, tip_name):
        self._tip_name = tip_name
        self.update_ui()

    def set_status(self, status):
        self._status = status
        self.update_ui()

    def set_test_detail(self, name, value):
        self.set_test_details([(name, value)])

    def set_test_details(self, test_details):
        self._test_details.clear()

        for t in test_details:
            self._test_details.append("<b>" + t[0] + "</b>: " + t[1] + "<br>")

        self.update_ui()

    def get_status(self):
        return self._status

    def update_ui(self):
        text = "<b>Status</b>: " + self._status + "<br>"
        text += "<b>DUT</b>: " + self._dut_name + "<br>"
        text += "<b>Tip</b>: " + self._tip_name + "<br>"

        for t in self._test_details:
            text += t

        self._ui.set_indicators(text)
