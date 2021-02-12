# coding=utf-8
import click
import subprocess
from importlib_resources import files
import os
from os import path
import re
import hashlib
from datetime import datetime
from spotify_gender_ex.replacement_table import ReplacementTable

# Version as shown in the credits
VERSION = '0.3.0'
RT_HASH = '8ca73f670adca762bf5d1b63c36ecd34'


class GenderEx:
    def __init__(self, folder_out, file_apk='', folder_apk='', file_replace='', no_interaction=False):
        self.spotify_version = ''
        self.no_interaction = no_interaction

        # Java libraries
        self.file_apktool = str(files('spotify_gender_ex.lib').joinpath('apktool.jar'))
        self.file_apksigner = str(files('spotify_gender_ex.lib').joinpath('uber-apk-signer-1.2.1.jar'))

        # Replacement table
        if not file_replace:
            file_replace = str(files('spotify_gender_ex.res').joinpath('replacements.json'))
        self.file_rt = str(file_replace)
        self.replacement_table = ReplacementTable.from_file(file_replace)

        # Replacement table hash
        self.rt_hash = self.md5(self.file_rt)
        self.rt_original = self.rt_hash == RT_HASH

        # Output folder
        try:
            os.makedirs(folder_out)
        except FileExistsError:
            pass
        self.folder_main = folder_out

        self.file_apk = str(file_apk)

        # Generate unique folder for apk decomp
        if folder_apk:
            self.folder_apk = str(folder_apk)
        else:
            i = 0
            while True:
                self.folder_apk = str(path.join(self.folder_main, os.path.splitext(os.path.basename(self.file_apk))[0]))
                if i > 0:
                    self.folder_apk += '_' + str(i)
                if not path.exists(self.folder_apk):
                    break
                i += 1

        # Output file
        self.file_apkout = self.folder_apk + '-gex.apk'

        # Generate unique table export file name
        i = 0
        while True:
            self.file_tableout = str(path.join(self.folder_main, 'replacements'))
            if i > 0:
                self.file_tableout += '_' + str(i)
            self.file_tableout += '.json'
            if not path.exists(self.file_tableout):
                break
            i += 1

        # Keystore file
        self.file_keystore = str(path.join(self.folder_main, 'genderex.keystore'))

    def decompile(self):
        subprocess.run(['java', '-jar', self.file_apktool, 'd', self.file_apk, '-s', '-o', self.folder_apk])

    def check_compatibility(self):
        self.spotify_version = self.get_spotify_version()
        click.echo('Spotify-Version %s erkannt.' % self.spotify_version)

        if self.replacement_table.spotify_compatible(self.spotify_version):
            click.echo('Diese Version ist mit der Ersetzungstabelle kompatibel.')
        else:
            click.echo(
                'Diese Version ist nicht mit der Ersetzungstabelle kompatibel. Erwarte, manuelle Anpassungen vornehmen zu müssen')

    def recompile(self):
        click.echo('Rekompiliere nach ' + self.file_apkout)
        subprocess.run(['java', '-jar', self.file_apktool, 'b', '--use-aapt2', self.folder_apk, '-o', self.file_apkout])

    def replace(self):
        n_replace, n_original_changed, n_suspicious = self.replacement_table.do_replace(self.folder_apk)
        click.echo('%d Ersetzungen vorgenommen' % n_replace)
        click.echo('%d Felder mit geändertem Original' % n_original_changed)
        click.echo('%d verdächtige Felder' % n_suspicious)

        if not self.no_interaction and (n_original_changed or n_suspicious):
            if click.confirm('Beenden und die Ersetzungstabelle zuerst manuell bearbeiten?'):
                self.replacement_table.to_file(self.file_tableout)
                exit(0)

        self.replacement_table.write_files(self.folder_apk)

    def get_spotify_version(self):
        apktool_file = path.join(self.folder_apk, 'apktool.yml')

        with open(apktool_file, 'r', encoding='utf-8') as f:
            text = f.read()

        for line in text.splitlines():
            line = line.strip()
            if line.startswith('versionName:'):
                return line[12:].strip()

    @staticmethod
    def md5(fname):
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def add_credits(self):
        # Read the credits file
        credits_file = files('spotify_gender_ex.res').joinpath('credits.html')
        html_file = path.join(self.folder_apk, 'assets', 'licenses.xhtml')

        with open(credits_file, 'r', encoding='utf-8') as f:
            cred = f.read()
        with open(html_file, 'r', encoding='utf-8') as f:
            html = f.read()

        # Fill in template
        cred = cred.replace('{{SPOTIFY_VERSION}}', self.spotify_version)
        cred = cred.replace('{{GENDEREX_VERSION}}', VERSION)
        cred = cred.replace('{{REPLACEMENT_TABLE}}', 'ORIGINAL' if self.rt_original else 'MODIFIZIERT')
        cred = cred.replace('{{REPLACEMENT_HASH}}', self.rt_hash)
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

    def make_keystore(self):
        if not path.exists(self.file_keystore):
            if os.name == 'nt':
                # Keytool on Windows
                keytool_base = str(os.path.join(os.getenv('JAVA_HOME'), 'bin', 'keytool.exe'))
            else:
                keytool_base = 'keytool'

            subprocess.run([keytool_base, '-keystore', self.file_keystore, '-genkey', '-alias', 'genderex',
                            '-keyalg', 'RSA', '-keysize', '2048', '-validity', '50000',
                            '-storepass', '12345678', '-keypass', '12345678', '-dname', 'CN=spotify-gender-ex'])

    def sign(self):
        self.make_keystore()
        subprocess.run(['java', '-jar', self.file_apksigner, '-a', self.file_apkout,
                        '--ks', self.file_keystore, '--ksAlias', 'genderex', '--ksPass', '12345678', '--ksKeyPass',
                        '12345678'])


