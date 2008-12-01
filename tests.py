import arcrest
import test.test_support
import unittest

class MultiUrl(object):
    _urls = ["http://flame6:8399/arcgis/rest/services",
             "http://flame5/arcgis/rest/services"]
    @classmethod
    def multiurltest(cls, fn):
        def execute(self):
            for url in cls._urls:
                fn(self, url)
        return execute

class GeometryTests(unittest.TestCase):
    def testSpatialReference(self):
        sr = arcrest.SpatialReference(26944)
        self.assert_((sr.name, sr.wkid) == 
                        ('NAD_1983_StatePlane_California_IV_FIPS_0404', 26944))
    def testCreatePoint(self):
        #create point with numbers
        pt = arcrest.geometry.Point(5.1, 5.5)
        self.assert_((pt.x, pt.y) == (5.1, 5.5), "Bad point values")
        #create a point with strings
        pt = arcrest.geometry.Point('10', '45.33')
        self.assert_((pt.x, pt.y) == (10., 45.33), "Bad point values")
        #create a point with a spatial reference
        sr = arcrest.SpatialReference(26944)
        pt = arcrest.Point(1959660, 640000, 26944)
        self.assert_((pt.x, pt.y, pt.spatialReference) == 
                        (1959660.0, 640000.0, sr), "Bad point created")
    def testCreatePolyLine(self):
        def testPolyLine(pl, pths):
            self.assert_(isinstance(pl, arcrest.geometry.Polyline),
                         "Not a line")
            self.assert_(isinstance(pl.paths[0][0], arcrest.geometry.Point), 
                         "path doesn't contain points")
            for i in range(0, len(pl.paths)):
                for j in range(0, len(pl.paths[i])):
                    pt1a = pl.paths[i][j]
                    pt1b = pths[i][j]
                    if isinstance(pt1b, arcrest.geometry.Point):
                        self.assert_((pt1a.x, pt1a.y, pt1a.spatialReference) ==
                                     (pt1b.x, pt1b.y, pt1b.spatialReference), 
                                     "Bad line created")
                    else:
                        self.assert_((pt1a.x, pt1a.y) ==
                                     (pt1b[0], pt1b[1]), "Bad line created")
            
        sr = arcrest.SpatialReference(26944)
        pt1 = arcrest.geometry.Point(1959660, 640000, 26944)
        pt2 = arcrest.geometry.Point(1959800, 640500, 26944)
        #create polyline from core structures (lists)
        polyline = arcrest.geometry.Polyline([[[1959660, 640000],
                                               [1959800, 640500]]], 26944)
        testPolyLine(polyline, [[[1959660, 640000],[1959800, 640500]]])
        #create polyline from arcrest classes (Points)
        polyline = arcrest.geometry.Polyline([[pt1, pt2]], 26944)
        testPolyLine(polyline, [[pt1, pt2]])
    def testCreatePolygon(self):
        def testPolygon(pl, rngs):
            self.assert_(isinstance(pl, arcrest.geometry.Polygon),
                         "Not a polygon")
            self.assert_(isinstance(pl.rings[0][0], arcrest.geometry.Point),
                         "ring doesn't contain points")
            for i in range(0, len(pl.rings)):
                for j in range(0, len(pl.rings[i])):
                    pt1a = pl.rings[i][j]
                    pt1b = rngs[i][j]
                    if isinstance(pt1b, arcrest.geometry.Point):
                        self.assert_((pt1a.x, pt1a.y, pt1a.spatialReference) ==
                                     (pt1b.x, pt1b.y, pt1b.spatialReference), 
                                     "Bad polygon created")
                    else:
                        self.assert_((pt1a.x, pt1a.y) ==
                                     (pt1b[0], pt1b[1]), "Bad polygon created")
            
        sr = arcrest.SpatialReference(26944)
        pt1 = arcrest.geometry.Point(1959660, 640000, 26944)
        pt2 = arcrest.geometry.Point(1959800, 640500, 26944)
        pt3 = arcrest.geometry.Point(1959925, 640250, 26944)
        #create polyline from core structures (lists)
        polygon = arcrest.geometry.Polygon([[[1959660, 640000],[1959800, 640500],[1959925, 640250]]], 26944)
        testPolygon(polygon, [[[1959660, 640000],[1959800, 640500],[1959925, 640250]]])
        #create polyline from arcrest classes (Points)
        polygon = arcrest.geometry.Polygon([[pt1, pt2, pt3]], 26944)
        testPolygon(polygon, [[pt1, pt2, pt3]])
    def testCreateFromJsonStructures(self):
        sr = {'wkid': '102113'}
        spatialref = arcrest.geometry.fromJson(sr)
        self.assert_(
            isinstance(spatialref, arcrest.geometry.SpatialReference),
                        "Not a spatial reference")
        pt = {'x': '-111.2', 'y': '110.3',
              'spatialReference': {'wkid': '102113'}}
        point = arcrest.geometry.fromJson(pt)
        self.assert_(isinstance(point, arcrest.geometry.Point), "Not a point")
        pl = {'paths': [[[10, 10], [15, 15]], 
                       [[50, 50], [51, 51], [52, 52]]],
              'spatialReference': {'wkid': '102113'}}
        polyline = arcrest.geometry.fromJson(pl)
        self.assert_(isinstance(polyline, arcrest.geometry.Polyline), 
                        "Not a polyline")
        pg = {'rings': [[[10, 10], [15, 15], [18, 18], [10, 10]], 
                       [[50, 50], [52, 51], [52, 54], [50, 50]]],
              'spatialReference': {'wkid': '102113'}}
        polygon = arcrest.geometry.fromJson(pg)
        self.assert_(isinstance(polygon, arcrest.geometry.Polygon), 
                        "Not a polygon")
        mp = {'points': [[10, 10], [15, 15], [18, 18], [10, 10], 
                         [50, 50], [52, 51], [52, 54], [50, 50]],
              'spatialReference': {'wkid': '102113'}}
        multipoint = arcrest.geometry.fromJson(mp)
        self.assert_(isinstance(multipoint, arcrest.geometry.Multipoint), 
                        "Not a multipoint")

