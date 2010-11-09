#!/usr/bin/env python 

import unittest
import platform
import socket
import os
from arcrest.admin import *

HOSTNAME = socket.getfqdn(platform.node()).upper()
ADMIN_URL = "http://localhost:6080/agsadmin/"

class ClusterTest(unittest.TestCase):
    def setUp(self):
        self._admin = Admin(ADMIN_URL)
        self.cluster = self._admin.clusters.create("NewCluster", [HOSTNAME])
        #self.assertTrue(self.cluster)
    def tearDown(self):
        self.assertTrue(self.cluster.delete())
    def test_clusters_create(self):
        self.assertTrue(self.cluster)
    def test_cluster_list_machines(self):
        self.assertEqual([HOSTNAME], self.cluster.list_machines())
    def test_cluster_start(self):
        self.assertTrue(self.cluster.start())
        self.cluster.status(_success=lambda x: self.assertEqual('STARTED',x['realTimeStatus']))
        self.assertTrue(self.cluster.stop())
    def test_cluster_can_remove_machine_from_cluster(self):
        self.assertTrue(HOSTNAME in self.cluster.machines)
        self.assertTrue(HOSTNAME in self.cluster.list_machines())
        self.assertTrue(self.cluster.machines.remove([HOSTNAME, 'localhost']))
        self.assertTrue(HOSTNAME not in self.cluster.machines)
        self.assertTrue(HOSTNAME not in self.cluster.list_machines())
    def test_cluster_can_add_machine_from_cluster(self):
        self.assertTrue(self.cluster.machines.remove([HOSTNAME]))
        self.assertTrue(HOSTNAME not in self.cluster.machines)
        self.assertTrue(self.cluster.machines.add([HOSTNAME]))
        self.assertTrue(HOSTNAME in self.cluster.machines)
    def test_cluster_machines_add_ignores_unregistered_machines(self):
        self.assertTrue("other.machine.org" not in self._admin.machines)
        self.assertTrue(self.cluster.machines.add(["other.machine.org"]))
        self.assertTrue("other.machine.org" not in self.cluster.machines)
    def test_cluster_machines_remove_fails_if_machine_cannot_be_removed(self):
        self.assertTrue("other.machine.org" not in self.cluster.machines)
        self.assertFalse(self.cluster.machines.remove(["other.machine.org"]))
    def test_clustername_in_clusters_returns_cluster(self):
        self.assertEqual(self.cluster, self._admin.clusters["NewCluster"])


class MachineTest(unittest.TestCase):
    def test_admin_has_list_of_registered_machines(self):
        self._admin = Admin(ADMIN_URL)
        self.assertTrue(HOSTNAME in self._admin.machines.keys())
        self.assertTrue(HOSTNAME, self._admin.machines[HOSTNAME]['machineName'])

class DirectoryTest(unittest.TestCase):
    def setUp(self):
        self._admin = Admin(ADMIN_URL)
        self.path = os.path.abspath(os.path.dirname(__file__))
    def tearDown(self):
        self._admin.directories.unregister(self.path)
    def test_register_data_directory(self):
        self.assertTrue(self._admin.directories.register('data', self.path))
        self.assertTrue(self.path in self._admin.directories)
        self.assertEqual('DATA', self._admin.directories[self.path]['directoryType'])
    def test_register_public_cache_directory(self):
        vpath = 'http://%s:6080/arcgis/server/extracache' % HOSTNAME
        self.assertTrue(self._admin.directories.register('cache', self.path, vpath))
        self.assertTrue(self.path in self._admin.directories)
        self.assertEqual('CACHE', self._admin.directories[self.path]['directoryType'])
        self.assertEqual(self.path, self._admin.directories[self.path]['physicalPath'])
        self.assertEqual(vpath, self._admin.directories[self.path]['virtualPath'])
        self.assertTrue(self._admin.directories.unregister(self.path))
    def test_register_public_cache_directory_with_bad_local_path(self):
        vpath = 'http://%s:6080/arcgis/server/extracache' % HOSTNAME
        self.assertFalse(self._admin.directories.register('cache', '/not/a/real/path', vpath))
        self.assertTrue(self.path not in self._admin.directories)


if __name__ == "__main__":
    unittest.main()

