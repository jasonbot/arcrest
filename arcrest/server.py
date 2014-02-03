# coding: utf-8
"""The ArcGIS Server REST API, short for Representational State Transfer, 
   provides a simple, open Web interface to services hosted by ArcGIS Server.
   All resources and operations exposed by the REST API are accessible through
   a hierarchy of endpoints or Uniform Resource Locators (URLs) for each GIS 
   service published with ArcGIS Server."""

import cgi
import json
import mimetypes
import os
import re
import uuid

from . import compat
from . import geometry
from . import gptypes
from . import utils

#: User agent to report when making requests
USER_AGENT = "Mozilla/4.0 (arcrest)"

#: Magic parameter name for propagating REFERER
REQUEST_REFERER_MAGIC_NAME = "HTTPREFERERTOKEN"

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
    __headers__ = Ellipsis     # Response headers
    __has_json__ = True        # Parse the data as a json struct? Set to
                               # false for binary data, html, etc.
    __token__ = None           # For token-based auth
    __lazy_fetch__ = True      # Fetch when constructed, or later on?
    __parent_type__ = None     # For automatically generated parent URLs
    __post__ = False           # Move query string to POST
    _parent = None
    _referer = None

    _pwdmgr = compat.urllib2.HTTPPasswordMgrWithDefaultRealm()
    _cookiejar = compat.cookielib.CookieJar()
    _basic_handler  = compat.urllib2.HTTPBasicAuthHandler(_pwdmgr)
    _digest_handler = compat.urllib2.HTTPDigestAuthHandler(_pwdmgr)
    _cookie_handler = compat.urllib2.HTTPCookieProcessor(_cookiejar)
    _opener = compat.urllib2.build_opener(_basic_handler,
                                   _digest_handler,
                                   _cookie_handler)
    compat.urllib2.install_opener(_opener)

    def __init__(self, url, file_data=None):
        # Expects a compat.urlsplitted list as the url, but accepts a
        # string because that is easier/makes more sense everywhere.
        if isinstance(url, basestring):
            url = compat.urlsplit(url)
        # Ellipsis is used instead of None for the case where no data
        # is returned from the server due to an error condition -- we
        # need to differentiate between 'NULL' and 'UNDEFINED'
        self.__urldata__ = Ellipsis
        # Pull out query, whatever it may be
        urllist = list(url)
        query_dict = {}
        # parse_qs returns a dict, but every value is a list (it assumes
        # that keys can be set multiple times like ?a=1&a=2 -- this flexibility
        # is probably useful somewhere, but not here). Pull out the first
        # element of every list so when we convert back to a query string
        # it doesn't enclose all values in []
        for k, v in cgi.parse_qs(urllist[3]).iteritems():
            query_dict[k] = v[0]
            if k.lower() == 'token':
                self.__token__ = v[0]
            elif k == REQUEST_REFERER_MAGIC_NAME:
                self._referer = v[0]
                del query_dict[REQUEST_REFERER_MAGIC_NAME]
        # Set the f= flag to json (so we can interface with it)
        if self.__has_json__ is True:
            query_dict['f'] = 'json'
        if self.__token__ is not None:
            query_dict['token'] = self.__token__
        # Hack our modified query string back into URL components
        urllist[3] = compat.urlencode(query_dict)
        self._url = urllist
        # Finally, set any file data parameters' data to local store.
        # file_data is expected to be a dictionary of name/filehandle
        # pairs if defined. And if there are any files, fetching will
        # automatically become a forced multipart upload. Also, force
        # keeping the results around; uploading data multiple times
        # is probably NEVER what anyone wants to do and file handles
        # can be exhausted. 
        self._file_data = file_data
        if file_data:
            self.__cache_request__ = True
        # Nonlazy: force a fetch
        if self.__lazy_fetch__ is False and self.__cache_request__ is True:
            self._contents
    def __repr__(self):
        url = self.url
        if len(url) > 100:
            url = url[:97] + "..."
        return "<%s(%r)>" % (self.__class__.__name__, url)
    def _get_subfolder(self, foldername, returntype,
                       params=None, file_data=None):
        """Return an object of the requested type with the path relative
           to the current object's URL. Optionally, query parameters
           may be set."""
        newurl = compat.urljoin(self.url, compat.quote(foldername), False)

        params = params or {}
        file_data = file_data or {}

        # Add the key-value pairs sent in params to query string if they
        # are so defined.
        query_dict = {}
        url_tuple = compat.urlsplit(newurl)
        urllist = list(url_tuple)

        if params:
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
                # Another special case: strings can't be quoted/escaped at the
                # top level
                elif isinstance(val, gptypes.GPString):
                    query_dict[key] = val.value
                # Just use the wkid of SpatialReferences
                elif isinstance(val, geometry.SpatialReference): 
                    query_dict[key] = val.wkid
                # If it's a list, make it a comma-separated string
                elif isinstance(val, (list, tuple, set)):
                    val = ",".join([str(v.id) 
                                    if isinstance(v, Layer)
                                    else str(v) for v in val])
                # If it's a dictionary, dump as JSON
                elif isinstance(val, dict):
                    val = json.dumps(val)
                # Ignore null values, and coerce string values (hopefully
                # everything sent in to a query has a sane __str__)
                elif val is not None:
                    query_dict[key] = str(val)
        if self.__token__ is not None:
            query_dict['token'] = self.__token__
        query_dict[REQUEST_REFERER_MAGIC_NAME] = self._referer or self.url
        # Replace URL query component with newly altered component
        urllist[3] = compat.urlencode(query_dict)
        newurl = urllist
        # Instantiate new RestURL or subclass
        rt = returntype(newurl, file_data)
        # Remind the resource where it came from
        try:
            rt.parent = self
        except:
            rt._parent = self
        return rt
    def _clear_cache(self):
        self.__json_struct__ = Ellipsis
        self.__urldata__ = Ellipsis
    @property
    def url(self):
        """The URL as a string of the resource."""
        urlparts = self._url
        if self.__post__:
            urlparts = list(urlparts)
            urlparts[3] = '' # Clear out query string on POST
            if self.__token__ is not None: # But not the token
                urlparts[3] = compat.urlencode({'token': self.__token__})
        return compat.urlunsplit(urlparts)
    @property
    def query(self):
        return self._url[3]
    @property
    def _headers(self):
        """The request headers as a dictionary. If contents are not lazy, will
           do one force fetch (non-cached) first."""
        if self.__headers__ is Ellipsis:
            self._contents
        return self.__headers__
    @property
    def _contents(self):
        """The raw contents of the URL as fetched, this is done lazily.
           For non-lazy fetching this is accessed in the object constructor."""
        if self.__urldata__ is Ellipsis or self.__cache_request__ is False:
            if self._file_data:
                # Special-case: do a multipart upload if there's file data
                self.__post__ = True
                boundary = "-"*12+str(uuid.uuid4())+"$"
                multipart_data = ''
                for k, v in cgi.parse_qs(self.query).iteritems():
                    if not isinstance(v, list):
                        v = [v]
                    for val in v:
                        multipart_data += boundary + "\r\n"
                        multipart_data += ('Content-Disposition: form-data; '
                                           'name="%s"\r\n\r\n' % k)
                        multipart_data += val + "\r\n"
                for k, v in self._file_data.iteritems():
                    fn = os.path.basename(getattr(v, 'name', 'file'))
                    ct = (mimetypes.guess_type(fn) 
                            or ("application/octet-stream",))[0]
                    multipart_data += boundary + "\r\n"
                    multipart_data += ('Content-Disposition: form-data; '
                                       'name="%s"; filename="%s"\r\n'
                                       'Content-Type:%s\r\n\r\n' % 
                                            (k, fn, ct))
                    multipart_data += v.read() + "\r\n"
                multipart_data += boundary + "--\r\n\r\n"
                req_dict = {'User-Agent' : USER_AGENT,
                            'Content-Type': 
                                'multipart/form-data; boundary='+boundary[2:],
                            'Content-Length': str(len(multipart_data))
                            }
                if self._referer:
                    req_dict['Referer'] = self._referer
                request = compat.urllib2.Request(self.url,
                                          multipart_data,
                                          req_dict)
            else:
                req_dict = {'User-Agent' : USER_AGENT}
                if self._referer:
                    req_dict['Referer'] = self._referer
                request = compat.urllib2.Request(self.url, self.query 
                                                        if self.__post__
                                                        else None,
                                           req_dict)
            handle = compat.urllib2.urlopen(request)
            # Handle the special case of a redirect (only follow once) --
            # Note that only the first 3 components (protocol, hostname, path)
            # are altered as component 4 is the query string, which can get
            # clobbered by the server.
            fetched_url = list(compat.urlsplit(handle.url)[:3])
            if fetched_url != list(self._url[:3]):
                self._url[:3] = fetched_url
                return self._contents
            # No redirect, proceed as usual.
            self.__headers__ = handle.headers.headers
            self.__urldata__ = handle.read()
        data = self.__urldata__
        if self.__cache_request__ is False:
            self.__urldata__ = Ellipsis
        return data
    @property
    def _json_struct(self):
        """The json data structure in the URL contents, it will cache this
           if it makes sense so it doesn't parse over and over."""
        if self.__has_json__:
            if self.__cache_request__:
                if self.__json_struct__ is Ellipsis:
                    if self._contents is not Ellipsis:
                        self.__json_struct__ = json.loads(self._contents
                                                              .strip() or '{}')
                    else:
                        return {}
                return self.__json_struct__
            else:
                return json.loads(self._contents)
        else:
            # Return an empty dict for things so they don't have to special
            # case against a None value or anything
            return {}
    @property
    def parent(self):
        "Get this object's parent"
        if self._parent:
            return self._parent
        # auto-compute parent if needed
        elif getattr(self, '__parent_type__', None):
            return self._get_subfolder('..' if self._url[2].endswith('/')
                                            else '.', self.__parent_type__)
        else:
            raise AttributeError("%r has no parent attribute" % type(self))
    @parent.setter
    def parent(self, val):
        self._parent = val

