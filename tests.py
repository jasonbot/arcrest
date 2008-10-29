import arcrest
import test.test_support
import unittest

class GeometryTests(unittest.TestCase):
    def testCreatePoint(self):
        pt = arcrest.geometry.Point(5.1, 5.5)

class ReSTURLTests(unittest.TestCase):
    def testURLInstatiatesAtAll(self):
        url = arcrest.ReSTURL("http://flame6:8399/arcgis/rest/services?f=json")
    def testUrlMaker(self):
        url = arcrest.ReSTURL("http://flame6:8399/arcgis/rest/services?f=json")
        url._contents

class ServerTests(unittest.TestCase):
    def testConnectToServer(self):
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
    def testUrl(self):
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
        self.failUnless(server.url == 'http://flame6:8399/arcgis/rest/services/?f=json', 
                        "URL is not formed correctly")
    def testServiceList(self):
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
        self.failUnless(set(server.services) == set(["Geometry"]),
                        "Services list does not match")
    def testFolderList(self):
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
        self.failUnless(set(server.folders) == 
                        set(["CachedMaps", "Geocode", "Geodata", "Globes", "GP", "Maps"]), 
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
        results = geocoder.FindAddressCandidates(Street="9081 Santa Monica", City="Los Angeles", Zip=90069)
    def testReverseGeocode(self):
        geocoder = arcrest.Catalog("http://flame6:8399/arcgis/rest/services").Geocode.California
        # Some random spot in San Francisco
        point = arcrest.geometry.Point(-122.405634, 37.780959)
        results = geocoder.ReverseGeocode(point, 200)
        self.assert_(results._json_struct['address']['ZIP'] == '94103', "Zip code is off")
        self.assert_(results._json_struct['address']['City'] == 'SAN FRANCISCO', "City is off")

if __name__ == '__main__':
    test.verbose = True
    test.test_support.run_unittest(GeometryTests, ReSTURLTests, ServerTests,
                                   MapServerTests, GeocodeServerTests)
