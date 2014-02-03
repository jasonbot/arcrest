# coding: utf-8
"""Arcrest is a Python binding to the ArcGIS REST Server API, similar to the
   JavaScript or Flex API in program structure as well as in the way it
   interfaces with ArcGIS servers.
   
   Getting Started with Arcrest
   ============================

   A simple example of connecting to a server:

      >>> import arcrest
      >>> catalog = arcrest.Catalog("http://sampleserver1.arcgisonline.com/arcgis/rest/services")
      >>> catalog.services
      [<GeometryServer ('http://sampleserver1.arcgisonline.com/arcgis/rest/services/Geometry/GeometryServer/?f=json')>]

   Getting a service from a catalog:

      >>> locator = catalog.Locators.ESRI_Geocode_USA
      >>> locator.url
      'http://sampleserver1.arcgisonline.com/arcgis/rest/services/Locators/ESRI_Geocode_USA/GeocodeServer/?f=json'
      >>> locator.FindAddressCandidates(Address="380 NEW YORK ST", City="Redlands", State="CA")
      <FindAddressCandidatesResult('http://sampleserver1.arcgisonline.com/arcgis/rest/services/Locators/ESRI_Geocode_USA/GeocodeServe...')>
      >>> candidates.candidates[0]
      {'attributes': {}, 'score': 81, 'location': POINT(-117.19568 34.05752), 'address': '380 NEW YORK ST, REDLANDS, CA, 92373'}

   Getting a service from a URL:

      >>> service = arcrest.GPService("http://sampleserver1.arcgisonline.com/ArcGIS/rest/services/Specialty/ESRI_Currents_World/GPServer")
      >>> service.url
      'http://sampleserver1.arcgisonline.com/ArcGIS/rest/services/Specialty/ESRI_Currents_World/GPServer/?f=json'

   Inspecting and executing a geoprocessing service:

      >>> service.tasks
      [<GPTask('http://sampleserver1.arcgisonline.com/ArcGIS/rest/services/Specialty/ESRI_Currents_World/GPServer...')>]
   
   Getting a task by name:

      >>> task = service.MessageInABottle
      >>> task.url
      'http://sampleserver1.arcgisonline.com/ArcGIS/rest/services/Specialty/ESRI_Currents_World/GPServer/MessageInABottle/?f=json'      
      >>> task.synchronous
      True
      >>> task.name
      'MessageInABottle'

   Inspecting tasks:

      >>> [(param['name'], param['dataType']) for param in task.parameters if param['direction'] == 'esriGPParameterDirectionInput']
      [('Input_Point', 'GPFeatureRecordSetLayer'), ('Days', 'GPDouble')]

   Executing a job:

      >>> results = service.MessageInABottle(arcrest.Point(-11, 38, arcrest.projections.geographic.GCS_WGS_1984), 2)
      >>> import time
      >>> while results.running:
      ...   time.sleep(0.25)
      ...      
      >>> results.Output.features
      [{'geometry': MULTILINESTRING((-11.00000 38.00000,-10.85327 37.73851,-10.83942 37.71683,-10.83734 37.71359,-10.83702 37.71310,-10.83697 37.71303)), 'attributes': {'shape_length': 0.330091748127675, 'fid': 1, 'fnode_': 0}}]

   """

from arcrest.geometry import *
from arcrest.gptypes import *
from arcrest.server import *
from arcrest.projections import projected, geographic
