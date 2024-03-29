# coding=utf-8
import os
import shutil
import subprocess


class Workdir:
    def __init__(self, pathin, ks_password='12345678', key_password='12345678'):
        """Create the required files and directories if needed"""
        self.ks_password = ks_password
        self.key_password = key_password

        self.dir_root = self._get_dir(os.path.join(pathin, 'GenderEx'))
        self.dir_output = self._get_dir(os.path.join(self.dir_root, 'output'))

        self.dir_tmp = os.path.join(self.dir_root, 'tmp')
        self._clear_tmp_folder()

        self.file_keystore = self._get_file(os.path.join(self.dir_root, 'genderex.keystore'), self._create_keystore)
        self.file_rtable = os.path.join(self.dir_root, 'replacements.json')
        self.file_version = os.path.join(self.dir_root, 'spotify_version.txt')

        self.file_apk = os.path.join(self.dir_tmp, 'app.apk')
        self.file_apkout = os.path.join(self.dir_tmp, 'app_out.apk')
        self.file_apkout_signed = os.path.join(self.dir_output, 'app_out-aligned-signed.apk')
        self.dir_apk = os.path.join(self.dir_tmp, 'app')
        self.file_apktool = os.path.join(self.dir_apk, 'apktool.yml')

    @staticmethod
    def _output_basename(spotify_version, rt_version):
        version_fn = spotify_version.replace('.', '-')
        return str('%s-genderex-%s' % (version_fn, rt_version))

    def _output_file(self, spotify_version, rt_version, name, ending, folder=''):
        basepath = self.dir_output
        if folder:
            basepath = Workdir._get_dir(os.path.join(basepath, folder))

        basename = Workdir._output_basename(spotify_version, rt_version)
        file = os.path.join(basepath, name + '-' + basename + '.' + ending)

        if os.path.isfile(file):
            os.remove(file)
        return file

    def get_file_apkout(self, spotify_version, rt_version):
        return self._output_file(spotify_version, rt_version, 'spotify', 'apk')

    def get_file_newrepl(self, spotify_version, rt_version):
        return self._output_file(spotify_version, rt_version, 'repl', 'json', 'repl')

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
    def _keytool_base():
        if os.name == 'nt':
            # Keytool on Windows
            return str(os.path.join(os.getenv('JAVA_HOME'), 'bin', 'keytool.exe'))
        else:
            # Keytool on Linux
            return 'keytool'

    def _create_keystore(self, keystorepath):
        subprocess.run([self._keytool_base(), '-keystore', keystorepath, '-genkey', '-alias', 'genderex',
                        '-keyalg', 'RSA', '-keysize', '2048', '-validity', '50000',
                        '-storepass', self.ks_password, '-keypass', self.key_password, '-dname',
                        'CN=spotify-gender-ex'], check=True)

        # Check if keystore generation was successful
        assert os.path.isfile(keystorepath), 'Keystore konnte nicht erzeugt werden'
