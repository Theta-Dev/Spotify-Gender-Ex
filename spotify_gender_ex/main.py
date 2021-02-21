# coding=utf-8
import click
import subprocess
from importlib_resources import files
import os
import re
from datetime import datetime
from spotify_gender_ex.replacement_table import ReplacementManager, ReplacementTable
from spotify_gender_ex.workdir import Workdir
from spotify_gender_ex import downloader

# Version as shown in the credits
VERSION = '1.0.0'


class GenderEx:
    def __init__(self, apk_file='', folder_out='.', replacement_table='', no_interaction=False):
        self.spotify_version = ''
        self.noia = no_interaction

        # Java libraries
        self.file_apktool = str(files('spotify_gender_ex.lib').joinpath('apktool.jar'))
        self.file_apksigner = str(files('spotify_gender_ex.lib').joinpath('uber-apk-signer-1.2.1.jar'))

        self.workdir = Workdir(folder_out)
        self.rtm = ReplacementManager(self.workdir, self._get_missing_replacement)

        try:
            self.downloader = downloader.Downloader()
            self.latest_spotify = self.downloader.spotify_version
        except downloader.DownloaderException as e:
            click.echo(str(e))
            self.downloader = None
            self.latest_spotify = 'NA'

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
            try:
                rtab_raw = downloader.get_replacement_table_raw()
                rt_builtin = ReplacementTable.from_string(rtab_raw)
            except Exception as e:
                click.echo(str(e))
                rt_builtin = ReplacementTable.from_file(files('spotify_gender_ex.res').joinpath('replacements.json'))

            self.rtm.add_rtab(rt_builtin, 'builtin')
            self.rtm.add_rtab(rt_custom, 'custom', True)

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
            click.echo('APK-Datei existiert bereits, Download übersprungen.')
            return True
        elif not self.downloader:
            click.echo('APK-Datei kann nicht heruntergeladen werden. Beende.')
            return False
        else:
            return self.downloader.download_spotify(self.workdir.file_apk)

    def decompile(self):
        """Decompiles Spotify using APKTool"""
        subprocess.run(
            ['java', '-jar', self.file_apktool, 'd', self.workdir.file_apk, '-s', '-o', self.workdir.dir_apk])

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
                        self.workdir.dir_apk, '-o', self.workdir.file_apkout])

    def replace(self):
        """Executes all replacements"""
        n_replaced, n_newrpl = self.rtm.do_replace()
        self.rtm.write_replacement_table(self.spotify_version)

        click.echo('%d Ersetzungen vorgenommen' % n_replaced)
        click.echo('%d neue Ersetzungsregeln hinzugefügt' % n_newrpl)

    def _get_missing_replacement(self, langfield):
        """
        This method gets called by the ReplacementManager if it cant replace a suspicious field.
        Prompts the user to manually enter a replacement value.
        In non-interactive mode it will skip the field instead.
        """
        click.echo('Verdächtig: %s' % langfield.old)
        if self.noia:
            return langfield.old
        else:
            try:
                new_text = click.edit(str(langfield.old))
            except click.ClickException:
                # No inline editing, less user friendly, but if the above does not work:
                new_text = click.prompt('Neuer Text:', str(langfield.old))

            if new_text:
                return new_text.strip()
            else:
                self.wait_for_enter('Enter drücken, um die Eingabe zu wiederholen.')
                return self._get_missing_replacement(langfield)

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
        subprocess.run(['java', '-jar', self.file_apksigner,
                        '-a', self.workdir.file_apkout, '-o', self.workdir.dir_output,
                        '--ks', self.workdir.file_keystore, '--ksAlias', 'genderex', '--ksPass', '12345678',
                        '--ksKeyPass', '12345678'])

        # Rename apk file
        self.file_apkout = self.workdir.get_file_apkout(self.spotify_version, self.rtm.get_rt_versions())
        os.renames(self.workdir.file_apkout_signed, self.file_apkout)

    def wait_for_enter(self, msg):
        """Displays a message and waits for the user to press ENTER. Does nothing in non-interactive mode."""
        if not self.noia:
            input(msg)


def start_genderex(apk_file, directory='.', replacement_table='', no_interaction=False, no_compile=False):
    click.echo('0. INFO')
    if not os.path.isdir(directory):
        click.echo('Keine Eingabedaten')
        return

    genderex = GenderEx(apk_file, directory, replacement_table, no_interaction)

    click.echo('Spotify-Gender-Ex Version: %s' % VERSION)
    click.echo('Aktuelle Spotify-Version: %s' % genderex.latest_spotify)

    # Non-interactive mode is meant for automation.
    # In this case, dont process the same spotify version multiple times
    if genderex.is_latest_spotify_processed():
        click.echo('Du hast bereits die aktuellste Spotify-Version degenderifiziert.')
        if no_interaction:
            click.echo('Vielen Dank.')
            return

    genderex.wait_for_enter('Drücke Enter zum Starten...')

    click.echo('1. HERUNTERLADEN')
    if not genderex.download():
        return

    click.echo('2. DEKOMPILIEREN')
    genderex.decompile()
    genderex.check_compatibility()

    click.echo('3. DEGENDERIFIZIEREN')
    genderex.replace()
    genderex.add_credits()

    # This is only for reducing test time
    if no_compile:
        return

    click.echo('4. REKOMPILIEREN')
    genderex.recompile()

    click.echo('5. SIGNIEREN')
    genderex.sign()

    click.echo('Degenderifizierung abgeschlossen. Vielen Dank.')
    click.echo('Deine Spotify-App befindet sich hier:')
    click.echo(genderex.file_apkout)


@click.command()
@click.option('-a', help='Spotify-App (APK)', default='', type=click.Path())
@click.option('-d', help='GenderEx-Ordner', default='.', type=click.Path())
@click.option('-rt', help='Ersetzungstabelle überschreiben', type=click.Path(exists=True))
@click.option('--noia', help='Prompts (ja/nein) deaktivieren', is_flag=True)
def run(a, d, rt, noia):
    """Entferne die Gendersternchen (z.B. Künstler*innen) aus der Spotify-App für Android!"""
    start_genderex(a, d, rt, noia)


if __name__ == '__main__':
    run()
