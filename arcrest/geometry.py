# coding: utf-8
"""This module implements the JSON geometry and spatial reference objects 
   as returned by the REST API. The REST API supports 4 geometry types - 
   points, polylines, polygons and envelopes."""

import json

from .projections import projected, geographic

def pointlist(points, sr):
    """Convert a list of the form [[x, y] ...] to a list of Point instances
       with the given x, y coordinates."""
    assert all(isinstance(pt, Point) or len(pt) == 2 
               for pt in points), "Point(s) not in [x, y] form"
    return [coord if isinstance(coord, Point) 
                  else Point(coord[0], coord[1], sr)
            for coord in points]

def listofpointlist(ptlist, sr):
    """Convert a list of the form [[[x, y] ...] ...] to a list of lists of 
       Point instances with the given x, y coordinates."""
    return [pointlist(listofpoints, sr) for listofpoints in ptlist]

class Geometry(object):
    """Represents an abstract base for json-represented geometries on
       the ArcGIS Server REST API. Please refer to 
       L{Point<arcrest.geometry.Point>}, 
       L{Multipoint<arcrest.geometry.Multipoint>},
       L{Polygon<arcrest.geometry.Polygon>},
       L{Polyline<arcrest.geometry.Polyline>} and 
       L{Envelope<arcrest.geometry.Envelope>} in this module for more
       information on geometry types. Calling the str() operator on any
       geometry subclass will return a WKT string for the geometry."""
    def __init__(self):
        raise NotImplementedError("Cannot instantiate abstract geometry type")
    def __len__(self):
        raise NotImplementedError("Length not implemented for %r" % 
                                   self.__class__.__name__)
    @property
    def __geo_interface__(self):
        raise NotImplementedError("Unimplemented conversion to GeoJSON")
    @property
    def _json_struct_without_sr(self):
        return self._json_struct
    @property
    def _json_struct(self):
        raise NotImplementedError("Unimplemented conversion to JSON")
    @property
    def _json_struct_without_sr(self):
        raise NotImplementedError("Unimplemented conversion to JSON")
    @property
    def _json_struct_for_featureset(self):
        return { 'geometry': self._json_struct_without_sr,
                 'attributes': getattr(self, 'attributes', {})}
    def __str__(self):
        return json.dumps(self._json_struct)
    @classmethod
    def fromJson(cls, struct):
        raise NotImplementedError("Unimplemented convert from JSON")
    @classmethod
    def fromGeoJson(cls, struct):
        raise NotImplementedError("Unimplemented convert from GeoJSON")

class NullGeometry(Geometry):
    "Represents a null or empty geometry."
    def __init__(self, struct=None):
        pass
    @property
    def __geo_interface__(self):
        return None
    @property
    def _json_struct(self):
        return None
    def __repr__(self):
        return "NULL GEOMETRY"

