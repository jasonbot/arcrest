#! python
# coding: utf-8

from distutils.core import setup
import os

setup(
    name='arcrest',
    version='10.3',
    summary="ArcGIS for Server REST API wrapper",
    description="""Wrapper to the ArcGIS REST API, and a Python analogue to the Javascript APIs""",
    author="Esri",
    author_email="jscheirer@esri.com",
    platform="any",
    license="Apache Software License",
    packages=['arcrest', 'arcrest.admin'],
    scripts=[
             os.path.join('cmdline', 'createservice.py'),
             os.path.join('cmdline', 'manageservice.py'),
             os.path.join('cmdline', 'managesite.py'),
             os.path.join('cmdline', 'deletecache.py'),
             os.path.join('cmdline', 'createcacheschema.py'),
             os.path.join('cmdline', 'managecachetiles.py'),
             os.path.join('cmdline', 'convertcachestorageformat.py'),
             os.path.join('cmdline', 'reportcachestatus.py'),
            ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities'
    ]
)
