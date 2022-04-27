import os
import shutil
import unittest
from unittest import mock
import pytest

import github3
from github3 import GitHub

import tests
from spotify_gender_ex import downloader, appstore, workdir, replacement_table, lang_file, gh_issue

RT_STRING = '''{
  "version": 1,
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
    def test_download_file(self):
        tests.clear_tmp_folder()

        path = os.path.join(tests.DIR_TMP, 'test.md')
        downloader.download_file('https://raw.githubusercontent.com/Theta-Dev/Spotify-Gender-Ex/master/README.md', path, 'README')
        self.assertGreater(os.path.getsize(path), 500)

    def test_download_replacement_table(self):
        rpl_text = downloader.get_replacement_table_raw()
        rtab = replacement_table.ReplacementTable.from_string(rpl_text)

        self.assertTrue(rtab.version > 0)
        self.assertTrue(len(rtab.sets) > 0)
        self.assertTrue(len(rtab.spotify_versions) > 0)


class AppstoreTest(unittest.TestCase):
    # Store sites dont work on GH actions because Cloudflare
    @pytest.mark.skipif(tests.ON_GH_ACTIONS, reason='GH Actions')
    def test_get_spotify_app(self):
        app = appstore.get_spotify_app()
        self.assertEqual(len(app.version.split('.')), 4)
        self.assertTrue(app.download_url.startswith('https://'))

    @pytest.mark.skipif(tests.ON_GH_ACTIONS, reason='GH Actions')
    def test_uptodown(self):
        utd = appstore.Uptodown()
        app = utd.get_spotify_app()
        self.assertEqual(len(app.version.split('.')), 4)
        self.assertTrue(app.download_url.startswith('https://'))

    @pytest.mark.skipif(tests.ON_GH_ACTIONS, reason='GH Actions')
    def test_apkcombo(self):
        utd = appstore.Apkcombo()
        app = utd.get_spotify_app()
        self.assertEqual(len(app.version.split('.')), 4)
        self.assertTrue(app.download_url.startswith('https://'))
    
    def test_compare_versions(self):
        self.assertEqual(0, appstore.compare_versions('8.6.4.971', '8.6.4.971'))
        self.assertEqual(1, appstore.compare_versions('8.6.5.971', '8.6.4.1000'))
        self.assertEqual(-1, appstore.compare_versions('8.6.5.971', '9.6.4.1000'))

    def test_check_app_file(self):
        with self.assertRaises(appstore.StoreException):
            appstore.check_app_file('https://thetadev.de/', {})

        appstore.check_app_file('https://github.com/TeamNewPipe/NewPipe/releases/download/v0.22.2/NewPipe_v0.22.2.apk', {})


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

        # noinspection PyUnusedLocal
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
            'Ich stimme den &lt;a href=\"spotify:internal:signup:tos\"&gt;Nutzungsbedingungen&lt;/a&gt; und der &lt;a href=\"spotify:internal:signup:policy\"&gt;Datenschutzrichtlinie&lt;/a&gt; von Spotify zu.': False,
            'Ich stimme den &lt;a href=\"spotify:internal:signup:tos\"&gt;Nutzungsbedingung:innen&lt;/a&gt; und der &lt;a href=\"spotify:internal:signup:policy\"&gt;Datenschutzrichtlinie&lt;/a&gt; von Spotify zu.': True,
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
        self.assertEqual(1, rt2.version)

        self.assertEqual(["unittest"], rt1.spotify_versions)
        self.assertEqual(["unittest"], rt2.spotify_versions)

        self.assertEqual(['file1_withgender.xml', 'file2_withgender.xml'], list(map(lambda s: s.path, rt1.sets)))
        self.assertEqual(['file1_withgender.xml', 'file2_withgender.xml'], list(map(lambda s: s.path, rt2.sets)))

        self.assertFalse(rt1.is_empty())
        self.assertTrue(rt2.is_empty())

    def test_from_string(self):
        rt = replacement_table.ReplacementTable.from_string(RT_STRING)

        self.assertIsNone(rt.path)
        self.assertEqual(1, rt.version)
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

    def test_count(self):
        path = os.path.join(tests.DIR_REPLACE, 'replacements.json')
        rt = replacement_table.ReplacementTable.from_file(path)

        self.assertEqual(10, rt.n_replacements())
        self.assertEqual(0, rt.n_suspicious())

    def test_count_suspicious(self):
        path = os.path.join(tests.DIR_REPLACE, 'replacements_issue.json')
        rt = replacement_table.ReplacementTable.from_file(path)

        self.assertEqual(6, rt.n_replacements())
        self.assertEqual(6, rt.n_suspicious())


class ReplacementManagerTest(unittest.TestCase):
    def test_add_rtab(self):
        path1 = os.path.join(tests.DIR_REPLACE, 'replacements.json')
        path2 = os.path.join(tests.DIR_REPLACE, 'replacements_testadd.json')
        path3 = os.path.join(tests.DIR_REPLACE, 'replacements_empty.json')

        rt1 = replacement_table.ReplacementTable.from_file(path1)
        rt2 = replacement_table.ReplacementTable.from_file(path2)
        rt3 = replacement_table.ReplacementTable.from_file(path3)

        rpm = replacement_table.ReplacementManager('')
        rpm.add_rtab(rt1, 'a')
        rpm.add_rtab(rt2, 'b')
        rpm.add_rtab(rt3, 'c')

        self.assertEqual(rt1, rpm._rtabs.get('a'))
        self.assertEqual(rt2, rpm._rtabs.get('b'))
        self.assertEqual(rt3, rpm._rtabs.get('c'))

        self.assertTrue(rpm.check_compatibility('unittest'))
        self.assertFalse(rpm.check_compatibility('v1'))

        self.assertEqual('a1b1', rpm.get_rt_versions())
        self.assertEqual('a1 (2416a1dc), b1 (24464164)', rpm.get_rt_versions(True))
        self.assertEqual('', rpm.get_new_repl_string())

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
        rpm.add_rtab(rt, 'rt')

        rpm.do_replace()
        rpm.write_new_replacements('newver', path)

        tests.assert_files_equal(self, os.path.join(tests.DIR_REPLACE, 'replacements_testwrite.json'), path)
        self.assertEqual('9S', rpm.get_new_repl_string())

    def test_version_string(self):
        path1 = os.path.join(tests.DIR_REPLACE, 'replacements.json')
        path2 = os.path.join(tests.DIR_REPLACE, 'replacements_3N2S.json')

        rpm = replacement_table.ReplacementManager('')
        rpm.add_rtab(replacement_table.ReplacementTable.from_file(path1), 'intern (lokal)')
        rpm.new_replacements = replacement_table.ReplacementTable.from_file(path2)

        self.assertEqual('i1', rpm.get_rt_versions())
        self.assertEqual('3N2S', rpm.get_new_repl_string())
        self.assertEqual('i1_3N2S', rpm.get_version_string())


class CreateIssueTest(unittest.TestCase):
    def test_create_issue(self):
        path = os.path.join(tests.DIR_REPLACE, 'replacements_issue.json')
        path_base = os.path.join(tests.DIR_REPLACE, 'replacements_issue_base.json')
        path_nogender = os.path.join(tests.DIR_REPLACE, 'replacements_issue_nogender.json')

        # Mock GitHub library
        gh = GitHub()
        gh.create_issue = mock.Mock()
        github3.login = mock.Mock(return_value=gh)

        # Get replacement table to convert into issue
        rt = replacement_table.ReplacementTable.from_file(path)

        # Create the issue
        self.assertTrue(gh_issue.create_issue(rt, 'newver', 'test_token'))

        # Verify GH library call args
        github3.login.assert_called_once_with(token='test_token')
        gh.create_issue.assert_called_once_with(gh_issue.REPO_OWNER, gh_issue.REPO_NAME,
                                                'Neue Ersetzungsregeln (Spotify newver)', mock.ANY)

        # Verify issue body
        issue_body = gh.create_issue.call_args.args[3]
        nrt = replacement_table.ReplacementTable.from_file(path_base)
        gh_issue.parse_issue(nrt, issue_body, '''
        [BEGIN VALUES]
        Künstler
        Hinweis: Der gemeinsame Mix ist für zwei Personen, also teile deine Einladung direkt mit einem Freund.
        Nur Premiumnutzer
        Künstlerradio\\nbasierend auf
        Künstler
        Künstler
        [END VALUES]
        ''')

        with open(path_nogender, encoding='utf-8') as f:
            exp_json = f.read()

        self.assertEqual(nrt.to_string(), exp_json)


if __name__ == '__main__':
    unittest.main()
