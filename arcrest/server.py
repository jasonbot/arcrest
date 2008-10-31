"""The ArcGIS Server REST API, short for Representational State Transfer, 
   provides a simple, open Web interface to services hosted by ArcGIS Server.
   All resources and operations exposed by the REST API are accessible through
   a hierarchy of endpoints or Uniform Resource Locators (URLs) for each GIS 
   service published with ArcGIS Server."""

# json parsing is a third-party library until 2.6, make some 
# effort to import it

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        raise ImportError("Please install the simplejson module "\
                          "from http://www.undefined.org/python/ "\
                          "or use arcrest with Python 2.6")

import cgi
import urllib
import urllib2
import urlparse

import geometry

# Note that nearly every class below derives from this RestURL class.
# The reasoning is that every object has an underlying URL resource on 
# the REST server. Some are static or near-static, such as a folder or a
# service's definition, but some URLs are volatile and represent the
# application of an action, such as Buffering a set of points using the
# geometry service. This class attempts to provide some baseline functionality
# required by the set of operations one performs using the ArcGIS REST API,
# such as making sure the format is always set to json, parsing the json,
# keeping the result in memory as needed, and returning instances of objects
# represented by relative URLs.

class RestURL(object):
    """Represents a top-level, base REST-style URL."""
    __cache_request__ = False  # Fetch every time or just once?
    __urldata__ = Ellipsis     # What actually gets HTTP GETten
    __json_struct__ = Ellipsis # Cache for json.loads(self.__urldata__)
    __has_json__ = True        # Parse the data as a json struct? Set to
                               # false for binary data, html, etc.
    __lazy_fetch__ = True      # Fetch when constructed, or later on?
    def __init__(self, url):
        # Expects a urlparse.urlsplitted list as the url, but accepts a
        # string because that is easier/makes more sense everywhere.
        if isinstance(url, basestring):
            url = urlparse.urlsplit(url)
        # Ellipsis is used instead of None for the case where no data
        # is returned from the server due to an error condition -- we
        # need to differentiate between 'NULL' and 'UNDEFINED'
        self.__urldata__ = Ellipsis
        # Pull out query, whatever it may be
        urllist = list(url)
        query_dict = {}
        # parse_qs returns a dict, but every value is a list (it assumes
        # that keys can be set multiple times like ?a=1&a=2 -- this flexibility
        # is probably useful to someone, but not here). Pull out the first
        # element of every list so when we convert back to a query string
        # it doesn't enclose all values in []
        for k, v in cgi.parse_qs(urllist[3]).iteritems():
            query_dict[k] = v[0]
        # Set the f= flag to json (so we can interface with it)
        if self.__has_json__ is True:
            query_dict['f'] = 'json'
        # Hack our modified query string back into URL components
        urllist[3] = urllib.urlencode(query_dict)
        self._url = urllist
        # Nonlazy: force a fetch
        if self.__lazy_fetch__ is False and self.__cache_request__ is True:
            self._contents
    def __repr__(self):
        return "<%s(%r)>" % (self.__class__.__name__, self.url)
    def _get_subfolder(self, foldername, returntype, params={}):
        """Return an object of the requested type with the path relative
           to the current object's URL. Optionally, query parameters
           may be set."""
        newurl = urlparse.urljoin(self.url, foldername, False)
        #print "    ", self.url, "(", foldername, ")", newurl
        # Add the key-value pairs sent in params to query string if they
        # are so defined.
        if params:
            url_tuple = urlparse.urlsplit(newurl)
            urllist = list(url_tuple)
            # As above, pull out first element from parse_qs' values
            query_dict = dict((k, v[0]) for k, v in 
                               cgi.parse_qs(urllist[3]).iteritems())
            for key, val in params.iteritems():
                # Lowercase bool string
                if isinstance(val, bool):
                    query_dict[key] = str(val).lower()
                # Special case: convert an envelope to .bbox in the bb
                # parameter
                elif isinstance(val, geometry.Envelope):
                    query_dict[key] = val.bbox
                # Just use the wkid of SpatialReferences
                elif isinstance(val, geometry.SpatialReference): 
                    query_dict[key] = val.wkid
                # Ignore null values, and coerce string values (hopefully
                # everything sent in to a query has a sane __str__)
                elif val is not None:
                    query_dict[key] = str(val)
            # Replace URL query component with newly altered component
            urllist[3] = urllib.urlencode(query_dict)
            newurl = urllist
        # Instantiate new RestURL or subclass
        rt = returntype(newurl)
        # Remind the resource where it came from
        rt.parent = self
        return rt
    @property
    def url(self):
        """The URL as a string of the resource."""
        return urlparse.urlunsplit(self._url)
    @property
    def _contents(self):
        """The raw contents of the URL as fetched, this is done lazily.
           For non-lazy fetching this is accessed in the object constructor."""
        if self.__urldata__ is Ellipsis or self.__cache_request__ is False:
            handle = urllib2.urlopen(self.url)
            # Handle the special case of a redirect (only follow once) --
            # Note that only the first 3 components (protocol, hostname, path)
            # are altered as component 4 is the query string, which can get
            # clobbered by the server.
            fetched_url = list(urlparse.urlsplit(handle.url)[:3])
            if fetched_url != list(self._url[:3]):
                self._url[:3] = fetched_url
                return self._contents
            # No redirect, proceed as usual.
            self.__urldata__ = handle.read()
        return self.__urldata__
    @property
    def _json_struct(self):
        """The json data structure in the URL contents, it will cache this
           if it makes sense so it doesn't parse over and over."""
        if self.__cache_request__:
            if self.__json_struct__ is Ellipsis:
                self.__json_struct__ = json.loads(self._contents)
            return self.__json_struct__
        else:
            return json.loads(self._contents)

