import unittest
import os
import shutil
from importlib_resources import files
from spotify_gender_ex import downloader, workdir, replacement_table, lang_file, main

DIR_TESTFILES = str(files('tests.testfiles').joinpath(''))
DIR_LANG = os.path.join(DIR_TESTFILES, 'lang')
DIR_REPLACE = os.path.join(DIR_TESTFILES, 'replace')
DIR_TMP = os.path.join(DIR_TESTFILES, 'tmp')

RT_STRING = '''{
  "version": 0,
  "spotify_versions": [
    "unittest"
  ],
  "files": [
    {
      "path": "file1_withgender.xml",
      "replace": []
    },
    {
      "path": "file2_withgender.xml",
      "replace": []
    }
  ]
}'''


def clear_tmp_folder():
    try:
        shutil.rmtree(DIR_TMP)
    except FileNotFoundError:
        pass

    try:
        os.makedirs(DIR_TMP)
    except FileExistsError:
        pass


def assert_files_equal(test: unittest.TestCase, file1, file2):
    with open(file1, 'r') as f:
        c1 = f.read()
    with open(file2, 'r') as f:
        c2 = f.read()
    test.assertEqual(c1, c2)


class DownloaderTest(unittest.TestCase):
    def test_spotify_version(self):
        dldr = downloader.Downloader()
        self.assertRegex(dldr.spotify_version, r'\d+.\d+.\d+.\d+')
        self.assertTrue(dldr.spotify_url.startswith('https://dw.uptodown.com/dwn/'))

    def test_download_spotify(self):
        clear_tmp_folder()

        dldr = downloader.Downloader()
        path = os.path.join(DIR_TMP, 'spotify.apk')
        dldr.download_spotify(path)
        self.assertGreater(os.path.getsize(path), 20000000)

    def test_download_replacement_table(self):
        rpl_text = downloader.get_replacement_table_raw()
        rtab = replacement_table.ReplacementTable.from_string(rpl_text)

        self.assertTrue(rtab.version > 0)
        self.assertTrue(len(rtab.sets) > 0)
        self.assertTrue(len(rtab.spotify_versions) > 0)


class WorkdirTest(unittest.TestCase):
    def test_workdir_creation(self):
        clear_tmp_folder()
        workdir.Workdir(DIR_TMP)
        dir_root = os.path.join(DIR_TMP, 'GenderEx')

        self.assertTrue(os.path.isfile(os.path.join(dir_root, 'genderex.keystore')))
        self.assertTrue(os.path.isdir(os.path.join(dir_root, 'tmp')))
        self.assertTrue(os.path.isdir(os.path.join(dir_root, 'output')))


class LangFileTest(unittest.TestCase):
    def test_from_file(self):
        self._test_from_file('file1_withgender.xml', 20)
        self._test_from_file('file2_withgender.xml', 8)

    def _test_from_file(self, file, ass_len):
        path = os.path.join(DIR_LANG, file)
        lfile = lang_file.LangFile.from_file(path)

        self.assertEqual(ass_len, len(lfile.fields))
        self.assertEqual(path, lfile.path)

    def test_to_file(self):
        self._test_to_file('file1_withgender.xml')
        self._test_to_file('file2_withgender.xml')

    def _test_to_file(self, file):
        clear_tmp_folder()
        path = os.path.join(DIR_LANG, file)
        path_out = os.path.join(DIR_TMP, 'lang.xml')

        lfile = lang_file.LangFile.from_file(path)
        lfile.to_file(path_out)

        assert_files_equal(self, path, path_out)

    def test_modify_file(self):
        self._test_modify_file('file1_withgender.xml', 'file1_mod.xml')
        self._test_modify_file('file2_withgender.xml', 'file2_mod.xml')

    def _test_modify_file(self, file, file_mod):
        clear_tmp_folder()
        path = os.path.join(DIR_LANG, file)
        path_mod = os.path.join(DIR_LANG, file_mod)
        path_out = os.path.join(DIR_TMP, 'lang.xml')

        lfile = lang_file.LangFile.from_file(path)
        lfile.fields[0].new = 'MODIFIED'
        self.assertTrue(lfile.fields[0].is_replaced())

        lfile.to_file(path_out)
        assert_files_equal(self, path_mod, path_out)

    def test_is_suspicious(self):
        self._test_is_suspicious('file1_withgender.xml', 6)
        self._test_is_suspicious('file2_withgender.xml', 4)

    def _test_is_suspicious(self, file, ass_sus):
        path = os.path.join(DIR_LANG, file)
        lfile = lang_file.LangFile.from_file(path)

        n_suspicious = sum(1 for field in lfile.fields if field.is_suspicious())
        self.assertEqual(ass_sus, n_suspicious)


