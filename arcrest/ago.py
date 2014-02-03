# coding: utf-8
"""Represents the ArcGIS online REST APIs"""

from . import compat, server

__all__ = ['AGORoot', 'Community', 'Content', 'Portals']

class AGORoot(server.RestURL):
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
        super(AGORoot, self).__init__(url)
    def search(self, q=None, bbox=None, start=None, num=None,
               sortField=None, sortOrder=None):
        return self._get_subfolder("./search", 
                                          server.JsonPostResult,
                                          {'q': q,
                                           'bbox': bbox,
                                           'start': start,
                                           'num': num,
                                           'sortField': sortField,
                                           'sortOrder': sortOrder})
    @property
    def community(self):
        return self._get_subfolder("./community/", Community)
    @property
    def content(self):
        return self._get_subfolder("./content/", Content)
    @property
    def portals(self):
        return self._get_subfolder("./portals/", Portals)

class Community(server.RestURL):
    pass

class Content(server.RestURL):
    pass

class Portals(server.RestURL):
    pass
