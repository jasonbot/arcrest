from arcrest import geometry, gptypes, server
import base64
import graphics
import time
import Tkinter

try:
    from PIL.ImageTk import PhotoImage
    has_PIL = True
except ImportError, e:
    from Tkinter import PhotoImage
    import base64
    has_PIL = False

"""A collection of Tkinter classes for displaying a dynamic map service"""

class MapActionButton(object):
    action = True
    @staticmethod
    def do(mapcanvas):
        pass

class MapCanvasMethods(object):
    action = False
    @staticmethod
    def move(mapcanvas, event):
        pass
    @staticmethod
    def drag(mapcanvas, event):
        pass
    @staticmethod
    def click(mapcanvas, event):
        pass
    @staticmethod
    def unclick(mapcanvas, event):
        pass
    @staticmethod
    def doubleclick(mapcanvas, event):
        pass
    @staticmethod
    def unfocus(mapcanvas):
        pass

class MapSelectPoint(MapCanvasMethods):
    @classmethod
    def unclick(cls, mapcanvas, event):
        point = mapcanvas.pixelToPointCoord(event.x, event.y)
        cls.do(mapcanvas, point)
    @staticmethod
    def do(mapcanvas, pt):
        pass

class BoxSelection(MapCanvasMethods):
    @classmethod
    def click(cls, mapcanvas, event):
        if hasattr(mapcanvas, 'boxselection'):
            mapcanvas.delete(mapcanvas.boxselection['rect'])
            del mapcanvas.boxselection
        mapcanvas.boxselection = {}
        mapcanvas.boxselection['rect'] = mapcanvas.create_rectangle(
                                                                event.x, event.y,
                                                                event.x, event.y)
        mapcanvas.boxselection['start'] = (event.x, event.y)
        mapcanvas.boxselection['end'] = (event.x, event.y)
        mapcanvas.boxselection['cls'] = cls
    @staticmethod
    def drag(mapcanvas, event):
        mapcanvas.boxselection['end'] = (event.x, event.y)
        x1, y1 = mapcanvas.boxselection['start']
        x2, y2 = mapcanvas.boxselection['end']
        mapcanvas.coords(mapcanvas.boxselection['rect'], x1, y1, x2, y2)
    @staticmethod
    def unclick(mapcanvas, event):
        mapcanvas.delete(mapcanvas.boxselection['rect'])
        x1, y1 = mapcanvas.pixelToPointCoord(*mapcanvas.boxselection['start'])
        x2, y2 = mapcanvas.pixelToPointCoord(*mapcanvas.boxselection['end'])
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))
        newextent = geometry.Envelope(x1, y1, x2, y2, 
                                      mapcanvas.parent.extent.spatialReference)
        cls = mapcanvas.boxselection['cls']
        del mapcanvas.boxselection
        cls.selectedExtent(mapcanvas, newextent)
    @staticmethod
    def unfocus(mapcanvas):
        if hasattr(mapcanvas, 'boxselection'):
            mapcanvas.delete(mapcanvas.boxselection['rect'])
            del mapcanvas.boxseelction

class PanTool(MapCanvasMethods):
    toolname = "Pan"
    #toolgraphic = graphics.pan
    @staticmethod
    def drag(mapcanvas, event):
        oldx, oldy = mapcanvas.graphicoffset
        newx, newy = (oldx - (mapcanvas.clickpair[0] - event.x), 
                      oldy - (mapcanvas.clickpair[1] - event.y))
        mapcanvas.coords(mapcanvas.mapgraphicid, newx, newy)
        mapcanvas._graphicoffset = (newx, newy)
    @staticmethod
    def click(mapcanvas, event):
        mapcanvas.clickpair = (event.x, event.y)
    @staticmethod
    def unclick(mapcanvas, event):
        oldx, oldy = mapcanvas.graphicoffset
        newx, newy = mapcanvas._graphicoffset
        pixdiff = abs(newx - oldx) + abs(newy - oldy)
        # Don't need to refresh map, just snap back if it's a small move
        if pixdiff > 8:
            oldoffset = mapcanvas.graphicoffset
            mapcanvas.graphicoffset = mapcanvas._graphicoffset
            newbox = mapcanvas.panExtent()
            top = newbox.top
            bottom = newbox.bottom
            if top not in mapcanvas.parent.service.fullExtent or \
               bottom not in mapcanvas.parent.service.fullExtent:
                mapcanvas.graphicoffset = oldoffset
                oldx, oldy = mapcanvas.graphicoffset
                mapcanvas.coords(mapcanvas.mapgraphicid, oldx, oldy)
            else:
                mapcanvas.extent = newbox
                mapcanvas.updateGraphics()
        else:
            oldx, oldy = mapcanvas.graphicoffset
            mapcanvas.coords(mapcanvas.mapgraphicid, oldx, oldy)

