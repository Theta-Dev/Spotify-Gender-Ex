import unittest
import os
import shutil
import tests
from spotify_gender_ex import downloader, workdir, replacement_table, lang_file

RT_STRING = '''{
  "version": 0,
  "spotify_versions": [
    "unittest"
  ],
  "files": [
    {
      "path": "file1_withgender.xml",
      "replace": {}
    },
    {
      "path": "file2_withgender.xml",
      "replace": {}
    }
  ]
}'''


class DownloaderTest(unittest.TestCase):
    def test_spotify_version(self):
        dldr = downloader.Downloader()
        self.assertRegex(dldr.spotify_version, r'\d+.\d+.\d+.\d+')
        self.assertTrue(dldr.spotify_url.startswith('https://play.googleapis.com/download/by-token/download?token='))

    @unittest.skipUnless(tests.TEST_DOWNLOAD, 'download skipped')
    def test_download_spotify(self):
        tests.clear_tmp_folder()

        dldr = downloader.Downloader()
        path = os.path.join(tests.DIR_TMP, 'spotify.apk')
        dldr.download_spotify(path)
        self.assertGreater(os.path.getsize(path), 20000000)

    def test_download_replacement_table(self):
        dldr = downloader.Downloader()
        rpl_text = dldr.get_replacement_table_raw()
        rtab = replacement_table.ReplacementTable.from_string(rpl_text)

        self.assertTrue(rtab.version > 0)
        self.assertTrue(len(rtab.sets) > 0)
        self.assertTrue(len(rtab.spotify_versions) > 0)


class WorkdirTest(unittest.TestCase):
    def test_workdir_creation(self):
        tests.clear_tmp_folder()
        workdir.Workdir(tests.DIR_TMP)
        dir_root = os.path.join(tests.DIR_TMP, 'GenderEx')

        self.assertTrue(os.path.isfile(
            os.path.join(dir_root, 'genderex.keystore')))
        self.assertTrue(os.path.isdir(os.path.join(dir_root, 'tmp')))
        self.assertTrue(os.path.isdir(os.path.join(dir_root, 'output')))


class LangFileTest(unittest.TestCase):
    def test_from_file(self):
        self._test_from_file('file1_withgender.xml', 20)
        self._test_from_file('file2_withgender.xml', 4)

    def _test_from_file(self, file, ass_len):
        path = os.path.join(tests.DIR_LANG, file)
        lfile = lang_file.LangFile(path)

        self.assertEqual(ass_len, len(lfile.tree.findall('*')))
        self.assertEqual(path, lfile.path)

    def test_to_file(self):
        self._test_to_file('file1_withgender.xml')
        self._test_to_file('file2_withgender.xml')

    def _test_to_file(self, file):
        tests.clear_tmp_folder()
        path = os.path.join(tests.DIR_LANG, file)
        path_out = os.path.join(tests.DIR_TMP, 'lang.xml')

        lfile = lang_file.LangFile(path)
        lfile.to_file(path_out)

        tests.assert_files_equal(self, path, path_out)

    def test_modify_file(self):
        self._test_modify_file('file1_withgender.xml', 'file1_mod.xml', 'Laglog')
        self._test_modify_file('file2_withgender.xml', 'file2_mod.xml', 'Urelex_Yeable/other')

    def _test_modify_file(self, file, file_mod, rkey):
        tests.clear_tmp_folder()
        path = os.path.join(tests.DIR_LANG, file)
        path_mod = os.path.join(tests.DIR_LANG, file_mod)
        path_out = os.path.join(tests.DIR_TMP, 'lang.xml')

        lfile = lang_file.LangFile(path)

        def fun_replace(key, old):
            if key == rkey:
                return 'MODIFIED'

        lfile.replace_tree(fun_replace)

        lfile.to_file(path_out)
        tests.assert_files_equal(self, path_mod, path_out)

    def test_is_suspicious(self):
        test_data = {
            'Hallo Welt!': False,
            'Künstler*innen': True,
            'Weitere Optionen': False,
            'Hinweis: Der gemeinsame Mix ist für zwei Personen, also teile deine Einladung direkt mit einem*einer Freund*in.': True,
            '„%1$s“ in Künstler*innen': True,
            'Tippe auf einer Folge auf {download}, um sie dir ohne Internetverbindung anzuhören.': False,
            'Ich stimme den &lt;a href=\"spotify:internal:signup:tos\"&gt;Nutzungsbedingungen&lt;/a&gt; und der &lt;a href=\"spotify:internal:signup:policy\"&gt;Datenschutzrichtlinie&lt;/a&gt; von Spotify zu.': False
        }

        for item in test_data.items():
            self.assertEqual(item[1], lang_file.is_suspicious(item[0]))


