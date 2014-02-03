# coding: utf-8
"""Implementation of the objects for the ArcGIS Server REST 
   Administration API"""

import cgi
import itertools
import os.path

from .. import compat, server, GenerateToken

__all__ = ['Admin', 'Folder', 'Services', 'Service', 
           'Machine', 'Machines', 'SiteMachines', 'ClusterMachines',
           'Directory', 'Directories',
           'Clusters', 'Cluster']

class Admin(server.RestURL):
    """Represents the top level URL resource of the ArcGIS Server
       Administration API"""
    def __init__(self, url, username=None, password=None,
                 token=None, generate_token=False,
                 expiration=60):
        url_list = list(compat.urlsplit(url))
        if not url_list[2].endswith('/'):
            url_list[2] += "/"
        url = compat.urlunsplit(url_list)
        if username is not None and password is not None:
            self._pwdmgr.add_password(None,
                                      url,
                                      username,
                                      password)
        if token:
            self.__token__ = token
        elif generate_token:
            self.__generateToken(url, username, password, expiration)
        super(Admin, self).__init__(url)
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
        
        self.__generateToken(self.url, username, password, 60)
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
        self.__token__ = None
        return res
    def __generateToken(self, url, username, password, expiration):
      token_auth = GenerateToken(url,
                                 username,
                                 password,
                                 expiration)
      if token_auth._json_struct.get('status', 'ok').lower() == 'error':
          raise compat.URLError('\n'.join(
                                      token_auth._json_struct.get(
                                          'messages', ['Failed.'])))
      self.__token__ = token_auth.token

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

class HasUploads(object):
    def upload(self, file, description=''):
        if isinstance(file, basestring):
            file = open(file, 'rb')
        sub = self._get_subfolder('./upload/', server.JsonResult,
                                  {'description': description},
                                  {'itemFile': file})
        return sub._json_struct['item']

class Uploads(server.RestURL, HasUploads):
    """Uploads URL"""
    pass

class DataItems(server.RestURL, HasUploads):
    """Server's data files"""
    @property
    def packages(self):
        return self._json_struct['packages']

class Folder(server.RestURL):
    @property
    def folderName(self):
        return self._json_struct['folderName']
    @property
    def description(self):
        return self._json_struct['description']
    @property
    def serviceNames(self):
        return [service['serviceName'] 
                for service in self._json_struct['services']]
    @property
    def services(self):
        return [self._get_subfolder("./%s.%s/" % 
                                        (servicename['serviceName'],
                                         servicename['type']), 
                                    Service)
                for servicename in self._json_struct['services']]
    def __getitem__(self, itemname):
        if '/' in itemname:
            itemname, rest = itemname.split('/', 1)
            return self[itemname][rest]
        for servicename in self._json_struct['services']:
            fstrings = (servicename['serviceName'].lower(),
                        (servicename['serviceName'] +
                            "." + 
                            servicename['type']).lower())
            if itemname.lower() in fstrings:
                return self._get_subfolder("./%s.%s/" % 
                                        (servicename['serviceName'],
                                         servicename['type']), 
                                    Service)
        raise KeyError(itemname)
    def __iter__(self):
        return iter(self.services)

class Services(Folder):
    def createFolder(self, folderName, description):
        raise NotImplementedError("Not implemented")
    @property
    def folders(self):
        return [self._get_subfolder("./%s/" % foldername, Folder) 
                for foldername in self._json_struct['folders']
                if foldername != "/"]
    @property
    def types(self):
        return_type = self._get_subfolder("./types/", server.JsonPostResult)
        return return_type._json_struct['types']
    def __getitem__(self, itemname):
        for foldername in self._json_struct['folders']:
            if foldername.lower() == itemname.lower():
                return self._get_subfolder("./%s/" % foldername, Folder)
        return super(Services, self).__getitem__(itemname)
    def __iter__(self):
        for folder in self.folders:
            for service in folder.services:
                yield service
        for service in super(Services, self).__iter__():
            yield service

class Service(server.RestURL):
    @property
    def name(self):
        return self._json_struct['serviceName'] + "." + self._json_struct['type']
    @property
    def status(self):
        return self._get_subfolder("./status/", 
                                   server.JsonPostResult)._json_struct
    @property
    def statistics(self):
        return self._get_subfolder("./statistics/",
                                   server.JsonPostResult)._json_struct
    def start(self):
        return self._get_subfolder("./start/", 
                                   server.JsonPostResult)._json_struct
    def stop(self):
        return self._get_subfolder("./stop/", 
                                   server.JsonPostResult)._json_struct
    def delete(self):
        return self._get_subfolder("./delete/", 
                                   server.JsonPostResult)._json_struct

class Machine(server.RestURL):
    """Base class for a single machine on a site"""
    @property
    def name(self):
        return self._json_struct['machineName']
    @property
    def admin_url(self):
        return self._json_struct['adminURL']
    @property
    def platform(self):
        return self._json_struct['platform']
    def start(self):
        return self._get_subfolder("./start/", 
                                   server.JsonPostResult)._json_struct
    def stop(self):
        return self._get_subfolder("./stop/", 
                                   server.JsonPostResult)._json_struct
    def unregister(self):
        return self._get_subfolder("./unregister/", 
                                   server.JsonPostResult)._json_struct

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
    def register(self, machine_name, admin_url=None):
        return self._get_subfolder("./register/", 
                                   server.JsonPostResult,
                                   {'machineName': machine_name,
                                    'adminURL': admin_url})._json_struct


class ClusterMachines(Machines):
    """A list of machines participating on a cluster"""
    def add(self, machine_names):
        if isinstance(machine_names, basestring):
            machine_names = [machine_names]
        responses = [self._get_subfolder("./add/", server.JsonPostResult, 
                                         {"machineNames": m}) 
                     for m in machine_names]
        return responses
    def remove(self, machine_names):
        if isinstance(machine_names, basestring):
            machine_names = [machine_names]
        responses = [self._get_subfolder("./remove/", server.JsonPostResult, 
                                         {"machineNames": m}) 
                     for m in machine_names]
        return responses

class SiteMachines(Machines):
    """A list of machines on a site"""
    def register(self, machineName, adminURL=None):
        res = self._get_subfolder("./register/", server.JsonPostResult,
                                  {'machineName': machineName,
                                   'adminURL': adminURL})
    @property
    def machines(self):
        return [self._get_subfolder("./%s/" % machinename, Machine) for
                machinename in self._machines]
    def __getitem__(self, itemname):
        assert itemname in self._machines, "Couldn't find %s" % itemname
        return self._get_subfolder('./%s/' % itemname, Machine)

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
    def start(self):
        return self._get_subfolder('./start/',
                                   server.JsonPostResult)._json_struct
    def stop(self):
        return self._get_subfolder('./stop/',
                                   server.JsonPostResult)._json_struct
    def delete(self):
        return self._get_subfolder('./delete/',
                                   server.JsonPostResult)._json_struct
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