class SpatialReference(Geometry):
    """The REST API only supports spatial references that have well-known 
       IDs associated with them. Given this constraint, a spatial reference
       object only contains one field - wkid (i.e. the well-known ID of the
       spatial reference).

       For a list of valid WKID values, see projected and 
       projections.graphic in this package."""
    def __init__(self, wkid):
        """Create a new Spatial Reference.
           
                >>> import arcrest
                >>> mysr = arcrest.geometry.SpatialReference(4326)
                >>> mysr.name
                'GCS_WGS_1984'
                >>> mysr.wkid
                4326
                >>> myothersr = arcrest.geometry.SpatialReference(mysr)
                >>> myothersr.wkid
                4326

           @param wkid: The Well-known ID of the target spatial reference
                        (or another instance of SpatialReference)
           """
        if isinstance(wkid, SpatialReference):
            wkid = wkid.wkid
        elif isinstance(wkid, dict):
            wkid = wkid['wkid']
        elif hasattr(projected, str(wkid)):
            wkid = getattr(projected, str(wkid))
        elif hasattr(geographic, str(wkid)):
            wkid = getattr(geographic, str(wkid))
        elif wkid is None:
            self.wkid = None
            return
        if wkid is not None:
            wkid = int(wkid)
        self.wkid = wkid
    def __repr__(self):
        return "<Spatial Reference %r>" % self.wkid
    def __len__(self):
        if self.wkid is None:
            return 0
        else:
            return 1
    @property
    def _json_struct(self):
        return {'wkid': self.wkid}
    def __eq__(self, other):
        if isinstance(other, SpatialReference):
            return self.wkid == other.wkid
        return self.wkid == other
    @property
    def name():
        "Get/view the name for the well known ID of a Projection"
        if self.wkid in projected:
            return projected[self.wkid]
        elif self.wkid in geographic:
            return geographic[self.wkid]
        else:
            raise KeyError("Not a known WKID.")
    @name.setter
    def name(self, wkid):
        if hasattr(projected, wkid):
            self.wkid = getattr(projected, wkid)
        elif hasattr(geographic, wkid):
            self.wkid = getattr(geographic, wkid)
        else:
            raise KeyError("Not a known projection name.")
    @classmethod
    def fromJson(cls, struct):
        return cls(int(struct['wkid']))

class Point(Geometry):
    """A point contains x and y fields along with a spatialReference field."""
    __geometry_type__ = "esriGeometryPoint"
    def __init__(self, x, y, spatialReference=None):
        """
        @param x: The X coordinate of the Point
        @param y: The Y coordinate of the Point
        @param spatialReference: The spatial reference, either as an instance
               of L{SpatialReference<arcpy.geometry.SpatialReference>} or the
               WKID of a spatial reference. If left as None, the point will not
               have a spatial reference.
               
                    >>> mysr = arcrest.geometry.SpatialReference(4326)
                    >>> arcrest.geometry.Point(10, 10, mysr)
                    POINT(10.00000 10.00000)
               """
        if not isinstance(spatialReference, SpatialReference):
            spatialReference = SpatialReference(spatialReference)
        self.x, self.y, self.spatialReference = \
            float(x), float(y), spatialReference
    def __repr__(self):
        return "POINT(%s %s)" %(("%0.5f" % self.x)
                                           if isinstance(self.x, float)
                                           else str(self.x),
                                ("%0.5f" % self.y)
                                           if isinstance(self.y, float)
                                           else str(self.y))
    def __len__(self):
        return 2
    def __iter__(self):
        yield self.x
        yield self.y
    def __getitem__(self, index):
        return [self.x, self.y][index]
    @property
    def __geo_interface__(self):
        retval = {
            'type': 'Point',
            'coordinates': [self.x, self.y]
        }
        if hasattr(self, 'attributes'):
            retval['properties'] = self.attributes
        if self.spatialReference:
            retval['@esri.sr'] = self.spatialReference._json_struct
        return retval
    @property
    def _json_struct_without_sr(self):
        return {'x': self.x,
                'y': self.y}
    @property
    def _json_struct(self):
        return {'x': self.x,
                'y': self.y,
                'spatialReference': None \
                                    if self.spatialReference is None \
                                    else self.spatialReference._json_struct}
    @classmethod
    def fromJson(cls, struct):
        if isinstance(struct, (list, tuple)) and len(struct) == 2:
            return cls(*struct)
        else:
            return cls(**struct)
    @classmethod
    def fromGeoJson(cls, struct):
        (x, y) = struct['coordinates']
        return [cls(x, y)]

