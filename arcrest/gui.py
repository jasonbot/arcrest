import geometry
import Tkinter
import server

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
    def do(self):
        pass

class MapCanvasMethods(object):
    action = False
    @staticmethod
    def move(self, event):
        pass
    @staticmethod
    def drag(self, event):
        pass
    @staticmethod
    def click(self, event):
        pass
    @staticmethod
    def unclick(self, event):
        pass
    @staticmethod
    def doubleclick(self, event):
        pass
    @staticmethod
    def unfocus(self):
        pass

class BoxSelection(MapCanvasMethods):
    @classmethod
    def click(cls, self, event):
        if hasattr(self, 'boxselection'):
            self.delete(self.boxselection['rect'])
            del self.boxselection
        self.boxselection = {}
        self.boxselection['rect'] = self.create_rectangle(event.x, event.y, 
                                                          event.x, event.y)
        self.boxselection['start'] = (event.x, event.y)
        self.boxselection['end'] = (event.x, event.y)
        self.boxselection['cls'] = cls
    @staticmethod
    def drag(self, event):
        self.boxselection['end'] = (event.x, event.y)
        x1, y1 = self.boxselection['start']
        x2, y2 = self.boxselection['end']
        self.coords(self.boxselection['rect'], x1, y1, x2, y2)
    @staticmethod
    def unclick(self, event):
        self.delete(self.boxselection['rect'])
        x1, y1 = self.pixelToPointCoord(*self.boxselection['start'])
        x2, y2 = self.pixelToPointCoord(*self.boxselection['end'])
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))
        newextent = geometry.Envelope(x1, y1, x2, y2, 
                                      self.parent.extent.spatialReference)
        cls = self.boxselection['cls']
        del self.boxselection
        cls.selectedExtent(self, newextent)
    @staticmethod
    def unfocus(self):
        if hasattr(self, 'boxselection'):
            self.delete(self.boxselection['rect'])
            del self.boxseelction

class PanTool(MapCanvasMethods):
    toolname = "Pan"
    @staticmethod
    def drag(self, event):
        oldx, oldy = self.graphicoffset
        newx, newy = (oldx - (self.clickpair[0] - event.x), 
                      oldy - (self.clickpair[1] - event.y))
        self.coords(self.mapgraphicid, newx, newy)
        self._graphicoffset = (newx, newy)
    @staticmethod
    def click(self, event):
        self.clickpair = (event.x, event.y)
    @staticmethod
    def unclick(self, event):
        oldx, oldy = self.graphicoffset
        newx, newy = self._graphicoffset
        pixdiff = abs(newx - oldx) + abs(newy - oldy)
        # Don't need to refresh map, just snap back if it's a small move
        if pixdiff > 8:
            oldoffset = self.graphicoffset
            self.graphicoffset = self._graphicoffset
            newbox = self.panExtent()
            top = newbox.top
            bottom = newbox.bottom
            if top not in self.parent.service.fullExtent or \
               bottom not in self.parent.service.fullExtent:
                self.graphicoffset = oldoffset
                oldx, oldy = self.graphicoffset
                self.coords(self.mapgraphicid, oldx, oldy)
            else:
                self.extent = newbox
                self.updateGraphics()
        else:
            oldx, oldy = self.graphicoffset
            self.coords(self.mapgraphicid, oldx, oldy)

class ZoomInTool(BoxSelection):
    toolname = "Zoom In"
    @staticmethod
    def selectedExtent(self, extent):
        self.extent = extent
        self.updateGraphics()

class ZoomOutTool(BoxSelection):
    toolname = "Zoom Out"
    @staticmethod
    def selectedExtent(self, extent):
        xmin, xmax = sorted((self.extent.xmin, self.extent.xmax))
        ymin, ymax = sorted((self.extent.ymin, self.extent.ymax))
        x1d = xmin - (xmin - extent.xmin)
        y1d = ymin + (ymin - extent.ymin)
        x2d = xmax - (xmax - extent.xmax)
        y2d = ymax + (ymax - extent.ymax)
        oe = self.extent
        self.extent = geometry.Envelope(x1d, y1d, x2d, y2d, 
                                        self.extent.spatialReference)
        self.updateGraphics()

class ZoomToExtent(MapActionButton):
    toolname = "Zoom to Extent"
    @staticmethod
    def do(self):
        self.extent = self.parent.service.fullExtent
        self.updateGraphics()

class ZoomIn50Percent(MapActionButton):
    toolname = "Zoom in 50%"
    @staticmethod
    def do(self):
        x1, y1, x2, y2 = self.extent.xmin, self.extent.ymin, \
                         self.extent.xmax, self.extent.ymax
        qx = (x2 - x1)/4.
        qy = (y2 - y1)/4.
        self.extent = geometry.Envelope(x1+qx, y1+qy, x2-qx, y2-qy)
        self.updateGraphics()

class ZoomOut50Percent(MapActionButton):
    toolname = "Zoom out 50%"
    @staticmethod
    def do(self):
        x1, y1, x2, y2 = self.extent.xmin, self.extent.ymin, \
                         self.extent.xmax, self.extent.ymax
        qx = (x2 - x1)/4.
        qy = (y2 - y1)/4.
        self.extent = geometry.Envelope(x1-qx, y1-qy, x2+qx, y2+qy)
        self.updateGraphics()

class MapCanvas(Tkinter.Canvas):
    def __init__(self, parent, width=800, height=600):
        self.action = None
        self.parent = parent
        self.width = width
        self.height = height
        self.extent = self.parent.service.fullExtent
        Tkinter.Canvas.__init__(self, parent, relief=Tkinter.SUNKEN,
                                borderwidth=2,
                                width=self.width, height=self.height)
        self.graphicoffset = (0, 0)
        self.bind("<Motion>", self.move)
        self.bind("<B1-Motion>", self.drag)
        self.bind("<Button-1>", self.click)
        self.bind("<ButtonRelease-1>", self.unclick)
        self.bind("<Double-Button-1>", self.doubleclick)
        self.updateGraphics()
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
        self.extent, data = self.parent.mapGraphic(self.extent, "%i,%i"%
                                                    (self.width, self.height))
        if hasattr(self, 'mapgraphic'):
            del self.mapgraphic
        if hasattr(self, 'mapgraphicid'):
            self.delete(self.mapgraphicid)
        self.mapgraphic = PhotoImage(data=data)
        self.mapgraphicid = self.create_image(0, 0, anchor=Tkinter.NW, 
                                              image=self.mapgraphic)
        self.graphicoffset = (0, 0)

class MapServiceWindow(Tkinter.Frame):
    """A pre-built GUI class for displaying non-tiled map services."""
    tools = (PanTool, ZoomToExtent, 
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
                config['image'] = PhotoImage(data=tool.toolgraphic)
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
                        tool.do(self.mappanel)
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

        self.labelframe.pack(side=Tkinter.LEFT, fill=Tkinter.Y)
        self.toolbar.pack(side=Tkinter.TOP, fill=Tkinter.X)
        self.mappanel.pack(side=Tkinter.BOTTOM)
    def __init__(self, service, width=800, height=600):
        root = Tkinter.Tk()
        assert isinstance(service, server.MapService)
        assert service._json_struct['singleFusedMapCache'] is False, \
            "This sample only works with dynamic map services"
        self.service = service
        self.visiblelayers = set(layer.id for layer in self.service.layers)
        self.extent = self.service.fullExtent
        root.title(self.service.mapName or self.service.description)
        Tkinter.Frame.__init__(self, root)
        self.createWidgets(width, height)
        self.pack()
        root.wm_resizable(None, None)        
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
