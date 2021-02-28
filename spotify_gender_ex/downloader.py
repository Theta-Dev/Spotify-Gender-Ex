import requests
import urllib.request
from tqdm import tqdm
import click
import re
import os
import logging

URL_UPTODOWN = 'https://spotify.de.uptodown.com/android/download'
URL_RTABLE = 'https://raw.githubusercontent.com/Theta-Dev/Spotify-Gender-Ex/master/spotify_gender_ex/res/replacements.json'


class Downloader:
    def __init__(self, ignore_ssl=False, download_id=''):
        pattern_url = re.escape('https://dw.uptodown.com/dwn/') + r'(\w|\.|\/|-|\+|=)+'
        pattern_version = r'(?<=<div class=version>)(\d|\.)+'
        self.verify = not ignore_ssl

        if download_id:
            url = URL_UPTODOWN + '/' + download_id
        else:
            url = URL_UPTODOWN

        try:
            r = requests.get(url, verify=self.verify)
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
            return requests.get(URL_RTABLE, verify=self.verify).text
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
        with _DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc=url.split('/')[-1]) as t:
            urllib.request.urlretrieve(url, filename=output_path, reporthook=t.update_to)
    except Exception:
        return False
    return os.path.isfile(output_path)
