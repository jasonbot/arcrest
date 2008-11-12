"""This module provides a conversion layer for data types passed to/from
   Geoprocessing tasks on an ArcGIS REST server."""

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        raise ImportError("Please install the simplejson module "\
                          "from http://www.undefined.org/python/ "\
                          "or use arcrest with Python 2.6")

import datetime
import geometry
import uuid

class GPBaseType(object):
    """Base type for Geoprocessing argument types"""
    class __metaclass__(type):
        def __init__(cls, name, bases, dict):
            type.__init__(name, bases, dict)
            try:
                if '|' not in cls.__name__:
                    GPBaseType._gp_type_mapping[cls.__name__] = cls
            except:
                pass
    #: Mapping from Geoprocessing type to name
    _gp_type_mapping = {}

    def __str__(self):
        return json.dumps(self._json_struct)
    @classmethod
    def _from_json_def(cls, json):
        return cls

class GPSimpleType(GPBaseType):
    """For geoprocessing types that simplify to base Python types, such as 
       int, bool, or string."""
    __conversion__ = None
    def __init__(self, val):
        self.value = val
    @property
    def _json_struct(self):
        return self.__conversion__(self.value)
    @classmethod
    def from_json_struct(cls, value):
        return cls.__conversion__(value)

class GPBoolean(GPSimpleType):
    """Represents a geoprocessing boolean parameter"""
    __conversion__ = bool

class GPDouble(GPSimpleType):
    """Represents a geoprocessing double parameter"""
    __conversion__ = float

class GPLong(GPSimpleType):
    """Represents a geoprocessing long parameter"""
    __conversion__ = long

class GPString(GPSimpleType):
    """Represents a geoprocessing long parameter"""
    __conversion__ = str

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
            if not unit.startswith('esri'):
                unit = 'esri' + unit
            assert unit in self.allowed_units, "Unit %r not valid" % unit
        self.distance, self.units = value, unit
    @property
    def _json_struct(self):
        return {'distance': self.distance, 'units': self.units}
    @classmethod
    def from_json_struct(cls, val):
        return cls(val['distance'], val['units'])

class FieldType(object):
    """Base class for ESRI Field Types"""
    class __metaclass__(type):
        def __init__(cls, name, bases, dict):
            type.__init__(name, bases, dict)
            try:
                FieldType._field_type_mapping[cls.__name__] = cls
            except: # Throws if this is FieldType -- no FieldType.* yet
                pass
    #: Mapping from field type to name
    _field_type_mapping = {}

    @classmethod
    def value_for_string(cls, string):
        return string

class esriFieldTypeSmallInteger(FieldType):
    """0  Integer."""
    @classmethod
    def value_for_string(cls, string):
        return int(string)

class esriFieldTypeInteger(esriFieldTypeSmallInteger):
    """1  Long Integer."""

class esriFieldTypeSingle(FieldType):
    """2  Single-precision floating-point number."""
    @classmethod
    def value_for_string(cls, string):
        return double(string)

class esriFieldTypeDouble(esriFieldTypeSingle):
    """3  Double-precision floating-point number."""

class esriFieldTypeString(FieldType):
    """4  Character string."""
    @classmethod
    def value_for_string(cls, string):
        return str(string)

class esriFieldTypeDate(FieldType):
    """5  Date."""
    @classmethod
    def value_for_string(cls, string):
        return GPDate(string).date

class esriFieldTypeOID(esriFieldTypeInteger):
    """6  Long Integer representing an object identifier."""

class esriFieldTypeGeometry(FieldType):
    """7  Geometry."""
    @classmethod
    def value_for_string(cls, string):
        raise ValueError("Cannot instantiate a geometry field in this manner.")

class esriFieldTypeBlob(FieldType):
    """8  Binary Large Object."""
    @classmethod
    def value_for_string(cls, string):
        return str(string)

class esriFieldTypeRaster(FieldType):
    """9  Raster."""

class esriFieldTypeGUID(FieldType):
    """10  Globally Unique Identifier."""
    @classmethod
    def value_for_string(cls, string):
        return uuid.UUID(string)

class esriFieldTypeGlobalID(esriFieldTypeGUID):
    """11  ESRI Global ID."""

class esriFieldTypeXML(esriFieldTypeString):
    """12  XML Document"""

class RecordSetCursor(object):
    """Base class for iteration over Record Sets. Implements a subset of the
       Cursor section of the Python database API 2.0 (PEP 249)"""
    def __init__(self, obj):
        self.__recordset = obj
        self.__index = 0
        self.rowcount = len(obj.features)
    def __len__(self):
        return self.rowcount
    def __iter__(self):
        x = self.next()
        while x:
            yield x
            x = self.next()
    @property
    def __row(self):
        raise ImplementationError("Cursor cannot make a row")
    def reset(self):
        self.__index = 0
    def next(self):
        if self.__index < self.rowcount:
            row = self.__row
            self.__index += 1
            return row
        else:
            return None
    def fetchone(self):
        return self.next()
    def fetchmany(self, count=5):
        return [row for row in (self.next() for ctr in range(count))
                if row is not None]
    def fetchall(self):
        all = []
        for row in self:
            all.append(row)
        return all

class GPFeatureRecordSetCursor(RecordSetCursor):
    """A Feature set cursor"""

