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
TESTVERSIONS = [
    '8-5-89-901',
    '8-5-93-445',
    '8-5-94-839',
    '8-5-98-984',
    '8-6-0-830'
]

# Test recompilation (Tests will take longer)
RECOMPILE = False


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
        start_genderex(apk_file, '', out_folder, True, not RECOMPILE)

        # Verify replacements
        for i in range(len(nogender_files)):
            with open(nogender_files[i], 'r') as f:
                nogender = f.read()
            with open(modified_files[i], 'r') as f:
                modified = f.read()

            self.assertEqual(nogender, modified)

        # Are output apks present?
        if RECOMPILE:
            self.assertTrue(path.isfile(path.join(out_folder, 'spotify-%s-gex.apk' % version)))
            self.assertTrue(path.isfile(path.join(out_folder, 'spotify-%s-gex-aligned-signed.apk' % version)))

    '''
    def test_complete(self):
        """Run tests for all compatible spotify versions"""
        for version in TESTVERSIONS:
            self.do_script_test(version)
    '''

    def test_reduced(self):
        """Run tests for oldest version + 2 most recent versions"""
        versions = TESTVERSIONS[0:1] + TESTVERSIONS[-2:]

        for version in versions:
            self.do_script_test(version)


if __name__ == '__main__':
    unittest.main()
