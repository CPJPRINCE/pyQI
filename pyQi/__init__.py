"""
pyQi package definitions

Author: Christopher Prince
license: Apache License 2.0"
"""

from .QiApi import QiAPI
from .QiApi_async import QiAPIAsync
from .common import QiRecord, QiRecords, base64_encode, parse_data
from .json_builder import JsonBuilder
import importlib.metadata


__author__ = "Christopher Prince (c.pj.prince@gmail.com)"
__license__ = "Apache License Version 2.0"
__version__ = importlib.metadata.version("pyQi_api")