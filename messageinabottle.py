import gui
import arcrest.server
import time
import Tkinter

message_in_a_bottle_service = \
    arcrest.server.GPTask("http://sampleserver1.arcgisonline.com/"
                             "ArcGIS/rest/services/Specialty/"
                             "ESRI_Currents_World/GPServer/MessageInABottle")

class MessageInABottleButton(gui.MapSelectPoint):
    toolname = "Run message in a bottle"
    @staticmethod
    def do(mapcanvas, point):
        text = mapcanvas.create_text(16, mapcanvas.height-20, 
                                text='Running', fill='black',
                                anchor=Tkinter.SW)
        mapcanvas.parent.update()
        try:
            job = message_in_a_bottle_service(point,
                                              mapcanvas.parent.days.get())
            runs = 0
            while job.running:
                runs += 1
                time.sleep(0.125)
                mapcanvas.itemconfigure(text, text="Running" + "."*runs)
                runs %= 10
                mapcanvas.parent.update()
            mapcanvas.addFeatureSet(job.Output)
        except Exception, e:
            mapcanvas.itemconfigure(text, text=str(e), fill='red')
            mapcanvas.parent.update()
            time.sleep(2)
        mapcanvas.delete(text)

class MessageInABottle(gui.DynamicMapServiceWindow):
    tools = gui.DynamicMapServiceWindow.tools + \
                (MessageInABottleButton,)
    def __init__(self):
        service = arcrest.server.MapService("http://flame6:8399/arcgis/rest/"
                                            "services/Maps/world/MapServer")
        gui.DynamicMapServiceWindow.__init__(self, service, 800, 600)
    def createWidgets(self, width, height):
        gui.DynamicMapServiceWindow.createWidgets(self, width, height)
        self.days = Tkinter.IntVar()
        self.days.set(360)
        label = Tkinter.Label(self.toolbar, text="Days:")
        entry = Tkinter.Entry(self.toolbar, textvariable=self.days)
        label.pack(side=Tkinter.LEFT)
        entry.pack(side=Tkinter.LEFT)

if __name__ == "__main__":
    MessageInABottle().mainloop()
