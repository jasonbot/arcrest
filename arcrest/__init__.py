"""Arcrest is a Python binding to the ArcGIS REST Server API, similar to the
   JavaScript or Flex API in program structure as well as in the way it
   interfaces with ArcGIS servers.
   
   Arcrest has one external third-party dependency: simplejson, which should
   be bundled with your copy of Arcrest. Users of Python 2.6 will not need
   this dependency, as it is now a part of the standard Python distribution.
   """

from geometry import *
from gptypes import *
from server import *
from projections import Projected, Geographic
import gui
