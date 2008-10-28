import arcrest
import test.test_support
import unittest

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
        self.failUnless(server.url == 'http://flame6:8399/arcgis/rest/services/?f=json', "URL is not formed correctly")
    def testServiceList(self):
        server = arcrest.Catalog("http://flame6:8399/arcgis/rest/services")
        self.failUnless(set(server.services) == set(["Geometry"]), "Services list does not match")
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
        print service.url
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
        # Both a MapServer and GPServer by the same name; alert to ambiguity
        def callable():
            byreftools = gp.ByRefTools
        self.assertRaises(AttributeError, callable)
        byreftools = gp.ByRefTools_GPServer

if __name__ == '__main__':
    test.verbose = True
    test.test_support.run_unittest(ReSTURLTests, ServerTests)
