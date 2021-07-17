import os
import re
import subprocess
from datetime import datetime
from typing import Iterable, Optional

import click
from importlib_resources import files

from spotify_gender_ex import __version__
from spotify_gender_ex import downloader
from spotify_gender_ex.replacement_table import ReplacementManager, ReplacementTable
from spotify_gender_ex.workdir import Workdir

_SPOTIFY_CERT_SHA256 = '6505b181933344f93893d586e399b94616183f04349cb572a9e81a3335e28ffd'


class GenderEx:
    def __init__(self, apk_file='', folder_out='.', replacement_tables: Optional[Iterable[str]] = None, builtin=False,
                 no_internal=False,
                 no_interaction=False, ks_password='', key_password=''):
        self.spotify_version = ''
        self.noia = no_interaction
        self.ks_password = ks_password or '12345678'
        self.key_password = key_password or '12345678'

        # Java libraries
        self.file_apktool = str(files('spotify_gender_ex.lib').joinpath('apktool.jar'))
        self.file_apksigner = str(files('spotify_gender_ex.lib').joinpath('uber-apk-signer-1.2.1.jar'))

        self.workdir = Workdir(folder_out, self.ks_password, self.key_password)
        self.rtm = ReplacementManager(self.workdir.dir_apk, self._get_missing_replacement)

        # Downloader
        self.downloader = downloader.Downloader()
        self.latest_spotify = self.downloader.spotify_version

        if apk_file and os.path.isfile(apk_file):
            self.workdir.file_apk = apk_file

        self.file_apkout = ''
        self.file_rtabout = ''

        # Replacement tables
        if not no_internal:
            # If we can, use the latest replacement table from GitHub
            got_rt = False

            if not builtin:
                try:
                    rtab_raw = self.downloader.get_replacement_table_raw()
                    rt = ReplacementTable.from_string(rtab_raw)
                    self.rtm.add_rtab(rt, 'builtin (GitHub)')
                    got_rt = True
                except Exception as e:
                    click.echo(str(e))

            if not got_rt:
                rt = ReplacementTable.from_file(files('spotify_gender_ex.res').joinpath('replacements.json'))
                self.rtm.add_rtab(rt, 'builtin (lokal)')
        if replacement_tables:
            for rtfile in replacement_tables:
                if os.path.isfile(rtfile):
                    # If replacement table specified, make it the only table
                    rt = ReplacementTable.from_file(rtfile)
                    self.rtm.add_rtab(rt, 'custom (%s)' % rtfile)

    def is_latest_spotify_processed(self) -> bool:
        """Check if the latest spotify version is already processed"""
        # Dont check if downloading has been disabled
        if not self.downloader:
            return False

        latest_version = '%s-%s' % (self.latest_spotify, self.rtm.get_rt_versions())

        # Check spotify_version.txt
        if os.path.isfile(self.workdir.file_version):
            with open(self.workdir.file_version, encoding='utf-8') as f:
                ver = f.read().strip()

            if latest_version == ver:
                return True
        return False

    def download(self) -> bool:
        """
        Download the Spotify app from uptodown.com if it is not present

        Default APK location: GenderEx/tmp/app.apk
        """
        if os.path.isfile(self.workdir.file_apk):
            msg = 'APK-Datei existiert bereits, Download übersprungen.'
            click.echo(msg)
            return True
        elif not self.downloader:
            msg = 'APK-Datei kann nicht heruntergeladen werden. Beende.'
            click.echo(msg)
            return False
        else:
            return self.downloader.download_spotify(self.workdir.file_apk)

    def verify(self):
        """Check if the Spotify apk file is genuine by verifying its certificate"""
        cmd = ['java', '-jar', self.file_apksigner, '-y', '--verifySha256', _SPOTIFY_CERT_SHA256,
               '-a', self.workdir.file_apk]

        subprocess.run(cmd, check=True)

    def decompile(self):
        """Decompiles Spotify using APKTool"""
        subprocess.run(
            ['java', '-jar', self.file_apktool, 'd', self.workdir.file_apk, '-s', '-o', self.workdir.dir_apk],
            check=True)

        # Check if decompile was successful
        assert os.path.isfile(self.workdir.file_apktool)

    def check_compatibility(self):
        """Checks if the decompiled Spotify version is compatible with all replacement tables"""
        self.spotify_version = self.get_spotify_version()
        click.echo('Spotify-Version %s erkannt.' % self.spotify_version)

        if self.rtm.check_compatibility(self.spotify_version):
            click.echo('Alle Ersetzungstabellen sind kompatibel.')
        else:
            click.echo('Erwarte, manuelle Anpassungen vornehmen zu müssen.')

    def recompile(self):
        """
        Recompiles the Spotify app using APKTool.

        Output file: GenderEx/tmp/app_out.apk
        """
        click.echo('Rekompiliere nach ' + self.workdir.file_apkout)
        subprocess.run(['java', '-jar', self.file_apktool, 'b', '--use-aapt2',
                        self.workdir.dir_apk, '-o', self.workdir.file_apkout], check=True)

        # Check if compile was successful
        assert os.path.isfile(self.workdir.file_apkout)

    def replace(self):
        """Executes all replacements"""
        n_replaced, n_newrpl = self.rtm.do_replace()

        click.echo('%d Ersetzungen vorgenommen' % n_replaced)
        click.echo('%d neue Ersetzungsregeln hinzugefügt' % n_newrpl)

    def _get_missing_replacement(self, key: str, old: str) -> str:
        """
        This method gets called by the ReplacementManager if it cant replace a suspicious field.
        Prompts the user to manually enter a replacement value.
        In non-interactive mode it will skip the field instead.
        """
        click.echo('Verdächtig: %s' % old)
        if self.noia:
            return old
        else:
            try:
                new_text = click.edit(str(old))
            except click.ClickException:
                # No inline editing, less user friendly, but if the above does not work:
                new_text = click.prompt('Neuer Text:', str(old))

            if new_text:
                return new_text.strip()
            else:
                self.wait_for_enter('Enter drücken, um die Eingabe zu wiederholen.')
                return self._get_missing_replacement(key, old)

    def get_spotify_version(self) -> str:
        """Reads the Spotify version number from the decompiled app."""
        with open(self.workdir.file_apktool, 'r', encoding='utf-8') as f:
            text = f.read()

        for line in text.splitlines():
            line = line.strip()
            if line.startswith('versionName:'):
                return line[12:].strip()

    def add_credits(self):
        """
        Add GenderEx credits and debug info to the licenses.xhtml file.

        Can be viewed in the finished Spotify app under Settings > Third Party Software
        """
        # Read the credits file
        credits_file = files('spotify_gender_ex.res').joinpath('credits.html')
        html_file = os.path.join(self.workdir.dir_apk, 'assets', 'licenses.xhtml')

        with open(credits_file, 'r', encoding='utf-8') as f:
            cred = f.read()
        with open(html_file, 'r', encoding='utf-8') as f:
            html = f.read()

        # Fill in template
        cred = cred.replace('{{SPOTIFY_VERSION}}', self.spotify_version)
        cred = cred.replace('{{GENDEREX_VERSION}}', __version__)
        cred = cred.replace('{{RT_VERSION}}', self.rtm.get_rt_versions(True))
        cred = cred.replace('{{NEW_REPL}}', self.rtm.get_new_repl_string())
        cred = cred.replace('{{BUILD_DATE}}', datetime.now().strftime("%d.%m.%Y %H:%M:%S"))

        # Remove credits if there are any
        html = re.sub(r'<div id="gender-ex-credits">[\s\S]*?</div>', '', html)

        # Include the template
        pos = html.find('<body>')
        if pos == -1:
            return
        pos += 6

        html = html[:pos] + cred + html[pos:]

        # Write back the html
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)

    def sign(self):
        """Signs the APK file using UberAPKSigner and copies the app into the output folder"""
        cmd = ['java', '-jar', self.file_apksigner,
               '-a', self.workdir.file_apkout, '-o', self.workdir.dir_output,
               '--ks', self.workdir.file_keystore, '--ksAlias', 'genderex', '--ksPass', self.ks_password,
               '--ksKeyPass', self.key_password]

        subprocess.run(cmd, check=True)

        rtver = self.rtm.get_version_string()

        # Move apk file
        self.file_apkout = self.workdir.get_file_apkout(self.spotify_version, rtver)
        os.renames(self.workdir.file_apkout_signed, self.file_apkout)

        # Write spotify_version.txt
        with open(self.workdir.file_version, 'w', encoding='utf-8') as f:
            f.write('%s-%s' % (self.spotify_version, self.rtm.get_rt_versions()))

        # Save new replacements
        self.file_rtabout = self.workdir.get_file_newrepl(self.spotify_version, rtver)
        if self.rtm.write_new_replacements(self.spotify_version, self.file_rtabout):
            click.echo('Neue Ersetzungstabelle gespeichert')

    @staticmethod
    def set_github_var(key, value):
        def escape(val_in) -> str:
            return str(val_in).replace('"', '\\"').replace('\n', '\\n')

        os.system('echo "%s=%s" >> $GITHUB_ENV' % (escape(key), escape(value)))

    def set_github_vars(self):
        self.set_github_var('spotify_version', self.spotify_version)
        self.set_github_var('genderex_version', __version__)
        self.set_github_var('apk_file', os.path.abspath(self.file_apkout))
        self.set_github_var('rt_versions', self.rtm.get_rt_versions())
        self.set_github_var('repl_string', self.rtm.get_new_repl_string())

        if self.file_rtabout:
            self.set_github_var('rtab_file', os.path.abspath(self.file_rtabout))

    def wait_for_enter(self, msg):
        """Displays a message and waits for the user to press ENTER. Does nothing in non-interactive mode."""
        if not self.noia:
            input(msg)
