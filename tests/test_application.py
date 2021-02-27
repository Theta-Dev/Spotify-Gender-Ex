import unittest
import os
import tests
from spotify_gender_ex import start_genderex

"""
Information: Spotify APK files for script testing are not included in the repository for copyright reasons.
You have to download them manually from here: https://spotify.de.uptodown.com/android/versions
Put them in the tests/testfiles/apk directory.
"""
TESTVERSIONS = [
    '8-5-89-901',
    '8-5-93-445',
    '8-5-94-839',
    '8-5-98-984',
    '8-6-0-830'
]


@unittest.skipUnless(tests.TEST_APPLICATION, 'application test skipped')
class ScriptTest(unittest.TestCase):
    def do_script_test(self, version):
        self.maxDiff = None

        apk_file = os.path.join(tests.DIR_APK, 'spotify-%s.apk' % version)
        gex_folder = os.path.join(tests.DIR_TMP, 'GenderEx')
        out_folder = os.path.join(gex_folder, 'output')
        app_folder = os.path.join(gex_folder, 'tmp', 'app')

        nogender_files = [os.path.join(tests.DIR_TESTFILES, 'nogender', '%s_plurals.xml' % version),
                          os.path.join(tests.DIR_TESTFILES, 'nogender', '%s_strings.xml' % version)]
        modified_files = [os.path.join(app_folder, 'res', 'values-de', 'plurals.xml'),
                          os.path.join(app_folder, 'res', 'values-de', 'strings.xml')]

        # Empty output folder
        tests.clear_tmp_folder()

        # Run the script
        start_genderex(apk_file, tests.DIR_TMP, '', '', '', tests.NOSSL,
                       True, True, 0, False, not tests.RECOMPILE, True)

        # Verify replacements
        for i in range(len(nogender_files)):
            tests.assert_files_equal(self, nogender_files[i], modified_files[i])

        # Is output apk present?
        if tests.RECOMPILE:
            self.assertTrue(str(os.listdir(out_folder)[0]).startswith(
                'spotify-%s-genderex-' % version))

    def test_application(self):
        if tests.TEST_ALL_VERSIONS:
            versions = TESTVERSIONS
        else:
            # Run tests for oldest version + 2 most recent versions
            versions = TESTVERSIONS[0:1] + TESTVERSIONS[-2:]

        for version in versions:
            self.do_script_test(version)


if __name__ == '__main__':
    unittest.main()
