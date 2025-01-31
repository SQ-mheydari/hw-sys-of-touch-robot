class DummyPIT(object):
    """Dummy PIT driver for running FirstContactLatency test on simulator"""

    def __init__(self):
        pass

    def Multiplexer(self, port):
        """ This function is here because it is called in FirstContactLatency test.
        """
        return [port]

    def Initialize(self):
        """ This function is here because it is called in FirstContactLatency test.
        """
        pass

    def CLine(self, timeout, fingerTimeout, waitForFingerInterrupt):
        """ This function is here because it is called in FirstContactLatency test.
        Parameters are not needed. They are only there to avoid errors in FirstContactLatency test.
        """
        return 'OK'

    def CLineOff(self):
        """ This function is here because it is called in FirstContactLatency test.
        """
        return 'OK'

    def SingleTrigger(self):
        """ This function is here because it is called in FirstContactLatency test.
        """
        return 0

    def NormalTrigger(self):
        """ This function is here because it is called in FirstContactLatency test.
        """
        return 0

    def WriteSleepMode(self, SleepMode):
        """ This function is here because it is called in FirstContactLatency test.
        SleepMode is not needed. It is only there to avoid errors in FirstContactLatency test.
        Returns: status.
        """
        # Status copied from an actual PIT driver.
        status = []
        status.append((0, 0, 0, 0, 0, 0))
        status.append("OK")
        status.append("")
        return status