class RestURLTests(unittest.TestCase):
    @MultiUrl.multiurltest
    def testURLInstatiatesAtAll(self, url):
        urlobject = arcrest.RestURL(url)
    @MultiUrl.multiurltest
    def testUrlMakerHasContents(self, url):
        urlobject = arcrest.RestURL(url)
        urlobject._contents

class ServerTests(unittest.TestCase):
    @MultiUrl.multiurltest
    def testConnectToServer(self, url):
        server = arcrest.Catalog(url)
    @MultiUrl.multiurltest
    def testUrl(self, url):
        server = arcrest.Catalog(url)
        self.failUnless(server.url == url + '/?f=json', 
                        "URL is not formed correctly")
    @MultiUrl.multiurltest
    def testServiceList(self, url):
        server = arcrest.Catalog(url)
        self.failUnless(set(server.servicenames) == set(["Geometry"]),
                        "Services list does not match")
    @MultiUrl.multiurltest
    def testFolderList(self, url):
        server = arcrest.Catalog(url)
        self.failUnless(set(server.foldernames) == 
                        set(["CachedMaps", "Geocode", "Geodata", "Globes",
                             "GP",  "Maps"]), 
                        "Folder list does not match")
    @MultiUrl.multiurltest
    def testSecondFolderTest(self, url):
        server = arcrest.Catalog(url)
        folders = server.folders

        known_400s = set([
            "%s/GP/ClosestFacilitiesService/GPServer/"
            "Find Nearby Libraries/" % url,
            "%s/GP/DriveTimePolygonsService/GPServer/"
            "Calculate Drive Time Polygons/?f=json" % url,
            "%s/GP/ShortestRouteService/GPServer/"
            "Calculate Shortest Route and Text Directions/?f=json" % url
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
    @MultiUrl.multiurltest
    def testHasContents(self, url):
        server = arcrest.Catalog(url)
        server._contents
    @MultiUrl.multiurltest
    def testHasJSON(self, url):
        server = arcrest.Catalog(url)
        server._json_struct
    @MultiUrl.multiurltest
    def testGetService(self, url):
        server = arcrest.Catalog(url)
        service = server.Geometry
        self.assert_(isinstance(service, arcrest.Service), "Not a service.")
    @MultiUrl.multiurltest
    def testGetFolder(self, url): 
        server = arcrest.Catalog(url)
        folder = server.Geocode
        self.assert_(isinstance(folder, arcrest.Folder), "Not a folder.")
    @MultiUrl.multiurltest
    def testFolderIsNotAServiceByAnyMeans(self, url): 
        server = arcrest.Catalog(url)
        folder = server.Geocode
        self.failIf(isinstance(folder, arcrest.Service), "Not a service.")
    @MultiUrl.multiurltest
    def testGPServiceAmbiguity(self, url):
        server = arcrest.Catalog(url)
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
    @MultiUrl.multiurltest
    def testGetMapService(self, url):
        server = arcrest.Catalog(url)
        mapservice = server.Maps.Redlands.MapServer
        self.assert_(isinstance(mapservice, arcrest.MapService),
                     "Not a map service")
    @MultiUrl.multiurltest
    def testLayerNames(self, url):
        server = arcrest.Catalog(url)
        mapservice = server.Maps.Redlands.MapServer
        self.assert_(set(mapservice.layernames) ==
                     set(['Streets', 'Parcels', 'Redlands image']),
                     "Layer names did not match up")
    @MultiUrl.multiurltest
    def testLayers(self, url):
        server = arcrest.Catalog(url)
        mapservice = server.Maps.Redlands.MapServer
        self.assert_(all(isinstance(layer, arcrest.MapLayer) 
                     for layer in mapservice.layers), "Layers aren't layers")

class GeocodeServerTests(unittest.TestCase):
    @MultiUrl.multiurltest
    def testConnect(self, url):
        server = arcrest.Catalog(url)
        geocoder = server.Geocode.California
    @MultiUrl.multiurltest
    def testFindCandidates(self, url):
        server = arcrest.Catalog(url)
        geocoder = server.Geocode.California
        # The Troubadour in Hollywood
        results = geocoder.FindAddressCandidates(
                                             Street="9081 SANTA MONICA BLVD",
                                             City="LOS ANGELES",
                                             Zip=90069)
        results.candidates
    @MultiUrl.multiurltest
    def testReverseGeocode(self, url):
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
    @MultiUrl.multiurltest
    def testGetGPService(self, url):
        server = arcrest.Catalog(url)
        gp = server.GP.ByValTools.GPServer
        self.assert_(isinstance(gp, arcrest.GPService), "Not a GP service")
    @MultiUrl.multiurltest
    def testGetGPTasks(self, url):
        server = arcrest.Catalog(url)
        gp = server.GP.FunctionalityTools.GPServer
        self.assert_(all(isinstance(task, arcrest.GPTask) 
                         for task in gp.tasks), "Tasks aren't tasks")
    def testExecuteMessageInABottle(self):
        sampurl = "http://sampleserver1.arcgisonline.com/ArcGIS/rest/services/"
        server = arcrest.Catalog(sampurl)
        results = server.Specialty.ESRI_Currents_World.MessageInABottle(
            arcrest.geometry.Point(0, 0, spatialReference=4326), 5)
        self.assert_(isinstance(results.Output,
                                arcrest.gptypes.GPFeatureRecordSetLayer),
                     "Expected GPFeatureRecordSetLayer, got %r" % type(results.Output))
        for feature in results.Output.features:
            self.assert_(set(feature.keys()) == 
                         set(['geometry', 'attributes']),
                         "Expected two keys, got %r" % feature.keys())
            self.assert_(isinstance(feature['geometry'],
                                    arcrest.geometry.Polyline),
                         "Expected polyline got %r" %
                            type(results.Output.features))
        print
        print "===="
        print results.Output._columns
        self.assert_(all(isinstance(row['attributes'], dict) 
                         for row in results.Output), 
                     "Expected dict values for all attributes")
        for row in results.Output:
            print "ROW", row
            print "    FID: ", row['attributes']['fid']
        print "===="
        print results.messages
    @MultiUrl.multiurltest
    def testASync1(self, url):
        import time
        bvt = arcrest.GPService("%s/GP/ByValTools/GPServer/?f=json" % url)
        job = bvt.OutFeatureLayerParamTest.SubmitJob()
        while job.running:
            time.sleep(0.25)
        self.assert_(job.jobStatus == "esriJobSucceeded",
                     "testAsync1 (OutFeatureLayerParamTest) submitjob test failed")
        r = job.results
        self.assert_(isinstance(r['Output_Feature_Layer'],
                                arcrest.gptypes.GPFeatureRecordSetLayer),
                     "Expected GPFeatureRecordSetLayer, got %r" % type(r['Output_Feature_Layer']))
    @MultiUrl.multiurltest
    def testASync2(self, url):
        import time
        task = arcrest.GPTask("%s/GP/ByValTools/GPServer/OutFeatureLayerParamTest" % url)
        job = task()
        while job.running:
            time.sleep(0.25)
        self.assert_(job.jobStatus == "esriJobSucceeded",
                     "testAsync2 (OutFeatureLayerParamTest) submitjob test failed")
        r = job.results
    @MultiUrl.multiurltest
    def testJobObject(self, url):
        import time

        def testJobInfo(job):
            jobid = job.jobId
            self.assert_(jobid.startswith("j") == True,
                         "testJobObject Failed: Bad jobid")
            while job.running:
                time.sleep(0.25)
            if job.jobStatus == "esriJobSucceeded":
                expjobid = "%s/GP/ByValTools/GPServer/OutTblViewParamTests/jobs/%s/?f=json" % (url, jobid)
                self.assert_(job.url == expjobid,
                             "testJobObject Failed: job.url is invalid.\nExpected job.url: %s \nReceived job.url: %s" % (expjobid, job.url))
            else:
                self.assert_(job.jobStatus == "esriJobSucceeded",
                             "testJobObject can not be completed: job failed")
            self.assert_(isinstance(job.messages, list), "testJobObject Failed: job.messages did not return a list")
            for msg in job.messages:
                print msg

        #run OutTableViewParamTest
        bvt = arcrest.GPService("%s/GP/ByValTools/GPServer/?f=json" % url)
        job = bvt.OutTblViewParamTests.SubmitJob()
        testJobInfo(job)
        r = job.results

class GPTypeTests(unittest.TestCase):
    def testGPDate(self):
        date = arcrest.GPDate("2008-11-5")
        date.format
        #print date._json_struct
    @MultiUrl.multiurltest
    def testGPDateGPCall(self, url):
        import time
        bvt = arcrest.GPService("%s/GP/ByValTools/GPServer/" % url)
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
    @MultiUrl.multiurltest
    def testGPRasterDataLayerType(self, url):
        import time
        bvt = arcrest.GPService("%s/GP/ByValTools/GPServer/" % url)
        job = bvt.OutRasterLayerParamTest.SubmitJob()
        while job.running:
            time.sleep(0.25)
        r = job.results
        print type(r['Output_Raster_Layer'])
        print repr(r['Output_Raster_Layer'])
    @MultiUrl.multiurltest
    def testGPOutTableParam(self, url):
        import sys
        import time
        otv = arcrest.GPService("%s/GP/ByValTools/GPServer/" % url)
        job = otv.OutTblViewParamTests()
        print job, job.jobId, dir(job)
        while job.running:
            print ".",
            sys.stdout.flush()
            time.sleep(0.25)
        print "---"
        print job.Output_Table_View
        print job.Output_Table_View._columns

class GeometryServerTests(unittest.TestCase):
    @MultiUrl.multiurltest
    def testGetGeometryService(self, url):
        server = arcrest.Catalog(url)
        geo = server.Geometry
        self.assert_(isinstance(geo, arcrest.GeometryService),
                     "Not a geometry service")
    @MultiUrl.multiurltest
    def testBufferAPoint(self, url):
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
