# coding: utf-8
"""Represents the ArcGIS Portal REST APIs"""

from . import compat, server

__all__ = ['PortalRoot']

class PortalRoot(server.RestURL):
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
        super(PortalRoot, self).__init__(url)

