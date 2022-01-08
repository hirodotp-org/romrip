import os
import re
import string
import requests
import urllib3
import sys
from plugin import Module

NAME = "coolrom"
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
                self.get_rom(rom[0], rom[1], platform['directory'], platform['platform'])

    def get_cookies(self):
        url = self.gen_stage_url('cookies')
        r = requests.get(url)
        self.cookies = r.cookies

    def get_platforms(self):
        headers = {'User-Agent': USER_AGENT}
        url = self.gen_stage_url('platforms')
        res = requests.get(url, cookies = self.cookies, headers = headers)
        if res.status_code == 200:
            match = re.findall(r'<br><br>(.*?)<br><br><br>', res.text, re.DOTALL)
            if match:
                matches = re.findall(r'<a href="(.*?)">(.*?)</a>', match[0], re.DOTALL)
                if matches:
                    platforms = []
                    for pl in self._config['platforms']:
                        for platform in matches:
                            link = platform[0]
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
        subpages = ["0"]
        url = self.gen_stage_url('roms')

        print("Buffering ROMs... ", end=''),

        for subpage in string.ascii_lowercase:
            subpages.append(subpage)

        for subpage in subpages:
            romlist = "%s%s%s/" % (url, platform_link, subpage,)

            res = requests.get(romlist, cookies=self.cookies, headers=headers)
            if res.status_code == 200:
                matches = re.findall(r'<div class="USA"><a href="(.*?)">(.*?)</a><br /></div>', res.text, re.DOTALL|re.MULTILINE)
                roms = roms + matches

        print("done")
        return roms

    def get_rom(self, rom_url, rom_name, out_dir, platform):
        url = ("%s%s" % (self.gen_stage_url('download'), rom_url,)).replace('//', '/').replace('https:/', 'https://')
        referer = ("%s%s" % (self.gen_stage_url('download'), "/".join(url.split("/", 6)[3:6]),)).replace('//', '/').replace('https:/', 'https://')
        headers = {
            'User-Agent': USER_AGENT,
            'Referer': referer,
        }

        res = requests.get(url, headers=headers, cookies=self.cookies)
        if res.status_code == 200:
            self.cookies = res.cookies
            headers['Referer'] = url

            id = url.split('/', 6)[5]
            url = ("%s%s" % (self.gen_stage_url('download_popup'), id,)).replace('//', '/').replace('https:/', 'https://')

            res = requests.get(url, headers = headers, cookies = self.cookies)
            if res.status_code == 200:
                match = re.search(r'action="(https\:\/\/dl.coolrom.com.au\/dl\/' + str(id) + r'\/.*?)"', res.text, re.DOTALL)
                if match:
                    self.cookies = res.cookies
                    headers['Referer'] = url
                    headers['Origin'] = "%s%s" % (self._config['proto'], self._config['site'],)

                    result = self._download_rom(platform, match.group(1), None, out_dir, headers, self.cookies, method = "POST")
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