# On top of a URL, the ArcGIS Server folder structure lists subfolders
# and services.
class Folder(RestURL):
    """Represents a folder path on an ArcGIS REST server."""
    __cache_request__  = True
    # Conversion table from type string to class instance.
    _service_type_mapping = None
    @property
    def foldernames(self):
        "Returns a list of folder names available from this folder."
        return [folder.split('/')[-1] for folder 
                    in self._json_struct.get('folders', [])]
    @property
    def folders(self):
        "Returns a list of Folder objects available in this folder."
        return [self._get_subfolder(fn, Folder) for fn in self.foldernames]
    @property
    def servicenames(self):
        "Give the list of services available in this folder."
        return set([service['name'].rstrip('/').split('/')[-1] 
                        for service in self._json_struct.get('services', [])])
    @property
    def services(self):
        "Returns a list of Service objects available in this folder"
        return [self._get_subfolder("%s/%s/" % (s['name'], s['type']), 
                self._service_type_mapping.get(s['type'], Service)) for s
                in self._json_struct.get('services', [])]
    @property
    def url(self):
        """The URL as a string of the resource."""
        if not self._url[2].endswith('/'):
            self._url[2] += '/'
        return RestURL.url.__get__(self)
    def __getattr__(self, attr):
        return self[attr]
    def __getitem__(self, attr):
        # If it's a folder, easy:
        if attr in self.foldernames:
            return self._get_subfolder(attr, Folder)
        services = [x.copy() for x in self._json_struct['services']]
        # Strip out relative paths
        for service in services:
            service['name'] = service['name'].rstrip('/').split('/')[-1]
        # Handle the case of Folder_Name being potentially of Service_Type
        # format
        if '_' in attr: # May have a Name_Type service here
            al = attr.rstrip('/').split('/')[-1].split('_')
            servicetype = al.pop()
            untyped_attr = '_'.join(al)
            matchingservices = [svc for svc in services 
                                if svc['name'] == untyped_attr
                                and svc['type'] == servicetype]
            if len(matchingservices) == 1: 
                return self._get_subfolder("%s/%s/" % 
                    (untyped_attr, servicetype),
                    self._service_type_mapping.get(servicetype, Service))
        # Then match by service name
        matchingservices = [svc for svc in services if svc['name'] == attr]
        # Found more than one match, there is ambiguity so return an
        # object holding .ServiceType attributes representing each service.
        if len(matchingservices) > 1:
            # Return an instance with accessors for overlapping services
            class AmbiguousService(object):
                """This service name has multiple service types."""
            ambiguous = AmbiguousService()
            for svc in matchingservices:
                attr, servicetype = svc['name'], svc['type']
                service = self._get_subfolder("%s/%s/" % (attr, servicetype), 
                    self._service_type_mapping.get(servicetype, Service))
                setattr(ambiguous, servicetype, service)
            return ambiguous
        # Just one match, can return itself.
        elif len(matchingservices) == 1:
            servicetype = matchingservices[0]['type']
            return self._get_subfolder("%s/%s/" % (attr, servicetype), 
                self._service_type_mapping.get(servicetype, Service))
        raise AttributeError("No service or folder named %r found" % attr)

# A catalog root functions the same as a folder, so treat Catalog as just a
# special case of Folder

