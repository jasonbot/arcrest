try:
    import json
except ImportError:
    try:
        import simplejson as json
    except:
        raise ImportError("Please install the simplejson module "\
                          "from http://www.undefined.org/python/ "\
                          "or use arcrest with Python 2.6")
import cgi
import urllib
import urllib2
import urlparse

class ReSTURL(object):
    __caching__ = False # Fetch every time or just once?
    def __init__(self, url):
        if isinstance(url, basestring):
            url = urlparse.urlsplit(url)
        self._url = url
        #self.__lazy_properties__ = {}
        #self.__class__ = type(self.__class__.__name__, (self.__class__,), self.__dict__)
    def _get_subfolder(self, foldername, returntype=None):
        if returntype is None:
            returntype = self.__class__
        return returntype(urlparse.urljoin(self._url, foldername, False))
    @property
    def url(self):
        return urlparse.urlunsplit(self._url)
    @property
    def contents(self):
        if (not hasattr(self, '__urldata__')) or self.__caching__ is False:
            handle = urllib2.urlopen(self.url)
            self.__urldata__ = handle.read()
        return self.__urldata__

class Folder(ReSTURL):
    __caching__  = True
    def __init__(self, url):
        # Pull out query, whatever it may be
        urllist = list(urlparse.urlsplit(url))
        query_dict = cgi.parse_qs(urllist[3])
        # Set the f= flag to json (so we can interface with it)
        query_dict['f'] = 'json'
        urllist[3] = urllib.urlencode(query_dict)
        super(Folder, self).__init__(urllist)
    @property
    def json_struct(self):
        return json.loads(self.contents)
    @property
    def folders(self):
        return self.json_struct['folders']
    @property
    def services(self):
        return [service['name'] for service in self.json_struct['services']]
    def __getattr__(self, attr):
        if attr in self.folders:
            return self._get_subfolder(attr, Folder)
        if attr in self.services:
            return self._get_subfolder(attr, Service)

class Server(Folder):
    def __init__(self, url):
        super(Server, self).__init__(url)

class Service(ReSTURL):
    def __init__(self, url):
        super(Service, self).__init__(url)
