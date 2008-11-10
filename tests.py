import arcrest
import test.test_support
import unittest

class GeometryTests(unittest.TestCase):
    def testCreatePoint(self):
        pt = arcrest.geometry.Point(5.1, 5.5)
        pt = arcrest.geometry.Point('10', '45.33')
        self.assert_((pt.x, pt.y) == (10., 45.33))
    def testCreateFromJsonStructures(self):
        sr = {'wkid': '102113'}
        spatialref = arcrest.geometry.convert_from_json(sr)
        self.assert_(
            isinstance(spatialref, arcrest.geometry.SpatialReference),
                        "Not a spatial reference")
        pt = {'x': '-111.2', 'y': '110.3',
              'spatialReference': {'wkid': '102113'}}
        point = arcrest.geometry.convert_from_json(pt)
        self.assert_(isinstance(point, arcrest.geometry.Point), "Not a point")
        pl = {'paths': [[[10, 10], [15, 15]], 
                       [[50, 50], [51, 51], [52, 52]]],
              'spatialReference': {'wkid': '102113'}}
        polyline = arcrest.geometry.convert_from_json(pl)
        self.assert_(isinstance(polyline, arcrest.geometry.Polyline), 
                        "Not a polyline")
        pg = {'rings': [[[10, 10], [15, 15], [18, 18], [10, 10]], 
                       [[50, 50], [52, 51], [52, 54], [50, 50]]],
              'spatialReference': {'wkid': '102113'}}
        polygon = arcrest.geometry.convert_from_json(pg)
        self.assert_(isinstance(polygon, arcrest.geometry.Polygon), 
                        "Not a polygon")
        mp = {'points': [[10, 10], [15, 15], [18, 18], [10, 10], 
                         [50, 50], [52, 51], [52, 54], [50, 50]],
              'spatialReference': {'wkid': '102113'}}
        multipoint = arcrest.geometry.convert_from_json(mp)
        self.assert_(isinstance(multipoint, arcrest.geometry.Multipoint), 
                        "Not a multipoint")

class RestURLTests(unittest.TestCase):
    def testURLInstatiatesAtAll(self):
        url = "http://flame6:8399/arcgis/rest/services?f=json"
        urlobject = arcrest.RestURL(url)
    def testUrlMakerHasContents(self):
        url = "http://flame6:8399/arcgis/rest/services?f=json"
        urlobject = arcrest.RestURL(url)
        urlobject._contents

class ServerTests(unittest.TestCase):
    def testConnectToServer(self):
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
    def testUrl(self):
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
        self.failUnless(server.url == 
                        'http://flame6:8399/arcgis/rest/services/?f=json', 
                        "URL is not formed correctly")
    def testServiceList(self):
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
        self.failUnless(set(server.servicenames) == set(["Geometry"]),
                        "Services list does not match")
    def testFolderList(self):
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
        self.failUnless(set(server.foldernames) == 
                        set(["CachedMaps", "Geocode", "Geodata", "Globes",
                             "GP",  "Maps"]), 
                        "Folder list does not match")
    def testSecondFolderTest(self):
        server = arcrest.Catalog("http://flame5/ArcGIS/rest/services")
        folders = server.folders

        known_400s = set([
            "http://flame5/ArcGIS/rest/services/GP/ClosestFacilitiesService/"
              "GPServer/Find Nearby Libraries/?f=json",
            "http://flame5/ArcGIS/rest/services/GP/DriveTimePolygonsService/"
              "GPServer/Calculate Drive Time Polygons/?f=json",
            "http://flame5/ArcGIS/rest/services/GP/ShortestRouteService/"
              "GPServer/Calculate Shortest Route and Text Directions/?f=json"
        ])
        for folder in folders:
            services = folder.services
            for service in services:
                if type(service) == arcrest.GPService:
                    tasks = service.tasks
                    for task in tasks:
                        try:
                            # Force a fetch, get an attr
                            task.name
                        except:
                            self.assert_(task.url in known_400s,
                                         "Unknown failure: %r" % task.url)
    def testHasContents(self):
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
        server._contents
    def testHasJSON(self):
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
        server._json_struct
    def testGetService(self):
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
        service = server.Geometry
        self.assert_(isinstance(service, arcrest.Service), "Not a service.")
    def testGetFolder(self): 
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
        folder = server.Geocode
        self.assert_(isinstance(folder, arcrest.Folder), "Not a folder.")
    def testFolderIsNotAServiceByAnyMeans(self): 
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
        folder = server.Geocode
        self.failIf(isinstance(folder, arcrest.Service), "Not a service.")
    def testGPServiceAmbiguity(self):
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
        gp = server.GP
        self.assert_(not isinstance(gp.ByRefTools, 
                                     (arcrest.GPService, arcrest.MapService)),
                                "Ambiguous--should not be a concrete service")
        byreftools1 = gp.ByRefTools.GPServer
        byreftools2 = gp.ByRefTools_GPServer
        self.assert_(byreftools1.url == byreftools2.url, 
                     "URLs should be identical: %r, %r" % (byreftools1.url,
                                                           byreftools2.url))

