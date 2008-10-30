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

class ReSTURL(object):
    """Represents a top-level, base REST-style URL."""
    __cache_request__ = False # Fetch every time or just once?
    __urldata__ = Ellipsis
    __json_struct__ = Ellipsis
    __lazy_fetch__ = True
    def __init__(self, url):
        if isinstance(url, basestring):
            url = urlparse.urlsplit(url)
        # Ellipsis is used instead of None for the case where no data
        # is returned from the server due to an error condition -- we
        # need to differentiate between 'NULL' and 'UNDEFINED'
        self.__urldata__ = Ellipsis
        # Pull out query, whatever it may be
        urllist = list(url)
        query_dict = {}
        for k, v in cgi.parse_qs(urllist[3]).iteritems():
            query_dict[k] = v[0]
        # Set the f= flag to json (so we can interface with it)
        query_dict['f'] = 'json'
        # Hack our modified query string back into URL components
        urllist[3] = urllib.urlencode(query_dict)
        self._url = urllist
        if self.__lazy_fetch__ is False and self.__cache_request__ is True:
            self._contents
    def __repr__(self):
        return "<%s(%r)>" % (self.__class__.__name__, self.url)
    def _get_subfolder(self, foldername, returntype, params={}):
        """Return an object of the requested type with the path relative
           to the current object's URL. Optionally, query parameters
           may be set."""
        newurl = urlparse.urljoin(self.url, foldername, False)
        # Add the key-value pairs sent in params to query string
        if params:
            url_tuple = urlparse.urlsplit(newurl)
            urllist = list(url_tuple)
            query_dict = cgi.parse_qs(urllist[3])
            for key, val in params.iteritems():
                # Lowercase bool string
                if isinstance(val, bool):
                    query_dict[key] = str(val).lower()
                # Special case: convert an envelope to .bbox in the bb
                # parameter
                elif key == 'bbox' and isinstance(val, geometry.Envelope):
                    query_dict[key] = val.bbox
                # Ignore null values, coerce strings
                elif val is not None:
                    query_dict[key] = str(val)
            urllist[3] = urllib.urlencode(query_dict)
            newurl = urllist
        # Instantiate new ReSTURL or subclass
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
           for non-lazy fetching this is accessed in the object constructor."""
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
class Folder(ReSTURL):
    """Represents a folder path on an ArcGIS ReST server."""
    __cache_request__  = True
    # Conversion table from type string to class instance.
    _service_type_mapping = None
    @property
    def _foldernames(self):
        "Returns a list of folder names available from this folder."
        return [folder.split('/')[-1] for folder 
                    in self._json_struct.get('folders', [])]
    @property
    def folders(self):
        "Returns a list of Folder objects available in this folder."
        return [self._get_subfolder(fn, Folder) for fn in self._foldernames]
    @property
    def _servicenames(self):
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
        if not self._url[2].endswith('/'):
            self._url[2] += '/'
        return ReSTURL.url.__get__(self)
    def __getattr__(self, attr):
        return self[attr]
    def __getitem__(self, attr):
        # If it's a folder, easy:
        if attr in self._foldernames:
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

class Service(ReSTURL):
    """Represents an ArcGIS ReST service. This is an abstract base -- services
       derive from this."""
    __cache_request__ = False
    def __init__(self, url):
        super(Service, self).__init__(url)

class ServerError(Exception):
    """Exception for server-side error responses"""
    pass

class Result(ReSTURL):
    """Abstract class representing the result of an operation performed on a
       ReST service"""
    __cache_request__ = True # Only request the URL once
    __lazy_fetch__ = False # Force-fetch immediately
    def __init__(self, url):
        super(Result, self).__init__(url)
        if 'error' in self._json_struct:
            raise ServerError("ERROR %i: %s <%s>" % 
                               (self._json_struct['error']['code'], 
                                self._json_struct['error']['message'],
                                self.url))

# Service implementations -- mostly simple conversion wrappers for the
# functionality handled up above, wrapper types for results, etc.

class MapService(Service):
    """Map services offer access to map and layer content. Map services can
       either be cached or dynamic. A map service that fulfills requests with
       pre-created tiles from a cache instead of dynamically rendering part of
       the map is called a cached map service. A dynamic map service requires
       the server to render the map each time a request comes in. Map services
       using a tile cache can significantly improve performance while
       delivering maps, while dynamic map services offer more flexibility."""
    @property
    def MapServer(self):
        return self
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
    def Identify(self, geometry, sr=None, layers=None, tolerance=1, 
                 mapExtent=None, imageDisplay=None, returnGeometry=True):
        """The identify operation is performed on a map service resource. The
           result of this operation is an identify results resource. Each
           identified result includes its name, layer ID, layer name, geometry
           and geometry type, and other attributes of that result as name-value
           pairs."""
        assert hasattr(geometry, '__geometry_type__'), "Invalid geometry"
        gt = geometry.__geometry_type__
        return self._get_subfolder('identify/', Result,
                                                {'geometry': geometry,
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
           includes  its value, feature ID, field name,?layer ID, layer name,
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
        return self._get_subfolder('generateKml/', Result, {'docName': docName, 
                                                            'layers': layers,
                                                            'layerOptions':
                                                                layerOptions})

class FindAddressCandidatesResult(Result):
    """Represents the result from a Geocode operation"""
    @property
    def candidates(self):
        def cditer():
            for candidate in self._json_struct['candidates']:
                newcandidate = candidate.copy()
                newcandidate['location'] = \
                    geometry.convert_from_json(newcandidate['location'])
                yield newcandidate
        return list(cditer())

class ReverseGeocodeResult(Result):
    """Represents the result from a reverse geocode operation"""
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
    @property
    def GeocodeServer(self):
        return self
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
    pass

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
    @property
    def GPServer(self):
        return self

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
    @property
    def GeometryServer(self):
        return self

    def Project(self, geometries, outSR, inSR=None):
        """The project operation is performed on a geometry service resource.
           The result of this operation is an array of projected geometries.
           This resource projects an array of input geometries from an input
           spatial reference to an output spatial reference."""

        if isinstance(geometries, geometry.Geometry):
            geometries = [geometries]

        if isinstance(inSR, geometry.SpatialReference):
            inSR = inSR.wkid
        elif inSR is None:
            inSR = geometries[0].spatialReference.wkid

        if isinstance(outSR, geometry.SpatialReference):
            outSR = outSR.wkid

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

        if isinstance(sr, geometry.SpatialReference):
            sr = sr.wkid
        elif sr is None:
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

        if isinstance(inSR, geometry.SpatialReference):
            inSR = inSR.wkid
        elif inSR is None:
            inSR = geometries[0].spatialReference.wkid

        if isinstance(outSR, geometry.SpatialReference):
            outSR = outSR.wkid
        elif outSR is None:
            outSR = geometries[0].spatialReference.wkid

        if isinstance(bufferSR, geometry.SpatialReference):
            bufferSR = bufferSR.wkid
        elif bufferSR is None:
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

        if isinstance(sr, geometry.SpatialReference):
            sr = sr.wkid
        elif sr is None:
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

        if isinstance(sr, geometry.SpatialReference):
            sr = sr.wkid
        elif sr is None:
            sr = polylines[0].spatialReference.wkid

        geo_json = json.dumps([polyline._json_struct_without_sr
                                 for polyline in polylines])

        return self._get_subfolder('lengths', LengthsResult, 
                                    {'polylines': geo_json,
                                     'sr': sr
                                    })

class ImageService(Service):
    """An image service provides read-only access to a mosaicked collection of
       images or a raster data set."""
    @property
    def ImageServer(self):
        return self
    def ExportImage(self):
        """The export operation is performed on a map service resource. The
           result of this operation is a map image resource. This resource
           provides information about the exported map image such as its URL,
           its width and height, extent and scale."""
        pass

class NetworkService(Service):
    """The network service resource represents a network analysis service
       published with ArcGIS Server. The resource provides information about
       the service such as the service description and the various network
       layers (route, closest facility and service area layers) contained in
       the network analysis service."""
    @property
    def NAServer(self):
        return self
    class NetworkLayer(Folder):
        """The network layer resource represents a single network layer in a
           network analysis service published by ArcGIS Server. It provides
           basic information about the network layer such as its name, type,
           and network classes. Additionally, depending on the layer type, it
           provides different pieces of information as detailed in the
           examples."""
        pass

class GeoDataService(Service):
    """The geodata service resource represents a geodata service that you have
       published with ArcGIS Server. The resource provides basic information
       associated with the geodata service such as the service description,
       its workspace type, default  working version, versions, and replicas."""
    @property
    def GeoDataServer(self):
        return self

class GlobeService(Service):
    """The globe service resource represents a globe service published with
       ArcGIS Server. The resource provides information about the service such
       as the service description and the various layers contained in the
       published globe document."""
    @property
    def GlobeServer(self):
        return self

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
