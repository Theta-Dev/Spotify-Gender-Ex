import requests
import urllib.request
from tqdm import tqdm
import click
import re
import os
import logging

URL_APKCOMBO = 'https://apkcombo.com/spotify-listen-to-podcasts-find-music-you-love/com.spotify.music/download/apk'
URL_RTABLE = 'https://raw.githubusercontent.com/Theta-Dev/Spotify-Gender-Ex/master/spotify_gender_ex/res/replacements.json'


class Downloader:
    def __init__(self, arm32=False):
        if arm32:
            d_code = 'armeabi-v7a'
        else:
            d_code = 'arm64-v8a'

        pattern_url = r'(?<=' + re.escape(d_code) + r'</code>\W<a href=")' +\
                      re.escape('https://play.googleapis.com/download/by-token/download?token=') + r'[^"]+'
        pattern_version = r'(?<=<strong>spotify-listen-to-podcasts-find-music-you-love_)(\d|\.)+(?=.apk<\/strong>)'

        url = URL_APKCOMBO

        try:
            r = requests.get(url)
        except Exception:
            msg = 'Spotify-Version konnte nicht abgerufen werden'
            logging.error(msg)
            click.echo(msg)
            self.spotify_version = 'NA'
            self.spotify_url = ''
            return

        search_url = re.search(pattern_url, r.text)
        search_version = re.search(pattern_version, r.text)

        if not search_url or not search_version:
            msg = 'Spotify-Version nicht gefunden'
            logging.error(msg)
            click.echo(msg)
            self.spotify_version = 'NA'
            self.spotify_url = ''
            return

        self.spotify_url = str(search_url[0])
        self.spotify_version = str(search_version[0])

        logging.info('Aktuelle Spotify-Version: %s' % self.spotify_version)

    def download_spotify(self, output_path):
        if not self.spotify_url:
            return False

        return _download(self.spotify_url, output_path, 'Spotify')

    def get_replacement_table_raw(self):
        logging.info('Ersetzungstabelle von GitHub abrufen')
        try:
            return requests.get(URL_RTABLE).text
        except Exception:
            msg = 'Ersetzungstabelle konnte nicht abgerufen werden. Verwende eingebaute Tabelle.'
            logging.error(msg)


# See here
# https://stackoverflow.com/questions/15644964/python-progress-bar-and-downloads

class _DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def _download(url, output_path, description=''):
    if description:
        msg = 'Lade %s herunter: %s' % (description, url)
    else:
        msg = 'Herunterladen: ' + url
    click.echo(msg)
    logging.info(msg)

    try:
        with _DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc=description) as t:
            urllib.request.urlretrieve(url, filename=output_path, reporthook=t.update_to)
    except Exception:
        return False
    return os.path.isfile(output_path)
