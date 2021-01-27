import click
import subprocess
from importlib_resources import files
import os
from os import path
import re
import hashlib
from spotify_gender_ex.replacement_table import ReplacementTable

# Version as shown in the credits
VERSION = '0.0.1'

class GenderEx:
    def __init__(self, folder_out, file_apk='', folder_apk='', file_replace='', file_apktool='', file_apksigner=''):
        self.spotify_version = ''

        if not file_replace:
            self.rt_original = True
            file_replace = files('spotify_gender_ex.res').joinpath('replacements.json')
        else:
            self.rt_original = False
        self.file_rt = file_replace
        self.replacement_table = ReplacementTable.from_file(file_replace)

        if file_apktool:
            self.file_apktool = file_apktool
        else:
            self.file_apktool = str(files('spotify_gender_ex.lib').joinpath('apktool.jar'))

        if file_apksigner:
            self.file_apksigner = file_apksigner
        else:
            self.file_apksigner = str(files('spotify_gender_ex.lib').joinpath('uber-apk-signer-1.2.1.jar'))

        self.file_apk = file_apk

        try:
            os.makedirs(folder_out)
        except FileExistsError:
            pass
        self.folder_main = folder_out

        # Generate unique folder for apk decomp
        if folder_apk:
            self.folder_apk = folder_apk
        else:
            i = 0
            while True:
                self.folder_apk = path.join(self.folder_main, os.path.splitext(os.path.basename(self.file_apk))[0])
                if i > 0:
                    self.folder_apk += '_' + str(i)
                if not path.exists(self.folder_apk):
                    break
                i += 1

        # Generate unique output file name
        i = 0
        while True:
            self.file_apkout = path.join(self.folder_main, os.path.basename(self.folder_apk))
            if i > 0:
                self.file_apkout += '_' + str(i)
            self.file_apkout += '.apk'
            if not path.exists(self.file_apkout):
                break
            i += 1

        # Generate unique table export file name
        i = 0
        while True:
            self.file_tableout = path.join(self.folder_main, 'replacement')
            if i > 0:
                self.file_tableout += '_' + str(i)
            self.file_tableout += '.json'
            if not path.exists(self.file_tableout):
                break
            i += 1

        self.file_keystore = path.join(self.folder_main, 'genderex.keystore')

    def decompile(self):
        if self.file_apk:
            subprocess.run(['java', '-jar', self.file_apktool, 'd', self.file_apk, '-s', '-o', self.folder_apk])
        else:
            click.echo('Dekompilierung übersprungen.')
        self.spotify_version = self.get_spotify_version()
        click.echo('Spotify-Version %s erkannt.' % self.spotify_version)

    def recompile(self):
        click.echo('Rekompiliere nach ' + self.file_apkout)
        subprocess.run(['java', '-jar', self.file_apktool, 'b', '--use-aapt2', self.folder_apk, '-o', self.file_apkout])

    def replace(self):
        n_replace, n_original_changed, n_suspicious = self.replacement_table.do_replace(self.folder_apk)
        click.echo('%d Ersetzungen vorgenommen' % n_replace)
        click.echo('%d Felder mit geändertem Original' % n_original_changed)
        click.echo('%d verdächtige Felder' % n_suspicious)

        if n_original_changed or n_suspicious:
            if click.confirm('Beenden und die Ersetzungstabelle zuerst manuell bearbeiten?'):
                self.replacement_table.to_file(self.file_tableout)
                exit(0)

        self.replacement_table.write_files(self.folder_apk)

    def get_spotify_version(self):
        apktool_file = path.join(self.folder_apk, 'apktool.yml')

        with open(apktool_file, 'r') as f:
            text = f.read()

        for l in text.splitlines():
            line = l.strip()
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

        with open(credits_file, 'r') as f:
            cred = f.read()
        with open(html_file, 'r') as f:
            html = f.read()

        # Fill in template
        cred = cred.replace('{{SPOTIFY_VERSION}}', self.spotify_version)
        cred = cred.replace('{{GENDEREX_VERSION}}', VERSION)
        cred = cred.replace('{{REPLACEMENT_TABLE}}', 'ORIGINAL' if self.rt_original else 'GEÄNDERT')
        cred = cred.replace('{{REPLACEMENT_HASH}}', self.md5(self.file_rt))

        # Remove credits if there are any
        html = re.sub(r'<div id="gender-ex-credits">[\s\S]*?</div>', '', html)

        # Include the template
        pos = html.find('<body>')
        if pos == -1:
            return
        pos += 6

        html = html[:pos] + cred + html[pos:]

        # Write back the html
        with open(html_file, 'w') as f:
            f.write(html)


    def make_keystore(self):
        if not path.exists(self.file_keystore):
            subprocess.run(['keytool', '-keystore', self.file_keystore, '-genkey', '-alias', 'genderex',
                            '-keyalg', 'RSA', '-keysize', '2048', '-validity', '10000',
                            '-storepass', '12345678', '-keypass', '12345678', '-dname', 'CN=spotify-gender-ex'])

    def sign(self):
        self.make_keystore()
        subprocess.run(['java', '-jar', self.file_apksigner, '-a', self.file_apkout,
                        '--ks', self.file_keystore, '--ksAlias', 'genderex', '--ksPass', '12345678', '--ksKeyPass',
                        '12345678'])


@click.command()
@click.argument('input', type=click.Path(exists=True))
@click.option('-rt', help='Ersetzungstabelle', default='')
def run(input, rt):
    click.echo('0. INFO')
    if path.isfile(input):
        genderex = GenderEx('genderex', file_apk=input, file_replace=rt)
    elif path.isdir(input):
        genderex = GenderEx('genderex', folder_apk=input, file_replace=rt)
    else:
        click.echo('Keine Eingabedaten')
        return

    click.echo('In: %s' % input)
    click.echo('Out: %s' % genderex.folder_main)
    click.echo('APKTool: %s' % genderex.file_apktool)
    click.echo('APKSigner: %s' % genderex.file_apksigner)
    if not click.confirm('Starten?'):
        return

    click.echo('1. DEKOMPILIEREN')
    genderex.decompile()

    click.echo('2. DEGENDERIFIZIEREN')
    genderex.replace()
    genderex.add_credits()

    click.echo('3. REKOMPILIEREN')
    genderex.recompile()

    click.echo('4. SIGNIEREN')
    genderex.sign()

    click.echo('Degenderifizierung abgeschlossen. Vielen Dank.')


if __name__ == '__main__':
    run()