class ReplacementTest(unittest.TestCase):
    def test_replacement(self):
        rp1 = replacement_table.Replacement('testkey', 'testval', 'MODIFIED')
        rp2 = replacement_table.Replacement('testkey/xyz', 'testval', 'MODIFIED_2')

        lf = lang_file.LangField(['testkey'], 'testval')

        self.assertFalse(rp2.try_replace(lf))
        self.assertTrue(rp1.try_replace(lf))
        self.assertTrue(rp2.try_replace(lf))

    def test_from_langfield(self):
        lf1 = lang_file.LangField(['testkey'], 'testval')
        lf2 = lang_file.LangField(['testkey', 'xyz'], 'testval')

        rp1 = replacement_table.Replacement.from_langfield(lf1)
        rp2 = replacement_table.Replacement.from_langfield(lf2)

        self.assertEqual(['testkey'], rp1.key_list)
        self.assertEqual(['testkey', 'xyz'], rp2.key_list)

        self.assertEqual('testval', rp1.old)
        self.assertEqual('testval', rp1.new)

        self.assertEqual('testval', rp2.old)
        self.assertEqual('testval', rp2.new)

        self.assertTrue(rp1.inserted)
        self.assertTrue(rp2.inserted)

    def test_to_json(self):
        rp = replacement_table.Replacement('testkey/xyz', 'testval', 'MODIFIED')
        data = {
            'key': 'testkey/xyz',
            'old': 'testval',
            'new': 'MODIFIED'
        }
        self.assertEqual(data, rp.to_json())


class ReplacementTableTest(unittest.TestCase):
    def test_from_file(self):
        path1 = os.path.join(DIR_REPLACE, 'replacements.json')
        path2 = os.path.join(DIR_REPLACE, 'replacements_empty.json')

        rt1 = replacement_table.ReplacementTable.from_file(path1)
        rt2 = replacement_table.ReplacementTable.from_file(path2)

        self.assertEqual(path1, rt1.path)
        self.assertEqual(path2, rt2.path)

        self.assertEqual(1, rt1.version)
        self.assertEqual(0, rt2.version)

        self.assertEqual(["unittest"], rt1.spotify_versions)
        self.assertEqual(["unittest"], rt2.spotify_versions)

        self.assertEqual(['file1_withgender.xml', 'file2_withgender.xml'], list(map(lambda s: s.path, rt1.sets)))
        self.assertEqual(['file1_withgender.xml', 'file2_withgender.xml'], list(map(lambda s: s.path, rt2.sets)))

    def test_from_string(self):
        rt = replacement_table.ReplacementTable.from_string(RT_STRING)

        self.assertIsNone(rt.path)
        self.assertEqual(0, rt.version)
        self.assertEqual(["unittest"], rt.spotify_versions)
        self.assertEqual(['file1_withgender.xml', 'file2_withgender.xml'], list(map(lambda s: s.path, rt.sets)))

    def test_set_from_langfile(self):
        path = os.path.join(DIR_REPLACE, 'replacements_empty.json')
        rt = replacement_table.ReplacementTable.from_file(path)

        rset = rt.set_from_langfile('file1_withgender.xml')
        self.assertEqual('file1_withgender.xml', rset.path)

        rset = rt.set_from_langfile('missingno.xml')
        self.assertIsNone(rset)

        rset = rt.make_set_from_langfile('missingno.xml')
        self.assertEqual('missingno.xml', rset.path)

    def test_add_to_file(self):
        clear_tmp_folder()

        path = os.path.join(DIR_REPLACE, 'replacements_empty.json')
        path_out = os.path.join(DIR_TMP, 'replacements.json')
        path_ass = os.path.join(DIR_REPLACE, 'replacements_testadd.json')

        rt = replacement_table.ReplacementTable.from_file(path)

        rt.set_from_langfile('file1_withgender.xml') \
            .add(replacement_table.Replacement('Biblec', 'Künstler*innen', 'Künstler'))

        rt.to_file(path_out)
        assert_files_equal(self, path_ass, path_out)

    def test_to_string(self):
        path = os.path.join(DIR_REPLACE, 'replacements_empty.json')
        rt = replacement_table.ReplacementTable.from_file(path)

        self.assertEqual(RT_STRING, rt.to_string())