# For AGO-style authentication
class AGOLoginToken(RestURL):
    """Used by Catalog is authentication method is set to """
    __post__ = True
    __cache_request__ = True
    __lazy_fetch__ = False
    __has_json__ = False
    def __init__(self, origin_url, username, password):
        if username is not None and password is not None:
            self._pwdmgr.add_password(None,
                                      origin_url,
                                      username,
                                      password)


# For token-based authentication
class GenerateToken(RestURL):
    """Used by the Admin and Catalog class if authentication method is set to
       AUTH_TOKEN. Contains additional workarounds to discover the
       generateToken verb's URL from scraping HTML."""
    __post__ = True
    __cache_request__ = True
    __lazy_fetch__ = False
    def __init__(self, origin_url, username, password, expiration=60,
                 html_login=True):
        if username is not None and password is not None:
            self._pwdmgr.add_password(None,
                                      origin_url,
                                      username,
                                      password)
        self._html_login = html_login
        self._expiration = expiration
        url1 = compat.urljoin(origin_url, '../../tokens/generateToken', False)
        url2 = compat.urljoin(origin_url, '../tokens/generateToken', False)
        url3 = compat.urljoin(origin_url, './generateToken', False)
        url4 = compat.urljoin(origin_url, '/admin/generateToken', False)
        url5 = compat.urljoin(origin_url, '/generateToken', False)
        self._referer = url1
        for url in (url1, url2, url3, url4, url5):
            try:
                self._referer = url
                url_tuple = compat.urlsplit(url)
                urllist = list(url_tuple)
                query_dict = dict((k, v[0]) for k, v in 
                                  cgi.parse_qs(urllist[3]).iteritems())
                query_dict['username'] = username
                query_dict['password'] = password
                self._username = username
                self._password = password
                query_dict['expiration'] = str(self._expiration)
                query_dict['client'] = 'requestip'
                urllist[3] = compat.urlencode(query_dict)
                url = compat.urlunsplit(urllist)
                super(GenerateToken, self).__init__(url)
                self._json_struct['token']
                return
            except compat.urllib2.HTTPError:
                pass
            except KeyError:
                pass
        raise compat.urllib2.HTTPError(origin_url, 401, "Could not create token using URL {}"
                                .format(origin_url), None, None)
    @property
    def token(self):
        return self._json_struct['token']
    @property
    def _contents(self):
        try:
            return super(GenerateToken, self)._contents
        except compat.urllib2.HTTPError:
            if self._html_login:
                # Hack: scrape HTML version for path to /login,
                ##      then to wherever generateToken lives
                username, password = self._username, self._password
                payload ={'username': username,
                          'password': password,
                          'redirect': '/'}
                # Loop through what look like forms
                for formurl in re.findall('action="(.*?)"',
                                          compat.urllib2.urlopen(self._referer)
                                                                      .read()):
                    relurl = compat.urljoin(self._referer, formurl)
                    try:
                        html_request = compat.urllib2.Request(relurl,
                                                       compat.urlencode(
                                                                    payload),
                                                      {'Referer': 
                                                          self._referer})
                        html_response = compat.urllib2.urlopen(html_request).read()

                        # Seek out what looks like the redirect hidden form
                        # element in the HTML response
                        redirect_value = [re.findall('value="(.*?)"', input) 
                                          for input in 
                                            re.findall(
                                                '<input.*?name="redirect".*?>',
                                                html_response)]
                        if redirect_value:
                            redirect = redirect_value[0][0]
                        else:
                            redirect = None
                        # Loop through what look like links
                        for href in re.findall('(?:href|action)="(.*?)"',
                                               html_response):
                            if 'generatetoken' in href.lower():
                                try:
                                    gentokenurl = compat.urljoin(relurl,
                                                                   href)
                                    gentokenpayload = {'username': username,
                                                       'password': password,
                                                       'expiration': 
                                                            str(
                                                             self._expiration),
                                                       'client': 'requestip',
                                                       'f': 'json'}
                                    if redirect:
                                        gentokenpayload['redirect'] = redirect
                                    self.__urldata__ = compat.urlopen(
                                                          gentokenurl,
                                                          compat.urlencode(
                                                               gentokenpayload)
                                                          ).read()
                                    if self.__urldata__:
                                        return self.__urldata__
                                except compat.HTTPError:
                                    pass
                    except compat.urllib2.HTTPError:
                        pass
                return self.__urldata__ or '{}'
            else:
                raise

