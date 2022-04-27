import re
from dataclasses import dataclass
from typing import List, Set

import requests
from bs4 import BeautifulSoup

URL_APKCOMBO = 'https://apkcombo.com/%s/download/apk'
URL_APKCOMBO_CHECKIN = 'https://apkcombo.com/checkin'
URL_UPTODOWN = 'https://spotify.de.uptodown.com/android/download'

DEFAULT_CPU = 'arm64-v8a'
DEFAULT_UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36'


@dataclass
class App:
    version: str
    cpu_archs: Set[str]
    download_url: str

    def __eq__(self, o: 'App') -> bool:
        return self.version == o.version

    def __gt__(self, o: 'App') -> bool:
        return compare_versions(self.version, o.version) > 0


class StoreException(Exception):
    pass


class Apkcombo:
    def __init__(self, user_agent=DEFAULT_UA, cpu_arch=DEFAULT_CPU):
        self.cpu_arch = cpu_arch
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Dnt": "1",
            "Upgrade-Insecure-Requests": "1",
            'User-Agent': user_agent
        }

    def _query_url(self, url) -> str:
        try:
            resp = requests.get(url, headers=self.headers)
            if resp.status_code != 200:
                raise StoreException('HTTP status code: ' + str(resp.status_code))
            return resp.text
        except Exception as e:
            raise StoreException(e)

    def _query_page(self, app_name) -> str:
        url = URL_APKCOMBO % app_name
        return self._query_url(url)

    def _query_checkin(self) -> str:
        return self._query_url(URL_APKCOMBO_CHECKIN)

    def _parse_page(self, raw_page, checkin_token) -> List[App]:
        soup = BeautifulSoup(raw_page, 'html.parser')

        arch_list_elm = soup.select_one('#variants-tab ul')
        if arch_list_elm is None:
            raise StoreException('Could not find arch-list')

        arch_list = arch_list_elm.find_all('li', recursive=False)
        parsed_apps = []

        for arch_elm in arch_list:
            raw_arch = arch_elm.select_one('.blur').get_text()
            archs = set(map(str.strip, raw_arch.split(',')))

            file_list_elm = arch_elm.select_one('.file-list')
            if file_list_elm is None:
                continue
            file_list = file_list_elm.find_all('li', recursive=False)

            for file_elm in file_list:
                file_a_elm = file_elm.find('a')
                if file_a_elm is None or 'href' not in file_a_elm.attrs:
                    continue
                download_url = file_a_elm['href']
                if not self._is_apk_path(download_url):
                    continue

                vername_elm = file_elm.select_one('.vername')
                if vername_elm is None:
                    continue

                pattern_version = r'\d+(\.\d+){3}'
                match = re.search(pattern_version, vername_elm.get_text())
                if match is None:
                    continue
                version = match.group(0)

                parsed_apps.append(App(version, archs, f'{download_url}&{checkin_token}'))

        return parsed_apps

    @staticmethod
    def _is_apk_path(download_url) -> bool:
        filename = download_url.split('?')[0]
        return filename.endswith('.apk')

    def _pick_app(self, apps: List[App]) -> App:
        for app in apps:
            if self.cpu_arch in app.cpu_archs:
                return app

        for app in apps:
            if 'universal' in app.cpu_archs:
                return app

        raise StoreException('Could not find apk for ' + self.cpu_arch)

    def get_spotify_app(self) -> App:
        checkin_token = self._query_checkin()
        raw_page = self._query_page('spotify/com.spotify.music')
        apps = self._parse_page(raw_page, checkin_token)
        app = self._pick_app(apps)
        check_app_file(app.download_url, self.headers)
        return app


class Uptodown:
    def __init__(self,
                 user_agent=DEFAULT_UA,
                 cpu_arch=DEFAULT_CPU,
                 download_id=''):
        self.download_id = download_id
        self.headers = {'User-Agent': user_agent}

    def get_spotify_app(self) -> App:
        pattern_url = re.escape(
            'https://dw.uptodown.com/dwn/') + r'(\w|\.|\/|-|\+|=)+'
        pattern_version = r'(?<=<div class=version>)(\d|\.)+'

        if self.download_id:
            url = URL_UPTODOWN + '/' + self.download_id
        else:
            url = URL_UPTODOWN

        try:
            r = requests.get(url)
        except Exception as e:
            raise StoreException(e)

        search_url = re.search(pattern_url, r.text)
        search_version = re.search(pattern_version, r.text)

        if not search_url or not search_version:
            raise StoreException('Could not get Spotify version')

        spotify_url = str(search_url[0])
        spotify_version = str(search_version[0])

        check_app_file(spotify_url, self.headers)

        return App(spotify_version, {'universal'}, spotify_url)


STORES = [Apkcombo, Uptodown]


def get_spotify_app(cpu_arch=DEFAULT_CPU) -> App:
    found_apps = []

    for store_class in STORES:
        store = store_class(cpu_arch=cpu_arch)

        try:
            app = store.get_spotify_app()
            found_apps.append(app)
            print(store_class.__name__ + ': gefundene Version ' + app.version)
        except Exception as e:
            print(store_class.__name__ + ': ' + str(e))

    if len(found_apps) == 0:
        raise StoreException('Spotify-App konnte nicht abgerufen werden')

    return max(found_apps)


def get_spotify_app_from_id(download_id) -> App:
    utd = Uptodown(download_id=download_id)
    return utd.get_spotify_app()


def compare_versions(version_a: str, version_b: str) -> int:
    """
    Return 1 if va is more recent, -1 if vb is more recent
    and 0 if the versions are equal.
    """
    if version_a == version_b:
        return 0

    va_parts = version_a.split('.')
    vb_parts = version_b.split('.')

    if len(va_parts) > len(vb_parts):
        return 1
    if len(va_parts) < len(vb_parts):
        return -1

    for i in range(len(va_parts)):
        n_a = int(va_parts[i])
        n_b = int(vb_parts[i])

        if n_a > n_b:
            return 1
        if n_a < n_b:
            return -1


def check_app_file(app_url: str, headers: dict):
    file_headers = requests.get(app_url, headers=headers, stream=True).headers
    file_type = file_headers.get('Content-Type')

    try:
        file_size = int(file_headers.get('Content-Length'))
    except TypeError or ValueError:
        raise StoreException('Did not receive content length')

    if file_type != 'application/vnd.android.package-archive':
        raise StoreException(f'Received file of type: {file_type}, no android app')

    if file_size < 1e6:
        raise StoreException('Received file smaller than 1MB')