def start_genderex(inputfile, rt='', out='genderex', no_interaction=False, no_compile=False):
    click.echo('0. INFO')
    if path.isfile(inputfile):
        decomp = True
        genderex = GenderEx(out, file_apk=inputfile, file_replace=rt, no_interaction=no_interaction)
    elif path.isdir(inputfile):
        decomp = False
        genderex = GenderEx(out, folder_apk=inputfile, file_replace=rt, no_interaction=no_interaction)
    else:
        click.echo('Keine Eingabedaten')
        return

    click.echo('Spotify-Gender-Ex Version %s' % VERSION)
    click.echo('In: %s' % inputfile)
    click.echo('Out: %s' % genderex.folder_main)
    click.echo('Ersetzungstabelle: %s' % genderex.file_rt)
    click.echo('ET-Hash: %s (%s)' % (genderex.rt_hash, 'Original' if genderex.rt_original else 'Modifiziert'))
    click.echo('APKTool: %s' % genderex.file_apktool)
    click.echo('APKSigner: %s' % genderex.file_apksigner)
    if not no_interaction:
        if not click.confirm('Starten?'):
            return

    if decomp:
        click.echo('1. DEKOMPILIEREN')
        genderex.decompile()

    genderex.check_compatibility()

    click.echo('2. DEGENDERIFIZIEREN')
    genderex.replace()
    genderex.add_credits()

    if no_compile:
        return

    if not no_interaction:
        if not click.confirm('Rekompilieren?'):
            return

    click.echo('3. REKOMPILIEREN')
    genderex.recompile()

    click.echo('4. SIGNIEREN')
    genderex.sign()

    click.echo('Degenderifizierung abgeschlossen. Vielen Dank.')


@click.command()
@click.argument('inputfile', type=click.Path(exists=True))
@click.option('-rt', help='Ersetzungstabelle', default='')
@click.option('-out', help='Ausgabeordner', default='genderex')
@click.option('--noia', help='Prompts (ja/nein) deaktivieren', is_flag=True)
def run(inputfile, rt, out, noia):
    """Entferne die Gendersternchen (z.B. Künstler*innen) aus der Spotify-App für Android!"""
    start_genderex(inputfile, rt, out, noia)


if __name__ == '__main__':
    run()
