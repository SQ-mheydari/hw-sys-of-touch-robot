
from .tnt_client import *
from . import logger

log = logger.get_logger(__name__)

            
class TnTIconClient(TnTClientObject):
    """
    Icon resource holding reference to Halcon Shapemodel file and to reference PNG image.
    """
    def __init__(self, name, workspace=TnTClientObject.default_workspace, host="127.0.0.1", port=8000):
        TnTClientObject.__init__(self, host, port, workspace, "icons", name)
        
    def remove(self):
        """
        Remove the resource.
        After the resource has been removed, the client object is no longer valid.
        """
        return self._DELETE('', {})
    
    def png(self, ):    
        """
        Get icon PNG image.
        :return: PNG image.
        """
        params = {
        }
        
        
        return self._GET('png', params)
        
    def convert(self, image=None, parameters=None):    
        """
        Convert given image to icon model.
        Can also re-convert existing PNG image to update the icon model.
        :param image: PNG image as base64 encoded string or bytes object. If None, then existing PNG is converted.
        :param parameters: Optional parameters for shape model creation to override default parameters.

        Example:

        with open("icon_image.png", "rb") as file:
            data = file.read()

        icon_client.convert(data)
        """
        params = {
        }
        
        if image is not None:
            params['image'] = image
        if parameters is not None:
            params['parameters'] = parameters
        
        return self._PUT('convert', params)
        
