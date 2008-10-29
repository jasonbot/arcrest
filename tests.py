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

class ReSTURLTests(unittest.TestCase):
    def testURLInstatiatesAtAll(self):
        url = "http://flame6:8399/arcgis/rest/services?f=json"
        urlobject = arcrest.ReSTURL(url)
    def testUrlMakerHasContents(self):
        url = "http://flame6:8399/arcgis/rest/services?f=json"
        urlobject = arcrest.ReSTURL(url)
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
        self.failUnless(set(server._servicenames) == set(["Geometry"]),
                        "Services list does not match")
    def testFolderList(self):
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
        self.failUnless(set(server._foldernames) == 
                        set(["CachedMaps", "Geocode", "Geodata", "Globes",
                             "GP",  "Maps"]), 
                        "Folder list does not match")
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
        byreftools = gp.ByRefTools.GPServer
        byreftools = gp.ByRefTools_GPServer

class MapServerTests(unittest.TestCase):
    pass

class GeocodeServerTests(unittest.TestCase):
    def testConnect(self):
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
        geocoder = server.Geocode.California
    def testFindCandidates(self):
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
        geocoder = server.Geocode.California
        results = geocoder.FindAddressCandidates(Street="9081 Santa Monica",
                                                 City="Los Angeles",
                                                 Zip=90069)
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

if __name__ == '__main__':
    test.verbose = True
    test.test_support.run_unittest(GeometryTests, ReSTURLTests, ServerTests,
                                   MapServerTests, GeocodeServerTests)