class ZoomInTool(BoxSelection):
    toolname = "Zoom In"
    #toolgraphic = graphics.zoominframe
    @staticmethod
    def selectedExtent(mapcanvas, extent):
        mapcanvas.extent = extent
        mapcanvas.updateGraphics()

class ZoomOutTool(BoxSelection):
    toolname = "Zoom Out"
    #toolgraphic = graphics.zoomoutframe
    @staticmethod
    def selectedExtent(mapcanvas, extent):
        xmin, xmax = sorted((mapcanvas.extent.xmin, mapcanvas.extent.xmax))
        ymin, ymax = sorted((mapcanvas.extent.ymin, mapcanvas.extent.ymax))
        x1d = xmin - (xmin - extent.xmin)
        y1d = ymin + (ymin - extent.ymin)
        x2d = xmax - (xmax - extent.xmax)
        y2d = ymax + (ymax - extent.ymax)
        oe = mapcanvas.extent
        mapcanvas.extent = geometry.Envelope(x1d, y1d, x2d, y2d, 
                                             mapcanvas.extent.spatialReference)
        mapcanvas.updateGraphics()

class ZoomToExtent(MapActionButton):
    toolname = "Zoom to Full Extent"
    #toolgraphic = graphics.zoomtoextent
    @staticmethod
    def do(mapcanvas):
        mapcanvas.extent = mapcanvas.parent.service.fullExtent
        mapcanvas.updateGraphics()

class ZoomToInitialExtent(MapActionButton):
    toolname = "Zoom to Initial Extent"
    @staticmethod
    def do(mapcanvas):
        mapcanvas.extent = mapcanvas.parent.service.initialExtent
        mapcanvas.updateGraphics()

class ZoomIn50Percent(MapActionButton):
    toolname = "Zoom in 50%"
    #toolgraphic = graphics.zoomin
    @staticmethod
    def do(mapcanvas):
        x1, y1, x2, y2 = mapcanvas.extent.xmin, mapcanvas.extent.ymin, \
                         mapcanvas.extent.xmax, mapcanvas.extent.ymax
        qx = (x2 - x1)/4.
        qy = (y2 - y1)/4.
        mapcanvas.extent = geometry.Envelope(x1+qx, y1+qy, x2-qx, y2-qy)
        mapcanvas.updateGraphics()

class ZoomOut50Percent(MapActionButton):
    toolname = "Zoom out 50%"
    #toolgraphic = graphics.zoomout
    @staticmethod
    def do(mapcanvas):
        x1, y1, x2, y2 = mapcanvas.extent.xmin, mapcanvas.extent.ymin, \
                         mapcanvas.extent.xmax, mapcanvas.extent.ymax
        qx = (x2 - x1)/4.
        qy = (y2 - y1)/4.
        mapcanvas.extent = geometry.Envelope(x1-qx, y1-qy, x2+qx, y2+qy)
        mapcanvas.updateGraphics()