class MapServerTests(unittest.TestCase):
    def testGetMapService(self):
        url = "http://flame6:8399/arcgis/rest/services/"
        server = arcrest.Catalog(url)
        mapservice = server.Maps.Redlands.MapServer
        self.assert_(isinstance(mapservice, arcrest.MapService),
                     "Not a map service")
    def testLayerNames(self):
        url = "http://flame6:8399/arcgis/rest/services/"
        server = arcrest.Catalog(url)
        mapservice = server.Maps.Redlands.MapServer
        self.assert_(set(mapservice.layernames) ==
                     set(['Streets', 'Parcels', 'Redlands image']),
                     "Layer names did not match up")
    def testLayers(self):
        url = "http://flame6:8399/arcgis/rest/services/"
        server = arcrest.Catalog(url)
        mapservice = server.Maps.Redlands.MapServer
        self.assert_(all(isinstance(layer, arcrest.MapLayer) 
                     for layer in mapservice.layers), "Layers aren't layers")

class GeocodeServerTests(unittest.TestCase):
    def testConnect(self):
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
        geocoder = server.Geocode.California
    def testFindCandidates(self):
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
        geocoder = server.Geocode.California
        # The Troubadour in Hollywood
        results = geocoder.FindAddressCandidates(
                                             Street="9081 SANTA MONICA BLVD",
                                             City="LOS ANGELES",
                                             Zip=90069)
        results.candidates
    def testReverseGeocode(self):
        url = "http://flame6:8399/arcgis/rest/services"
        geocoder = arcrest.Catalog(url).Geocode.California
        # Some random spot in San Francisco
        point = arcrest.geometry.Point(-122.405634, 37.780959)
        results = geocoder.ReverseGeocode(point, 200)
        self.assert_(results.ZIP == '94103',
                     "Zip code is off")
        self.assert_(results.City == 'SAN FRANCISCO',
                     "City is off")
        self.assert_(isinstance(results.location, arcrest.geometry.Point), 
                     "Expected point for location")

class GPServerTests(unittest.TestCase):
    def testGetGPService(self):
        url = "http://sampleserver1.arcgisonline.com/ArcGIS/rest/services/"
        server = arcrest.Catalog(url)
        gp = server.Elevation.ESRI_Elevation_World.GPServer
        self.assert_(isinstance(gp, arcrest.GPService), "Not a GP service")
    def testGetGPTasks(self):
        url = "http://sampleserver1.arcgisonline.com/ArcGIS/rest/services/"
        server = arcrest.Catalog(url)
        gp = server.Elevation.ESRI_Elevation_World.GPServer
        self.assert_(all(isinstance(task, arcrest.GPTask) 
                         for task in gp.tasks), "Tasks aren't tasks")
    def testExecuteSynchronousGPTask(self):
        url = "http://sampleserver1.arcgisonline.com/ArcGIS/rest/services/"
        server = arcrest.Catalog(url)
        results = server.Specialty.ESRI_Currents_World.MessageInABottle(
            arcrest.geometry.Point(0, 0, spatialReference=4326), 5)
        self.assert_(isinstance(results.Output,
                                arcrest.gptypes.GPFeatureRecordSetLayer),
                     "Expected recordsetlayer, got %r" % type(results.Output))
        for feature in results.Output.features:
            self.assert_(isinstance(feature, 
                                    arcrest.geometry.Polyline),
                         "Expected polyline got %r" %
                            type(results.Output.features))
        #print results.messages
    def testExecuteAsynchronousGPTask(self):
        import time
        url = "http://flame6:8399/arcgis/rest/services/"
        server = arcrest.Catalog(url)
        gp = server.GP.FunctionalityTools.GPServer.LongProcessTool
        job = gp(2.0)
        start = time.time()
        while job.running and (time.time() - start < 4.0):
            time.sleep(0.15)
        self.assert_(time.time() - start < 4.0, "Took too long to execute")
        self.assert_(job.Output_String == "Done Sleeping",
                     "Output didn't match")
    def testExecuteAsync2(self):
        import time
        task = arcrest.GPTask("http://flame6:8399/arcgis/rest/services/"
                              "GP/ByValTools/GPServer/"
                              "OutFeatureLayerParamTest")
        job = task()
        while job.running:
            time.sleep(0.25)
        #print "****"
        #print job.results
        #print job.messages
        #print job.results['Output_Feature_Layer'].features

