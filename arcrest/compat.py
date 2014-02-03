# coding: utf-8
"""Provides a place for functions/modules which have been reogranized in the
   python 2/3 switch use in this library to be located regardless of their
   location in the running Python's standard library."""

__all__ = ['cookielib', 'urllib2', 'HTTPError', 'URLError', 'urlsplit',
           'urljoin', 'urlunsplit', 'urlencode', 'quote']

try:
    import cookielib
except ImportError:
    import http.cookiejar as cookielib

try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

try:
    from urllib2 import HTTPError, URLError
except ImportError:
    from urllib.error import HTTPError, URLError

try:
    from urlparse import urlsplit, urljoin, urlunsplit
except ImportError:
    from urllib.parse import urlsplit, urljoin, urlunsplit

try:
    from urllib import urlencode, quote
except ImportError:
    from urllib.parse import urlencode, quote