class MapCanvas(Tkinter.Canvas):
    def __init__(self, parent, width=800, height=600):
        self.action = None
        self.parent = parent
        self.width = width
        self.height = height
        self.extent = self.parent.service.initialExtent
        Tkinter.Canvas.__init__(self, parent, relief=Tkinter.SUNKEN,
                                borderwidth=2,
                                width=self.width, height=self.height)
        self.graphicoffset = (0, 0)
        self.bind("<Configure>", self.configure)
        self.bind("<Motion>", self.move)
        self.bind("<B1-Motion>", self.drag)
        self.bind("<Button-1>", self.click)
        self.bind("<ButtonRelease-1>", self.unclick)
        self.bind("<Double-Button-1>", self.doubleclick)
        self.graphics_stale = None
        self.feature_sets = []
        self.feature_set_ids = []
    def addFeatureSet(self, fs, **rendering):
        assert isinstance(fs, gptypes.GPFeatureRecordSetLayer)
        self.feature_sets.append((fs, rendering or {'width': 2,'fill': black}))
        self.updateFeatureSets()
    def configure(self, event):
        if (self.width, self.height) != (event.width, event.height):
            self.width, self.height = event.width, event.height
            if self.graphics_stale is not None:
                self.after_cancel(self.graphics_stale)
                self.graphics_stale = None
            self.graphics_stale = self.after(900, self.updateGraphics)
    def move(self, event):
        self.action.move(self, event)
    def drag(self, event):
        self.action.drag(self, event)
    def click(self, event):
        self.action.click(self, event)
    def unclick(self, event):
        self.action.unclick(self, event)
    def doubleclick(self, event):
        self.action.doubleclick(self, event)
    def pixelToPointCoord(self, x, y):
        adjx, adjy = x - self.graphicoffset[0], (self.height - y) - \
                                                self.graphicoffset[1]
        xoffset, xmultiplier = self.extent.xmin, \
                               self.extent.xmax - self.extent.xmin
        yoffset, ymultiplier = self.extent.ymin, \
                               self.extent.ymax - self.extent.ymin
        posx = xoffset + (adjx/float(self.width) * xmultiplier)
        posy = yoffset + (adjy/float(self.height) * ymultiplier)
        return geometry.Point(posx, posy, self.parent.extent.spatialReference)
    def pointToPixelCoord(self, pt):
        x, y = pt.x, pt.y
        xoffset, xmultiplier = self.extent.xmin, \
                               self.extent.xmax - self.extent.xmin
        yoffset, ymultiplier = self.extent.ymin, \
                               self.extent.ymax - self.extent.ymin
        projx = self.width*((x - xoffset)/xmultiplier)
        projy = self.height - self.height*((y - yoffset)/ymultiplier)
        return (projx, projy)
    def panExtent(self):
        ctr = self.pixelToPointCoord(self.width/2., self.height/2.)
        x = self.extent.xmin + (self.extent.xmax - self.extent.xmin)/2.
        y = self.extent.ymin + (self.extent.ymax - self.extent.ymin)/2.
        xd = x - ctr.x
        yd = ctr.y - y
        x1, x2 = (self.extent.xmin - xd, self.extent.xmax - xd)
        y1, y2 = (self.extent.ymin - yd, self.extent.ymax - yd)
        return geometry.Envelope(x1, y1, x2, y2, self.extent.spatialReference)
    def updateGraphics(self):
        text = self.create_text(self.width/2., 30, 
                                text='Loading...', fill='black',
                                anchor=Tkinter.SE)
        self.parent.update()
        try:
            self.extent, data = self.parent.mapGraphic(self.extent, "%i,%i"%
                                                     (self.width, self.height))
        except:
            pass
        self.delete(text)
        if hasattr(self, 'mapgraphic'):
            del self.mapgraphic
        if hasattr(self, 'mapgraphicid'):
            self.delete(self.mapgraphicid)
        self.mapgraphic = PhotoImage(data=data)
        self.mapgraphicid = self.create_image(0, 0, anchor=Tkinter.NW, 
                                              image=self.mapgraphic)
        self.graphicoffset = (0, 0)
        self.graphics_stale = None
        self.updateFeatureSets()
    def updateFeatureSets(self):
        for fs in self.feature_set_ids:
            self.delete(fs)
        for featureset, style in self.feature_sets:
            for geom in (row['geometry'] for row in featureset):
                if isinstance(geom, geometry.Point):
                    x, y = self.pointToPixelCoord(geom)
                    self.feature_set_ids.append(
                            self.create_rectangle(x-1,y-1,x+1,y+1, **style))
                elif isinstance(geom, geometry.Polyline):
                    for path in geom.paths:
                        pl = []
                        for pt in path:
                            map(pl.append, self.pointToPixelCoord(pt))
                        self.feature_set_ids.append(self.create_line(*pl, 
                                                                     **style))
                elif isinstance(geom, geometry.Polygon):
                    for ring in geom.rings:
                        pl = []
                        for pt in ring:
                            map(pl.append, self.pointToPixelCoord(pt))
                        self.feature_set_ids.append(self.create_polygon(*pl,
                                                                      **style))
                elif isinstance(geom, geometry.Multipoint):
                    for point in geom.points:
                        x, y = self.pointToPixelCoord(geom)
                        self.feature_set_ids.append(
                                self.create_rectangle(x-1,y-1,x+1,y+1, 
                                                      **style))
                else:
                    raise ValueError("What is %r?" % geom)

