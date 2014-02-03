# coding: utf-8
"""This module provides a conversion layer for data types passed to/from
   Geoprocessing tasks on an ArcGIS REST server."""

import datetime
import json

from . import geometry

try:
    long, unicode, basestring
except NameError:
    long, unicode, basestring = int, str, str

class GPMultiValue(object):
    """Represents a multivalue Geoprocessing parameter"""
    _container_type = None
    def __init__(self, values):
        self._values = [self._container_type.fromJson(item)
                            if not isinstance(item, GPBaseType)
                            else item
                        for item in values]
    def __iter__(self):
        return iter(self._values)
    @classmethod
    def _from_json_def(cls, json):
        return cls
    @property
    def _json_struct(self):
        return [getattr(x, '_json_struct', x) for x in self._values]
    @classmethod
    def fromJson(cls, val):
        return cls(val)
    @staticmethod
    def fromType(datatype):
        """Use this method to create a MultiValue type from a specific GP Value
           type.
           
              >>> gpmultistr = arcrest.GPMultiValue.fromType(arcrest.GPString)
              >>> gpvalue = gpmultistr(["a", "b", "c"])
        """
        if issubclass(datatype, GPBaseType):
            return GPBaseType._get_type_by_name("GPMultiValue:%s" % 
                                                datatype.__name__)
        else:
            return GPBaseType._get_type_by_name("GPMultiValue:%s" % 
                                                str(datatype))

class GPBaseType(object):
    """Base type for (singular) Geoprocessing argument value types"""
    #: Mapping from Geoprocessing type to name
    _gp_type_mapping = {}

    def __str__(self):
        return json.dumps(self._json_struct)
    @classmethod
    def _from_json_def(cls, json):
        return cls
    @classmethod
    def _get_type_by_name(cls, name):
        if (name.startswith("GPMultiValue:") and 
                name not in cls._gp_type_mapping):
            def make_multivalue(name, base_type):
                new_multivalue_type = type(str(name), (GPMultiValue,), {})
                new_multivalue_type._container_type = base_type
                return new_multivalue_type
            mvs, dtype = name.split(":", 1)
            mytype = cls._gp_type_mapping.get(dtype, GPString)
            multivalue_type = make_multivalue(name, mytype)
            cls._gp_type_mapping[name] = multivalue_type
            return multivalue_type
        else:
            return cls._gp_type_mapping.get(name, GPString)
    @classmethod
    def _register_type(cls, newcls):
        cls._gp_type_mapping[newcls.__name__] = newcls
        return newcls

class GPSimpleType(GPBaseType):
    """For geoprocessing types that simplify to base Python types, such as 
       int, bool, or string."""
    __conversion__ = None
    def __init__(self, val):
        self.value = val
    @property
    def _json_struct(self):
        try:
            return self.__conversion__(self.value)
        except:
            if self.value is None:
                return None
            raise
    @classmethod
    def fromJson(cls, value):
        return cls.__conversion__(value)

@GPBaseType._register_type
class GPBoolean(GPSimpleType):
    """Represents a geoprocessing boolean parameter"""
    __conversion__ = bool

@GPBaseType._register_type
class GPDouble(GPSimpleType):
    """Represents a geoprocessing double parameter"""
    __conversion__ = float

@GPBaseType._register_type
class GPLong(GPSimpleType):
    """Represents a geoprocessing long parameter"""
    __conversion__ = long

@GPBaseType._register_type
class GPString(GPSimpleType):
    """Represents a geoprocessing string parameter"""
    __conversion__ = str

@GPBaseType._register_type
class GPLinearUnit(GPBaseType):
    """Represents a geoprocessing linear unit parameter"""
    #: The set of unit names allowed, defaulting to esriMeters
    allowed_units = set(['esriCentimeters',
                         'esriDecimalDegrees',
                         'esriDecimeters',
                         'esriFeet',
                         'esriInches',
                         'esriKilometers',
                         'esriMeters',
                         'esriMiles',
                         'esriMillimeters',
                         'esriNauticalMiles',
                         'esriPoints',
                         'esriUnknownUnits',
                         'esriYards'])
    def __init__(self, value, unit=None):
        if isinstance(value, (list, tuple)) and len(value) == 2:
            value, unit = value
        value = float(value)
        # Default to meters? Maybe take this out.
        if unit is None:
            unit = 'esriMeters'
        else:
            assert unit in self.allowed_units, "Unit %r not valid" % unit
        self.distance, self.units = value, unit
    @property
    def _json_struct(self):
        return {'distance': self.distance, 'units': self.units}
    @classmethod
    def fromJson(cls, val):
        return cls(val['distance'], val['units'])

def rowtuple(colnames):
    import operator
    class RowTuple(tuple):
        def __new__(cls, *values):
            return tuple.__new__(cls, *values)
    for i, col in enumerate(colnames):
        setattr(RowTuple, col, property(operator.itemgetter(i)))
    RowTuple.__slots__ = ()
    return RowTuple