class Polyline(Geometry):
    """A polyline contains an array of paths and a spatialReference. Each 
       path is represented as an array of points. And each point in the path is
       represented as a 2-element array. The 0-index is the x-coordinate and
       the 1-index is the y-coordinate."""
    __geometry_type__ = "esriGeometryPolyline"
    def __init__(self, paths=[], spatialReference=None):
        """
        @param paths: A list of lists of points. Actual acceptable values are
                      fairly permissive, allowing for any iterable item 
                      (list, tuple, generator) containing any number of 
                      iterables containing instances of 
                      L{Point<arcrest.geometry.Point>} or lists/tuples of
                      exactly two items, representing a coordinate pair.

        @param spatialReference: A spatial reference passed in as an instance
                                 of SpatialReference or the WKID of a spatial
                                 reference. If this is not set, the Polyline
                                 will not have a spatial reference and if the
                                 polyline is used in a context where a spatial
                                 reference is required, it will attempt to
                                 guess the spatial reference from the set
                                 spatial reference of a constitutent point.
        """
        if not isinstance(spatialReference, SpatialReference):
            spatialReference = SpatialReference(spatialReference)
        self.spatialReference = spatialReference
        self.paths = listofpointlist(paths, spatialReference)
    def __repr__(self):
        return "MULTILINESTRING(%s)" % " ".join(
                                        "(%s)"%"".join(
                                           ",".join(
                                                " ".join("%0.5f"%x 
                                                       if isinstance(x, float)
                                                       else str(x) for x in pt)
                                            for pt in path)) 
                                        for path in self._json_paths)
    def __len__(self):
        return len(self.paths)
    @property
    def __geo_interface__(self):
        retval = {
            'type': 'MultiLineString',
            'coordinates': self._json_paths
        }
        if hasattr(self, 'attributes'):
            retval['properties'] = self.attributes
        if self.spatialReference:
            retval['@esri.sr'] = self.spatialReference._json_struct
        return retval
    @property
    def _json_paths(self):
        def fixpath(somepath):
            for pt in somepath:
                if isinstance(pt, Point):
                    assert pt.spatialReference == None or\
                        pt.spatialReference == self.spatialReference, \
                        "Point is not in same spatial reference as Polyline"\
                        "(%r, %r)" % (pt.spatialReference, 
                                      self.spatialReference)
                    yield [pt.x, pt.y]
                else:
                    yield list(pt)
        return [list(fixpath(path)) for path in self.paths]
    @property
    def _json_struct_without_sr(self):
        return {'paths': self._json_paths}
    @property
    def _json_struct(self):
        return {'paths': self._json_paths,
                'spatialReference': self.spatialReference._json_struct}
    @classmethod
    def fromJson(cls, struct):
        return cls(**struct)
    @classmethod
    def fromGeoJson(cls, struct):
        if struct['type'] == "LineString":
            return [cls([struct['coordinates']])]
        elif struct['type'] == "MultiLineString":
            return [cls(struct['coordinates'])]
    @classmethod
    def fromCompressedGeometry(cls, compressedstring, attributes=None):
        result = []
        import re
        ints = [(-1 if number[0] == '-' else 1) * int(number[1:], 32)
                   for number in re.findall("([+-][a-v0-9]*)",
                                            compressedstring)]
        multiplier = float(ints.pop(0))
        oldx, oldy = 0, 0
        while ints:
            x, y = ints[:2]
            ints = ints[2:]
            x += oldx
            y += oldy
            result.append(Point(x/multiplier, y/multiplier))
            oldx, oldy = x, y
        retval = cls([result])
        if attributes:
            retval.attributes = attributes
        return retval
    def asCompressedGeometry(self, multiplier=55000):
        def base32(num):
            sign = "+" if num >= 0 else "-"
            if num < 0:
                num = -num
            digits = "0123456789abcdefghijklmnopqrstuv"
            nums = []
            while num:
                nums.append(num & 0x1F)
                num = num >> 5
            return sign + ''.join(digits[x] for x in reversed(nums))
        def compressedstring():
            yield base32(multiplier)
            oldx, oldy = 0, 0
            for ints in self._json_paths:
                for (x, y) in ints:
                    yield base32(int((x - oldx)*multiplier))
                    yield base32(int((y - oldy)*multiplier))
                    oldx, oldy = x, y
        return ''.join(compressedstring())

