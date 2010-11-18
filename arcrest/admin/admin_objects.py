"""Implementation of the objects for the ArcGIS Server REST 
   Administration API"""

import cgi
import os.path
from arcrest import server
import urllib
import urlparse
import urllib2

__all__ = ['Admin', 'Folder', 'Services', 'Machines',
           'SiteMachines', 'ClusterMachines', 'Directory',
           'Directories', 'Clusters', 'Cluster']

class Admin(server.RestURL):
    """Represents the top level URL resource of the ArcGIS Server
       Administration API"""
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
        return self._get_subfolder("./machines/", SiteMachines)
    @property
    def data(self):
        return self._get_subfolder("./data/", Data)
    @property
    def uploads(self):
        return self._get_subfolder('./uploads/', Uploads)
    @property
    def system(self):
        return self._get_subfolder("./system/", System)
    def createNewSite(self, username, password, configStoreConnection=None, 
                      directories=None, cluster=None):
        res = self._get_subfolder("./createNewSite", 
                                  server.JsonPostResult,
                                  {'username': username,
                                   'password': password,
                                   'configStoreConnection': configStoreConnection,
                                   'directories': directories,
                                   'cluster': cluster})
        return res
    def joinSite(self, adminURL, username, password):
        res = self._get_subfolder("./joinSite", 
                                  server.JsonPostResult,
                                  {'username': username,
                                   'password': password,
                                   'adminURL': adminURL})
        return res
    def deleteSite(self):
        res = self._get_subfolder("./deleteSite", 
                                  server.JsonPostResult)
        return res


class Data(server.RestURL):
    """Administration URL's data store -- Geodatabases and file data"""
    @property
    def geodatabases(self):
        return self._get_subfolder("./geodatabases/", GeoDatabases)
    @property
    def items(self):
        return self._get_subfolder("./items/", DataItems)

class GeoDatabases(server.RestURL):
    """Server's geodatabases and GDB connections"""
    pass

class Uploads(server.RestURL):
    def upload(self, file, description=''):
        if isinstance(file, basestring):
            file = open(file, 'rb')
        sub = self._get_subfolder('./upload/', server.JsonResult,
                                  {'description': description},
                                  {'packageFile': file})
        return sub._json_struct['package']

class DataItems(server.RestURL, Uploads):
    """Server's data files"""
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
        return [self] + [self._get_subfolder("./%s/" % foldername, Folder) 
                        for foldername in self._json_struct['folders']
                        if foldername != "/"]
    @property
    def types(self):
        return_type = self._get_subfolder("./types/", server.JsonPostResult)
        return return_type._json_struct['types']


class Machines(server.RestURL):
    """Base class for a list of machines, both on a Cluster and a Site"""
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
                    for item in self._machines.itervalues())

class ClusterMachines(Machines):
    """A list of machines participating on a cluster"""
    def add(self, machine_names):
        if isinstance(machine_names, basestring):
            machine_names = [machine_names]
        responses = [self._get_subfolder("./add", server.JsonPostResult, 
                                         {"machineNames": m}) 
                     for m in machine_names]
        return responses
    def remove(self, machine_names):
        if isinstance(machine_names, basestring):
            machine_names = [machine_names]
        responses = [self._get_subfolder("./remove", server.JsonPostResult, 
                                         {"machineNames": m}) 
                     for m in machine_names]
        return responses

class SiteMachines(Machines):
    """A list of machines on a site"""
    def register(self, machineName, adminURL=None):
        res = self._get_subfolder("./register/", server.JsonPostResult,
                                  {'machineName': machineName,
                                   'adminURL': adminURL})

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
    def register(self, type, path, vpath=None):
        response = self._get_subfolder('./register', server.JsonPostResult,
                                      {'directoryType': type.upper(),
                                       'physicalPath': path,
                                       'virtualPath': vpath})._json_struct
    def unregister(self, path):
        response = self._get_subfolder('./unregister', server.JsonPostResult,
                                      {'physicalPath': path})._json_struct

class Cluster(server.JsonResult):
    __post__ = True
    __lazy_fetch__ = False
    __cache_request__ = True
    def __eq__(self, other):
        if not isinstance(other, Cluster):
            return False
        return self._url == other._url
    @property
    def machineNames(self, _error=None, _success=None):
        if "machineNames" in self._json_struct:
            return self._json_struct["machineNames"]
    @property
    def machines(self):
        return self._get_subfolder("./machines/", ClusterMachines)
    def delete(self):
        self._get_subfolder('./delete', server.JsonPostResult)
    def editProtocol(self, type="TCP", tcpClusterPort=-1, 
               multicastAddress=10, multicastPort=-1):
        if type not in ("TCP", "UDP"):
            raise ValueError("Got %r. Valid choices are: TCP, UDP" % type)
        res = self._get_subfolder('./editProtocol', server.JsonPostResult,
                                     {'type': type,
                                      'tcpClusterPort': tcpClusterPort 
                                                            if type == "TCP" 
                                                            else None,
                                      'multicastAddress': multicastAddress 
                                                            if type == "UDP" 
                                                            else None,
                                      'multicastPort': multicastPort
                                                            if type == "UDP" 
                                                            else None})

class Clusters(server.RestURL):
    __post__ = True
    __directories__ = Ellipsis
    __cluster_cache__ = Ellipsis
    @property
    def _clusters(self):
        if self.__cluster_cache__ is Ellipsis:
            path_and_attribs = [(d['clusterName'],
                                self._get_subfolder('./%s/' %d['clusterName'],
                                                    Cluster)) 
                                for d in self._json_struct['clusters']] 
            self.__cluster_cache__ = dict(path_and_attribs)
        return self.__cluster_cache__
    @property
    def clusterNames(self):
        return [d['clusterName'] for d in self._json_struct['clusters']]
    def __contains__(self, k):
        if isinstance(k, int):
            return k < len(self)
        return self._clusters.__contains__(k)
    def __getitem__(self, k):
        if isinstance(k, int):
            k = self.clusterNames[k]
        return self._clusters.__getitem__(k)
    def __len__(self):
        return len(self.clusterNames)
    def create(self, clusterName, type="TCP", tcpClusterPort=-1, 
               multicastAddress=10, multicastPort=-1):
        if type not in ("TCP", "UDP"):
            raise ValueError("Got %r. Valid choices are: TCP, UDP" % type)
        res = self._get_subfolder('./create', server.JsonPostResult,
                                     {'clusterName': clusterName,
                                      'type': type,
                                      'tcpClusterPort': tcpClusterPort 
                                                            if type == "TCP" 
                                                            else None,
                                      'multicastAddress': multicastAddress 
                                                            if type == "UDP" 
                                                            else None,
                                      'multicastPort': multicastPort
                                                            if type == "UDP" 
                                                            else None})
        return self._get_subfolder('./%s/' % clusterName, Cluster)