class Catalog(Folder):
    """The catalog resource is the root node and initial entry point into an 
       ArcGIS Server host. This resource represents a catalog of folders and 
       services published on the host."""
    __cache_request__  = True
    def __init__(self, url):
        url_ = list(urlparse.urlsplit(url))
        if not url_[2].endswith('/'):
            url_[2] += "/"
        super(Catalog, self).__init__(url_)
        # Basically a Folder, but do some really, really rudimentary sanity
        # checking (look for folders/services, make sure format is JSON) so we
        # can verify this URL behaves like a Folder -- catch errors early 
        # before any other manipulations go on.
        assert 'folders' in self._json_struct, "No folders in catalog root"
        assert 'services' in self._json_struct, "No services in catalog root"

# Definitions for classes calling/manipulating services

class Service(RestURL):
    """Represents an ArcGIS REST service. This is an abstract base -- services
       derive from this."""
    __cache_request__ = False
    __service_type__ = None
    @property
    def serviceDescription(self):
        """Get a short description of the service. Will return None if there is
           no description for this service or service type."""
        return self._json_struct.get('serviceDescription', None)
    def __repr__(self):
        return "<%s%s (%r)>" % (self.__service_type__,
                                " - %r" % self.serviceDescription
                                   if self.serviceDescription
                                   else '',
                                self.url)
    def __getattr__(self, attr):
        # Special-cased __getattr__ -- if a folder has an unambiguous service
        # by name it will return a Service instance, otherwise it will return
        # an AmbiguousService instance with accessors. For example,
        # http://flame6:8399/arcgis/rest/services/GP has ByRefTools as a
        # MapServer and a GPServer, so
        #    >>> server = Catalog("http://flame6:8399/arcgis/rest/services/")
        #    >>> server.GP.ByRefTools
        # has an ambiguous match, meaning you need to access
        #    >>> server.GP.ByRefTools.GPServer
        # to get to the GP verion of the service, but
        #    >>> server.GP.DriveTimePolygons
        # gives you the GPServer. This gives and inconsistent interface,
        # because then
        #    >>> server.GP.DriveTimePolygons.GPServer
        # doesn't work and that's inconsistent. Meant to be a balance between
        # ease-of-use and explicitness.
        if attr == self.__service_type__:
            return self
        raise AttributeError("%r does not have attribute %r" % 
                             (self.__class__.__name__, attr))

class ServerError(Exception):
    """Exception for server-side error responses"""

class Result(RestURL):
    """Abstract class representing the result of an operation performed on a
       REST service"""
    __cache_request__ = True # Only request the URL once
    __lazy_fetch__ = False # Force-fetch immediately
    def __init__(self, url):
        super(Result, self).__init__(url)
        if 'error' in self._json_struct:
            raise ServerError("ERROR %i: %r <%s>" % 
                               (self._json_struct['error']['code'], 
                                self._json_struct['error']['message'],
                                self.url))

class Layer(RestURL):
    """Represents the base class for map and network layers"""
    __cache_request__ = True # Only request the URL once
    __lazy_fetch__ = False # Force-fetch immediately

# Service implementations -- mostly simple conversion wrappers for the
# functionality handled up above, wrapper types for results, etc.

class MapLayer(Layer):
    """The layer resource represents a single layer in a map of a map service 
       published by ArcGIS Server. It provides basic information about the
       layer such as its name, type, parent and sub-layers, fields, min and
       max scales, extent, and copyright text."""
    def QueryLayer(self, text=None, Geometry=None, inSR=None, 
                   spatialRel='esriSpatialRelIntersects', where=None,
                   outFields=None, returnGeometry=None, outSR=None):
        """The query operation is performed on a layer resource. The result
           of this operation is a resultset resource. This resource provides
           information about query results including the values for the fields
           requested by the user. If you request geometry information, the
           geometry of each result is also returned in the resultset.

           Spatial Relation Options:
                esriSpatialRelIntersects | esriSpatialRelContains | 
                esriSpatialRelCrosses | esriSpatialRelEnvelopeIntersects | 
                esriSpatialRelIndexIntersects | esriSpatialRelOverlaps | 
                esriSpatialRelTouches | esriSpatialRelWithin"""
    @property
    def id(self):
        return self._json_struct['id']
    @property
    def name(self):
        return self._json_struct['name']
    @property
    def type(self):
        return self._json_struct['type']
    @property
    def geometryType(self):
        return self._json_struct['geometryType']
    @property
    def copyrightText(self):
        return self._json_struct['copyrightText']
    @property
    def parentLayer(self):
        return self._get_subfolder("../%s/" % 
                                   self._json_struct['parentLayer']['id'],
                                   MapLayer)
    @property
    def subLayers(self):
        return [self._get_subfolder("../%s/" % 
                                    layer['parentLayer']['id'],
                                    MapLayer)
                for layer in self._json_struct['subLayers']]
    @property
    def minScale(self):
        return self._json_struct['minScale']
    @property
    def maxScale(self):
        return self._json_struct['maxScale']
    @property
    def extent(self):
        return geometry.convert_from_json(self._json_struct['extent'])
    @property
    def displayField(self):
        return self._json_struct['displayField']
    @property
    def fields(self):
        return self._json_struct['fields']

