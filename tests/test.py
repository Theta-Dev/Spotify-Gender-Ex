from spotify_gender_ex.replacement_table import *
from spotify_gender_ex.lang_file import *
from unittest import TestCase
from os import path

TESTFILES = path.join(path.dirname(path.realpath(__file__)), 'testfiles')


class ReplacementFileTest(TestCase):
    def test_from_file(self):
        file = path.join(TESTFILES, 'replacement', 'replacements.json')
        replacements = ReplacementTable.from_file(file)

        self.assertEqual('0.0.1', replacements.version)
        self.assertEqual(["spotify-8-5-89-901"], replacements.spotify_versions)

        file0 = replacements.files[0]
        self.assertEqual('original/8-5-89-901_plurals.xml', file0.path)
        rep0_0 = file0.replace[0]
        self.assertEqual(['home_inline_onboarding_header_title', 'other'], rep0_0.key_list)
        self.assertEqual('Folge %1$d Künstler*innen, um speziell für dich ausgewählte Musik zu erhalten.', rep0_0.old)
        self.assertEqual('Folge %1$d Künstlern, um speziell für dich ausgewählte Musik zu erhalten.', rep0_0.new)

    def test_replacement(self):
        rep = Replacement('test', 'Old', 'New')
        lfd1 = LangField(['tes2'], 'Old')
        lfd2 = LangField(['test'], 'Old2')
        lfd3 = LangField(['test'], 'Old')

        self.assertEqual(ReplacementResult.KEYS_DONT_MATCH, rep.try_replace(lfd1))
        self.assertEqual(ReplacementResult.ORIGINAL_CHANGED, rep.try_replace(lfd2))
        self.assertEqual(ReplacementResult.REPLACED, rep.try_replace(lfd3))

    def test_to_string(self):
        file = path.join(TESTFILES, 'replacement', 'replacements_1.json')
        replacements = ReplacementTable.from_file(file)

        replacements.files[0].add(Replacement('key2', 'Old2', 'New2'))

        expected = '''
{
  "version": "0.0.1",
  "spotify_versions": [
    "spotify-8-5-89-901"
  ],
  "files": [
    {
      "path": "file1",
      "replace": [
        {
          "key": "key1",
          "old": "Old1",
          "new": "New1"
        },
        {
          "key": "key2",
          "old": "Old2",
          "new": "New2"
        }
      ]
    }
  ]
}
        '''
        self.assertEqual(expected.strip(), replacements.to_string().strip())

    def test_do_replace(self):
        file = path.join(TESTFILES, 'replacement', 'replacements.json')
        replacements = ReplacementTable.from_file(file)

        set_plurals = replacements.files[0]
        n_replace, n_original_changed, n_suspicious, new_replacements = set_plurals.do_replace(TESTFILES)

        self.assertEqual(2, n_replace)
        self.assertEqual(0, n_original_changed)
        self.assertEqual(5, n_suspicious)
        self.assertEqual(5, len(new_replacements))

        self.assertEqual('%1$s + %2$d weitere*r', new_replacements[0].old)
        self.assertEqual('%1$s + %2$d weitere*r EDIT', new_replacements[0].new)

    def test_add_replacements(self):
        file = path.join(TESTFILES, 'replacement', 'replacements.json')
        file_out = path.join(TESTFILES, 'output', 'add_replacements.json')

        replacements = ReplacementTable.from_file(file)

        n_replace, n_original_changed, n_suspicious = replacements.do_replace(TESTFILES)
        self.assertEqual(4, n_replace)
        self.assertEqual(0, n_original_changed)
        self.assertEqual(132, n_suspicious)

        replacements.to_file(file_out)

    def test_complete_replace(self):
        # Replace using full replacement table and export the new language file
        file = path.join(TESTFILES, 'replacement', 'replacements_full.json')
        file_out = path.join(TESTFILES, 'output')

        replacements = ReplacementTable.from_file(file)
        replacements.do_replace(TESTFILES)

        replacements.write_files(file_out)


class LanguageFileTest(TestCase):
    def test_from_file(self):
        file = path.join(TESTFILES, 'original', '8-5-89-901_plurals.xml')
        lang_file = LangFile.from_file(file)

        self.assertEqual(168, len(lang_file.fields))
        self.assertEqual(['add_to_playlist_your_episodes_subtitle', 'other'], lang_file.fields[0].key_list)
        self.assertEqual('%1$s Folgen', lang_file.fields[0].old)
        self.assertEqual('%1$s Folgen', lang_file.fields[0].new)
        self.assertEqual(0, lang_file.fields[0].res)

    def test_to_file(self):
        file = path.join(TESTFILES, 'original', '8-5-89-901_plurals.xml')
        outfile = path.join(TESTFILES, 'output', 'lang_to_file.xml')
        lang_file = LangFile.from_file(file)

        # Add a replacement
        lang_file.fields[0].new = 'Hallo'
        lang_file.fields[0].res = 2

        lang_file.to_file(outfile)

        # Read back the file and compare
        lang_file_test = LangFile.from_file(outfile)
        self.assertEqual('Hallo', lang_file_test.fields[0].old)
