from spotify_gender_ex.replacements import *
from unittest import TestCase
import os


TESTFILES = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'testfiles')

class RepacementFileTest(TestCase):
    def test_from_file(self):
        file = os.path.join(TESTFILES, 'replacement', 'replacements.json')
        replacements = Replacements.from_file(file)

        self.assertEqual('0.0.1', replacements.version)
        self.assertEqual(["spotify-8-5-89-901"], replacements.spotify_versions)

        file0 = replacements.files[0]
        self.assertEqual('res/values-de/plurals.xml', file0.path)
        rep0_0 = file0.replace[0]
        self.assertEqual(['home_inline_onboarding_header_title', 'other'], rep0_0.key_list)
        self.assertEqual('Folge %1$d Künstler*innen, um speziell für dich ausgewählte Musik zu erhalten.', rep0_0.old)
        self.assertEqual('Folge %1$d Künstlern, um speziell für dich ausgewählte Musik zu erhalten.', rep0_0.new)