class MapTile(RestURL):
    """Represents the map tile fetched from a map service."""
    __has_json__ = False
    def save(self, outfile):
        """Save the image data to a file or file-like object"""
        if isinstance(outfile, basestring):
            outfile = open(outfile, 'wb')
        outfile.write(self._contents)

class MapService(Service):
    """Map services offer access to map and layer content. Map services can
       either be cached or dynamic. A map service that fulfills requests with
       pre-created tiles from a cache instead of dynamically rendering part of
       the map is called a cached map service. A dynamic map service requires
       the server to render the map each time a request comes in. Map services
       using a tile cache can significantly improve performance while
       delivering maps, while dynamic map services offer more flexibility."""
    __service_type__ = "MapServer"
    def ExportMap(self, bbox, size=None, dpi=None, imageSR=None, bboxSR=None,
                  format=None, layerDefs=None, layers=None, transparent=False):
        """The export operation is performed on a map service resource. The
           result of this operation is a map image resource. This resource
           provides information about the exported map image such as its URL,
           its width and height, extent and scale."""
        return self._get_subfolder('export/', Result, 
                                              {'bbox': bbox, 
                                               'size': size,
                                               'dpi': dpi,
                                               'imageSR': imageSR,
                                               'bboxSR': bboxSR,
                                               'format': format,
                                               'layerDefs': layerDefs,
                                               'layers': layers,
                                               'transparent': transparent})
    def Identify(self, Geometry, sr=None, layers=None, tolerance=1, 
                 mapExtent=None, imageDisplay=None, returnGeometry=True):
        """The identify operation is performed on a map service resource. The
           result of this operation is an identify results resource. Each
           identified result includes its name, layer ID, layer name, geometry
           and geometry type, and other attributes of that result as name-value
           pairs."""
        assert hasattr(Geometry, '__geometry_type__'), "Invalid geometry"
        gt = Geometry.__geometry_type__
        if sr is None:
            sr = Geometry.spatialReference.wkid
        geo_json = json.dumps(Geometry._json_struct_without_srReference.wkid)
        return self._get_subfolder('identify/', Result,
                                                {'geometry': geo_json,
                                                 'geometryType': gt,
                                                 'sr': sr,
                                                 'layers': layers,
                                                 'tolerance': tolerance,
                                                 'mapExtent': mapExtent,
                                                 'imageDisplay': 
                                                    imageDisplay,
                                                 'returnGeometry':
                                                    returnGeometry})
    def Find(self, searchText, contains=True, searchFields=None, sr=None, 
             layers=None, returnGeometry=True):
        """The find operation is performed on a map service resource. The
           result of this operation is a find results resource. Each result
           includes  its value, feature ID, field name, layer ID, layer name,
           geometry, geometry type, and attributes in the form of name-value
           pairs."""
        return self._get_subfolder('find/', Result, 
                                            {'searchText': searchText,
                                             'contains': contains,
                                             'searchFields': searchFields,
                                             'sr': sr, 
                                             'layers': layers,
                                             'returnGeometry': returnGeometry})
    def GenerateKML(self, docName, layers, layerOptions='composite'):
        """The generateKml operation is performed on a map service resource.
           The result of this operation is a KML document wrapped in a KMZ 
           file. The document contains a network link to the KML Service 
           endpoint with properties and parameters you specify.

           Layer Options:
                 composite: (default) All layers as a single composite image.
                            Layers cannot be turned on and off in the client.
             separateImage: Each layer as a separate image.
              nonComposite: Vector layers as vectors and raster layers as
                            images."""
        return self._get_subfolder('generateKml/', Result,
                                       {'docName': docName, 
                                        'layers': layers,
                                        'layerOptions': layerOptions})
    def tile(self, row, col, zoomlevel=None):
        """For cached maps, this resource represents a single cached tile for
           the map. The image bytes for the tile at the specified level, row 
           and column are directly streamed to the client. If the tile is not
           found, an HTTP status code of 404 (Not found) is returned."""
        return self._get_subfolder("tile/%s/%s/%s/" % (row, col, zoomlevel), 
                                   MapTile)

    @property
    def mapName(self):
        """This map's name"""
        return self._json_struct['mapName']
    @property
    def description(self):
        """This map's description"""
        return self._json_struct['description']
    @property
    def copyrightText(self):
        """This map's copyright text"""
        return self._json_struct['copyrightText']
    @property
    def spatialReference(self):
        """This map's Spatial Reference"""
        return geometry._convert_from_json(
                                        self._json_struct['spatialReference'])
    @property
    def initialExtent(self):
        """This map's initial extent"""
        return geometry._convert_from_json(
                                        self._json_struct['initialExtent'])
    @property
    def fullExtent(self):
        """This map's full extent"""
        return geometry._convert_from_json(
                                        self._json_struct['fullExtent'])
    @property
    def layernames(self):
        """Return a list of the names of this map's layers"""
        return [layer['name'] for layer in self._json_struct['layers']]
    @property
    def layers(self):
        """Return a list of this map's layer objects"""
        return [self._get_subfolder("%s/" % layer['id'], MapLayer)
                for layer in self._json_struct['layers']]

