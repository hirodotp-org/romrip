import os
import sys
import re
import yaml
import importlib
import pathlib
import tempfile
import hashlib
import shutil
import requests

class Module:
    # Override this with your module name (must match the name of the configuration 
    # file under etc/plugins.conf.d/ excluding the .conf extension).
    name = "default"

    def __init__(self, parent):
        self._parent = parent
        self._db = self._parent.db
        self.md5 = None
        self._config = False
        self._config_directory = pathlib.Path(__file__).parent
        self._config_file = os.path.join(self._config_directory, "etc", "plugins.conf.d", self.name + ".yaml")

        if os.path.isfile(self._config_file):
            self._read_config()

        self._bootstrap()

    def _read_config(self):
        with open(self._config_file, 'r') as fd:
            self._config = yaml.safe_load(fd)

    def _bootstrap(self):
        print("Bootstrap %s... " % (self.name,), end='')
        files = []
        for platform in self._config['platforms']:
            directory = os.path.join(self._config['directory'], platform.get('directory', platform['name']))
            files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

            for f in files:
                row = self._db.query(r'SELECT id FROM local WHERE path = ?', "/".join(f.split(os.sep)[-2:])).fetchall()
                if len(row) == 0:
                    self._hash_rom_init()
                    with open(f, 'rb') as fd:
                        data = fd.read(4096)
                        while data:
                            self._hash_rom_update(data)
                            data = fd.read(4096)
                    md5sum = self._hash_rom_digest()
                    self._db.query(r'INSERT INTO local (path, hash) VALUES(?, ?)', "/".join(f.split(os.sep)[-2:]), md5sum)
            self._db.commit()

            # clean up any removed files from database
            plat = directory.split('/').pop()
            rows = self._db.query(r'SELECT id,path FROM local WHERE path LIKE ?', plat + "/%").fetchall()
            for row in rows:
                fullpath = os.path.join(directory.split(plat).pop(0), plat, row[1].split(os.path.sep).pop())
                if not os.path.exists(fullpath):
                    self._db.query(r'DELETE FROM local WHERE id = ?', row[0])            
                    self._db.commit()
        print("done")

    def _download_rom(self, platform, rom_url, rom_name, out_dir, headers = None, cookies = None, method = "GET"):
        extension = False
        row = self._db.query(r'SELECT id FROM hash WHERE url = ?', rom_url).fetchall()
        if len(row) == 0:
            with tempfile.TemporaryFile() as temp_fd:
                if method == "GET":
                    res = requests.get(rom_url, headers=headers, cookies=cookies, verify=False)
                elif method == "POST":
                    res = requests.post(rom_url, headers=headers, cookies=cookies, verify=False)

                if res.status_code == 200:
                    if rom_name is None or rom_name is False:
                        rom_name = re.findall(r'filename="(.+)"', res.headers['content-disposition'])
                        if rom_name:
                            extension = rom_name[0].split('.')[-1:][0]
                            rom_name = ".".join(rom_name[0].split('.')[0:-1])
                        else:
                            return False

                    self._hash_rom_init()

                    for chunk in res.iter_content(4096):
                        temp_fd.write(chunk)
                        self._hash_rom_update(chunk)

                    md5_hash = self._hash_rom_digest()
                    row = self._db.query(r'SELECT cache.status as status FROM cache, hash WHERE cache.hash_id = hash.id AND hash.hash = ?', md5_hash).fetchall()
                    row2 = self._db.query(r'SELECT id FROM local WHERE hash = ?', md5_hash).fetchall()

                    # If there isn't a file downloaded and in the cache tables with
                    # the md5 hash we just generated, we go ahead and store it in 
                    # the database and at the final destination.
                    if len(row) == 0 and len(row2) == 0:
                        if extension:
                            out_path = os.path.abspath("%s/%s.%s" % (out_dir, rom_name.replace('/', '_'), extension))
                            complete_rom_name = "%s.%s" % (rom_name.replace('/', '_'), extension,)
                        else:
                            out_path = os.path.abspath("%s/%s" % (out_dir, rom_name.replace('/', '_'),))
                            complete_rom_name = rom_name.replace('/', '_')

                        with open(out_path, 'wb') as fd:
                            temp_fd.seek(0)
                            shutil.copyfileobj(temp_fd, fd)
                            self._db.query(r'INSERT INTO hash (name, url, hash) VALUES(?, ?, ?)', complete_rom_name, rom_url, md5_hash)
                            row = self._db.query(r'SELECT id FROM hash WHERE hash = ?', md5_hash).fetchall()
                            id = row[0]
                            self._db.query(r'INSERT INTO cache (hash_id, status) VALUES(?, ?)', id[0], self._parent.ROM_STATE_DOWNLOADED)
                            self._db.query(r'INSERT INTO local (path, hash) VALUES(?, ?)', os.path.join(platform, complete_rom_name), md5_hash)
                            self._db.commit()

                        temp_fd.close()
                        return out_path.split(os.path.sep)[-1:][0]
                    temp_fd.close()
                    return None
                temp_fd.close()
                return False

        return None

    def _hash_rom_init(self):
        self.md5 = hashlib.md5()

    def _hash_rom_update(self, data):
        self.md5.update(data)

    def _hash_rom_digest(self):
        return self.md5.hexdigest()

class Plugin:
    name = None
    version = None
    plugin = None

    def __init__(self, parent, module):
        plug = importlib.import_module("plugins.%s" % module, ".")
        self.name = plug.Plugin.name
        self.version = plug.Plugin.version
        self.stub = plug.Plugin(parent)