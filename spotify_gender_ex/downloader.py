import os
import urllib.request

import click
import requests
from tqdm import tqdm

URL_GHAPI = 'https://api.github.com/repos/Theta-Dev/Spotify-Gender-Ex/commits/master'
URL_RTABLE = 'https://raw.githubusercontent.com/Theta-Dev/Spotify-Gender-Ex/%s/spotify_gender_ex/res/replacements.json'


def get_replacement_table_raw() -> str:
    try:
        # Get latest commit
        sha = requests.get(URL_GHAPI).json()['sha']
        return requests.get(URL_RTABLE % sha).text
    except Exception:
        click.echo(
            'Ersetzungstabelle konnte nicht abgerufen werden. Verwende eingebaute Tabelle.'
        )


# See here
# https://stackoverflow.com/questions/15644964/python-progress-bar-and-downloads


class _DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def download_file(url, output_path, description='') -> bool:
    if description:
        click.echo('Lade %s herunter: %s' % (description, url))
    else:
        click.echo('Herunterladen: ' + url)

    try:
        with _DownloadProgressBar(unit='B',
                                  unit_scale=True,
                                  miniters=1,
                                  desc=description) as t:
            urllib.request.urlretrieve(url,
                                       filename=output_path,
                                       reporthook=t.update_to)
    except Exception:
        return False
    return os.path.isfile(output_path)