class FindAddressCandidatesResult(Result):
    """Represents the result from a geocode operation. The .candidates
       field holds a list of candidate addresses as python dicts; the
       ['location'] key in each is a geometry.Point for the location of the
       address."""
    @property
    def candidates(self):
        """A list of candidate addresses from a geocode operation"""
        # convert x['location'] to a point from a json point struct
        def cditer():
            for candidate in self._json_struct['candidates']:
                newcandidate = candidate.copy()
                newcandidate['location'] = \
                    geometry.convert_from_json(newcandidate['location'])
                yield newcandidate
        return list(cditer())

class ReverseGeocodeResult(Result):
    """Represents the result from a reverse geocode operation -- the two
       interesting fields are .address, which is a dictionary with the
       fields of the candidate address, and .location, which is a
       geometry.Point which is the actual location of the address."""
    @property
    def address(self):
        return self._json_struct['address']
    @property
    def location(self):
        return geometry.convert_from_json(self._json_struct['location'])
    def __getattr__(self, attr):
        return self._json_struct['address'][attr]

class GeocodeService(Service):
    """Geocoding is the process of assigning a location, usually in the form
       of coordinate values (points), to an address by comparing the
       descriptive location elements in the address to those present in the
       reference material. Addresses come in many forms, ranging from the
       common address format of a house number followed by the street name and
       succeeding information to other location descriptions such as postal
       zone or census tract. An address includes any type of information that
       distinguishes a place."""
    __service_type__ = "GeocodeServer"
    def FindAddressCandidates(self, outFields=[], **fields):
        """The findAddressCandidates operation is performed on a geocode
           service resource. The result of this operation is a resource
           representing the  list of address candidates. This resource
           provides information about candidates including the address,
           location, and score."""
        required_unset_fields = []
        for field in self._json_struct['addressFields']:
            if field['required'] and field['name'] not in fields:
                required_unset_fields.append(field['name'])
        if required_unset_fields:
            raise ValueError("Required field%s not set for Geocode: %s" % 
                               ('' if len(required_unset_fields) == 1 
                                   else 's', ', '.join(required_unset_fields)))
        query = fields.copy()
        query['outFields'] = outFields
        return self._get_subfolder('findAddressCandidates/', 
                                   FindAddressCandidatesResult, query)
    def ReverseGeocode(self, location, distance):
        """The reverseGeocode operation is performed on a geocode service 
           resource. The result of this operation is a reverse geocoded address
           resource. This resource provides information about all the address
           fields pertaining to the reverse geocoded address as well as its
           exact location."""
        return self._get_subfolder('reverseGeocode/', ReverseGeocodeResult, 
                                                      {'location': location, 
                                                       'distance': distance})

class GPTask(Service):
    """The GP task resource represents a single task in a GP service published
       using the ArcGIS Server. It provides basic information about the task
       including its name and display name. It also provides detailed 
       information about the various input and output parameters exposed by the
       task"""
    @property
    def executionType(self):
        """Returns the execution type of this task."""
        return self._json_struct['executionType']
    @property
    def synchronous(self):
        """Returns a boolean indicating whether this tasks runs synchronously
           (True) or asynchronously (False)."""
        sv = self._json_struct['executionType']
        if sv == 'esriExecutionTypeSynchronous':
            return True
        elif sv == 'esriExecutionTypeAsynchronous':
            return False
        raise ValueError("Unknown synchronous value: %r" % sv)

class GPService(Service):
    """Geoprocessing is a fundamental part of enterprise GIS operations. 
       Geoprocessing provides the data analysis, data management, and data 
       conversion tools necessary for all GIS users.

       A geoprocessing service represents a collection of published tools that
       perform tasks necessary for manipulating and analyzing geographic 
       information across a wide range of disciplines. Each tool performs one
       or more operations, such as projecting a data set from one map
       projection to another, adding fields to a table, or creating buffer 
       zones around features. A tool accepts input (such as feature sets, 
       tables, and property values), executes operations using the input data,
       and generates output for presentation in a map or further processing by 
       the client. Tools can be executed synchronously (in sequence) or
       asynchronously."""
    __service_type__ = "GPServer"
    @property
    def tasknames(self):
        return self._json_struct['tasks']
    @property
    def tasks(self):
        return [self._get_subfolder(taskname, GPTask)
                for taskname in self.tasknames]