class DynamicMapServiceWindow(Tkinter.Frame):
    """A pre-built GUI class for displaying non-tiled map services."""
    tools = (PanTool, ZoomToExtent, ZoomToInitialExtent,
             ZoomInTool, ZoomIn50Percent, 
             ZoomOutTool, ZoomOut50Percent)
    def createWidgets(self, width, height):
        self.toolbar = Tkinter.Frame(self, relief=Tkinter.RAISED, 
                                     borderwidth=2)
        self.mappanel = MapCanvas(self, width, height)
        self.labelframe = Tkinter.Frame(self)
        self.toollabels = []
        # Set up top toolbar buttons
        for tool in self.tools:
            config = {'relief': Tkinter.RAISED, 'borderwidth': 2}
            if hasattr(tool, 'toolgraphic'):
                if not hasattr(tool, 'toolimage'):
                    if has_PIL:
                        tool.toolimage = PhotoImage(data=base64.b64decode(
                                                            tool.toolgraphic))
                    else:
                        tool.toolimage = PhotoImage(data=tool.toolgraphic)
                config['image'] = tool.toolimage
            else:
                config['text'] = tool.toolname
            label = Tkinter.Label(self.toolbar, **config)
            if not self.mappanel.action:
                self.mappanel.action = tool
                label.config(relief=Tkinter.SUNKEN)
            def selector(tool):
                def selection(ev):
                    oldaction = self.mappanel.action
                    if not tool.action:
                        self.mappanel.action = tool
                    lbl = None
                    oldlbl = None
                    for label, tool_ in self.toollabels:
                        label.config(relief=Tkinter.SUNKEN
                                     if tool_ == tool
                                     else Tkinter.RAISED)
                        if tool_ == tool:
                            lbl = label
                        if tool_ == oldaction:
                            oldlbl = label
                            tool_.unfocus(self)
                    if tool.action:
                        self.update()
                        try:
                            tool.do(self.mappanel)
                        except:
                            pass
                        lbl.config(relief=Tkinter.RAISED)
                        oldlbl.config(relief=Tkinter.SUNKEN)
                return selection
            label.pack(side=Tkinter.LEFT)
            label.bind("<Button-1>", selector(tool))
            self.toollabels.append((label, tool))

        # Set up layer view
        for layer in self.service.layers:
            def command(layer, var):
                def cmd():
                    if var.get() == "ON":
                        self.visiblelayers.add(layer.id)
                    else:
                        self.visiblelayers.remove(layer.id)
                    self.mappanel.updateGraphics()
                return cmd
            labelbutton = Tkinter.Checkbutton(self.labelframe, 
                                              text=layer.name,
                                              onvalue="ON",
                                              offvalue="OFF")
            var = Tkinter.StringVar(master=labelbutton, value="ON")
            labelbutton.config(command=command(layer, var), variable=var)
            labelbutton.pack(side=Tkinter.TOP)

    def doPack(self):
        self.labelframe.pack(side=Tkinter.LEFT, fill=Tkinter.Y)
        self.toolbar.pack(side=Tkinter.TOP, fill=Tkinter.X)
        self.mappanel.pack(side=Tkinter.BOTTOM, fill=Tkinter.BOTH)
    def __init__(self, service, width=800, height=600):
        self.root = Tkinter.Tk()
        assert isinstance(service, server.MapService)
        assert service._json_struct['singleFusedMapCache'] is False, \
            "This sample only works with dynamic map services"
        self.service = service
        self.visiblelayers = set(layer.id for layer in self.service.layers)
        self.extent = self.service.fullExtent
        self.root.title(self.service.mapName or self.service.description)
        Tkinter.Frame.__init__(self, self.root)
        self.createWidgets(width, height)
        self.doPack()
        self.pack(fill=Tkinter.BOTH)
        self.last_conf = time.time()
        self.later_id = None
    def mapGraphic(self, extent=None, size="800,600"):
        exported = self.service.ExportMap(bbox=extent,
                                          format=('gif' 
                                                   if not has_PIL 
                                                   else 'png24'), size=size,
                                          layers='show:%s'%','.join(
                                                sorted(str(id) for id in
                                                        self.visiblelayers)))
        self.width = exported.width
        self.height = exported.height
        self.extent = exported.extent
        if not has_PIL:
            data = base64.b64encode(exported.data)
        else:
            data = exported.data
        return exported.extent, data
