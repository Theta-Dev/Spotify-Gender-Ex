import os
import re
import urllib.request

import click
import requests
from tqdm import tqdm

URL_UPTODOWN = 'https://spotify.de.uptodown.com/android/download'
URL_RTABLE = 'https://raw.githubusercontent.com/Theta-Dev/Spotify-Gender-Ex/master/spotify_gender_ex/res/replacements.json'


class Downloader:
    def __init__(self, download_id=''):
        pattern_url = re.escape('https://dw.uptodown.com/dwn/') + r'(\w|\.|\/|-|\+|=)+'
        pattern_version = r'(?<=<div class=version>)(\d|\.)+'

        if download_id:
            url = URL_UPTODOWN + '/' + download_id
        else:
            url = URL_UPTODOWN

        try:
            r = requests.get(url)
        except Exception:
            msg = 'Spotify-Version konnte nicht abgerufen werden'
            click.echo(msg)
            self.spotify_version = 'NA'
            self.spotify_url = ''
            return

        search_url = re.search(pattern_url, r.text)
        search_version = re.search(pattern_version, r.text)

        if not search_url or not search_version:
            msg = 'Spotify-Version nicht gefunden'
            click.echo(msg)
            self.spotify_version = 'NA'
            self.spotify_url = ''
            return

        self.spotify_url = str(search_url[0])
        self.spotify_version = str(search_version[0])

    def download_spotify(self, output_path):
        if not self.spotify_url:
            return False

        return _download(self.spotify_url, output_path, 'Spotify')

    def get_replacement_table_raw(self):
        try:
            return requests.get(URL_RTABLE).text
        except Exception:
            click.echo('Ersetzungstabelle konnte nicht abgerufen werden. Verwende eingebaute Tabelle.')


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

    try:
        with _DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc=url.split('/')[-1]) as t:
            urllib.request.urlretrieve(url, filename=output_path, reporthook=t.update_to)
    except Exception:
        return False
    return os.path.isfile(output_path)