@GPBaseType._register_type
class GPFeatureRecordSetLayer(GPBaseType):
    """Represents a geoprocessing feature recordset parameter"""
    _columns = None
    def __init__(self, Geometry, sr=None):
        if isinstance(Geometry, geometry.Geometry):
            Geometry = [Geometry]
        self._features = Geometry
        if sr:
            self.spatialReference = geometry.SpatialReference(sr)
        elif getattr(self, '_features', None) and len(self._features):
            self.spatialReference = geometry.SpatialReference(
                                        self._features[0].spatialReference)
        else:
            raise ValueError("Could not determine spatial reference")
        if self._columns is None and self._features:
            _columns = sorted(reduce(lambda x, y: x | y, 
                                   (set(getattr(row, 'attributes', {}).keys())
                                   for row in self._features)))
            if 'shape' not in (col.lower() for col in _columns):
                _columns = ['shape'] + _columns
            self._columns = tuple(_columns)
    @property
    def features(self):
        return list(self)
    def __iter__(self):
        return ({'geometry': feature, 
                 'attributes': getattr(feature, 'attributes', {})} 
                 for feature in self._features)
    @property
    def _json_struct(self):
        geometry_types = set(geom.__geometry_type__ for geom in self._features)
        assert len(geometry_types) == 1, "Must have consistent geometries"
        geometry_type = list(geometry_types)[0]
        return {
                    'geometryType': geometry_type,
                    'spatialReference': self.spatialReference._json_struct,
                    'features': [
                        x._json_struct_for_featureset for x in self._features]
               }
    @classmethod
    def fromJson(cls, value):
        spatialreference = geometry.fromJson(value['spatialReference']) \
            if 'spatialReference' in value else None
        geometries = [geometry.Polyline.fromCompressedGeometry(
                            geo['compressedGeometry'], geo['attributes'])
                      if "compressedGeometry" in geo
                      else geometry.fromJson(geo['geometry'], geo['attributes']) 
                      for geo in value['features']]
        return cls(geometries, spatialreference)

@GPBaseType._register_type
class GPRecordSet(GPBaseType):
    """Represents a geoprocessing recordset parameter"""
    _columns = None
    def __init__(self, arg, exceededTransferLimit=None):
        self.features = arg
        self._exceededTransferLimit = exceededTransferLimit
        if self._columns is None:
            _columns = sorted(reduce(lambda x, y: x | y, 
                                   (set(row['attributes'].keys()) 
                                   for row in self.features)))
            self._columns = tuple(_columns)
    def __iter__(self):
        return (feature for feature in self.features)
    @property
    def exceededTransferLimit(self):
        return self._exceededTransferLimit
    @classmethod
    def fromJson(cls, json):
        return cls(json['features'], json.get('exceededTransferLimit', None))
    @property
    def _json_struct(self):
        return { 'features': self.features }

@GPBaseType._register_type
class GPDate(GPBaseType):
    """Represents a geoprocessing date parameter. The format parameter
       in the object constructor varies from the REST API's format parameters
       in that each date field in the format string must be preceded by a
       percent sign, as in the strftime function. For further information
       about Python strftime format strings, please refer to
       http://docs.python.org/library/time.html#time.strftime"""
    #: default date format
    __date_format = "%a %b %d %H:%M:%S %Z %Y"
    #: secondary (fallback) date formats
    __secondary_date_formats = ["%c",
                                "%Y%m%dT%H:%M:%S",
                                "%Y-%m-%d %H:%M:%S",
                                "%m/%d/%Y %I:%M:%S %p"]
    def __init__(self, date, format=None):
        if isinstance(date, basestring):
            try:
                self.date = datetime.datetime.strptime(date, format)
            except (ValueError, TypeError) as e:
                try:
                    self.date = datetime.datetime.strptime(date, 
                                                           self.__date_format)
                    self.format = self.__date_format
                except ValueError:
                    for sformat in self.__secondary_date_formats:
                        try:
                            self.date = datetime.datetime.strptime(date, sformat)
                            self.format = format
                        except ValueError:
                            pass
                    if not getattr(self, 'date', None):
                        try:
                            import utils
                            self.date = utils.timetopythonvalue(date)
                        except:
                            pass
                        raise ValueError("Cannot convert %r to date" % date)
        elif isinstance(date, (datetime.date, datetime.datetime)):
            self.date = date
        else:
            try:
                import utils
                self.date = utils.timetopythonvalue(date)
            except:
                raise ValueError("Cannot convert %r to a date" % date)
        self.format = format
    @property
    def _json_struct(self):
        if self.format:
            return {'date': self.date.strftime(self.format),
                    'format': self.format.replace('%', '')}
        else:
            import utils
            return utils.pythonvaluetotime(self.date)
        #return self.date.strftime(self.__date_format)
    @classmethod
    def fromJson(cls, value):
        if isinstance(value, dict):
            datestring = value['date']
            formatstring = value['format']
            # Re-escape field names from formats like Y-m-d back to
            # strftime-style %Y-%m-%d strings
            for chr in "%aAbBcdHIjmMpSUwWxXyYZ":
                formatstring = formatstring.replace(chr, '%'+chr)
            return cls(datestring, formatstring)
        elif isinstance(value, basestring):
            return cls(value, cls.__date_format)

@GPBaseType._register_type
class GPDataFile(GPBaseType):
    """A URL for a geoprocessing data file parameter"""
    #: The URL of the data file
    url = ''
    def __init__(self, url):
        self.url = url
    @property
    def _json_struct(self):
        return {'url': self.url}
    @classmethod
    def fromJson(cls, value):
        return cls(value['url'])

class GPUrlWithFormatType(GPBaseType):
    """A class for representing Raster data and Raster layers -- both have a 
       URL and a Format attribute."""
    #: The URL of the resource
    url = ''
    #: The data format of the raster: jpeg, png, etc.
    format = ''
    def __init__(self, url, format):
        self.url, self.format = url, format
    @property
    def _json_struct(self):
        return {'url': self.url, 'format': self.format}
    @classmethod
    def fromJson(cls, value):
        return cls(value['url'], value['format'])

@GPBaseType._register_type
class GPRasterData(GPUrlWithFormatType):
    """A URL for a geoprocessing raster data file parameter, with format."""

@GPBaseType._register_type
class GPRasterDataLayer(GPUrlWithFormatType):
    """A URL for a geoprocessing raster data layer file parameter,
       with format."""

__all__ = sorted(GPBaseType._gp_type_mapping) + ['GPMultiValue']