class GeometryResult(Result):
    """Represents the output of a Project, Simplify or Buffer operation 
       performed by an ArcGIS REST API Geometry service."""
    @property
    def geometries(self):
        return [geometry.convert_from_json(geo) 
                for geo in self._json_struct['geometries']]

class LengthsResult(Result):
    """Represents the output of a Lengths operation performed by an ArcGIS
       REST API Geometry service."""
    @property
    def lengths(self):
        return map(float(length) for length in self._json_struct['lengths'])

class AreasAndLengthsResult(LengthsResult):
    """Represents the output of a AreasAndLengths operation performed by an 
       ArcGIS REST API Geometry service."""
    @property
    def areas(self):
        return map(float(area) for area in self._json_struct['areas'])

class GeometryService(Service):
    """A geometry service contains utility methods, which provide access to
       sophisticated and frequently used geometric operations. An ArcGIS Server
       Web site can only expose one geometry service with the static name
       "Geometry." Note that geometry input and output, where required, are
       always packaged as an array."""
    __service_type__ = "GeometryServer"

    def Project(self, geometries, outSR, inSR=None):
        """The project operation is performed on a geometry service resource.
           The result of this operation is an array of projected geometries.
           This resource projects an array of input geometries from an input
           spatial reference to an output spatial reference."""

        if isinstance(geometries, geometry.Geometry):
            geometries = [geometries]

        if inSR is None:
            inSR = geometries[0].spatialReference.wkid

        geometry_types = set([x.__geometry_type__ for x in geometries])
        assert len(geometry_types) == 1, "Too many geometry types"
        geo_json = json.dumps({'geometryType': list(geometry_types)[0],
                    'geometries': [geo._json_struct_without_sr 
                                        for geo in geometries]
                    })

        return self._get_subfolder('project', GeometryResult, 
                                   {'geometries': geo_json,
                                    'inSR': inSR,
                                    'outSR': outSR
                                   })

    def Simplify(self, geometries, sr=None):
        """The simplify operation is performed on a geometry service resource. 
           Simplify permanently alters the input geometry so that the geometry 
           becomes topologically consistent. This resource applies the ArcGIS 
           simplify operation to each geometry in the input array. For more 
           information, see ITopologicalOperator.Simplify Method and 
           IPolyline.SimplifyNetwork Method."""

        if isinstance(geometries, geometry.Geometry):
            geometries = [geometries]

        if sr is None:
            sr = geometries[0].spatialReference.wkid

        geometry_types = set([x.__geometry_type__ for x in geometries])
        assert len(geometry_types) == 1, "Too many geometry types"
        geo_json = json.dumps({'geometryType': list(geometry_types)[0],
                    'geometries': [geo._json_struct_without_sr
                                        for geo in geometries]
                    })
        return self._get_subfolder('simplify', GeometryResult, 
                                   {'geometries': geo_json,
                                    'sr': sr
                                   })

    def Buffer(self, geometries, distances, unit=None, unionResults=False,
               inSR=None, outSR=None, bufferSR=None):
        """The buffer operation is performed on a geometry service resource.
           The result of this operation is buffer polygons at the specified
           distances for the input geometry array. An option is available to
           union buffers at each distance."""

        if isinstance(geometries, geometry.Geometry):
            geometries = [geometries]

        geometry_types = set([x.__geometry_type__ for x in geometries])
        assert len(geometry_types) == 1, "Too many geometry types"
        geo_json = json.dumps({'geometryType': list(geometry_types)[0],
                    'geometries': [geo._json_struct_without_sr
                                        for geo in geometries]
                    })

        if inSR is None:
            inSR = geometries[0].spatialReference.wkid

        if outSR is None:
            outSR = geometries[0].spatialReference.wkid

        if bufferSR is None:
            bufferSR = geometries[0].spatialReference.wkid

        return self._get_subfolder('buffer', GeometryResult, 
                                   {'geometries': geo_json,
                                    'distances': distances,
                                    'unit': unit,
                                    'unionResults': unionResults,
                                    'inSR': inSR,
                                    'outSR': outSR,
                                    'bufferSR': bufferSR
                                   })

    def AreasAndLengths(self, polygons, sr=None):
        """The areasAndLengths operation is performed on a geometry service
           resource. This operation calculates areas and perimeter lengths for
           each polygon specified in the input array."""

        if isinstance(polygons, geometry.Geometry):
            polygons = [polygons]

        if sr is None:
            sr = polygons[0].spatialReference.wkid

        geo_json = json.dumps([polygon._json_struct_without_sr
                                   for polygon in polygons])

        return self._get_subfolder('areasAndLengths', AreasAndLengthsResult, 
                                    {'polygons': geo_json,
                                     'sr': sr
                                    })
        
    def Lengths(self, polylines, sr=None):
        """The lengths operation is performed on a geometry service resource.
           This operation calculates the lengths of each polyline specified in
           the input array"""

        if isinstance(polylines, geometry.Geometry):
            polylines = [polylines]

        if sr is None:
            sr = polylines[0].spatialReference.wkid

        geo_json = json.dumps([polyline._json_struct_without_sr
                                 for polyline in polylines])

        return self._get_subfolder('lengths', LengthsResult, 
                                    {'polylines': geo_json,
                                     'sr': sr
                                    })