class ReplacementTableTest(unittest.TestCase):
    def test_from_file(self):
        path1 = os.path.join(tests.DIR_REPLACE, 'replacements.json')
        path2 = os.path.join(tests.DIR_REPLACE, 'replacements_empty.json')

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

        self.assertFalse(rt1.is_empty())
        self.assertTrue(rt2.is_empty())

    def test_from_string(self):
        rt = replacement_table.ReplacementTable.from_string(RT_STRING)

        self.assertIsNone(rt.path)
        self.assertEqual(0, rt.version)
        self.assertEqual(["unittest"], rt.spotify_versions)
        self.assertEqual(['file1_withgender.xml', 'file2_withgender.xml'], list(map(lambda s: s.path, rt.sets)))

    def test_set_from_langfile(self):
        path = os.path.join(tests.DIR_REPLACE, 'replacements_empty.json')
        rt = replacement_table.ReplacementTable.from_file(path)

        rset = rt.set_from_langfile('file1_withgender.xml')
        self.assertEqual('file1_withgender.xml', rset.path)

        rset = rt.set_from_langfile('missingno.xml')
        self.assertIsNone(rset)

        rset = rt.make_set_from_langfile('missingno.xml')
        self.assertEqual('missingno.xml', rset.path)

    def test_add_to_file(self):
        tests.clear_tmp_folder()

        path = os.path.join(tests.DIR_REPLACE, 'replacements_empty.json')
        path_out = os.path.join(tests.DIR_TMP, 'replacements.json')
        path_ass = os.path.join(tests.DIR_REPLACE, 'replacements_testadd.json')

        rt = replacement_table.ReplacementTable.from_file(path)

        rt.set_from_langfile('file1_withgender.xml').add('Biblec', 'Künstler*innen', 'Künstler')

        rt.to_file(path_out)
        tests.assert_files_equal(self, path_ass, path_out)

    def test_to_string(self):
        path = os.path.join(tests.DIR_REPLACE, 'replacements_empty.json')
        rt = replacement_table.ReplacementTable.from_file(path)

        self.assertEqual(RT_STRING, rt.to_string())


class ReplacementManagerTest(unittest.TestCase):
    def test_add_rtab(self):
        path1 = os.path.join(tests.DIR_REPLACE, 'replacements.json')
        path2 = os.path.join(tests.DIR_REPLACE, 'replacements_testadd.json')
        path3 = os.path.join(tests.DIR_REPLACE, 'replacements_empty.json')

        rt1 = replacement_table.ReplacementTable.from_file(path1)
        rt2 = replacement_table.ReplacementTable.from_file(path2)
        rt3 = replacement_table.ReplacementTable.from_file(path3)

        # noinspection PyTypeChecker
        rpm = replacement_table.ReplacementManager(None)
        rpm.add_rtab(rt2, 'b', True)
        rpm.add_rtab(rt1, 'a')
        rpm.add_rtab(rt3, 'c')

        self.assertEqual(rt2, rpm._rtabs.get('b'))
        self.assertEqual(rt1, rpm._rtabs.get('a'))
        self.assertEqual(rt2, rpm._mutable_rtab)

        self.assertTrue(rpm.check_compatibility('unittest'))
        self.assertFalse(rpm.check_compatibility('v1'))

        self.assertEqual('b0a1', rpm.get_rt_versions())

    def test_do_replacement(self):
        tests.clear_tmp_folder()

        shutil.copyfile(os.path.join(tests.DIR_LANG, 'file1_withgender.xml'),
                        os.path.join(tests.DIR_TMP, 'file1_withgender.xml'))
        shutil.copyfile(os.path.join(tests.DIR_LANG, 'file2_withgender.xml'),
                        os.path.join(tests.DIR_TMP, 'file2_withgender.xml'))

        path1 = os.path.join(tests.DIR_REPLACE, 'replacements_testadd.json')
        path2 = os.path.join(tests.DIR_REPLACE, 'replacements_part2.json')

        rt1 = replacement_table.ReplacementTable.from_file(path1)
        rt2 = replacement_table.ReplacementTable.from_file(path2)

        rpm = replacement_table.ReplacementManager(tests.DIR_TMP)
        rpm.add_rtab(rt1, 'rt1')
        rpm.add_rtab(rt2, 'rt2')

        rpm.do_replace()

        tests.assert_files_equal(self, os.path.join(tests.DIR_LANG, 'file1_nogender.xml'),
                                 os.path.join(tests.DIR_TMP, 'file1_withgender.xml'))
        tests.assert_files_equal(self, os.path.join(tests.DIR_LANG, 'file2_nogender.xml'),
                                 os.path.join(tests.DIR_TMP, 'file2_withgender.xml'))

    def test_write_replacement_table(self):
        tests.clear_tmp_folder()
        wd = workdir.Workdir(tests.DIR_TMP)
        dir_apk = wd._get_dir(wd.dir_apk)
        shutil.copyfile(os.path.join(tests.DIR_LANG, 'file1_withgender.xml'),
                        os.path.join(dir_apk, 'file1_withgender.xml'))
        shutil.copyfile(os.path.join(tests.DIR_LANG, 'file2_withgender.xml'),
                        os.path.join(dir_apk, 'file2_withgender.xml'))

        path = os.path.join(tests.DIR_TMP, 'replacements.json')
        shutil.copyfile(os.path.join(tests.DIR_REPLACE, 'replacements_testadd.json'), path)
        rt = replacement_table.ReplacementTable.from_file(path)

        rpm = replacement_table.ReplacementManager(dir_apk, lambda key, old: old + '_MOD')
        rpm.add_rtab(rt, 'rt', True)

        rpm.do_replace()
        rpm.write_replacement_table('newver')

        tests.assert_files_equal(self, os.path.join(tests.DIR_REPLACE, 'replacements_testwrite.json'), path)


if __name__ == '__main__':
    unittest.main()