class GPFeatureRecordSetLayer(GPBaseType):
    """Represents a geoprocessing feature recordset parameter"""
    _columns = None
    def __init__(self, Geometry, sr=None):
        if isinstance(Geometry, geometry.Geometry):
            Geometry = [Geometry]
        self.features = Geometry
        if sr:
            self.spatialReference = geometry.SpatialReference(sr)
        elif len(self.features):
            self.spatialReference = geometry.SpatialReference(
                                        self.features[0].spatialReference)
        else:
            raise ValueError("Could not determine spatial reference")
        if self._columns is None:
            fieldlist = []
            fields = set()
            def adder(fieldname):
                if fieldname not in fields:
                    fieldlist.append(fieldname)
                    fields.add(fieldname)
            for row in self.features:
                map(adder, set(getattr(row, 'attributes', {}).keys()))
            self._columns = tuple((name, esriFieldTypeString) 
                                   for name in fieldlist)
    def __iter__(self):
        return iter(self.cursor())
    def cursor(self):
        return GPFeatureRecordSetCursor(self)
    @property
    def _json_struct(self):
        geometry_types = set(geom.__geometry_type__ for geom in self.features)
        assert len(geometry_types) == 1, "Must have consistent geometries"
        geometry_type = list(geometry_types)[0]
        return {
                    'geometryType': geometry_type,
                    'spatialReference': self.spatialReference._json_struct,
                    'features': [
                        x._json_struct_for_featureset for x in self.features]
               }
    @classmethod
    def from_json_struct(cls, value):
        spatialreference = geometry.convert_from_json(value['spatialReference'])
        geometries = [geometry.convert_from_json(geo['geometry'], 
                                                 geo['attributes']) 
                        for geo in value['features']]
        return cls(geometries, spatialreference)
    @classmethod
    def _from_json_def(cls, json):
        types = []
        for field in json['defaultValue'].get(
                'fields', json['defaultValue'].get('Fields', {})):
            types.append((field['name'], 
                          FieldType._field_type_mapping.get(
                                           field['type'], esriFieldTypeString)))
        nt = type("%s|%s" % (cls.__name__, 
                             ','.join(field[0] for field in types)),
                  (cls,), {})
        tps = tuple(types)
        nt._columns = tps
        return nt

class GPRecordSetCursor(RecordSetCursor):
    """A cursor"""

class GPRecordSet(GPBaseType):
    """Represents a geoprocessing recordset parameter"""
    _columns = None
    def __init__(self, arg):
        self.features = arg
        if self._columns is None:
            fieldlist = []
            fields = set()
            def adder(fieldname):
                if fieldname not in fields:
                    fieldlist.append(fieldname)
                    fields.add(fieldname)
            for row in self.features:
                map(adder, getattr(row, 'attributes', {}).keys())
            self._columns = tuple((name, esriFieldTypeString) 
                                  for name in fieldlist)
    def __iter__(self):
        return iter(self.cursor())
    def cursor():
        return GPRecordSetCursor(self)
    @classmethod
    def from_json_struct(cls, json):
        return cls(json['features'])
    @property
    def _json_struct(self):
        return { 'features': self.features }
    @classmethod
    def _from_json_def(cls, json):
        types = []
        for field in json['defaultValue'].get(
                'fields', json['defaultValue'].get('Fields', {})):
            types.append((field['name'], 
                          FieldType._field_type_mapping.get(
                                           field['type'], esriFieldTypeString)))
        nt = type("%s|%s" % (cls.__name__, 
                             ','.join(field[0] for field in types)),
                  (cls,), {})
        nt._columns = tuple(types)
        return nt

class GPDate(GPBaseType):
    """Represents a geoprocessing date parameter. The format parameter
       in the object constructor varies from the REST API's format parameters
       in that each date field in the format string must be preceded by a
       percent sign, as in the strftime function. For further information
       about Python strftime format strings, please refer to
       http://docs.python.org/library/time.html#time.strftime"""
    #: default date format
    __date_format = "%a %b %d %H:%M:%S %Z %Y"
    __secondary_date_format = "%m/%d/%Y %I:%M:%S %p"

    def __init__(self, date, format="%Y-%m-%d"):
        if isinstance(date, basestring):
            try:
                self.date = datetime.datetime.strptime(date, format)
            except ValueError:
                try:
                    self.date = datetime.datetime.strptime(date, 
                                                           self.__date_format)
                    self.format = self.__date_format
                except ValueError:
                    self.date = datetime.datetime.strptime(date, 
                                                   self.__secondary_date_format)
                    self.format = self.__secondary_date_format
        elif isinstance(date, (datetime.date, datetime.datetime)):
            self.date = date
        else:
            raise ValueError("Cannot convert %r to a date" % date)
        self.format = format
    @property
    def _json_struct(self):
        return {'date': self.date.strftime(self.format),
                'format': self.format.replace('%', '')}
        #return self.date.strftime(self.__date_format)
    @classmethod
    def from_json_struct(cls, value):
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

class GPDataFile(GPBaseType):
    """A URL for a geoprocessing data file parameter"""
    #: The URL of the data file
    url = ''
    def __init__(self, url):
        self.url = url
    def _json_struct(self):
        return {'url': self.url}
    @classmethod
    def from_json_struct(cls, value):
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
    def from_json_struct(cls, value):
        return cls(value['url'], value['format'])

class GPRasterData(GPUrlWithFormatType):
    """A URL for a geoprocessing raster data file parameter, with format."""

class GPRasterDataLayer(GPUrlWithFormatType):
    """A URL for a geoprocessing raster data layer file parameter,
       with format."""
