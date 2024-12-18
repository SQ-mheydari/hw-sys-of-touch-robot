
from .tnt_client import *
from . import logger

log = logger.get_logger(__name__)

            
class TnTTipClient(TnTClientObject):
    """
    TnT Compatible tip resource
    Tip can be parented to a Tool node.
    """
    def __init__(self, name, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):
        TnTClientObject.__init__(self, host, port, workspace, "tips", name)
        
    def remove(self):
        """
        Remove the resource.
        After the resource has been removed, the client object is no longer valid.
        """
        return self._DELETE('', {})
    
    @property
    def diameter(self):
        """
        Diameter of the tip.
        """
        return self.get_property('diameter')
        
    @diameter.setter
    def diameter(self, value):
        """
        Diameter of the tip.
        """
        self.set_property('diameter', value)
        
    @property
    def first_finger_offset(self):
        """
        Distance from the middle of multifinger tip to the first finger.
        """
        return self.get_property('first_finger_offset')
        
    @first_finger_offset.setter
    def first_finger_offset(self, value):
        """
        Distance from the middle of multifinger tip to the first finger.
        """
        self.set_property('first_finger_offset', value)
        
    @property
    def is_multifinger(self):
        """
        Is tip multifinger.
        """
        return self.get_property('is_multifinger')
        
    @property
    def length(self):
        """
        Length of the tip.
        """
        return self.get_property('length')
        
    @length.setter
    def length(self, value):
        """
        Length of the tip.
        """
        self.set_property('length', value)
        
    @property
    def model(self):
        """
        Tip model ("Standard", "Multifinger").
        """
        return self.get_property('model')
        
    @model.setter
    def model(self, value):
        """
        Tip model ("Standard", "Multifinger").
        """
        self.set_property('model', value)
        
    @property
    def num_tips(self):
        """
        Number of tips in multifinger.
        """
        return self.get_property('num_tips')
        
    @num_tips.setter
    def num_tips(self, value):
        """
        Number of tips in multifinger.
        """
        self.set_property('num_tips', value)
        
    @property
    def separation(self):
        """
        Separation of two-finger tool required to pick multifinger.
        """
        return self.get_property('separation')
        
    @separation.setter
    def separation(self, value):
        """
        Separation of two-finger tool required to pick multifinger.
        """
        self.set_property('separation', value)
        
    @property
    def slot_in(self):
        """
        Tip's slot-in position in workspace context. In this position tip is fixed to a rack.
        """
        return self.get_property('slot_in')
        
    @slot_in.setter
    def slot_in(self, value):
        """
        Tip's slot-in position in workspace context. In this position tip is fixed to a rack.
        """
        self.set_property('slot_in', value)
        
    @property
    def slot_out(self):
        """
        Tip's slot-out position in workspace context. In this position tip is free from a rack.
        When robot attaches or detaches a tip, it will first move over slot-out position.
        """
        return self.get_property('slot_out')
        
    @slot_out.setter
    def slot_out(self, value):
        """
        Tip's slot-out position in workspace context. In this position tip is free from a rack.
        When robot attaches or detaches a tip, it will first move over slot-out position.
        """
        self.set_property('slot_out', value)
        
    @property
    def tip_distance(self):
        """
        Axial distance of adjacent tips in multifinger.
        """
        return self.get_property('tip_distance')
        
    @tip_distance.setter
    def tip_distance(self, value):
        """
        Axial distance of adjacent tips in multifinger.
        """
        self.set_property('tip_distance', value)
        
