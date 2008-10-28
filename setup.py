from distutils.core import setup
import os

setup(
    name='arcrest',
    version='0.1',
    description="""Wrapper to the ArcGIS REST API, and a Python analogue to the Javascript APIs""",
    author="ESRI",
    author_email="jscheirer@esri.com",
    packages=['arcrest'],
    package_data={'arcrest': ['*.txt']}
)
