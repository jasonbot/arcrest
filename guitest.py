import arcrest

if __name__ == "__main__":
    service = arcrest.server.MapService("http://flame6:8399/arcgis/rest/"
                                        "services/Maps/Redlands/MapServer/")
    gui = arcrest.gui.MapServiceWindow(service)
    gui.mainloop()
