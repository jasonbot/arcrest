import unittest
import platform
from arcrest.admin import *

HOSTNAME=platform.node().upper()

class ClusterTest(unittest.TestCase):
    def setUp(self):
        self._admin = Admin("http://localhost:5050/agsadmin/")
        self.cluster = self._admin.clusters.create("NewCluster", [HOSTNAME])
        self.assertTrue(self.cluster)
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

class DirectoryTest(unittest.TestCase):
    def setUp(self):
        self._admin = Admin("http://localhost:5050/agsadmin/")
        self.path = os.path.abspath(os.path.dirname(__file__))
    def tearDown(self):
        self._admin.directories.unregister(self.path)
    def test_register_data_directory(self):
        self.assertTrue(self._admin.directories.register('data', self.path))
        self.assertTrue(self.path in self._admin.directories)
        self.assertEqual('DATA', self._admin.directories[self.path]['directoryType'])
    def test_register_public_cache_directory(self):
        vpath = 'http://%s:5050/arcgis/server/extracache' % HOSTNAME
        self.assertTrue(self._admin.directories.register('cache', self.path, vpath))
        self.assertTrue(self.path in self._admin.directories)
        self.assertEqual('CACHE', self._admin.directories[self.path]['directoryType'])
        self.assertEqual(self.path, self._admin.directories[self.path]['physicalPath'])
        self.assertEqual(vpath, self._admin.directories[self.path]['virtualPath'])
        self.assertTrue(self._admin.directories.unregister(self.path))
    def test_register_public_cache_directory_with_bad_local_path(self):
        vpath = 'http://%s:5050/arcgis/server/extracache' % HOSTNAME
        self.assertFalse(self._admin.directories.register('cache', '/not/a/real/path', vpath))
        self.assertTrue(self.path not in self._admin.directories)


if __name__ == "__main__":
    unittest.main()

