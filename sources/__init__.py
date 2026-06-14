from .base import BaseSource
from .anichin import AnichinSource
from .donghuafun import DonghuaFunSource
from .animexin import AnimexinSource

def get_sources():
    """
    Returns a list of all available scrapers.
    To add a new scraper source, implement the BaseSource class
    in a new file under this package, and add its instance here.
    """
    return [
        AnichinSource(),
        DonghuaFunSource(),
        AnimexinSource()
    ]