class Polygon(Geometry):
    """A polygon contains an array of rings and a spatialReference. Each ring 
       is represented as an array of points. The first point of each ring is
       always the same as the last point. And each point in the ring is 
       represented as a 2-element array. The 0-index is the x-coordinate and
       the 1-index is the y-coordinate."""
    __geometry_type__ = "esriGeometryPolygon"
    def __init__(self, rings=[], spatialReference=None):
        """
        @param rings: A list of lists of points. Actual acceptable values are
                      fairly permissive, allowing for any iterable item 
                      (list, tuple, generator) containing any number of 
                      iterables containing instances of 
                      L{Point<arcrest.geometry.Point>} or lists/tuples of
                      exactly two items, representing a coordinate pair. Note
                      that the first and last point of each ring I{must} be
                      the same.

        @param spatialReference: A spatial reference passed in as an instance
                                 of SpatialReference or the WKID of a spatial
                                 reference. If this is not set, the Polyline
                                 will not have a spatial reference and if the
                                 polyline is used in a context where a spatial
                                 reference is required, it will attempt to
                                 guess the spatial reference from the set
                                 spatial reference of a constitutent point.
        """
        if not isinstance(spatialReference, SpatialReference):
            spatialReference = SpatialReference(spatialReference)
        self.spatialReference = spatialReference
        self.rings = listofpointlist(rings, spatialReference)
    def __repr__(self):
        return "POLYGON(%s)" % " ".join(
                                        "(%s)"%"".join(
                                           ",".join(
                                                " ".join("%0.5f"%x 
                                                      if isinstance(x, float)
                                                      else str(x) for x in pt)
                                            for pt in ring)) 
                                        for ring in self._json_rings)
    def __len__(self):
        return len(self.rings)
    @property
    def __geo_interface__(self):
        retval = {
            'type': 'Polygon',
            'coordinates': self._json_rings
        }
        if hasattr(self, 'attributes'):
            retval['properties'] = self.attributes
        if self.spatialReference:
            retval['@esri.sr'] = self.spatialReference._json_struct
        return retval
    def contains(self, pt):
        "Tests if the provided point is in the polygon."
        if isinstance(pt, Point):
            ptx, pty = pt.x, pt.y
            assert (self.spatialReference is None or \
                    self.spatialReference.wkid is None) or \
                    (pt.spatialReference is None or \
                     pt.spatialReference.wkid is None) or \
                   self.spatialReference == pt.spatialReference, \
                   "Spatial references do not match."
        else:
            ptx, pty = pt
        in_shape = False
        # Ported nearly line-for-line from the Javascript API
        for ring in self._json_rings:
            for idx in range(len(ring)):
                idxp1 = idx + 1
                if idxp1 >= len(ring):
                    idxp1 -= len(ring)
                pi, pj = ring[idx], ring[idxp1]
                # Divide-by-zero checks
                if (pi[1] == pj[1]) and pty >= min((pi[1], pj[1])):
                    if ptx >= max((pi[0], pj[0])):
                        in_shape = not in_shape
                elif (pi[0] == pj[0]) and pty >= min((pi[0], pj[0])):
                    if ptx >= max((pi[1], pj[1])):
                        in_shape = not in_shape
                elif (((pi[1] < pty and pj[1] >= pty) or 
                     (pj[1] < pty and pi[1] >= pty)) and 
                    (pi[0] + (pty - pi[1]) / 
                     (pj[1] - pi[1]) * (pj[0] - pi[0]) < ptx)):
                    in_shape = not in_shape
        return in_shape
    def __contains__(self, pt):
        return self.contains(pt)
    @property
    def _json_rings(self):
        def fixring(somering):
            for pt in somering:
                if isinstance(pt, Point):
                    assert pt.spatialReference == None or \
                        pt.spatialReference == self.spatialReference, \
                        "Point is not in the same spatial reference as Polygon"
                    yield [pt.x, pt.y]
                else:
                    yield list(pt)
        return [list(fixring(ring)) for ring in self.rings]
    @property
    def _json_struct_without_sr(self):
        return {'rings': self._json_rings}
    @property
    def _json_struct(self):
        return {'rings': self._json_rings,
                'spatialReference': self.spatialReference._json_struct}
    @classmethod
    def fromJson(cls, struct):
        return cls(**struct)
    @classmethod
    def fromGeoJson(cls, struct):
        if struct['type'] == "MultiPolygon":
            return [cls(x) for x in struct['coordinates']]
        else:
            return [cls(struct['coordinates'])]

