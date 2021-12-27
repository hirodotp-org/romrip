import sys
import requests
import importlib
from bs4 import BeautifulSoup
from plugin import Plugin

PLUGINS = ["freeroms"]

class Application:
    def __init__(self, plugins:list=[]):
        if plugins != []:
            self._plugins = [Plugin(plugin) for plugin in plugins]
        else:
            self._plugins = [Plugin("default")]
        
    def main(self):
        for plugin in self._plugins:
            print("LOADED %s %s" % (plugin.name, plugin.version,))
            plugin.stub.main()

if __name__ == "__main__":
    app = Application(PLUGINS)
    app.main()
    sys.exit(0)