# coding=utf-8
import os
import shutil
import subprocess
import click


class Workdir:
    def __init__(self, pathin):
        """Create the required files and directories if needed"""
        self.dir_root = self._get_dir(os.path.join(pathin, 'GenderEx'))
        self.dir_output = self._get_dir(os.path.join(self.dir_root, 'output'))
        self.dir_log = self._get_dir(os.path.join(self.dir_output, 'log'))

        self.dir_tmp = os.path.join(self.dir_root, 'tmp')
        self._clear_tmp_folder()

        self.file_keystore = self._get_file(os.path.join(self.dir_root, 'genderex.keystore'), self._create_keystore)
        self.file_rtable = os.path.join(self.dir_root, 'replacements.json')
        self.file_rtable_upd = os.path.join(self.dir_root, 'replacements_updated.json')

        self.file_apk = os.path.join(self.dir_tmp, 'app.apk')
        self.file_log = os.path.join(self.dir_tmp, 'log.txt')
        self.file_apkout = os.path.join(self.dir_tmp, 'app_out.apk')
        self.file_apkout_signed = os.path.join(self.dir_output, 'app_out-aligned-signed.apk')
        self.dir_apk = os.path.join(self.dir_tmp, 'app')
        self.file_apktool = os.path.join(self.dir_apk, 'apktool.yml')

    def get_file_apkout(self, spotify_version, rt_version):
        version_fn = spotify_version.replace('.', '-')
        fname = 'spotify-%s-genderex-%s.apk' % (version_fn, rt_version)
        return os.path.join(self.dir_output, fname)

    def cleanup(self, max_files=0):
        if max_files > 0:
            file_list = sorted(filter(lambda x: x.endswith('.apk'), os.listdir(self.dir_output)))

            for i in range(len(file_list) - max_files):
                click.echo('Löschen: ' + file_list[i])
                os.remove(os.path.join(self.dir_output, file_list[i]))

            self._clear_tmp_folder()

    def _clear_tmp_folder(self):
        try:
            shutil.rmtree(self.dir_tmp)
        except FileNotFoundError:
            pass

        try:
            os.makedirs(self.dir_tmp)
        except FileExistsError:
            pass

    @staticmethod
    def _get_dir(dirpath):
        try:
            os.makedirs(dirpath)
        except FileExistsError:
            pass
        return dirpath

    @staticmethod
    def _get_file(filepath, creator):
        if not os.path.isfile(filepath):
            if callable(creator):
                creator(filepath)
            else:
                return None
        return filepath

    @staticmethod
    def _create_keystore(keystorepath):
        if os.name == 'nt':
            # Keytool on Windows
            keytool_base = str(os.path.join(os.getenv('JAVA_HOME'), 'bin', 'keytool.exe'))
        else:
            # Keytool on Linux
            keytool_base = 'keytool'

        subprocess.run([keytool_base, '-keystore', keystorepath, '-genkey', '-alias', 'genderex',
                        '-keyalg', 'RSA', '-keysize', '2048', '-validity', '50000',
                        '-storepass', '12345678', '-keypass', '12345678', '-dname', 'CN=spotify-gender-ex'])
