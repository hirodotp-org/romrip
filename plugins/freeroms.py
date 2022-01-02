import os
import re
import string
import requests
import urllib3
import shutil
from plugin import Module

NAME = "freeroms"
VERSION = "0.1"
USER_AGENT = "Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.130 Safari/537.36"

class Plugin(Module):
    name = NAME
    version = VERSION

    def __init__(self, parent):
        Module.__init__(self, parent)

    def main(self):

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Initialize the cookie bucket with any site cookies set.
        self.get_cookies()

        # Retrieve a list of platforms
        platforms = self.get_platforms()

        # Retrieve a list of roms for each of [a-z0-9#]
        for platform in platforms:
            roms = self.get_roms(platform['link'])
            for rom in roms:
                self.get_rom(rom[0], rom[1], platform['directory'])

    def get_cookies(self):
        url = self.gen_stage_url('cookies')
        r = requests.get(url)
        self.cookies = r.cookies

    def get_platforms(self):
        headers = {'User-Agent': USER_AGENT}
        url = self.gen_stage_url('platforms')
        res = requests.get(url, cookies = self.cookies, headers = headers)
        if res.status_code == 200:
            matches = re.findall(r'online\-td.*?href="(.*?)">(.*?)</a>', res.text, re.DOTALL)
            if matches:
                platforms = []
                for pl in self._config['platforms']:
                    for platform in matches:
                        link = platform[0][1:].split('.htm')[0]
                        plat = platform[1]

                        pl_name = pl.get('name', False)

                        if pl_name:
                            if plat.lower() == pl_name.lower():
                                print("Found platform " + pl.get('name', 'unknown'))
                                
                                # Create the path to store the 
                                outdir = pl.get('directory', False)
                                if not outdir:
                                    outdir = self._config.get('directory', False)
                                    if outdir:
                                        outdir = os.path.join(outdir, pl.get('name'))

                                if outdir:
                                    platforms.append({'platform': plat, 'link': pl.get('key', link), 'directory': outdir })
                                    if not os.path.exists(os.path.abspath(outdir)):
                                        os.mkdir(os.path.abspath(outdir))
                return platforms
        return False

    def get_roms(self, platform_link):
        headers = {'User-Agent': USER_AGENT}
        roms = []
        subpages = ["NUM"]
        url = self.gen_stage_url('roms')

        print("Buffering ROMs... ", end=''),

        for subpage in string.ascii_uppercase:
            subpages.append(subpage)

        for subpage in subpages:
            if platform_link[-5:] == "_roms":
                romlist = "%s%s_%s.htm" % (url, platform_link, subpage,)
            else:
                romlist = "%s%s_roms_%s.htm" % (url, platform_link, subpage,)

            res = requests.get(romlist, cookies=self.cookies, headers=headers)
            if res.status_code == 200:
                matches = re.findall(r'rom\-tr title.*?href="(.*?)".*?"name">(.*?)</span>', res.text, re.DOTALL|re.MULTILINE)
                roms = roms + matches

        print("done")
        return roms

    def get_rom(self, rom_url, rom_name, out_dir):
        url = "%s%s" % (self.gen_stage_url('download'), rom_url)
        headers = {'User-Agent': USER_AGENT}

        res = requests.get(url, headers=headers, cookies=self.cookies)
        if res.status_code == 200:
            self.cookies = res.cookies
            match = re.findall(r'Chrome.*?clickAndDisable.*?href="(.*?)"', res.text, re.DOTALL|re.MULTILINE)
            if match:
                extension = match[0].split('.')[-1:][0]
                rom_name = "%s.%s" % (rom_name, extension)
                headers['Referer'] = self.gen_stage_referer('download')

                result = self._download_rom(match[0], rom_name, out_dir, headers = headers, cookies = self.cookies)
                if result is not None and result:
                    print("%s:\t success" % (result,)),
                    return True
                elif result is False:
                    print("%s:\t failure" % (rom_name,)),

        return False

    def gen_stage_url(self, stage):
        url = "%s://%s%s" % (self._config['proto'], self._config['site'], self._config['stages'][stage]['url'],)
        return(url)

    def gen_stage_referer(self, stage):
        return(self._config['stages'][stage]['referer'])