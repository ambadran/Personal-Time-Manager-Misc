'''

'''
import pytest
from unittest.mock import MagicMock

# A trick to allow imports from the 'src' directory
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))


