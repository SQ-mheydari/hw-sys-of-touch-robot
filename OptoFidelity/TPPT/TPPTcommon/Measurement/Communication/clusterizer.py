from xml.etree import cElementTree as ElementTree

class Clusterizer:
    """class for cluster variable handling
    """
    def __init__(self, clusterXml=None):
        # create empty cluster, if none is specified
        if clusterXml is None:
            clusterXml = """<Cluster>
                        <Name>MsgCluster</Name>
                        <NumElts>3</NumElts>
                        <String>
                            <Name>Command</Name>
                            <Val>sdsd</Val>
                        </String>
                        <Array>
                            <Name>Data</Name>
                            <Dimsize>0</Dimsize>
                            <String>
                                <Name></Name>
                                <Val></Val>
                            </String>
                        </Array>
                        <String>
                            <Name>ID</Name>
                            <Val></Val>
                        </String>
                    </Cluster>
                    """
        self._root = ElementTree.fromstring(clusterXml)
        #self.Sender = self._get_val("Sender")
        #self.Target = self._get_val("Target")
        self.command = self._get_val("Command")
        self.data = self._get_val("Data")
        self.id = self._get_val("ID")

    def tostring(self):
        """ Convert to string
        """
        #self._set_val("Sender", self.Sender)
        #self._set_val("Target", self.Target)
        self._set_val("Command", self.command)
        self._set_val("Data", self.data)
        self._set_val("ID", self.id)
        # fix the braindead way of LabVIEW not understanding about empty tags..
        return ElementTree.tostring(self._root).decode().replace("<Name />", "<Name></Name>") \
               .replace("<Val />", "<Val></Val>")

    def _find_element(self, name, node=None):
        """ tries to find an element that contains a <Name>-tag with a matching name
            return None, if no matching element was found
        """
        if node is None:
            node = self._root
        for element in list(node):
            if element.findtext("Name") == name:
                return element
        return None

    def _get_val(self, name, node=None):
        """ retrieves the contents of <Val>-tag from within a node that contains
            a matching <Name>-tag
        """
        element = self._find_element(name, node)
        # if we did not find the name, return None
        if element is None:
            data = None
        # if the element is an array, populate and return a list
        elif element.tag == "Array":
            data = []
            for subelement in list(element):
                value = subelement.findtext("Val")
                if value is not None:
                    data.append(value)
        # otherwise return the actual value, or None, if no value was present
        else:
            data = element.findtext("Val")
        return data

    def _set_val(self, name, value, node=None):
        """ stores values into <Val>-tag with matching <Name>-tag
        """
        element = self._find_element(name, node)
        # raise KeyError, if the name was not found
        if element is None:
            raise KeyError("Cluster item '%s' was not found in cluster" % name)
        # if the value is a list, store it into an array
        if type(value) == list:
            if element.tag != "Array":
                raise ValueError("Cluster item '%s' is not an array" % name)
            # delete all nodes, except Name, DimSize and the first array item
            excess_nodes = list(element)[3:]
            for subelement in excess_nodes:
                element.remove(subelement)
            # store array size
            element.find("Dimsize").text = str(len(value))
            # store first array item value
            if len(value) == 0:
                value = ['']
            element.find("String").find("Val").text = str(value[0])
            # create and populate array item elements for the remaining items
            for item in value[1:]:
                new_element = ElementTree.Element("String")
                new_element.append(ElementTree.Element("Name"))
                new_element[-1].text = ''
                new_element.append(ElementTree.Element("Val"))
                new_element[-1].text = str(item)
                element.append(new_element)
        # otherwise store a scalar value
        else:
            if element.tag == "Array":
                raise ValueError("Cluster item '%s' is an array" % name)
            element.find("Val").text = str(value)
