# coding: utf-8
"""Provides a place for functions/modules which have been reogranized in the
   python 2/3 switch use in this library to be located regardless of their
   location in the running Python's standard library."""

__all__ = ['cookielib', 'urllib2', 'HTTPError', 'URLError', 'urlsplit',
           'urljoin', 'urlunsplit', 'urlencode', 'quote', 'string_type',
           'ensure_string', 'ensure_bytes', 'get_headers']

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

string_type = str

try:
    unicode
    string_type = basestring
    bytes = str
except NameError:
    unicode = str
    string_type = str

def ensure_string(payload_bytes):
    if isinstance(payload_bytes, bytes):
        return payload_bytes.decode("utf-8")
    return payload_bytes

def ensure_bytes(payload_string):
    if isinstance(payload_string, unicode):
        return payload_string.encode("utf-8")
    return payload_string

def get_headers(handle):
    if hasattr(handle.headers, 'headers'):
        return handle.headers.headers
    return dict(handle.headers.items())