# On top of a URL, the ArcGIS Server folder structure lists subfolders
# and services.
class Folder(RestURL):
    """Represents a folder path on an ArcGIS REST server."""
    __cache_request__  = True
    # Conversion table from type string to class instance.
    _service_type_mapping = {}

    @classmethod
    def _register_service_type(cls, subclass):
        """Registers subclass handlers of various service-type-specific service
           implementations. Look for classes decorated with
           @Folder._register_service_type for hints on how this works."""
        if hasattr(subclass, '__service_type__'):
            cls._service_type_mapping[subclass.__service_type__] = subclass
            if subclass.__service_type__:
                setattr(subclass,
                        subclass.__service_type__,
                        property(lambda x: x))
        return subclass

    @property
    def __members__(self):
        return sorted(self.foldernames + 
                      list(self.servicenames) + 
                      self.clusternames)
    @property
    def foldernames(self):
        "Returns a list of folder names available from this folder."
        return [folder.strip('/').split('/')[-1] for folder 
                    in self._json_struct.get('folders', [])]
    @property
    def folders(self):
        "Returns a list of Folder objects available in this folder."
        return [self._get_subfolder(fn+'/', Folder) for fn in self.foldernames]
    @property
    def clusternames(self):
        "Returns a list of cluster names available from this folder."
        return [cluster.strip('/').split('/')[-1] for cluster 
                    in self._json_struct.get('clusters', [])]
    @property
    def clusters(self):
        "Returns a list of Folder objects available in this folder."
        return [self._get_subfolder(fn+'/', Folder) for fn in self.clusternames]
    @property
    def servicenames(self):
        "Give the list of services available in this folder."
        return set([service['name'].rstrip('/').split('/')[-1] 
                        for service in self._json_struct.get('services', [])])
    @property
    def services(self):
        "Returns a list of Service objects available in this folder"
        return [self._get_subfolder("%s/%s/" % 
                (s['name'].rstrip('/').split('/')[-1], s['type']), 
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
        elif attr in self.clusternames:
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

    def __init__(self, url, username=None, password=None, token=None,
                 generate_token=False, expiration=60, ago_login=False):
        """If a username/password is provided, AUTH and AUTH_DIGEST
           authentication will be handled automatically. If using
           token based authentication, either
                1. Pass a token in the token argument
                2. Set generate_token to True for generateToken-style auth
                3. Set ago_login for ArcGIS online-style auth"""
        if username is not None and password is not None:
            self._pwdmgr.add_password(None,
                                      url,
                                      username,
                                      password)
        url_ = list(compat.urlsplit(url))
        if not url_[2].endswith('/'):
            url_[2] += "/"
        if token is not None:
            self.__token__ = token
        elif ago_login and generate_token:
            raise ValueError("Only one authentication method of ago_login or "
                             "generate_token may be set")
        elif ago_login:
            new_url = compat.urlunsplit(url_)
            agologin = AGOLoginToken(url, username, password)
            self.__token__ = agologin.token
        elif generate_token:
            new_url = compat.urlunsplit(url_)
            gentoken = GenerateToken(url, username, password, expiration)
            self._referer = gentoken._referer
            self.__token__ = gentoken.token
        super(Catalog, self).__init__(url_)
        # Basically a Folder, but do some really, really rudimentary sanity
        # checking (look for folders/services, make sure format is JSON) so we
        # can verify this URL behaves like a Folder -- catch errors early 
        # before any other manipulations go on.
        assert 'folders' in self._json_struct, "No folders in catalog root"
        assert 'services' in self._json_struct, "No services in catalog root"
    @property
    def currentVersion(self):
        return self._json_struct.get('currentVersion', 9.3)

# Definitions for classes calling/manipulating services

class Service(RestURL):
    """Represents an ArcGIS REST service. This is an abstract base -- services
       derive from this."""
    __cache_request__ = True
    __service_type__ = None
    __parent_type__ = Folder

    def __init__(self, url, file_data=None):
        if not isinstance(url, (tuple, list)):
            url_ = list(compat.urlsplit(url))
        else:
            url_ = url
        if not url_[2].endswith('/'):
            url_[2] += "/"
        super(Service, self).__init__(url_, file_data)
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

class ServerError(Exception):
    """Exception for server-side error responses"""

class Result(RestURL):
    """Abstract class representing the result of an operation performed on a
       REST service"""
    __cache_request__ = True # Only request the URL once
    __lazy_fetch__ = False   # Force-fetch immediately

class BinaryResult(Result):
    """Class representing the result of an operation perfomed on a service with
       some sort of opaque binary data, such as a PNG or KMZ. Contrast to a
       JsonResult, which has an immediately accessible data structure."""
    __has_json__ = False

    @property
    def data(self):
        """Return the raw data from this request"""
        return self._contents

    def save(self, outfile):
        """Save the image data to a file or file-like object"""
        if isinstance(outfile, basestring):
            outfile = open(outfile, 'wb')
        outfile.write(self._contents)

class JsonResult(Result):
    """Class representing a specialization to results that expect
       some sort of json data"""
    __has_json__ = True

    def __init__(self, url, file_data=None):
        super(JsonResult, self).__init__(url, file_data)
        js = self._json_struct
        if 'error' in js:
            detailstring = ", ".join(js['error'].get('details', []))
            if detailstring:
                detailstring = " -- " + detailstring
            raise ServerError("ERROR %r: %r%s <%s>" % 
                               (js['error']['code'], 
                                js['error']['message'] or 
                                    'Unspecified',
                                detailstring,
                                self.url))
        elif "status" in js:
            if js['status'] == "error":
                raise ServerError(''.join(
                    js.get('messages', 
                           [js.get('message', 
                               'Unspecified Error')])))

class JsonPostResult(JsonResult):
    """Class representing a specialization of a REST call which moves all
       parameters to the payload of a POST request instead of in the URL
       query string in a GET"""
    __post__ = True

    pass

class Layer(RestURL):
    """The base class for map and network layers"""
    __cache_request__ = True # Only request the URL once
    __lazy_fetch__ = False # Force-fetch immediately

# Service implementations -- mostly simple conversion wrappers for the
# functionality handled up above, wrapper types for results, etc.

class AttachmentData(BinaryResult):
    """Represents the binary attachment data associated with a layer"""
    __lazy_fetch__ = True

class AttachmentInfos(JsonResult):
    """The attachment infos resource returns information about attachments
       associated with a feature. This resource is available only if the layer
       has advertised that it has attachments. A layer has attachments if its
       hasAttachments property is true."""

    @property
    def attachments(self):
        for attachment in self._json_struct['attachmentInfos']:
            attachment_dict = attachment.copy()
            attachment_dict['attachment'] = \
                    self._get_subfolder("%i/" % attachment_dict['id'],
                                        AttachmentData)

class MapLayer(Layer):
    """The layer resource represents a single layer or standalone table in a
       map of a map service  published by ArcGIS Server. It provides basic
       information about the layer such as its name, type, parent and
       sub-layers, fields, min and max scales, extent, and copyright text."""

    def QueryLayer(self, text=None, Geometry=None, inSR=None, 
                   spatialRel='esriSpatialRelIntersects', where=None,
                   outFields=None, returnGeometry=None, outSR=None,
                   objectIds=None, time=None, maxAllowableOffset=None,
                   returnIdsOnly=None):
        """The query operation is performed on a layer resource. The result
           of this operation is a resultset resource. This resource provides
           information about query results including the values for the fields
           requested by the user. If you request geometry information, the
           geometry of each result is also returned in the resultset.

           B{Spatial Relation Options:}
             - esriSpatialRelIntersects
             - esriSpatialRelContains
             - esriSpatialRelCrosses
             - esriSpatialRelEnvelopeIntersects
             - esriSpatialRelIndexIntersects
             - esriSpatialRelOverlaps
             - esriSpatialRelTouches
             - esriSpatialRelWithin"""
        if not inSR:
            if Geometry:
                inSR = Geometry.spatialReference
        out = self._get_subfolder("./query", JsonResult, {
                                               'text': text,
                                               'geometry': geometry,
                                               'inSR': inSR,
                                               'spatialRel': spatialRel,
                                               'where': where,
                                               'outFields': outFields,
                                               'returnGeometry': 
                                                    returnGeometry,
                                               'outSR': outSR,
                                               'objectIds': objectIds,
                                               'time': 
                                                    utils.pythonvaluetotime(
                                                        time),
                                               'maxAllowableOffset':
                                                    maxAllowableOffset,
                                               'returnIdsOnly':
                                                    returnIdsOnly
                                                })
        return gptypes.GPFeatureRecordSetLayer.fromJson(out._json_struct)
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
        return geometry.fromJson(self._json_struct['extent'])
    @property
    def displayField(self):
        return self._json_struct['displayField']
    @property
    def fields(self):
        return self._json_struct['fields']
    @property
    def types(self):
        return self._json_struct.get('types', [])
    @property
    def relationships(self):
        return self._json_struct.get('relationships', [])
    @property
    def timeInfo(self):
        """Return the time info for this Map Service"""
        time_info = self._json_struct.get('timeInfo', {})
        if not time_info:
            return None
        time_info = time_info.copy()
        if 'timeExtent' in time_info:
            time_info['timeExtent'] = utils.timetopythonvalue(
                                                    time_info['timeExtent'])
        return time_info
    @property
    def hasAttachments(self):
        return self._json_struct.get('hasAttachments', False)
    @property
    def attachments(self):
        if not self.hasAttachments:
            return []
        return self._get_subfolder("attachments/", AttachmentInfos).attachments


class MapTile(BinaryResult):
    """Represents the map tile fetched from a map service."""

    pass

class ExportMapResult(JsonResult):
    """Represents the result of an Export Map operation performed on a Map
       Service."""

    @property
    def href(self):
        return self._json_struct['href']
    @property
    def width(self):
        return self._json_struct['width']
    @property
    def height(self):
        return self._json_struct['height']
    @property
    def extent(self):
        return geometry.fromJson(self._json_struct['extent'])
    @property
    def scale(self):
        return self._json_struct['scale']
    @property
    def data(self):
        if not hasattr(self, '_data'):
            self._data = compat.urllib2.urlopen(self.href).read()
        return self._data
    def save(self, outfile):
        """Save the image data to a file or file-like object"""
        if isinstance(outfile, basestring):
            outfile = open(outfile, 'wb')
        assert hasattr(outfile, 'write') and callable(outfile.write), \
            "Expect a file or file-like object with a .write() method"
        outfile.write(self.data)

class IdentifyOrFindResult(JsonResult):
    """Represents the result of a Find or Identify operation performed on a
       Map Service."""

    @property
    def results(self):
        def resiter():
            for result in self._json_struct['results']:
                if 'geometry' in result:
                    geom = geometry.fromJson(result['geometry'])
                else:
                    geom = geometry.NullGeometry()
                geom.attributes = result.get('attributes')
                for key in ('displayFieldName', 'value', 
                            'layerId', 'layerName'):
                    geom.attributes[key] = result[key]
                yield geom
        return gptypes.GPFeatureRecordSetLayer(list(resiter()),
                                               self.parent.spatialReference)

class ExportKMLResult(BinaryResult):
    """Represents the result of an Export KML operation performed on a Map
       Service."""

@Folder._register_service_type
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
                  format=None, layerDefs=None, layers=None, transparent=False,
                  time=None):
        """The export operation is performed on a map service resource. The
           result of this operation is a map image resource. This resource
           provides information about the exported map image such as its URL,
           its width and height, extent and scale."""
        return self._get_subfolder('export/', ExportMapResult, 
                                              {'bbox': bbox, 
                                               'size': size,
                                               'dpi': dpi,
                                               'imageSR': imageSR,
                                               'bboxSR': bboxSR,
                                               'format': format,
                                               'layerDefs': layerDefs,
                                               'layers': layers,
                                               'transparent': transparent,
                                               'time': 
                                                    utils.pythonvaluetotime(
                                                        time)
                                                })

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
        geo_json = json.dumps(Geometry._json_struct_without_sr)
        return self._get_subfolder('identify/', IdentifyOrFindResult,
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
        return self._get_subfolder('find/', IdentifyOrFindResult, 
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

           B{Layer Options:}
             - composite: (default) All layers as a single composite image.
                          Layers cannot be turned on and off in the client.
             - separateImage: Each layer as a separate image.
             - nonComposite: Vector layers as vectors and raster layers as
                             images."""
        return self._get_subfolder('generateKml/', GenerateKMLResult,
                                       {'docName': docName, 
                                        'layers': layers,
                                        'layerOptions': layerOptions})

    def tile(self, row, col, zoomlevel):
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
        return geometry.fromJson(
                                        self._json_struct['spatialReference'])
    @property
    def initialExtent(self):
        """This map's initial extent"""
        return geometry.fromJson(
                                        self._json_struct['initialExtent'])
    @property
    def fullExtent(self):
        """This map's full extent"""
        return geometry.fromJson(
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
    @property
    def tablenames(self):
        """Return a list of the names of this map's tables"""
        return [table['name'] for table in self._json_struct.get('tables', [])]
    @property
    def tables(self):
        """Return a list of this map's table objects"""
        return [self._get_subfolder("%s/" % table['id'], MapLayer)
                for table in self._json_struct.get('tables', [])]
    @property
    def timeInfo(self):
        """Return the time info for this Map Service"""
        time_info = self._json_struct.get('timeInfo', {})
        if not time_info:
            return None
        time_info = time_info.copy()
        if 'timeExtent' in time_info:
            time_info['timeExtent'] = utils.timetopythonvalue(
                                                    time_info['timeExtent'])
        return time_info
    @property
    def supportedImageFormatTypes(self):
        """Return a list of supported image formats for this Map Service"""
        return [x.strip() 
                  for x in 
                    self._json_struct['supportedImageFormatTypes'].split(',')]

class FindAddressCandidatesResult(JsonResult):
    """Represents the result from a geocode operation. The .candidates
       field holds a list of candidate addresses as python dicts; the
       ['location'] key in each is a geometry.Point for the location of the
       address."""

    @property
    def candidates(self):
        """A list of candidate addresses (as dictionaries) from a geocode
           operation"""
        # convert x['location'] to a point from a json point struct
        def cditer():
            for candidate in self._json_struct['candidates']:
                newcandidate = candidate.copy()
                newcandidate['location'] = \
                    geometry.fromJson(newcandidate['location'])
                yield newcandidate
        return list(cditer())

class ReverseGeocodeResult(JsonResult):
    """Represents the result from a reverse geocode operation -- the two
       interesting fields are .address, which is a dictionary with the
       fields of the candidate address, and .location, which is a
       geometry.Point which is the actual location of the address."""

    @property
    def address(self):
        return self._json_struct['address']
    @property
    def location(self):
        return geometry.fromJson(self._json_struct['location'])
    def __getitem__(self, attr):
        return self._json_struct['address'][attr]
    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError as e:
            raise AttributeError(str(e))

@Folder._register_service_type
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

    def FindAddressCandidates(self, outFields=[], outSR=None, **fields):
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
        if outSR:
            query['outSR'] = (outSR.wkid 
                                if isinstance(outSR, geometry.SpatialReference)
                                else outSR)
        return self._get_subfolder('findAddressCandidates/', 
                                   FindAddressCandidatesResult, query)

    def ReverseGeocode(self, location, distance, outSR=None):
        """The reverseGeocode operation is performed on a geocode service 
           resource. The result of this operation is a reverse geocoded address
           resource. This resource provides information about all the address
           fields pertaining to the reverse geocoded address as well as its
           exact location."""
        if outSR:
            outSR = (outSR.wkid 
                       if isinstance(outSR, geometry.SpatialReference)
                       else outSR)

        return self._get_subfolder('reverseGeocode/', ReverseGeocodeResult, 
                                                      {'location': location, 
                                                       'distance': distance,
                                                       'outSR': outSR})

class GPMessage(object):
    """Represents a message generated during the execution of a
        geoprocessing task. It includes information such as when the
        processing started, what parameter values are being used, the task
        progress, warnings of potential problems and errors. It is composed
        of a message type and description."""
    __message_types = set(["esriJobMessageTypeInformative",
                           "esriJobMessageTypeWarning",
                           "esriJobMessageTypeError",
                           "esriJobMessageTypeEmpty",
                           "esriJobMessageTypeAbort"])
    def __init__(self, description, type=None):
        if isinstance(description, dict):
            description, type = (description.get('description'),
                                 description.get('type'))
        elif isinstance(description, (tuple, list)):
            description, type = description[0], description[1]
        self.description, self.type = description, type
    def __repr__(self):
        return "<{0:<11}: {1}>".format(self.type[len('esriJobMessageType'):],
                                       self.description)
    def __str__(self):
        return self.description

@Folder._register_service_type
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
        return [task for task in self._json_struct['tasks']]
    @property
    def tasks(self):
        return [self._get_subfolder(taskname+'/', GPTask)
                for taskname in self.tasknames]
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
    def __getitem__(self, attr):
        for task in self.tasknames:
            if task == attr:
                return self._get_subfolder(task+'/', GPTask)
        raise KeyError("No task named %r found" % attr)
    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            return Service.__getattr__(self, attr)

class GPJobStatus(RestURL):
    """This class represents the current/pending status of an asynchronous
       GP Task. Please refer to the GPJob class for more information."""
    __cache_request__ = False
    _results = None

    # All the job status codes we are aware of (from Java API)
    job_statuses = set([
        'esriJobCancelled',
        'esriJobCancelling',
        'esriJobDeleted',
        'esriJobDeleting',
        'esriJobExecuting',
        'esriJobFailed',
        'esriJobNew',
        'esriJobSubmitted',
        'esriJobSucceeded',
        'esriJobTimedOut',
        'esriJobWaiting'])

    # If this is the status, self.running = True
    _still_running = set([
        'esriJobCancelling',
        'esriJobDeleting',
        'esriJobExecuting',
        'esriJobNew',
        'esriJobSubmitted',
        'esriJobWaiting'])

    # If this is the status, then throw an error
    _error_status = set([
        'esriJobCancelled',
        'esriJobDeleted',
        'esriJobFailed',
        'esriJobTimedOut',
    ])

    @property
    def _json_struct(self):
        js = RestURL._json_struct.__get__(self)
        if js['jobStatus'] not in self._still_running:
            self.__cache_request__ = True
            self.__json_struct__ = js
        return js
    @property
    def jobId(self):
        return self._json_struct['jobId']
    @property
    def jobStatus(self):
        return self._json_struct['jobStatus']
    @property
    def running(self):
        return self._json_struct['jobStatus'] in self._still_running
    @property
    def results(self):
        assert (not self.running), "Task is still executing."
        if self.jobStatus in self._error_status:
            raise ServerError("Error: job status %r" % self.jobStatus)
        if self._results is None:
            def item_iterator():
                for resref in self._json_struct['results'].itervalues():
                    rel = self._get_subfolder(resref['paramUrl'], RestURL)
                    result = rel._json_struct
                    #self.parent.parent.parameters
                    #datatype = gptypes.GPBaseType._gp_type_mapping.get(
                    #                                result['dataType'],None)
                    datatype = None
                    conversion = None
                    for param in self.parent.parent.parameters:
                        if param['name'] == result['paramName']:
                            datatype = param['datatype']
                    if datatype is None:
                        conversion = str
                    else:
                        conversion = datatype.fromJson
                    dt = result['paramName']
                    val = conversion(result['value'])
                    yield (dt, val)
            self._results = dict(item_iterator())
        return self._results
    @property
    def messages(self):
        "Return a list of messages returned from the server."
        return map(GPMessage, self._json_struct['messages'])
    def __getitem__(self, key):
        return self.__class__.results.__get__(self)[key]
    def __getattr__(self, attr):
        return self.__class__.results.__get__(self)[attr]

class GPJob(JsonResult):
    """The GP job resource represents a job submitted using the submit job
       operation. It provides basic information about the job such as the job
       ID, status and messages. Additionally, if the job has successfully
       completed, it provides information about the result parameters as well
       as input parameters."""

    _jobstatus = None
    def __init__(self, url, file_data=None):
        super(GPJob, self).__init__(url, file_data)
        self._jobstatus = self._get_subfolder('../jobs/%s/' % 
                                              self._json_struct['jobId'],
                                              GPJobStatus)
    @property
    def jobId(self):
        "Return the unique ID the server assigned this task"
        return self._jobstatus.jobId
    @property
    def jobStatus(self):
        return self._jobstatus.jobStatus
    @property
    def running(self):
        "A boolean (True: job completion pending; False: no longer executing)"
        return self._jobstatus.running
    @property
    def results(self):
        "Returns a dict of outputs from the GPTask execution."
        return self._jobstatus.results
    @property
    def messages(self):
        "Return a list of messages returned from the server."
        return self._jobstatus.messages
    def __getitem__(self, key):
        return self._jobstatus.results[key]
    def __getattr__(self, attr):
        return self._jobstatus.results[attr]

class GPExecutionResult(JsonResult):
    """The GPExecutionResult object represents the output of running a 
       synchronous GPTask."""
    _results = None
    @property
    def messages(self):
        "Return a list of messages returned from the server."
        return map(GPMessage, self._json_struct['messages'])
    @property
    def results(self):
        "Returns a dict of outputs from the GPTask execution."
        if self._results is None:
            results = self._json_struct['results']
            def result_iterator():
                for result in results:
                    datatype = None
                    conversion = None
                    for param in self.parent.parameters:
                        if param['name'] == result['paramName']:
                            datatype = param['datatype']
                    if datatype is None:
                        conversion = str
                    else:
                        conversion = datatype.fromJson
                    dt = result['paramName']
                    val = conversion(result['value'])
                    yield (dt, val)
            self._results = dict(res for res in result_iterator())
        return self._results
    @property
    def running(self):
        "For method compatibility with GPJob, always return false"
        return False
    def __getitem__(self, key):
        return self.__class__.results.__get__(self)[key]
    def __getattr__(self, attr):
        return self.__class__.results.__get__(self)[attr]

class GPTask(RestURL):
    """The GP task resource represents a single task in a GP service published
       using the ArcGIS Server. It provides basic information about the task
       including its name and display name. It also provides detailed 
       information about the various input and output parameters exposed by the
       task"""
    __parent_type__ = GPService
    __cache_request__ = True

    def __init__(self, url, file_data=None):
        # Need to force final slash
        if isinstance(url, basestring):
            url = list(compat.urlsplit(url))
        if not url[2].endswith('/'):
            url[2] += '/'
        super(GPTask, self).__init__(url, file_data)

    def __expandparamstodict(self, params, kw):
        self_parameters = self.parameters
        parametervalues = dict(zip((p['name'] for p in self_parameters),
                                    params))
        for kw, kwval in kw.iteritems():
            if kw in parametervalues:
                raise KeyError("Multiple definitions of parameter %r" % kw)
            parametervalues[kw] = kwval
        for param_to_convert in self_parameters:
            if param_to_convert['name'] in parametervalues:
                val = parametervalues[param_to_convert['name']]
                if val is None:
                    parametervalues[param_to_convert['name']] = ''
                elif not isinstance(val, param_to_convert['datatype']):
                    conversion = param_to_convert['datatype'](val)
                    parametervalues[param_to_convert['name']] = \
                        getattr(conversion, '_json_struct', conversion)
            elif param_to_convert['parameterType'] != 'esriGPParameterTypeDerived':
                parametervalues[param_to_convert['name']] = ''
        return parametervalues
    def Execute(self, *params, **kw):
        """Synchronously execute the specified GP task. Parameters are passed
           in either in order or as keywords."""
        fp = self.__expandparamstodict(params, kw)
        return self._get_subfolder('execute/', GPExecutionResult, fp)
    def SubmitJob(self, *params, **kw):
        """Asynchronously execute the specified GP task. This will return a 
           Geoprocessing Job object. Parameters are passed in either in order
           or as keywords."""
        fp = self.__expandparamstodict(params, kw)
        return self._get_subfolder('submitJob/', GPJob, fp)._jobstatus
    def __call__(self, *params, **kw):
        """Either submit a job, if the task is synchronous, or execute it,
           if it is synchronous. Note that the GPJob and GPExecutionResult
           objects both have the C{.running} property that will return True
           while the job is running in the case of a job, and always return
           False with the case of the execution result. This can be used to
           treat both types of execution as the same in your code; with the
           idiom
           
              >>> result = task(Param_1, Param_2, Param_3, ...)
              >>> while result.running:
              ...     time.sleep(0.125)
              >>> print result.Output1
        """
        if self.synchronous:
            return self.Execute(*params, **kw)
        else:
            return self.SubmitJob(*params, **kw)
    @property
    def name(self):
        return self._json_struct.get('name', '')
    @property
    def displayName(self):
        return self._json_struct['displayName']
    @property
    def category(self):
        return self._json_struct['category']
    @property
    def helpUrl(self):
        return self._json_struct['helpUrl']
    @property
    def parameters(self):
        parameters = self._json_struct['parameters']
        for parameter in parameters:
            dt = parameter['dataType']
            parameter['datatype'] = \
                gptypes.GPBaseType._get_type_by_name(
                            dt)._from_json_def(parameter)
        return parameters
    @property
    def executionType(self):
        """Returns the execution type of this task."""
        return self.parent.executionType
    @property
    def synchronous(self):
        """Returns a boolean indicating whether this tasks runs synchronously
           (True) or asynchronously (False)."""
        return self.parent.synchronous



class GeometryResult(JsonResult):
    """Represents the output of a Project, Simplify or Buffer operation 
       performed by an ArcGIS REST API Geometry service."""

    @property
    def geometries(self):
        return [geometry.fromJson(geo) 
                for geo in self._json_struct['geometries']]

class LengthsResult(JsonResult):
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

class LabelPointsResult(JsonResult):
    """Represents the output of a Label Points operation
       performed by an ArcGIS REST API Geometry service."""

    @property
    def labelPoints(self):
        """Label points for the provided polygon(s)."""
        return [geometry.fromJson(geo) 
                for geo in self._json_struct['labelPoints']]

@Folder._register_service_type
class GeometryService(Service):
    """A geometry service contains utility methods, which provide access to
       sophisticated and frequently used geometric operations. An ArcGIS Server
       Web site can only expose one geometry service with the static name
       "Geometry." Note that geometry input and output, where required, are
       always packaged as an array."""
    __service_type__ = "GeometryServer"

    def Project(self, geometries, inSR=None, outSR=None):
        """The project operation is performed on a geometry service resource.
           The result of this operation is an array of projected geometries.
           This resource projects an array of input geometries from an input
           spatial reference to an output spatial reference."""

        if isinstance(geometries, geometry.Geometry):
            geometries = [geometries]

        if inSR is None:
            inSR = geometries[0].spatialReference.wkid

        assert outSR, "Cannot project to an empty output projection."

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

        if isinstance(distances, (list, tuple)):
            distances=",".join(str(distance) for distance in distances)

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

    def AreasAndLengths(self, polygons, sr=None, lengthUnit=None, 
                        areaUnit=None):
        """The areasAndLengths operation is performed on a geometry service
           resource. This operation calculates areas and perimeter lengths for
           each polygon specified in the input array."""

        if isinstance(polygons, geometry.Geometry):
            polygons = [polygons]

        assert all(isinstance(polygon, geometry.Polygon)
                   for polygon in polygons), "Must use polygons"

        if sr is None:
            sr = polygons[0].spatialReference.wkid

        geo_json = json.dumps([polygon._json_struct_without_sr
                                   for polygon in polygons])

        return self._get_subfolder('areasAndLengths', AreasAndLengthsResult, 
                                    {'polygons': geo_json,
                                     'sr': sr,
                                     'lengthUnit': lengthUnit,
                                     'areaUnit': areaUnit
                                    })
        
    def Lengths(self, polylines, sr=None, lengthUnit=None, geodesic=None):
        """The lengths operation is performed on a geometry service resource.
           This operation calculates the lengths of each polyline specified in
           the input array"""

        if isinstance(polylines, geometry.Geometry):
            polylines = [polylines]

        assert all(isinstance(polyline, geometry.Polyline)
                   for polyline in polylines), "Must use polylines"

        if sr is None:
            sr = polylines[0].spatialReference.wkid

        geo_json = json.dumps([polyline._json_struct_without_sr
                                 for polyline in polylines])

        if geodesic is not None:
            geodesic = bool(geodesic)

        return self._get_subfolder('lengths', LengthsResult, 
                                    {'polylines': geo_json,
                                     'sr': sr,
                                     'lengthUnit': lengthUnit,
                                     'geodesic': geodesic
                                    })

    def LabelPoints(self, polygons, sr):
        """The labelPoints operation is performed on a geometry service
           resource. This operation calculates an interior point for each
           polygon specified in the input array. These interior points can be
           used by clients for labeling the polygons."""
        if isinstance(polygons, geometry.Geometry):
            polygons = [polygons]

        assert all(isinstance(polygon, geometry.Polygon)
                   for polygon in polygons), "Must use polygons"

        if sr is None:
            sr = polygons[0].spatialReference.wkid

        geo_json = json.dumps([polygon._json_struct_without_sr
                                 for polygon in polygons])

        return self._get_subfolder('labelPoints', LabelPointsResult, 
                                    {'polygons': geo_json,
                                     'sr': sr
                                    })
    def ConvexHull(self, geometries=None, sr=None):
        """The convexHull operation is performed on a geometry service
           resource. It returns the convex hull of the input geometry. The
           input geometry can be a point, multipoint, polyline or polygon. The
           hull is typically a polygon but can also be a polyline or point in
           degenerate cases."""

        if isinstance(geometries, geometry.Geometry):
            geometries = [geometries]

        geometry_types = set([x.__geometry_type__ for x in geometries])
        assert len(geometry_types) == 1, "Too many geometry types"
        geo_json = json.dumps({'geometryType': list(geometry_types)[0],
                    'geometries': [geo._json_struct_without_sr
                                        for geo in geometries]
                    })

        if sr is None:
            sr = geometries[0].spatialReference.wkid

        return self._get_subfolder('convexHull', GeometryResult,
                                   {'geometries': geo_json, 'sr': sr})
    def Densify(self, geometries=None, sr=None, maxSegmentLength=None,
                geodesic=None, lengthUnit=None):
        """The densify operation is performed on a geometry service resource.
           This operation densifies geometries by plotting points between
           existing vertices."""

        if isinstance(geometries, geometry.Geometry):
            geometries = [geometries]

        geometry_types = set([x.__geometry_type__ for x in geometries])
        assert len(geometry_types) == 1, "Too many geometry types"
        geo_json = json.dumps({'geometryType': list(geometry_types)[0],
                    'geometries': [geo._json_struct_without_sr
                                        for geo in geometries]
                    })

        if sr is None:
            sr = geometries[0].spatialReference.wkid

        return self._get_subfolder('convexHull', GeometryResult,
                                   {'geometries': geo_json,
                                    'sr': sr,
                                    'maxSegmentLength': maxSegmentLength,
                                    'geodesic': geodesic,
                                    'lengthUnit': lengthUnit
                                    })
    def Distance(self, geometry1=None, geometry2=None, sr=None,
                 distanceUnit=None, geodesic=None):
        """The distance operation is performed on a geometry service resource.
           It reports the planar (projected space) / geodesic shortest distance
           between A and B. sr is a projected coordinate system. Distance is
           reported in the linear units specified by units or the units of sr
           if units is null."""

        if not sr:
            sr = (geometry1.spatialReference.wkid or
                  geometry2.spatialReference.wkid)
        geo_json_1 = json.dumps({'geometryType': geometry1.__geometry_type__,
                                 'geometry': geometry1._json_struct})
        geo_json_2 = json.dumps({'geometryType': geometry2.__geometry_type__,
                                 'geometry': geometry2._json_struct})
        folder = self._get_subfolder('distance', JsonResult,
                                   {'geometry1': geo_json_1,
                                    'geometry2': geo_json_2,
                                    'sr': sr,
                                    'distanceUnit': distanceUnit,
                                    'geodesic': geodesic,
                                    })
        return folder._json_struct['distance']
    def Generalize(self, geometries=None, sr=None, maxDeviation=None,
                   deviationUnit=None):
        """The generalize operation is performed on a geometry service
           resource. It returns generalized (Douglas-Poiker) versions of the
           input geometries."""

        if isinstance(geometries, geometry.Geometry):
            geometries = [geometries]

        geometry_types = set([x.__geometry_type__ for x in geometries])
        assert len(geometry_types) == 1, "Too many geometry types"
        geo_json = json.dumps({'geometryType': list(geometry_types)[0],
                    'geometries': [geo._json_struct_without_sr
                                        for geo in geometries]
                    })

        if sr is None:
            sr = geometries[0].spatialReference.wkid

        return self._get_subfolder('generalize', GeometryResult,
                                   {'geometries': geo_json,
                                    'sr': sr,
                                    'maxDeviation': maxDeviation,
                                    'deviationUnit': deviationUnit
                                    })
    def Offset(self, geometries=None, sr=None, offsetDistance=None,
               offsetUnit=None, offsetHow=None, bevelRatio=None):
        """The offset operation is performed on a geometry service resource.
           Offset constructs the offset of the given input geometries. If the
           offset parameter is positive the constructed offset will be on the
           right side of the geometry. (Left side offsets are constructed with
           negative parameters.) Tracing the geometry from it's first vertex to
           the last will give you a direction along the geometry. It is to the
           right and left perspective of this direction that the positive and
           negative parameters will dictate where the offset is contructed. In
           these terms it is simple to infer where the offset of even
           horizontal geometries will be constructed. The offsetHow parameter
           determines how outer corners between segments are handled. Rounded
           offset rounds the corner between extended offsets. Bevelled offset
           squares off the corner after a given ratio distance. Mitered offset
           attempts to allow extended offsets to naturally intersect, but if
           that intersection occurs too far from the corner, the corner is
           eventually bevelled off at a fixed distance."""

        if isinstance(geometries, geometry.Geometry):
            geometries = [geometries]

        geometry_types = set([x.__geometry_type__ for x in geometries])
        assert len(geometry_types) == 1, "Too many geometry types"
        geo_json = json.dumps({'geometryType': list(geometry_types)[0],
                    'geometries': [geo._json_struct_without_sr
                                        for geo in geometries]
                    })

        if sr is None:
            sr = geometries[0].spatialReference.wkid

        return self._get_subfolder('offset', GeometryResult,
                                   {'geometries': geo_json,
                                    'sr': sr,
                                    'offsetDistance': offsetUnit,
                                    'offsetUnit': offsetHow,
                                    'bevelRatio': bevelRatio
                                    })

    def TrimExtend(self, polylines=None, trimExtendTo=None, sr=None,
                   extendHow=None):
        """The trimExtend operation is performed on a geometry service
           resource. This operation trims / extends each polyline specified
           in the input array, using the user specified guide polylines. When
           trimming features, the part to the left of the oriented cutting line
           is preserved in the output and the other part is discarded. An empty
           polyline is added to the output array if the corresponding input
           polyline is neither cut nor extended."""

        if isinstance(polylines, geometry.Geometry):
            polylines = [polylines]

        assert all(isinstance(polyline, geometry.Polyline)
                   for polyline in polylines), "Must use polylines"

        if sr is None:
            sr = polylines[0].spatialReference.wkid

        geo_json = json.dumps([polyline._json_struct_without_sr
                                 for polyline in polylines])

        return self._get_subfolder('trimExtend', GeometryResult, 
                                    {'polylines': geo_json,
                                     'trimExtendTo': trimExtendTo,
                                     'extendHow': extendHow,
                                     'sr': sr
                                    })
    def AutoComplete(self, polygons=None, polylines=None, sr=None):
        """The Auto Complete operation is performed on a geometry service
           resource. The AutoComplete operation simplifies the process of
           constructing new polygons that are adjacent to other polygons. It
           constructs polygons that fill in the gaps between existing polygons
           and a set of polylines."""        
        raise NotImplementedError()
    def Cut(self, cutter=None, target=None, sr=None):
        """The cut operation is performed on a geometry service resource. This
           operation splits the input polyline or polygon where it crosses a
           cutting polyline"""
        raise NotImplementedError()
    def Difference(self, geometries=None, geometry=None, sr=None):
        """The difference operation is performed on a geometry service
           resource. This operation constructs the set-theoretic difference
           between an array of geometries and another geometry."""
        raise NotImplementedError()
    def Intersect(self, geometries=None, geometry=None, sr=None):
        """The intersect operation is performed on a geometry service
           resource. This operation constructs the set-theoretic intersection
           between an array of geometries and another geometry"""
        raise NotImplementedError()
    def Reshape(self, target=None, reshaper=None, sr=None):
        """The reshape operation is performed on a geometry service resource.
           It reshapes a polyline or a part of a polygon using a reshaping
           line."""
        raise NotImplementedError()
    def Union(self, geometries=None, sr=None):
        """The union operation is performed on a geometry service resource.
           This operation constructs the set-theoretic union of the geometries
           in the input array. All inputs must be of the same type."""
        raise NotImplementedError()

class ExportImageResult(JsonResult):
    """Represents the output of an Image Service exportImage call."""

    @property
    def href(self):
        return self._json_struct['href']
    @property
    def width(self):
        return self._json_struct['width']
    @property
    def height(self):
        return self._json_struct['height']
    @property
    def extent(self):
        return geometry.fromJson(self._json_struct['extent'])
    def save(self, outfile):
        """Save the image data to a file or file-like object"""
        if isinstance(outfile, basestring):
            outfile = open(outfile, 'wb')
        outfile.write(compat.urllib2.urlopen(self.href).read())

@Folder._register_service_type
class ImageService(Service):
    """An image service provides read-only access to a mosaicked collection of
       images or a raster data set."""
    __service_type__ = "ImageServer"

    def ExportImage(self, bbox=None, size=None, imageSR=None, bboxSR=None,
                    format=None, pixelType=None, noData=None, 
                    interpolation=None, compressionQuality=None, bandIds=None,
                    mosaicProperties=None, viewpointProperties=None,
                    mosaicRule=None, renderingRule=None):
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
                                     'viewpointProperties': viewpointProperties,
                                     'mosaicRule': mosaicRule,
                                     'renderingRule': renderingRule
                                    })

@Folder._register_service_type
class NetworkService(Service):
    """The network service resource represents a network analysis service
       published with ArcGIS Server. The resource provides information about
       the service such as the service description and the various network
       layers (route, closest facility and service area layers) contained in
       the network analysis service."""
    __service_type__ = "NAServer"

    @property
    def routeLayers(self):
        return [self._get_subfolder("%s/" % layer, RouteNetworkLayer)
                for layer in self._json_struct['routeLayers']]
    @property
    def serviceAreaLayers(self):
        return [self._get_subfolder("%s/" % layer, NetworkLayer)
                for layer in self._json_struct['serviceAreaLayers']]
    @property
    def closestFacilityLayers(self):
        return [self._get_subfolder("%s/" % layer, NetworkLayer)
                for layer in self._json_struct['closestFacilityLayers']]
    def __getitem__(self, attr):
        layer_names = set(self._json_struct['routeLayers'] +
                          self._json_struct['serviceAreaLayers'] +
                          self._json_struct['closestFacilityLayers'])
        if attr in layer_names:
            self._get_subfolder("%s/" % attr, NetworkLayer)
        raise KeyError("No attribute %r found" % attr)
    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError as e:
            raise AttributeError(str(e))

class DirectionResult(object):
    """Represents an individual directions entry in a Network Solve operation
       result."""
    def __init__(self, direction):
        self._json_struct = direction
    @property
    def routeId(self):
        return self._json_struct["routeId"]
    @property
    def routeName(self):
        return self._json_struct["routeName"]
    @property
    def summary(self):
        return self._json_struct["summary"]
    @property
    def features(self):
        return gptypes.GPFeatureRecordSetLayer.fromJson(self._json_struct)

class NetworkSolveResult(JsonResult):
    """Represents a solve operation's output performed on a Route Network
       layer."""

    @property
    def directions(self):
        return [DirectionResult(direction)
                for direction in self._json_struct['directions']]
    @property
    def routes(self):
        return gptypes.GPFeatureRecordSetLayer.fromJson(
                                                 self._json_struct['routes'])
    @property
    def stops(self):
        return gptypes.GPFeatureRecordSetLayer.fromJson(
                                                 self._json_struct['stops'])
    @property
    def barriers(self):
        return gptypes.GPFeatureRecordSetLayer.fromJson(
                                                 self._json_struct['barriers'])
    @property
    def messages(self):
        return self._json_struct['messages']

class NetworkLayer(Layer):
    """The network layer resource represents a single network layer in a
       network analysis service published by ArcGIS Server. It provides
       basic information about the network layer such as its name, type,
       and network classes. Additionally, depending on the layer type, it
       provides different pieces of information as detailed in the
       examples."""
    __parent_type__ = NetworkService

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
    def SolveClosestFacility(self, facilities=None, 
                             incidents=None, 
                             barriers=None,
                             polylineBarriers=None,
                             polygonBarriers=None, 
                             attributeParameterValues=None,
                             returnDirections=None,
                             directionsLanguage=None,
                             directionsStyleName=None,
                             directionsLengthUnits=None,
                             directionsTimeAttributeName=None,
                             returnCFRoutes=None,
                             returnFacilities=None,
                             returnIncidents=None,
                             returnBarriers=None,
                             returnPolylineBarriers=None,
                             returnPolygonBarriers=None,
                             facilityReturnType=None,
                             outputLines=None,
                             defaultCutoff=None,
                             defaultTargetFacilityCount=None,
                             travelDirection=None,
                             outSR=None,
                             impedanceAttributeName=None,
                             restrictionAttributeNames=None,
                             restrictUTurns=None,
                             useHierarchy=None,
                             outputGeometryPrecision=None,
                             outputGeometryPrecisionUnits=None):
        """The solve operation is performed on a network layer resource of type
           closest facility."""
        raise NotImplementedError()
    def SolveServiceArea(self, facilities=None,
                         barriers=None,
                         polylineBarriers=None,
                         polygonBarriers=None,
                         attributeParameterValues=None,
                         defaultBreaks=None,
                         excludeSourcesFromPolygons=None,
                         mergeSimilarPolygonRanges=None,
                         outputLines=None,
                         outputPolygons=None,
                         overlapLines=None,
                         overlapPolygons=None,
                         splitLinesAtBreaks=None,
                         splitPolygonsAtBreaks=None,
                         travelDirection=None,
                         trimOuterPolygon=None,
                         trimPolygonDistance=None,
                         trimPolygonDistanceUnits=None,
                         accumulateAttributeNames=None,
                         impedanceAttributeName=None,
                         restrictionAttributeNames=None,
                         restrictUTurns=None,
                         outputGeometryPrecision=None,
                         outputGeometryPrecisionUnits=None):
        """The solve operation is performed on a network layer resource of type
           service area (layerType is esriNAServerServiceArea)."""
        raise NotImplementedError()


class RouteNetworkLayer(NetworkLayer):
    """Represents a Route Network Layer"""
    def Solve(self, stops=None, barriers=None, returnDirections=None,
              returnRoutes=None, returnStops=None, returnBarriers=None,
              outSR=None, ignoreInvalidLocations=None, outputLines=None,
              findBestSequence=None, preserveFirstStop=None,
              preserveLastStop=None, useTimeWindows=None, startTime=None, 
              accumulateAttributeNames=None, impedanceAttributeName=None,
              restrictionAttributeNames=None, restrictUTurns=None,
              useHierarchy=None, directionsLanguage=None,
              outputGeometryPrecision=None, directionsLengthUnits=None,
              directionsTimeAttributeName=None, attributeParameterValues=None,
              polylineBarriers=None, polygonBarriers=None):
        """The solve operation is performed on a network layer resource.

           At 9.3.1, the solve operation is supported only on the route layer.
           Or specifically, on a network layer whose layerType is
           esriNAServerRouteLayer.

           You can provide arguments to the solve route operation as query
           parameters defined in the parameters table below.
        """
        def ptlist_as_semilist(lst):
            if isinstance(lst, geometry.Point):
                lst = [lst]
            if isinstance(lst, (list, tuple)):
                return ";".join(','.join(str(x) for x in pt) for pt in lst)
            return lst
        if self.layerType != "esriNAServerRouteLayer":
            raise TypeError("Layer is of type %s; Solve is not available."
                            % self.layerType)
        return self._get_subfolder('solve/', NetworkSolveResult,
                       {'stops': ptlist_as_semilist(stops),
                        'barriers': ptlist_as_semilist(barriers),
                        'returnDirections': returnDirections,
                        'returnRoutes': returnRoutes,
                        'returnStops': returnStops,
                        'returnBarriers': returnBarriers,
                        'outSR': outSR,
                        'ignoreInvalidLocations': ignoreInvalidLocations,
                        'outputLines': outputLines,
                        'findBestSequence': findBestSequence,
                        'preserveFirstStop': preserveFirstStop,
                        'preserveLastStop': preserveLastStop,
                        'useTimeWindows': useTimeWindows,
                        'startTime': startTime,
                        'accumulateAttributeNames': accumulateAttributeNames,
                        'impedanceAttributeName': impedanceAttributeName,
                        'restrictionAttributeNames': restrictionAttributeNames,
                        'restrictUTurns': restrictUTurns,
                        'useHierarchy': useHierarchy,
                        'directionsLanguage': directionsLanguage,
                        'outputGeometryPrecision': outputGeometryPrecision,
                        'directionsLengthUnits': directionsLengthUnits,
                        'directionsTimeAttributeName':
                                                  directionsTimeAttributeName,
                        'attributeParameterValues': attributeParameterValues,
                        'polylineBarriers': polylineBarriers,
                        'polygonBarriers': polygonBarriers})

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
    def children(self):
        return [self._get_subfolder("../%s" % version_name, 
                                    GeoDataVersion) 
                    for version_name in
                        self._json_struct['childVersions']]
    @property
    def ancestorVersions(self):
        return self._json_struct['ancestorVersions']
    @property
    def ancestors(self):
        return [self._get_subfolder("../%s" % version_name, 
                                    GeoDataVersion) 
                    for version_name in
                        self._json_struct['ancestorVersions']]

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
        return geometry.fromJson(self._json_struct['queryGeometry'])
    @property
    def transferRelatedObjects(self):
        return self._json_struct['transferRelatedObjects']
    @property
    def reconcilePolicy(self):
        return self._json_struct['reconcilePolicy']

@Folder._register_service_type
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
    def versionNames(self):
        return self._json_struct['versions']
    @property
    def versions(self):
        return [self._get_subfolder("versions/%s/" % version, GeoDataVersion)
                for version in self.versionNames]
    @property
    def replicaNames(self):
        return self._json_struct['replicas']
    @property
    def replicas(self):
        return [self._get_subfolder("replicas/%s/" % version, GeoDataReplica)
                for replica in self.replicaNames]

class GlobeLayer(Layer):
    """The globe layer resource represents a single layer in a globe service
       published by ArcGIS Server. It provides basic information about the
       layer such as its ID, name, type, parent and sub-layers, fields, extent,
       data type, sampling mode, and extrusion type."""

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
    def description(self):
        return self._json_struct['description']
    @property
    def extent(self):
        return geometry.fromJson(self._json_struct['extent'])
    @property
    def dataType(self):
        return self._json_struct['dataType']
    @property
    def maxDistance(self):
        return self._json_struct['maxDistance']
    @property
    def minDistance(self):
        return self._json_struct['minDistance']
    @property
    def samplingMode(self):
        return self._json_struct['samplingMode']
    @property
    def baseID(self):
        return self._json_struct['baseID']
    @property
    def baseOption(self):
        return self._json_struct['baseOption']
    @property
    def extrusionType(self):
        return self._json_struct['extrusionType']
    @property
    def extrusionExpression(self):
        return self._json_struct['extrusionExpression']
    @property
    def cullMode(self):
        return self._json_struct['cullMode']
    @property
    def copyrightText(self):
        return self._json_struct['copyrightText']
    @property
    def displayField(self):
        return self._json_struct['displayField']
    @property
    def fields(self):
        return self._json_struct['fields']
    @property
    def parentLayer(self):
        return self._get_subfolder("../%s/" % 
                                   self._json_struct['parentLayer']['id'],
                                   GlobeLayer)
    @property
    def subLayers(self):
        return [self._get_subfolder("../%s/" % layer['id'], GlobeLayer)
                for layer in self._json_struct['subLayers']]

@Folder._register_service_type
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
        return [self._get_subfolder("./%s/" % layer['id'], GlobeLayer)
                for layer in self._json_struct['layers']]

@Folder._register_service_type
class FeatureLayerFeature(object):
    """The feature resource represents a single feature in a layer in a feature
       service."""
    @property
    def geometry(self):
        if 'geometry' in self._json_struct['feature']:
            geom = geometry.fromJson(
                        self._json_struct['feature'].get('geometry',
                                                              None),
                        self._json_struct['feature'].get('attributes', 
                                                              {}))
        else:
            geom = geometry.NullGeometry()
            geom.attributes = self._json_struct['feature'].get('attributes',
                                                                    {})
        return geom
    @property
    def attributes(self):
        return self._json_struct['feature'].get('attributes', 
                                                              {})
    @property
    def attachments(self):
        return self._get_subfolder("./attachments/", AttachmentInfos)
    def AddAttachment(self, attachment=None):
        """This operation adds an attachment to the associated feature (POST
           only). The add attachment operation is performed on a feature
           service feature resource."""
        return self._get_subfolder("./addAttachment", JsonPostResult,
                                   {'attachment': attachment})
    def UpdateAttachment(self, attachmentId=None, attachment=None):
        """This operation updates an attachment associated with a feature
           (POST only). The update attachment operation is performed on a
           feature service feature resource."""
        return self._get_subfolder("./updateAttachment", JsonPostResult,
                                   {'attachment': attachment,
                                    'attachmentId': attachmentId})
    def DeleteAttachments(self, attachmentIds=None):
        """This operation deletes attachments associated with a feature (POST
           only). The delete attachments operation is performed on a feature
           service feature resource."""
        return self._get_subfolder("./deleteAttachments", JsonPostResult,
                                    {'attachmentIds': attachmentIds})


class FeatureLayer(MapLayer):
    """The layer resource represents a single editable feature layer or non
       spatial table in a feature service."""

    def __getitem__(self, index):
        """Get a feature by featureId"""
        return self._get_subfolder(str(index), FeatureLayerFeature)
    def Feature(self, featureId):
        """Return a feature from this FeatureService by its ID"""
        return self[featureId]
    def QueryRelatedRecords(self, objectIds=None, relationshipId=None,
                            outFields=None, definitionExpression=None,
                            returnGeometry=None, outSR=None):
        """The query operation is performed on a feature service layer
           resource. The result of this operation are featuresets grouped by
           source layer / table object IDs. Each featureset contains Feature
           objects including the values for the fields requested by the user.
           For related layers, if you request geometry information, the
           geometry of each feature is also returned in the featureset. For
           related tables, the featureset does not include geometries."""

        out = self._get_subfolder("./queryRelatedRecords", JsonResult, {
                                                        'objectIds':
                                                            objectIds,
                                                        'relationshipId':
                                                            relationshipId,
                                                        'outFields':
                                                            outFields,
                                                        'definitionExpression':
                                                          definitionExpression,
                                                        'returnGeometry':
                                                            returnGeometry,
                                                        'outSR': outSR
                                                })
        return out._json_struct
    def AddFeatures(self, features):
        """This operation adds features to the associated feature layer or
           table (POST only). The add features operation is performed on a
           feature service layer resource. The result of this operation is an
           array of edit results. Each edit result identifies a single feature
           and indicates if the edit were successful or not. If not, it also
           includes an error code and an error description."""
        fd = {'features': ",".join(json.dumps(
                                        feature._json_struct_for_featureset) 
                                    for feature in features)}
        return self._get_subfolder("./addFeatures", JsonPostResult, fd)
    def UpdateFeatures(self, features):
        """This operation updates features to the associated feature layer or
           table (POST only). The update features operation is performed on a
           feature service layer resource. The result of this operation is an
           array of edit results. Each edit result identifies a single feature
           and indicates if the edit were successful or not. If not, it also
           includes an error code and an error description."""
        fd = {'features': ",".join(json.dumps(
                                        feature._json_struct_for_featureset) 
                                    for feature in features)}
        return self._get_subfolder("./updateFeatures", JsonPostResult, fd)
    def DeleteFeatures(self, objectIds=None, where=None, geometry=None,
                       inSR=None, spatialRel=None):
        """This operation deletes features in a feature layer or table (POST
           only). The delete features operation is performed on a feature
           service layer resource. The result of this operation is an array
           of edit results. Each edit result identifies a single feature and
           indicates if the edit were successful or not. If not, it also
           includes an error code and an error description."""
        gt = geometry.__geometry_type__
        if sr is None:
            sr = geometry.spatialReference.wkid
        geo_json = json.dumps(Geometry._json_struct_without_sr)
        return self._get_subfolder("./deleteFeatures", JsonPostResult, {
                                                    'objectIds': objectIds,
                                                    'where': where,
                                                    'geometry': geo_json,
                                                    'geometryType':
                                                            geometryType,
                                                    'inSR': inSR,
                                                    'spatialRel': spatialRel
                                    })
    def ApplyEdits(self, adds=None, updates=None, deletes=None):
        """This operation adds, updates and deletes features to the associated
           feature layer or table in a single call (POST only). The apply edits
           operation is performed on a feature service layer resource. The
           result of this operation are 3 arrays of edit results (for adds,
           updates and deletes respectively). Each edit result identifies a
           single feature and indicates if the edit were successful or not. If
           not, it also includes an error code and an error description."""
        add_str, update_str = None, None
        if adds:
            add_str = ",".join(json.dumps(
                                        feature._json_struct_for_featureset) 
                                    for feature in adds)
        if updates:
            update_str = ",".join(json.dumps(
                                        feature._json_struct_for_featureset) 
                                    for feature in updates)
        return self._get_subfolder("./applyEdits", JsonPostResult,
                                                                 {'adds':
                                                                       add_str,
                                                                  'updates':
                                                                    update_str,
                                                                   'deletes':
                                                                        deletes
                                                                   })
        

@Folder._register_service_type
class FeatureService(Service):
    """A feature service allows clients to query and edit features. Features
       include geometry, attributes and symbology and are organized into layers
       and sub types within a layer."""
    __service_type__ = "FeatureServer"

    @property
    def layernames(self):
        """Return a list of the names of this service's layers"""
        return [layer['name'] for layer in self._json_struct['layers']]
    @property
    def layers(self):
        """Return a list of this service's layer objects"""
        return [self._get_subfolder("%s/" % layer['id'], FeatureLayer)
                for layer in self._json_struct['layers']]
    @property
    def tablenames(self):
        """Return a list of the names of this service's tables"""
        return [table['name'] for table in self._json_struct.get('tables', [])]
    @property
    def tables(self):
        """Return a list of this service's table objects"""
        return [self._get_subfolder("%s/" % table['id'], FeatureLayer)
                for table in self._json_struct.get('tables', [])]
