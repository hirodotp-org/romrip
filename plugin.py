import os
import glob
import yaml
import importlib
import pathlib
import sys

class Module:
    # Override this with your module name (must match the name of the configuration 
    # file under etc/plugins.conf.d/ excluding the .conf extension).
    name = "default"

    def __init__(self):
        self._config = False
        self._config_directory = pathlib.Path(__file__).parent
        self._config_file = os.path.join(self._config_directory, "etc", "plugins.conf.d", self.name + ".yaml")

        if os.path.isfile(self._config_file):
            self._read_config()

    def _read_config(self):
        with open(self._config_file, 'r') as fd:
            self._config = yaml.safe_load(fd)

    def _download_rom(self, outdir, rom, callback):
        '''
        outdir = output directory
        rom = list, [0] is url, [1] is rom name
        callback = function to download the rom
        '''
        romname = rom[1].replace('/', '_').replace('-', '?').replace('[', '?').replace(']', '?')
        rompath = os.path.abspath(outdir)
        romglob = "%s/%s.*" % (rompath, romname,)
        out_path = glob.glob(romglob)
        if not out_path:
            callback(rom[0], rom[1], outdir)

class Plugin:
    name = None
    version = None
    plugin = None

    def __init__(self, module):
        plug = importlib.import_module("plugins.%s" % module, ".")
        self.name = plug.Plugin.name
        self.version = plug.Plugin.version
        self.stub = plug.Plugin()