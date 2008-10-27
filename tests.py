import arcrest
import test.test_support
import unittest

class ReSTURLTests(unittest.TestCase):
    def testURLInstatiatesAtAll(self):
        url = arcrest.ReSTURL("http://flame6:8399/arcgis/rest/services?f=json")
    def testUrlMaker(self):
        url = arcrest.ReSTURL("http://flame6:8399/arcgis/rest/services?f=json")
        url.contents

class ServerTests(unittest.TestCase):
    def testConnectToServer(self):
        server = arcrest.Server("http://flame6:8399/arcgis/rest/services")
    def testUrl(self):
        server = arcrest.Server("http://flame6:8399/arcgis/rest/services")
        self.failUnless(server.url == 'http://flame6:8399/arcgis/rest/services?f=json', "URL is not formed correctly")
    def testServiceList(self):
        server = arcrest.Server("http://flame6:8399/arcgis/rest/services")
        self.failUnless(set(server.services) == set(["Geometry"]), "Services list does not match")
    def testFolderList(self):
        server = arcrest.Server("http://flame6:8399/arcgis/rest/services")
        self.failUnless(set(server.folders) == 
                        set(["CachedMaps", "Geocode", "Geodata", "Globes", "GP", "Maps"]), 
                        "Folder list does not match")
    def testHasContents(self):
        server = arcrest.Server("http://flame6:8399/arcgis/rest/services")
        server.contents
    def testHasJSON(self):
        server = arcrest.Server("http://flame6:8399/arcgis/rest/services")
        server.json_struct

if __name__ == '__main__':
    test.verbose = True
    test.test_support.run_unittest(ReSTURLTests, ServerTests)