class Multipoint(Geometry):
    """A multipoint contains an array of points and a spatialReference. Each
       point is represented as a 2-element array. The 0-index is the
       x-coordinate and the 1-index is the y-coordinate."""
    def __init__(self, points=[], spatialReference=None):
        if not isinstance(spatialReference, SpatialReference):
            spatialReference = SpatialReference(spatialReference)
        self.spatialReference = spatialReference
        self.points = pointlist(points, spatialReference)
    def __repr__(self):
        return "MULTIPOINT(%s)" % ",".join("%0.5f %0.5f" % tuple(map(float,
                                                                     pt))
                                           for pt in self._json_points)
    def __len__(self):
        return len(self.points)
    @property
    def __geo_interface__(self):
        retval = {
            'type': 'MultiPoint',
            'coordinates': self._json_points
        }
        if hasattr(self, 'attributes'):
            retval['properties'] = self.attributes
        if self.spatialReference:
            retval['@esri.sr'] = self.spatialReference._json_struct
        return retval
    @property
    def _json_points(self):
        def fixpoint(somepointarray):
            for pt in somepointarray:
                if isinstance(pt, Point):
                    assert pt.spatialReference == None or \
                        pt.spatialReference == self.spatialReference, \
                        "Point is not in same spatial reference as Multipoint"
                    yield [pt.x, pt.y]
                else:
                    yield list(pt)
        return list(fixpoint(self.points))
    @property
    def _json_struct_without_sr(self):
        return {'points': self._json_points}
    @property
    def _json_struct(self):
        return {'points': self._json_points,
                'spatialReference': self.spatialReference._json_struct}
    @classmethod
    def fromJson(cls, struct):
        return cls(**struct)
    @classmethod
    def fromGeoJson(cls, struct):
        return [cls(struct['coordinates'])]

class Envelope(Geometry):
    """An envelope contains the corner points of an extent and is represented
       by xmin, ymin, xmax, and ymax, along with a spatialReference."""
    __geometry_type__ = "esriGeometryEnvelope"
    def __init__(self, xmin, ymin, xmax, ymax,
                 spatialReference=None):
        if not isinstance(spatialReference, SpatialReference):
            spatialReference = SpatialReference(spatialReference)
        self.spatialReference = spatialReference
        self.xmin, self.ymin, self.xmax, self.ymax = \
            float(xmin), float(ymin), float(xmax), float(ymax)
    def __contains__(self, pt):
        if isinstance(pt, Point):
            assert pt.spatialReference is None or \
                   self.spatialReference is None or\
                   pt.spatialReference == self.spatialReference, \
                   "Incompatible spatial reference for point"
            x, y = pt.x, pt.y
        else:
            x, y = pt[:2]
        return (self.xmax >= x >= self.xmin) and (self.ymax >= y >= self.ymin)
    def __bool__(self):
        return bool(self.wkid is not None)
    @property
    def __geo_interface__(self):
        retval = {
            'type': 'Box',
            'coordinates': [[self.xmin, self.ymin], [self.xmax, self.ymax]]
        }
        if hasattr(self, 'attributes'):
            retval['properties'] = self.attributes
        if self.spatialReference:
            retval['@esri.sr'] = self.spatialReference._json_struct
        return retval
    @property
    def top(self):
        return Point(self.xmin, self.ymin, self.spatialReference)
    @property
    def bottom(self):
        return Point(self.xmax, self.ymax, self.spatialReference)
    @property
    def _json_struct_without_sr(self):
        return {'xmin': self.xmin, 
                'ymin': self.ymin,
                'xmax': self.xmax,
                'ymax': self.ymax}
    @property
    def _json_struct(self):
        return {'xmin': self.xmin,
                'ymin': self.ymin,
                'xmax': self.xmax,
                'ymax': self.ymax,
                'spatialReference': self.spatialReference._json_struct}
    @property
    def bbox(self):
        "Return the envelope as a Bound Box string compatible with (bb) params"
        return ",".join(str(attr) for attr in 
                            (self.xmin, self.ymin, self.xmax, self.ymax))
    @classmethod
    def fromJson(cls, struct):
        return cls(**struct)
    @classmethod
    def fromGeoJson(cls, struct):
        ((xmin, ymin), (xmax, ymax)) = struct['coordinates']
        return [cls(xmin, ymin, xmax, ymax)]

