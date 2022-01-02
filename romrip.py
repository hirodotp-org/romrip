import os
import sys
import pathlib
import yaml

from database import Database, sql_create_hash_table, sql_create_cache_table
from plugin import Plugin

PLUGINS = ["freeroms", "coolrom"]

class Application:
    ROM_STATE_SKIP = 1
    ROM_STATE_DOWNLOADED = 1

    def __init__(self, plugins:list=[]):
        self.config = False
        self.config_directory = pathlib.Path(__file__).parent
        self.config_file = os.path.join(self.config_directory, "etc", "romrip.yaml")

        if os.path.isfile(self.config_file):
            with open(self.config_file, 'r') as fd:
                self.config = yaml.safe_load(fd)
            self.db = Database(self.config["database"])

        if plugins != []:
            self._plugins = [Plugin(self, plugin) for plugin in plugins]
        else:
            self._plugins = [Plugin(self, "default")]

    def main(self):
        self.bootstrap()

        for plugin in self._plugins:
            print("LOADED %s %s" % (plugin.name, plugin.version,))
            plugin.stub.main()

    def bootstrap(self):
        self.db.create_table(sql_create_hash_table)
        self.db.create_table(sql_create_cache_table)

if __name__ == "__main__":
    app = Application(PLUGINS)
    app.main()
    sys.exit(0)