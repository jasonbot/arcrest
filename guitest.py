import arcrest
import random

if __name__ == "__main__":
    urls=["http://flame6:8399/arcgis/rest/services/Maps/Redlands/MapServer/",
          "http://flame6:8399/arcgis/rest/services/Maps/NewZealand/MapServer",
          "http://flame6:8399/arcgis/rest/services/Maps/world/MapServer",
          "http://flame4:8399/arcgis/rest/services/Maps/Holland/MapServer",
          "http://flame4:8399/arcgis/rest/services/Maps/"
            "SanFrancisco-SimpleRoute/MapServer"]
    service = arcrest.server.MapService(random.choice(urls))
    gui = arcrest.gui.DynamicMapServiceWindow(service, 1000, 800)
    gui.mainloop()
