import click
import subprocess
from importlib_resources import files
import re
import logging
import os
from datetime import datetime
from spotify_gender_ex.replacement_table import ReplacementManager, ReplacementTable
from spotify_gender_ex.workdir import Workdir
from spotify_gender_ex import downloader

# Version as shown in the credits
VERSION = '2.0.0'


class GenderEx:
    def __init__(self, apk_file='', folder_out='.', replacement_table='', builtin=False, no_interaction=False, debug=False,
                 ks_password='', key_password='', ignore_ssl=False, no_logfile=False):
        self.spotify_version = ''
        self.noia = no_interaction
        self.ks_password = ks_password or '12345678'
        self.key_password = key_password or '12345678'

        # Java libraries
        self.file_apktool = str(files('spotify_gender_ex.lib').joinpath('apktool.jar'))
        self.file_apksigner = str(files('spotify_gender_ex.lib').joinpath('uber-apk-signer-1.2.1.jar'))

        self.workdir = Workdir(folder_out, self.ks_password, self.key_password)
        self.rtm = ReplacementManager(self.workdir.dir_apk, self._get_missing_replacement)

        # Logging
        if not no_logfile:
            logging.basicConfig(filename=self.workdir.file_log, level=logging.DEBUG if debug else logging.INFO)

        logging.info('Starte Spotify GenderEx V' + VERSION)

        # Downloader
        self.downloader = downloader.Downloader(ignore_ssl)
        self.latest_spotify = self.downloader.spotify_version

        if apk_file and os.path.isfile(apk_file):
            self.workdir.file_apk = apk_file

        self.file_apkout = ''

        # Replacement tables
        if replacement_table and os.path.isfile(replacement_table):
            # If replacement table specified, make it the only table
            rt_specified = ReplacementTable.from_file(replacement_table)
            self.rtm.add_rtab(rt_specified, 'specified')
        else:
            # Otherwise use custom table on top of the builtin one
            rt_custom = ReplacementTable.from_file(self.workdir.file_rtable)

            # If we can, use the latest replacement table from GitHub
            rt_builtin = None

            if not builtin:
                try:
                    rtab_raw = self.downloader.get_replacement_table_raw()
                    rt_builtin = ReplacementTable.from_string(rtab_raw)
                except Exception as e:
                    click.echo(str(e))

            if not rt_builtin:
                rt_builtin = ReplacementTable.from_file(files('spotify_gender_ex.res').joinpath('replacements.json'))

            self.rtm.add_rtab(rt_builtin, 'builtin')
            # Dont modify custom replcement table when in noia mode
            self.rtm.add_rtab(rt_custom, 'custom', not no_interaction)

    def is_latest_spotify_processed(self):
        """Check if the latest spotify version is already processed and present in the output folder"""
        if not self.downloader:
            return False

        search_version = self.latest_spotify.replace('.', '-')

        for file in os.listdir(self.workdir.dir_output):
            # Remove spotify- prefix from filename
            if str(file).startswith(search_version, 8):
                return True
        return False

    def download(self):
        """
        Download the Spotify app from uptodown.com if it is not present

        Default APK location: GenderEx/tmp/app.apk
        """
        if os.path.isfile(self.workdir.file_apk):
            msg = 'APK-Datei existiert bereits, Download übersprungen.'
            click.echo(msg)
            logging.info(msg)
            return True
        elif not self.downloader:
            msg = 'APK-Datei kann nicht heruntergeladen werden. Beende.'
            click.echo(msg)
            logging.error(msg)
            return False
        else:
            return self.downloader.download_spotify(self.workdir.file_apk)

    def decompile(self):
        """Decompiles Spotify using APKTool"""
        logging.info('Dekompiliere %s mit APKTool ins Verzeichnis %s' % (self.workdir.file_apk, self.workdir.dir_apk))
        subprocess.run(
            ['java', '-jar', self.file_apktool, 'd', self.workdir.file_apk, '-s', '-o', self.workdir.dir_apk])

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
        msg = 'Rekompiliere nach ' + self.workdir.file_apkout
        click.echo(msg)
        logging.info(msg)
        subprocess.run(['java', '-jar', self.file_apktool, 'b', '--use-aapt2',
                        self.workdir.dir_apk, '-o', self.workdir.file_apkout])

        # Check if compile was successful
        assert os.path.isfile(self.workdir.file_apkout)

    def replace(self):
        """Executes all replacements"""
        n_replaced, n_newrpl = self.rtm.do_replace()
        self.rtm.write_replacement_table(self.spotify_version)

        click.echo('%d Ersetzungen vorgenommen' % n_replaced)
        click.echo('%d neue Ersetzungsregeln hinzugefügt' % n_newrpl)

    def _get_missing_replacement(self, key, old):
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
                return self._get_missing_replacement(old)

    def get_spotify_version(self):
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
        cred = cred.replace('{{GENDEREX_VERSION}}', VERSION)
        cred = cred.replace('{{RT_VERSION}}', self.rtm.get_rt_versions())
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
        # Tests if zipalign is installed
        has_zip_align = True
        try:
            subprocess.run('zipalign')
        except FileNotFoundError:
            has_zip_align = False

        cmd = ['java', '-jar', self.file_apksigner,
               '-a', self.workdir.file_apkout, '-o', self.workdir.dir_output,
               '--ks', self.workdir.file_keystore, '--ksAlias', 'genderex', '--ksPass', self.ks_password,
               '--ksKeyPass', self.key_password]

        if has_zip_align:
            cmd += ['--zipAlignPath', 'zipalign']

        subprocess.run(cmd)

        rtver = self.rtm.get_rt_versions()

        # Move apk file
        self.file_apkout = self.workdir.get_file_apkout(self.spotify_version, rtver)
        logging.info('Speichere App unter %s' % self.file_apkout)
        os.renames(self.workdir.file_apkout_signed, self.file_apkout)

        # Move log file
        logging.shutdown()
        if os.path.isfile(self.workdir.file_log):
            file_logout = self.workdir.get_file_logout(self.spotify_version, rtver)
            os.renames(self.workdir.file_log, file_logout)

    def wait_for_enter(self, msg):
        """Displays a message and waits for the user to press ENTER. Does nothing in non-interactive mode."""
        if not self.noia:
            input(msg)