def fromJson(struct, attributes=None):
    "Convert a JSON struct to a Geometry based on its structure"
    if isinstance(struct, basestring):
        struct = json.loads(struct)
    indicative_attributes = {
        'x': Point,
        'wkid': SpatialReference,
        'paths': Polyline,
        'rings': Polygon,
        'points': Multipoint,
        'xmin': Envelope
    }
    # bbox string
    if isinstance(struct, basestring) and len(struct.split(',')) == 4:
        return Envelope(*map(float, struct.split(',')))
    # Look for telltale attributes in the dict
    if isinstance(struct, dict):
        for key, cls in indicative_attributes.iteritems():
            if key in struct:
                ret = cls.fromJson(dict((str(key), value)
                                   for (key, value) in struct.iteritems()))
                if attributes:
                    ret.attributes = dict((str(key.lower()), val) 
                                           for (key, val)
                                           in attributes.iteritems())
                return ret
    raise ValueError("Unconvertible to geometry")

def fromGeoJson(struct, attributes=None):
    "Convert a GeoJSON-like struct to a Geometry based on its structure"
    if isinstance(struct, basestring):
        struct = json.loads(struct)
    type_map = {
        'Point': Point,
        'MultiLineString': Polyline,
        'LineString': Polyline,
        'Polygon': Polygon,
        'MultiPolygon': Polygon,
        'MultiPoint': Multipoint,
        'Box': Envelope
    }
    if struct['type'] == "Feature":
        return fromGeoJson(struct, struct.get('properties', None))
    elif struct['type'] == "FeatureCollection":
        sr = None
        if 'crs' in struct:
            sr = SpatialReference(struct['crs']['properties']['code'])
            members = map(fromGeoJson, struct['members'])
            for member in members:
                member.spatialReference = sr
            return members
        else:
            return map(fromGeoJson, struct['members'])
    elif struct['type'] in type_map and hasattr(type_map[struct['type']], 
                                              'fromGeoJson'):
        instances = type_map[struct['type']].fromGeoJson(struct)
        i = []
        assert instances is not None, "GeoJson conversion returned a Null geom"
        for instance in instances:
            if 'properties' in struct:
                instance.attributes = struct['properties'].copy()
                if '@esri.sr' in instance.attributes:
                    instance.spatialReference = SpatialReference.fromJson(
                                               instance.attributes['@esri.sr'])
                    del instance.attributes['@esri.sr']
            if attributes:
                if not hasattr(instance, 'attributes'):
                    instance.attributes = {}
                for k, v in attributes.iteritems():
                    instance.attributes[k] = v
            i.append(instance)
        if i:
            if len(i) > 1:
                return i
            return i[0]
    raise ValueError("Unconvertible to geometry")
