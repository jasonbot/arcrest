"""This module implements the JSON geometry and spatial reference objects 
   as returned by the REST API. The REST API supports 4 geometry types - 
   points, polylines, polygons and envelopes."""

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        raise ImportError("Please install the simplejson module "\
                          "from http://www.undefined.org/python/ "\
                          "or use arcrest with Python 2.6")

import projections

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
       the ArcGIS Server REST API. Please refer to Point, Multipoint,
       Polygon, Polyline and Envelope in this module for more information
       on geometry types."""
    def __init__(self):
        raise NotImplementedError("Cannot instantiate abstract geometry type")
    def __len__(self):
        raise NotImplementedError("Length not implemented for %r" % 
                                   self.__class__.__name__)
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
    def from_json_struct(cls, struct):
        raise NotImplementedError("Unimplemented convert from JSON")

class SpatialReference(Geometry):
    """The REST API only supports spatial references that have well-known 
       IDs associated with them. Given this constraint, a spatial reference
       object only contains one field - wkid (i.e. the well-known ID of the
       spatial reference).

       For a list of valid WKID values, see projections.Projected and 
       projections.Graphic in this package."""
    def __init__(self, wkid):
        if isinstance(wkid, SpatialReference):
            wkid = wkid.wkid
        elif isinstance(wkid, dict):
            wkid = wkid['wkid']
        elif hasattr(projections.Projected, str(wkid)):
            wkid = getattr(projections.Projected, str(wkid))
        elif hasattr(projections.Geographic, str(wkid)):
            wkid = getattr(projections.Geographic, str(wkid))
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
    @apply
    def name():
        def get_(self):
            "Get/view the name for the well known ID of a Projection"
            if self.wkid in projections.Projected:
                return projections.Projected[self.wkid]
            elif self.wkid in projections.Geographic:
                return projections.Geographic[self.wkid]
            else:
                raise KeyError("Not a known WKID.")
        def set_(self, wkid):
            if hasattr(projections.Projected, wkid):
                self.wkid = getattr(projections.Projected, wkid)
            elif hasattr(projections.Geographic, wkid):
                self.wkid = getattr(projections.Geographic, wkid)
            else:
                raise KeyError("Not a known projection name.")
        return property(get_, set_)
    @classmethod
    def from_json_struct(cls, struct):
        return cls(int(struct['wkid']))

class Point(Geometry):
    """A point contains x and y fields along with a spatialReference field."""
    __geometry_type__ = "esriGeometryPoint"
    def __init__(self, x, y, spatialReference=None):
        if not isinstance(spatialReference, SpatialReference):
            spatialReference = SpatialReference(spatialReference)
        self.x, self.y, self.spatialReference = \
            float(x), float(y), spatialReference
    def __repr__(self):
        return "POINT(%0.5f %0.5f)" %("%0.5f" % self.x if isinstance(self.x, float)
                                                else str(self.x),
                                      "%0.5f" % self.y if isinstance(self.y, float)
                                                else str(self.y))
    def __len__(self):
        return 2
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
    def from_json_struct(cls, struct):
        if isinstance(struct, (list, tuple)) and len(struct) == 2:
            return cls(*struct)
        else:
            return cls(**struct)

class Polyline(Geometry):
    """A polyline contains an array of paths and a spatialReference. Each 
       path is represented as an array of points. And each point in the path is
       represented as a 2-element array. The 0-index is the x-coordinate and
       the 1-index is the y-coordinate."""
    __geometry_type__ = "esriGeometryPolyline"
    def __init__(self, paths=[], spatialReference=None):
        if not isinstance(spatialReference, SpatialReference):
            spatialReference = SpatialReference(spatialReference)
        self.spatialReference = spatialReference
        self.paths = listofpointlist(paths, spatialReference)
    def __repr__(self):
        return "MULTILINESTRING(%s)" % " ".join(
                                        "(%s)"%"".join(
                                           ",".join(
                                                " ".join("%0.5f"%x if isinstance(x, float)
                                                            else str(x) for x in pt)
                                            for pt in path)) 
                                        for path in self._json_paths)
    def __len__(self):
        return len(self.paths)
    @property
    def _json_paths(self):
        def fixpath(somepath):
            for pt in somepath:
                if isinstance(pt, Point):
                    assert pt.spatialReference is None or \
                        pt.spatialReference == self.spatialReference, \
                        "Point is not in same spatial reference as Polyline"
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
    def from_json_struct(cls, struct):
        return cls(**struct)

class Polygon(Geometry):
    """A polygon contains an array of rings and a spatialReference. Each ring 
       is represented as an array of points. The first point of each ring is
       always the same as the last point. And each point in the ring is 
       represented as a 2-element array. The 0-index is the x-coordinate and
       the 1-index is the y-coordinate."""
    __geometry_type__ = "esriGeometryPolygon"
    def __init__(self, rings=[], spatialReference=None):
        if not isinstance(spatialReference, SpatialReference):
            spatialReference = SpatialReference(spatialReference)
        self.spatialReference = spatialReference
        self.rings = listofpointlist(rings, spatialReference)
    def __repr__(self):
        return "POLYGON(%s)" % " ".join(
                                        "(%s)"%"".join(
                                           ",".join(
                                                " ".join("%0.5f"%x if isinstance(x, float)
                                                            else str(x) for x in pt)
                                            for pt in ring)) 
                                        for ring in self._json_rings)
    def __len__(self):
        return len(self.rings)
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
                    assert pt.spatialReference is None or \
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
    def from_json_struct(cls, struct):
        return cls(**struct)

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
        return "MULTIPOINT(%s)" % ",".join("%0.5f %0.5f" % map(float, pt)
                                           for pt in self._json_points)
    def __len__(self):
        return len(self.points)
    @property
    def _json_points(self):
        def fixpoint(somepointarray):
            for pt in somepointarray:
                if isinstance(pt, Point):
                    assert pt.spatialReference is None or \
                        pt.spatialReference == self.spatialReference, \
                        "Point is not in same spatial reference as Multipoint"
                    yield [pt.x, pt.y]
                else:
                    yield list(pt)
        return list(fixpoints(self.points))
    @property
    def _json_struct_without_sr(self):
        return {'points': self._json_points}
    @property
    def _json_struct(self):
        return {'points': self._json_points,
                'spatialReference': self.spatialReference._json_struct}
    @classmethod
    def from_json_struct(cls, struct):
        return cls(**struct)

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
    def from_json_struct(cls, struct):
        return cls(**struct)

def fromJson(struct, attributes=None):
    "Convert a JSON struct to a Geometry based on its structure"
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
                ret = cls.from_json_struct(struct)
                if attributes:
                    ret.attributes = dict((key.lower(), val) 
                                           for key, val 
                                           in attributes.iteritems())
                return ret
    raise ValueError("Unconvertible to geometry")