class GPTypeTests(unittest.TestCase):
    def testGPDate(self):
        date = arcrest.GPDate("2008-11-5")
        date.format
        #print date._json_struct
    def testGPDateGPCall(self):
        import time
        bvt = arcrest.GPService("http://nb2k3/arcgis/rest/services/GP/"
                                "ByValTools/GPServer/")
        gpdt = arcrest.GPDate.from_json_struct({"date": "4/6/07", 
                                                "format": "M/d/y"})
        job2 = bvt.SimpleParamTest(arcrest.GPString("hello"),
                                   gpdt,
                                   arcrest.GPLong(12345),
                                   arcrest.GPDouble(123.456),
                                   arcrest.GPBoolean(False),
                                   arcrest.GPLinearUnit(5, "esriMeters"))
        job2.jobId #print job2.jobId
        while job2.running:
            time.sleep(0.25)
        job2.jobStatus #print job2.jobStatus
         
        for msg in job2.messages:
            msg.description #print msg
         
        r2 = job2.results
    def testGPLinearUnit(self):
        unit = arcrest.GPLinearUnit(5, "esriCentimeters")
    def testGPRecordSetSpatialReference(self):
        rsl = arcrest.GPFeatureRecordSetLayer(arcrest.Point(1000000,1000000))
        repr(rsl)
        str(rsl)

class GeometryServerTests(unittest.TestCase):
    def testGetGeometryService(self):
        url = "http://flame6:8399/arcgis/rest/services"
        server = arcrest.Catalog(url)
        geo = server.Geometry
        self.assert_(isinstance(geo, arcrest.GeometryService),
                     "Not a geometry service")
    def testBufferAPoint(self):
        url = "http://flame6:8399/arcgis/rest/services"
        server = arcrest.Catalog(url)
        geo = server.Geometry
        point = arcrest.geometry.Point(-122.405634, 37.780959,
                                       spatialReference=4326)
        result = geo.Buffer(geometries=point, distances=[5, 10])
        self.assert_(all(isinstance(geom, arcrest.geometry.Polygon) 
                         for geom in result.geometries),
                     "Expected all polygons from Buffer operation.")
        geoms = result.geometries[0].rings
        self.assert_(all([all([isinstance(p, arcrest.geometry.Point)
                     for p in ring])for ring in geoms]),
                     "Result not a list of list of points")

class ImageServiceTests(unittest.TestCase):
    pass

class NetworkServiceTests(unittest.TestCase):
    pass

class GeoDataServiceTests(unittest.TestCase):
    pass

class GlobeServiceTests(unittest.TestCase):
    pass

if __name__ == '__main__':
    test.verbose = True
    test.test_support.run_unittest(GeometryTests,
                                   RestURLTests,
                                   ServerTests,
                                   MapServerTests,
                                   GeocodeServerTests,
                                   GPServerTests,
                                   GPTypeTests,
                                   GeometryServerTests,
                                   ImageServiceTests,
                                   NetworkServiceTests,
                                   GeoDataServiceTests,
                                   GlobeServiceTests)
