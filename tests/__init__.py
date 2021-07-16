import os
import shutil
from importlib_resources import files

# Test cases to run
TEST_DOWNLOAD = False
TEST_APPLICATION = False
TEST_PERFORMANCE = True

# Application test options
TEST_ALL_VERSIONS = False

DIR_TESTFILES = str(files('tests.testfiles').joinpath(''))
DIR_TMP = os.path.join(DIR_TESTFILES, 'tmp')
DIR_APK = os.path.join(DIR_TESTFILES, 'apk')
DIR_LANG = os.path.join(DIR_TESTFILES, 'lang')
DIR_REPLACE = os.path.join(DIR_TESTFILES, 'replace')
DIR_MAKE = os.path.join(DIR_TESTFILES, 'make')


def clear_tmp_folder():
    try:
        shutil.rmtree(DIR_TMP)
    except FileNotFoundError:
        pass

    try:
        os.makedirs(DIR_TMP)
    except FileExistsError:
        pass


def assert_files_equal(test, file1, file2):
    with open(file1, 'r') as f:
        c1 = f.read()
    with open(file2, 'r') as f:
        c2 = f.read()
    test.assertEqual(c1, c2)
