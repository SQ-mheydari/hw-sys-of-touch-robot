import logging
import importlib

from tntserver.Nodes.Node import *
from tntserver.Nodes.TnT.Dut import Dut
from . import ListingNode

log = logging.getLogger(__name__)


class Duts(ListingNode):
    """
    TnT™ Compatible DUTs resource
    Should work together with
    - TnT Sequencer
    - TnT Positioning Tool

    is a container for Dut resources
    """

    def __init__(self, name):
        super().__init__(name, resources={"Dut": Dut})

        self.gestures_cls = None

    def _init(self, gestures_cls, **kwargs):

        gestures_module = importlib.import_module("tntserver.Nodes." + gestures_cls)
        self.gestures_cls = gestures_module.Gestures

    def put_add(self):
        """
        Adds a new DUT
        DEPRECATED: Use post_self() instead.
        :return: Info of the newly generated DUT

        """

        # auto generate path
        name_base = "new_dut"
        name = name_base
        i = 1
        while True:
            try:
                self.find_child_with_path(name)
            except:
                break
            i += 1
            name = name_base + "_" + str(i)

        log.info("duts.add {}".format(name))
        dut = Dut(name=name)
        self.add_child(dut)
        dut._init()

        self.save()

        info = dut.api_info()
        return info

    @json_out
    def put_remove(self, name):
        """
        Remove DUT.
        DEPRECATED: Use delete_self() instead.
        :param name: Name of DUT to remove.
        """
        log.info("duts.remove {}".format(name))
        try:
            # Use dut objects delete_self-method to remove the dut and physical buttons related to it.
            self.children[name].remove()
            self.save()
            log.info("dut {} removed".format(name))
        except Exception:
            log.exception("dut {} could not be removed".format(name))
        return ""
