"""This module implements the JSON geometry and spatial reference objects as returned by the REST API. The REST API supports 4 geometry types - points, polylines, polygons and envelopes."""

class Geometry(object):
    """Represents an abstract base for geometries"""
    def __init__(self):
        raise ImplementationError("Cannot instantiate abstract geometry type")
    @property
    def _json_struct(self):
        raise ImplementationError("Unimplemented serialize to JSON")
    def __str__(self):
        try:
            import json
        except ImportError:
            try:
                import simplejson as json
            except ImportError:
                raise ImportError("Please install the simplejson module "\
                                  "from http://www.undefined.org/python/ "\
                                  "or use arcrest with Python 2.6")
        return json.dumps(self._json_struct)

class SpatialReference(Geometry):
    """The REST API only supports spatial references that have well-known IDs associated with them. Given this constraint, a spatial reference object only contains one field - wkid (i.e. the well-known ID of the spatial reference).

For a list of valid WKID values, see projections.Projected and projections.Graphic in this package."""
    def __init__(self, wkid):
        self.wkid = wkid
    @property
    def _json_struct(self):
        return {'wkid': self.wkid}
    def __eq__(self, other):
        if isinstance(other, SpatialReference):
            return self.wkid == other.wkid
        return self.wkid == other

class Point(Geometry):
    """A point contains x and y fields along with a spatialReference field."""
    __geometry_type__ = "esriGeometryPoint"
    def __init__(self, x, y, spatialReference=SpatialReference(4326)):
        if not isinstance(spatialReference, SpatialReference):
            spatialReference = SpatialReference(spatialReference)
        self.x, self.y, self.spatialReference = x, y, spatialReference
    @property
    def _json_struct(self):
        return {'x': self.x, 'y': self.y, 'spatialReference': self.spatialReference._json_struct}

class Polyline(Geometry):
    """A polyline contains an array of paths and a spatialReference. Each path is represented as an array of points. And each point in the path is represented as a 2-element array. The 0-index is the x-coordinate and the 1-index is the y-coordinate."""
    __geometry_type__ = "esriGeometryPolyline"
    def __init__(self, paths=[], spatialReference=SpatialReference(4326)):
        if not isinstance(spatialReference, SpatialReference):
            spatialReference = SpatialReference(spatialReference)
        self.spatialReference = spatialReference
        self.paths = paths
    @property
    def _json_paths(self):
        def fixpath(somepath):
            for pt in somepath:
                if isinstance(pt, Point):
                    assert pt.spatialReference is None or \
                        pt.spatialReference == self.spatialReference, \
                        "Point is not in the same spatial reference as Polyline"
                    yield [pt.x, pt.y]
                else:
                    yield list(pt)
        return [list(fixpath(path)) for path in self.paths]
    @property
    def _json_struct(self):
        return {'paths': self._json_paths, 'spatialReference': self.spatialReference._json_struct}

class Polygon(Polyline):
    """A polygon contains an array of rings and a spatialReference. Each ring is represented as an array of points. The first point of each ring is always the same as the last point. And each point in the ring is represented as a 2-element array. The 0-index is the x-coordinate and the 1-index is the y-coordinate."""
    __geometry_type__ = "esriGeometryPolygon"
    def __init__(self, rings=[], spatialReference=SpatialReference(4326)):
        if not isinstance(spatialReference, SpatialReference):
            spatialReference = SpatialReference(spatialReference)
        self.spatialReference = spatialReference
        self.rings = rings
    @property
    def _json_rings(self):
        def fixring(somering):
            for pt in somering:
                if isinstance(pt, Point):
                    assert pt.spatialReference is None or \
                        pt.spatialReference == self.spatialReference, \
                        "Point is not in the same spatial reference as Polygon"
                    yield [pt.x, pt.y]
                else:
                    yield list(pt)
        return [list(fixring(ring)) for ring in self.rings]
    @property
    def _json_struct(self):
        return {'rings': self._json_rings, 'spatialReference': self.spatialReference._json_struct}

class Multipoint(Geometry):
    """A multipoint contains an array of points and a spatialReference. Each point is represented as a 2-element array. The 0-index is the x-coordinate and the 1-index is the y-coordinate."""
    def __init__(self, points=[], spatialReference=SpatialReference(4326)):
        if not isinstance(spatialReference, SpatialReference):
            spatialReference = SpatialReference(spatialReference)
        self.spatialReference = spatialReference
        self.points = points
    @property
    def _json_points(self):
        def fixpoint(somepointarray):
            for pt in somepointarray:
                if isinstance(pt, Point):
                    assert pt.spatialReference is None or \
                        pt.spatialReference == self.spatialReference, \
                        "Point is not in the same spatial reference as Multipoint"
                    yield [pt.x, pt.y]
                else:
                    yield list(pt)
        return list(fixpoints(self.points))
    @property
    def _json_struct(self):
        return {'points': self._json_points, 'spatialReference': self.spatialReference._json_struct}

class Envelope(Geometry):
    """An envelope contains the corner points of an extent and is represented by xmin, ymin, xmax, and ymax, along with a spatialReference."""
    __geometry_type__ = "esriGeometryEnvelope"
    def __init__(self, xmin, ymin, xmax, ymax, spatialReference=SpatialReference(4326)):
        if not isinstance(spatialReference, SpatialReference):
            spatialReference = SpatialReference(spatialReference)
        self.spatialReference = spatialReference
        self.xmin, self.ymin, self.xmax, self.ymax = xmin, ymin, xmax, ymax
    @property
    def _json_struct(self):
        return {'xmin': self.xmin, 'ymin': self.ymin, 'xmax': self.xmax, 'ymax': self.ymax, 'spatialReference': self.spatialReference._json_struct}