class ReplacementManagerTest(unittest.TestCase):
    def test_add_rtab(self):
        path1 = os.path.join(DIR_REPLACE, 'replacements.json')
        path2 = os.path.join(DIR_REPLACE, 'replacements_testadd.json')

        rt1 = replacement_table.ReplacementTable.from_file(path1)
        rt2 = replacement_table.ReplacementTable.from_file(path2)

        # noinspection PyTypeChecker
        rpm = replacement_table.ReplacementManager(None)
        rpm.add_rtab(rt2, 'rt2', True)
        rpm.add_rtab(rt1, 'rt1')

        self.assertEqual(rt2, rpm._rtabs.get('rt2'))
        self.assertEqual(rt1, rpm._rtabs.get('rt1'))
        self.assertEqual(rt2, rpm._mutable_rtab)

        self.assertTrue(rpm.check_compatibility('unittest'))
        self.assertFalse(rpm.check_compatibility('v1'))

    def test_do_replacement(self):
        clear_tmp_folder()
        wd = workdir.Workdir(DIR_TMP)
        dir_apk = wd._get_dir(wd.dir_apk)
        shutil.copyfile(os.path.join(DIR_LANG, 'file1_withgender.xml'), os.path.join(dir_apk, 'file1_withgender.xml'))
        shutil.copyfile(os.path.join(DIR_LANG, 'file2_withgender.xml'), os.path.join(dir_apk, 'file2_withgender.xml'))

        path1 = os.path.join(DIR_REPLACE, 'replacements_testadd.json')
        path2 = os.path.join(DIR_REPLACE, 'replacements_part2.json')

        rt1 = replacement_table.ReplacementTable.from_file(path1)
        rt2 = replacement_table.ReplacementTable.from_file(path2)

        rpm = replacement_table.ReplacementManager(wd)
        rpm.add_rtab(rt1, 'rt1')
        rpm.add_rtab(rt2, 'rt2')

        rpm.do_replace()

        assert_files_equal(self, os.path.join(DIR_LANG, 'file1_nogender.xml'), os.path.join(dir_apk, 'file1_withgender.xml'))
        assert_files_equal(self, os.path.join(DIR_LANG, 'file2_nogender.xml'), os.path.join(dir_apk, 'file2_withgender.xml'))

    def test_write_replacement_table(self):
        clear_tmp_folder()
        wd = workdir.Workdir(DIR_TMP)
        dir_apk = wd._get_dir(wd.dir_apk)
        shutil.copyfile(os.path.join(DIR_LANG, 'file1_withgender.xml'), os.path.join(dir_apk, 'file1_withgender.xml'))
        shutil.copyfile(os.path.join(DIR_LANG, 'file2_withgender.xml'), os.path.join(dir_apk, 'file2_withgender.xml'))

        path = os.path.join(DIR_TMP, 'replacements.json')
        shutil.copyfile(os.path.join(DIR_REPLACE, 'replacements_testadd.json'), path)
        rt = replacement_table.ReplacementTable.from_file(path)

        rpm = replacement_table.ReplacementManager(wd, lambda lf: lf.old+'_MOD')
        rpm.add_rtab(rt, 'rt', True)

        rpm.do_replace()
        rpm.write_replacement_table('newver')

        assert_files_equal(self, os.path.join(DIR_REPLACE, 'replacements_testwrite.json'), path)


if __name__ == '__main__':
    unittest.main()