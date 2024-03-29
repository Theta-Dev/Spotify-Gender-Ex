import os
import unittest

import tests
from spotify_gender_ex import appstore, downloader
from spotify_gender_ex.__main__ import start_genderex

DOWNLOAD_IDS = {
    '8-5-89-901': '3065569',
    '8-5-93-445': '3145501',
    '8-5-94-839': '3170083',
    '8-5-98-984': '3217260',
    '8-6-0-830': '3243383',
    '8-6-4-971': '3313036'
}

TESTVERSIONS = list(DOWNLOAD_IDS.keys())


@unittest.skipUnless(tests.TEST_APPLICATION, 'application test skipped')
class ScriptTest(unittest.TestCase):
    def do_script_test(self, version, builtin):
        self.maxDiff = None

        # Create APK dir if not existant
        if not os.path.exists(tests.DIR_APK):
            os.makedirs(tests.DIR_APK)

        apk_file = os.path.join(tests.DIR_APK, 'spotify-%s.apk' % version)
        gex_folder = os.path.join(tests.DIR_TMP, 'GenderEx')
        out_folder = os.path.join(gex_folder, 'output')
        app_folder = os.path.join(gex_folder, 'tmp', 'app')

        nogender_files = [os.path.join(tests.DIR_TESTFILES, 'nogender', '%s_plurals.xml' % version),
                          os.path.join(tests.DIR_TESTFILES, 'nogender', '%s_strings.xml' % version)]
        modified_files = [os.path.join(app_folder, 'res', 'values-de', 'plurals.xml'),
                          os.path.join(app_folder, 'res', 'values-de', 'strings.xml')]

        # Dowload apk file if not existant
        if not os.path.isfile(apk_file):
            app = appstore.get_spotify_app_from_id(DOWNLOAD_IDS[version])

            if downloader.download_file(app.download_url, apk_file, version):
                print('Downloaded ' + version)
            else:
                self.fail('Download not successful')

        # Empty output folder
        tests.clear_tmp_folder()

        # Run the script
        start_genderex(apk_file, tests.DIR_TMP, builtin=builtin, no_interaction=True, force=True)

        # Verify replacements
        for i in range(len(nogender_files)):
            tests.assert_files_equal(self, nogender_files[i], modified_files[i])

        # Is output apk present?
        out_files = os.listdir(out_folder)
        out_apk = filter(lambda x: x.endswith('.apk'), out_files).__next__()

        self.assertTrue(out_apk.startswith('spotify-%s-genderex-' % version))

    def test_application(self):
        if tests.TEST_ALL_VERSIONS:
            versions = TESTVERSIONS
        else:
            # Run tests for oldest version + 2 most recent versions
            versions = TESTVERSIONS[0:1] + TESTVERSIONS[-2:]

        for version in versions:
            self.do_script_test(version, True)

    def test_github_replacements(self):
        self.do_script_test(TESTVERSIONS[-1], False)


if __name__ == '__main__':
    unittest.main()
