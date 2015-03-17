import logging
import unittest
try:
    from test_config import *
    test_config_available = True
except ImportError:
    test_config_available = False


class TestCase(unittest.TestCase):
    logging.basicConfig(level=logging.DEBUG)