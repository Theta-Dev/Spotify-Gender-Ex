import unittest
from importlib_resources import files
from os import path
import shutil
from spotify_gender_ex.main import start_genderex

"""
Information: Spotify APK files for script testing are not included in the repository for copyright reasons.
You have to download them manually from here: https://spotify.de.uptodown.com/android/versions
Put them in the tests/testfiles/apk directory.
"""
TESTFILES = str(files('tests.testfiles').joinpath(''))


class ScriptTest(unittest.TestCase):
    def do_script_test(self, version):
        self.maxDiff = None

        apk_file = path.join(TESTFILES, 'apk', 'spotify-%s.apk' % version)
        out_folder = path.join(TESTFILES, 'output', 'genderex')

        nogender_files = [path.join(TESTFILES, 'nogender', '%s_plurals.xml' % version),
                          path.join(TESTFILES, 'nogender', '%s_strings.xml' % version)]
        modified_files = [path.join(out_folder, 'spotify-%s' % version, 'res', 'values-de', 'plurals.xml'),
                          path.join(out_folder, 'spotify-%s' % version, 'res', 'values-de', 'strings.xml')]

        # Empty output folder
        shutil.rmtree(out_folder)

        # Run the script
        start_genderex(apk_file, '', out_folder, True)

        # Verify replacements
        for i in range(len(nogender_files)):
            with open(nogender_files[i], 'r') as f:
                nogender = f.read()
            with open(modified_files[i], 'r') as f:
                modified = f.read()

            self.assertEqual(nogender, modified)

        # Are output apks present?
        self.assertTrue(path.isfile(path.join(out_folder, 'spotify-%s-gex.apk' % version)))
        self.assertTrue(path.isfile(path.join(out_folder, 'spotify-%s-gex-aligned-signed.apk' % version)))

    # Run tests for all compatible Spotify versions
    def test_spotify_8_5_89_901(self):
        self.do_script_test('8-5-89-901')

    def test_spotify_8_5_93_445(self):
        self.do_script_test('8-5-93-445')

    def test_spotify_8_5_94_839(self):
        self.do_script_test('8-5-94-839')


if __name__ == '__main__':
    unittest.main()
