import base64
import geometry
import Tkinter
import server

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
                print str(self.parent.service.fullExtent), \
                      str(top), str(bottom)
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
        x1d = extent.xmin + (self.extent.xmin - extent.xmin)
        y1d = extent.ymin + (self.extent.ymin - extent.ymin)
        x2d = extent.xmax + (self.extent.xmax - extent.xmax)
        y2d = extent.ymax + (self.extent.ymax - extent.ymax)
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
    def __init__(self, parent):
        self.action = None
        self.parent = parent
        Tkinter.Canvas.__init__(self, parent, relief=Tkinter.SUNKEN,
                                borderwidth=2,
                                width=800, height=600)
        self.extent, data = self.parent.mapGraphic(
                                                self.parent.service.fullExtent)
        self.mapgraphic = Tkinter.PhotoImage(data=data)
        self.mapgraphicid = self.create_image(0, 0, anchor=Tkinter.NW, 
                                              image=self.mapgraphic)
        self.graphicoffset = (0, 0)
        self.bind("<Motion>", self.move)
        self.bind("<B1-Motion>", self.drag)
        self.bind("<Button-1>", self.click)
        self.bind("<ButtonRelease-1>", self.unclick)
        self.bind("<Double-Button-1>", self.doubleclick)
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
        adjx, adjy = x - self.graphicoffset[0], (600 - y) - \
                                                self.graphicoffset[1]
        xoffset, xmultiplier = self.extent.xmin, \
                               self.extent.xmax - self.extent.xmin
        yoffset, ymultiplier = self.extent.ymin, \
                               self.extent.ymax - self.extent.ymin
        posx = xoffset + (adjx/800. * xmultiplier)
        posy = yoffset + (adjy/600. * ymultiplier)
        return geometry.Point(posx, posy, self.parent.extent.spatialReference)
    def panExtent(self):
        ctr = self.pixelToPointCoord(400, 300)
        x = self.extent.xmin + (self.extent.xmax - self.extent.xmin)/2.
        y = self.extent.ymin + (self.extent.ymax - self.extent.ymin)/2.
        xd = x - ctr.x
        yd = ctr.y - y
        x1, x2 = (self.extent.xmin - xd, self.extent.xmax - xd)
        y1, y2 = (self.extent.ymin - yd, self.extent.ymax - yd)
        return geometry.Envelope(x1, y1, x2, y2, self.extent.spatialReference)
    def updateGraphics(self):
        self.extent, data = self.parent.mapGraphic(self.extent)
        if hasattr(self, 'mapgraphic'):
            del self.mapgraphic
        if hasattr(self, 'mapgraphicid'):
            self.delete(self.mapgraphicid)
        self.mapgraphic = Tkinter.PhotoImage(data=data)
        self.mapgraphicid = self.create_image(0, 0, anchor=Tkinter.NW, 
                                              image=self.mapgraphic)
        self.graphicoffset = (0, 0)

class MapServiceWindow(Tkinter.Frame):
    """A pre-built GUI class for displaying non-tiled map services."""
    tools = (PanTool, ZoomToExtent, 
             ZoomInTool, ZoomIn50Percent, 
             ZoomOutTool, ZoomOut50Percent)
    def createWidgets(self):
        self.toolbar = Tkinter.Frame(self, relief=Tkinter.RAISED, 
                                     borderwidth=2)
        self.mappanel = MapCanvas(self)
        self.toollabels = []
        for tool in self.tools:
            label = Tkinter.Label(self.toolbar, text=tool.toolname, 
                                  relief=Tkinter.RAISED, borderwidth=2)
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

        self.toolbar.pack(side=Tkinter.TOP, fill=Tkinter.X)
        self.mappanel.pack(side=Tkinter.BOTTOM)
    def rp(self, event):
        self.pack()
    def __init__(self, service):
        root = Tkinter.Tk()
        assert isinstance(service, server.MapService)
        assert service._json_struct['singleFusedMapCache'] is False, \
            "This sample only works with dynamic map services"
        self.service = service
        self.extent = self.service.fullExtent
        root.title(self.service.mapName or self.service.description)
        Tkinter.Frame.__init__(self, root)
        self.createWidgets()
        self.pack()
        self.bind('<Configure>', self.rp)
    def mapGraphic(self, extent=None):
        exported = self.service.ExportMap(bbox=extent,
                                          format='gif', size="800,600")
        self.width = exported.width
        self.height = exported.height
        self.extent = exported.extent
        return exported.extent, base64.b64encode(exported.data)
