import cgi
import os.path
from arcrest import server
import urllib
import urlparse
import urllib2

__all__ = ['Admin', 'Folder', 'Services',
           'Machines', 'Directory', 'Directories', 
           'Clusters', 'Cluster']

class Admin(server.RestURL):
    @property
    def resources(self):
        return self._json_struct['resources']
    @property
    def currentVersion(self):
        return self._json_struct['currentVersion']
    @property
    def clusters(self):
        return self._get_subfolder("./clusters/", Clusters)
    @property
    def services(self):
        return self._get_subfolder("./services/", Services)
    @property
    def machines(self):
        return self._get_subfolder("./machines/", Machines)
    @property
    def data(self):
        return self._get_subfolder("./data/", Data)
    @property
    def system(self):
        return self._get_subfolder("./system/", System)

class Data(server.RestURL):
    @property
    def geodatabases(self):
        return self._get_subfolder("./geodatabases/", GeoDatabases)
    @property
    def items(self):
        return self._get_subfolder("./items/", DataItems)

class GeoDatabases(server.RestURL):
    pass

class DataItems(server.RestURL):
    def upload(self, file, description=''):
        if isinstance(file, basestring):
            file = open(file, 'rb')
        sub = self._get_subfolder('./upload/', server.JsonResult,
                                  {'description': description},
                                  {'packageFile': file})
        return sub._json_struct['package']
    @property
    def packages(self):
        return self._json_struct['packages']

class Folder(server.RestURL):
    @property
    def services(self):
        raise NotImplementedError("Not implemented")
    @property
    def folderName(self):
        return self._json_struct['folderName']
    @property
    def description(self):
        return self._json_struct['description']
    @property
    def services(self):
        return [self._get_subfolder("./%s/" % servicename, Service) 
                for servicename in self._json_struct['services']]

class Services(Folder):
    def createFolder(self, folderName, description):
        raise NotImplementedError("Not implemented")
    @property
    def folders(self):
        return [self._get_subfolder("./%s/" % foldername, Folder) 
                for foldername in self._json_struct['folders']]

class Machines(server.RestURL):
    __post__ = True
    __machines__ = Ellipsis
    @property
    def _machines(self):
        if self.__machines__ is Ellipsis:
            path_and_attribs = [(d['machineName'], d) 
                                for d in self._json_struct['machines']]
            self.__machines__ = dict(path_and_attribs)
        return self.__machines__
    def keys(self):
        return self._machines.keys()
    def __iter__(self):
        return (Admin(item['adminURL']) 
                    for item in self._machines.iteritems())
    def add(self, machine_names):
        responses = [self._get_subfolder("./add", Machines, 
                                         {"machineNames": m})._json_struct 
                     for m in machine_names]
        return not any(map(is_json_error, responses))
    def remove(self, machine_names):
        machines = filter(lambda m: m in self._machines, machine_names)
        responses = [self._get_subfolder("./remove", Machines, 
                                         {"machineNames": m})._json_struct 
                     for m in machines]
        return (not any(map(is_json_error, responses))) and machines

class Directory(server.RestURL):
   __post__ = True

class Directories(server.RestURL):
    __directories__ = Ellipsis
    @property
    def _directories(self):
        path_and_attribs = [(d['physicalPath'], d) 
                            for d in self._json_struct['directories']]
        self.__directories__ = dict(path_and_attribs)
        return self.__directories__
    def __contains__(self, k):
        return self._directories.__contains__(k)
    def __getitem__(self, k):
        return self._directories.__getitem__(k)
    def register(self, type, path, vpath=None, _success=None, _error=None):
        response = self._get_subfolder('./register', Directory,
                                      {'directoryType': type.upper(),
                                       'physicalPath': path,
                                       'virtualPath': vpath})._json_struct
        return not is_json_error(response, _success=_success, _error=_error)
    def unregister(self, path, _success=None, _error=None):
        response = self._get_subfolder('./unregister', Directory,
                                      {'physicalPath': path})._json_struct
        return not is_json_error(response, _success=_success, _error=_error)

class Cluster(server.RestURL):
    __post__ = True
    __lazy_fetch__ = False
    __cache_request__ = True
    def __init__(self, url):
        super(Cluster, self).__init__(url)
        query_dict = dict((k, v[0]) for k, v in 
                               cgi.parse_qs(self.query).iteritems())
        # clusterName indicates the url is for a call to clusters/create
        # so we convert the url to clusters/<clusterName>/
        # and reset the __urldata__ to force a new request
        if "clusterName" in query_dict:
            urlparts = list(self._url)
            urlparts[2] = urlparts[2][0:-1]
            newurl = urlparse.urljoin(self.url,
                        urllib.quote(query_dict["clusterName"] + "/"), False)
            newurl = list(urlparse.urlsplit(newurl))
            newurl[3] = urllib.urlencode({'f':'json'})
            self._url = newurl
            self._clear_cache()
    def __eq__(self, other):
        if not isinstance(other, Cluster):
            return False
        return self._url == other._url 
    @property
    def machines(self):
        return self._get_subfolder("./machines/", Machines)
    def delete(self, _error=None):
        response = self._get_subfolder('./delete', Cluster)._json_struct
        return not is_json_error(response, _error=_error)
    def start(self, _error=None, _success=None):
        response = self._get_subfolder('./start', Cluster)._json_struct
        return not is_json_error(response, _error=_error, _success=_success)
    def stop(self):
        response = self._get_subfolder('./stop', Cluster)._json_struct
        return not is_json_error(response)
    def list_machines(self, _error=None, _success=None):
        self._clear_cache()
        if not is_json_error(self._json_struct, _error, _success):
            if "machineNames" in self._json_struct:
                return self._json_struct["machineNames"]
    def status(self, _error=None, _success=None):
        self._clear_cache()
        return not is_json_error(self._json_struct, _error, _success)

class Clusters(server.RestURL):
    __post__ = True
    __directories__ = Ellipsis
    @property
    def _clusters(self):
        path_and_attribs = [(d['clusterName'],
                            self._get_subfolder('./%s/' %d['clusterName'],
                                                Cluster)) 
                            for d in self._json_struct['clusters']] 
        self.__clusters__ = dict(path_and_attribs)
        return self.__clusters__
    def __contains__(self, k):
        return self._clusters.__contains__(k)
    def __getitem__(self, k):
        return self._clusters.__getitem__(k)
    def create(self, cluster_name, machines, _error=None, _success=None):
        cluster = self._get_subfolder('./create', Cluster,
                                     {'clusterName': cluster_name,
                                      'machineNames': machines[0],
                                      'clusterProtocol': 'TCP',
                                      'tcpClusterPort': '4013'})
        if not is_json_error(cluster._json_struct, _error=_error, _success=_success):
            return cluster

def is_json_error(_json, _error=None, _success=None):
    if 'status' in _json and _json['status'] == 'error':
        if _error:
            _error(_json)
        return True
    else:
        if _success:
            _success(_json)
    return False

