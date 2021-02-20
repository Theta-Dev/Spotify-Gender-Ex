import requests
import urllib.request
from tqdm import tqdm
import click
import re

URL_UPTODOWN = 'https://spotify.de.uptodown.com/android/download'
URL_RTABLE = 'https://raw.githubusercontent.com/Theta-Dev/Spotify-Gender-Ex/master/spotify_gender_ex/res/replacements.json'


class Downloader:
    def __init__(self):
        pattern_url = re.escape('https://dw.uptodown.com/dwn/') + '(\w|\.|\/|-|\+|=)+'
        pattern_version = '(?<=<div class=version>)(\d|\.)+'

        r = requests.get(URL_UPTODOWN)

        search_url = re.search(pattern_url, r.text)
        search_version = re.search(pattern_version, r.text)

        if not search_url or not search_version:
            raise DownloaderException('Spotify-Version nicht gefunden')

        self.spotify_url = str(search_url[0])
        self.spotify_version = str(search_version[0])

    def download_spotify(self, output_path):
        _download(self.spotify_url, output_path, 'Spotify')

    @staticmethod
    def download_rtable(output_path):
        _download(URL_RTABLE, output_path, 'Ersetzungstabelle')


# See here
# https://stackoverflow.com/questions/15644964/python-progress-bar-and-downloads

class _DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def _download(url, output_path, description=''):
    if description:
        click.echo('Lade %s herunter: %s' % (description, url))
    else:
        click.echo('Herunterladen: ' + url)
    with _DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc=url.split('/')[-1]) as t:
        urllib.request.urlretrieve(url, filename=output_path, reporthook=t.update_to)


class DownloaderException(Exception):
    pass