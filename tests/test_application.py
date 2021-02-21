import unittest
from importlib_resources import files
import os
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

ALL_VERSIONS = False

DIR_TESTFILES = str(files('tests.testfiles').joinpath(''))
DIR_TMP = os.path.join(DIR_TESTFILES, 'tmp')
DIR_APK = os.path.join(DIR_TESTFILES, 'apk')


def clear_tmp_folder():
    try:
        shutil.rmtree(DIR_TMP)
    except FileNotFoundError:
        pass

    try:
        os.makedirs(DIR_TMP)
    except FileExistsError:
        pass


class ScriptTest(unittest.TestCase):
    def do_script_test(self, version):
        self.maxDiff = None

        apk_file = os.path.join(DIR_APK, 'spotify-%s.apk' % version)
        gex_folder = os.path.join(DIR_TMP, 'GenderEx')
        out_folder = os.path.join(gex_folder, 'output')
        app_folder = os.path.join(gex_folder, 'tmp', 'app')

        nogender_files = [os.path.join(TESTFILES, 'nogender', '%s_plurals.xml' % version),
                          os.path.join(TESTFILES, 'nogender', '%s_strings.xml' % version)]
        modified_files = [os.path.join(app_folder, 'res', 'values-de', 'plurals.xml'),
                          os.path.join(app_folder, 'res', 'values-de', 'strings.xml')]

        # Empty output folder
        clear_tmp_folder()

        # Run the script
        start_genderex(apk_file, DIR_TMP, '', True, not RECOMPILE)

        # Verify replacements
        for i in range(len(nogender_files)):
            with open(nogender_files[i], 'r') as f:
                nogender = f.read()
            with open(modified_files[i], 'r') as f:
                modified = f.read()

            self.assertEqual(nogender, modified)

        # Is output apk present?
        if RECOMPILE:
            self.assertTrue(str(os.listdir(out_folder)[0]).startswith('spotify-%s-genderex-' % version))

    def test_application(self):
        if ALL_VERSIONS:
            versions = TESTVERSIONS
        else:
            # Run tests for oldest version + 2 most recent versions
            versions = TESTVERSIONS[0:1] + TESTVERSIONS[-2:]

        for version in versions:
            self.do_script_test(version)


if __name__ == '__main__':
    unittest.main()
