import unittest
import os
import time
import tests
from spotify_gender_ex import replacement_table

DIR_PERFORMANCE = os.path.join(tests.DIR_TESTFILES, 'performance')


@unittest.skipUnless(tests.TEST_PERFORMANCE, 'performance testing skipped')
class PerformanceTest(unittest.TestCase):
    def _performance_test(self, folder):
        tests.clear_tmp_folder()

        DIR_INPUT = os.path.join(DIR_PERFORMANCE, folder)
        manager = replacement_table.ReplacementManager(DIR_INPUT)

        i = 1
        while True:
            file = os.path.join(DIR_INPUT, 'replacements_%d.json' % i)
            if os.path.isfile(file):
                rt = replacement_table.ReplacementTable.from_file(file)
                manager.add_rtab(rt, str(i))
            else:
                break
            i += 1

        start_time = time.time_ns()
        manager.do_replace(tests.DIR_TMP)

        runtime = time.time_ns() - start_time
        print('%s test took %d ms' % (folder, (runtime / 1000000)))

        tests.assert_files_equal(self, os.path.join(DIR_INPUT, 'lang_nogender.xml'),
                                 os.path.join(tests.DIR_TMP, 'lang.xml'))

    def test_performance_1k(self):
        self._performance_test('1k')

    def test_performance_10k(self):
        self._performance_test('10k')

    def test_performance_100k(self):
        self._performance_test('100k')