class ExportImageResult(Result):
    """Represents the output of an Image Service exportImage call."""

class ImageService(Service):
    """An image service provides read-only access to a mosaicked collection of
       images or a raster data set."""
    __service_type__ = "ImageServer"
    def ExportImage(self, bbox=None, size=None, imageSR=None, bboxSR=None,
                    format=None, pixelType=None, noData=None, 
                    interpolation=None, compressionQuality=None, bandIds=None,
                    mosaicProperties=None, viewpointProperties=None):
        """The export operation is performed on a map service resource. The
           result of this operation is a map image resource. This resource
           provides information about the exported map image such as its URL,
           its width and height, extent and scale."""

        return self._get_subfolder('exportImage/', ExportImageResult, 
                                    {'bbox': bbox,
                                     'size': size,
                                     'imageSR': imageSR,
                                     'bboxSR': bboxSR,
                                     'format': format,
                                     'pixelType': pixelType,
                                     'noData': noData,
                                     'interpolation': interpolation,
                                     'compressionQuality': compressionQuality, 
                                     'bandIds': bandIds,
                                     'mosaicProperties': mosaicProperties,
                                     'viewpointProperties': viewpointProperties
                                    })

class NetworkLayer(Layer):
    """The network layer resource represents a single network layer in a
       network analysis service published by ArcGIS Server. It provides
       basic information about the network layer such as its name, type,
       and network classes. Additionally, depending on the layer type, it
       provides different pieces of information as detailed in the
       examples."""
    @property
    def layerName(self):
        return self._json_struct['layerName']
    @property
    def layerType(self):
        return self._json_struct['layerType']
    @property
    def impedance(self):
        return self._json_struct['impedance']
    @property
    def useStartTime(self):
        return self._json_struct['useStartTime']
    @property
    def useTimeWindows(self):
        return self._json_struct['useTimeWindows']
    @property
    def preserveFirstStop(self):
        return self._json_struct['preserveFirstStop']
    @property
    def preserveLastStop(self):
        return self._json_struct['preserveLastStop']
    @property
    def restrictUTurns(self):
        return self._json_struct['restrictUTurns']
    @property
    def outputLineType(self):
        return self._json_struct['outputLineType']
    @property
    def useHierarchy(self):
        return self._json_struct['useHierarchy']
    @property
    def ignoreInvalidLocations(self):
        return self._json_struct['ignoreInvalidLocations']
    @property
    def restrictions(self):
        return self._json_struct['restrictions']
    @property
    def distanceUnits(self):
        return self._json_struct['distanceUnits']
    @property
    def useTimeAttribute(self):
        return self._json_struct['useTimeAttribute']
    @property
    def networkClasses(self):
        return self._json_struct['networkClasses']

class NetworkService(Service):
    """The network service resource represents a network analysis service
       published with ArcGIS Server. The resource provides information about
       the service such as the service description and the various network
       layers (route, closest facility and service area layers) contained in
       the network analysis service."""
    __service_type__ = "NAServer"
    @property
    def routeLayers(self):
        return [self._get_subfolder("%s/" % layer, NetworkLayer) for layer in 
                self._json_struct['routeLayers']]
    @property
    def serviceAreaLayers(self):
        return [self._get_subfolder("%s/" % layer, NetworkLayer) for layer in 
                self._json_struct['serviceAreaLayers']]
    @property
    def closestFacilityLayers(self):
        return [self._get_subfolder("%s/" % layer, NetworkLayer) for layer in 
                self._json_struct['closestFacilityLayers']]

