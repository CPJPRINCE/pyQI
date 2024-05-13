"""
pyQi package definitions

Author: Christopher Prince
license: Apache License 2.0"
"""

from .pyQi import QiAPI, QiRecord, QiRecords
from .pyQi_async import QiAPI, QiRecord, QiRecords
from .xltojson import JsonBuilder 
import importlib.metadata

__author__ = "Christopher Prince (c.pj.prince@gmail.com)"
__license__ = "Apache License Version 2.0"
__version__ = importlib.metadata.version("pyQi")