import os

class proj(object):
    def __init__(self, filename):
        self._name_mapping = {}
        for line in open(os.path.join(os.path.dirname(__file__), filename)):
            val, key = line.split()
            setattr(self, key, val)
            self._name_mapping[int(val)] = key
    def __getitem__(self, index):
        return self._name_mapping[index]
    def __contains__(self, index):
        return index in self._name_mapping

Projected = proj('projected.txt')
Geographic = proj('geographic.txt')