class GeoDataVersion(RestURL):
    """The geodata version resource represents a single version in a geodata
       service published using ArcGIS Server. It provides basic information
       about the version such as its description, created and modified times,
       access type, as well as parent, children and ancestor versions."""
    @property
    def name(self):
        return self._json_struct['name']
    @property
    def description(self):
        return self._json_struct['description']
    @property
    def created(self):
        return self._json_struct['created']
    @property
    def modified(self):
        return self._json_struct['modified']
    @property
    def access(self):
        return self._json_struct['access']
    @property
    def parentVersion(self):
        return self._json_struct['parentVersion']
    @property
    def childVersions(self):
        return self._json_struct['childVersions']
    @property
    def ancestorVersions(self):
        return self._json_struct['ancestorVersions']

class GeoDataReplica(RestURL):
    """The geodata replica resource represents a single replica in a geodata
       service published using ArcGIS Server. It provides basic information
       about the replica such as its id, replica version, creation date, GUID,
       role, access type, and reconcile policy."""
    @property
    def name(self):
        return self._json_struct['name']
    @property
    def id(self):
        return self._json_struct['id']
    @property
    def replicaVersion(self):
        return self._json_struct['replicaVersion']
    @property
    def guid(self):
        return self._json_struct['guid']
    @property
    def role(self):
        return self._json_struct['role']
    @property
    def accessType(self):
        return self._json_struct['accessType']
    @property
    def myGenerationNumber(self):
        return self._json_struct['myGenerationNumber']
    @property
    def sibGenerationNumber(self):
        return self._json_struct['sibGenerationNumber']
    @property
    def sibMyGenerationNumber(self):
        return self._json_struct['sibMyGenerationNumber']
    @property
    def replicaState(self):
        return self._json_struct['replicaState']
    @property
    def sibConnectionString(self):
        return self._json_struct['sibConnectionString']
    @property
    def modelType(self):
        return self._json_struct['modelType']
    @property
    def singleGeneration(self):
        return self._json_struct['singleGeneration']
    @property
    def spatialRelation(self):
        return self._json_struct['spatialRelation']
    @property
    def queryGeometryType(self):
        return self._json_struct['queryGeometryType']
    @property
    def queryGeometry(self):
        return geometry.convert_from_json(self._json_struct['queryGeometry'])
    @property
    def transferRelatedObjects(self):
        return self._json_struct['transferRelatedObjects']
    @property
    def reconcilePolicy(self):
        return self._json_struct['reconcilePolicy']

class GeoDataService(Service):
    """The geodata service resource represents a geodata service that you have
       published with ArcGIS Server. The resource provides basic information
       associated with the geodata service such as the service description,
       its workspace type, default  working version, versions, and replicas."""
    __service_type__ = "GeoDataServer"
    @property
    def workspaceType(self):
        return self._json_struct['workspaceType']
    @property
    def defaultWorkingVersionName(self):
        return self._json_struct['defaultWorkingVersion']
    @property
    def defaultWorkingVersion(self):
        return self._get_subfolder("versions/%s/" % 
                                   self.defaultWorkingVersionName,
                                   GeoDataVersion)
    @property
    def versionnames(self):
        return self._json_struct['versions']
    @property
    def versions(self):
        return [self._get_subfolder("versions/%s/" % version, GeoDataVersion)
                for version in self.versionnames]
    @property
    def replicanames(self):
        return self._json_struct['replicas']
    @property
    def replicas(self):
        return [self._get_subfolder("replicas/%s/" % version, GeoDataReplica)
                for replica in self.replicanames]

class GlobeLayer(Layer):
    """The globe layer resource represents a single layer in a globe service
       published by ArcGIS Server. It provides basic information about the
       layer such as its ID, name, type, parent and sub-layers, fields, extent,
       data type, sampling mode, and extrusion type."""

class GlobeService(Service):
    """The globe service resource represents a globe service published with
       ArcGIS Server. The resource provides information about the service such
       as the service description and the various layers contained in the
       published globe document."""
    __service_type__ = "GlobeServer"
    @property
    def layernames(self):
        """Return a list of the names of this globe service's layers"""
        return [layer['name'] for layer in self._json_struct['layers']]
    @property
    def layers(self):
        """Return a list of this globe service's layer objects"""
        return [self._get_subfolder("%s/" % layer['id'], GlobeLayer)
                for layer in self._json_struct['layers']]

# Have to create mapping at the end for Folders, there are no forward 
# declarations in Python
Folder._service_type_mapping = {
    'MapServer': MapService,
    'GeocodeServer': GeocodeService,
    'GPServer': GPService,
    'GeometryServer': GeometryService,
    'ImageServer': ImageService,
    'NAServer': NetworkService,
    'GeoDataServer': GeoDataService,
    'GlobeServer': GlobeService
}
