import unittest
from importlib_resources import files

from spotify_gender_ex.replacement_table import ReplacementTable
from spotify_gender_ex.lang_file import is_suspicious


class ReplacementTest(unittest.TestCase):
    def test_replacement_table(self):
        rt_builtin = ReplacementTable.from_file(files('spotify_gender_ex.res').joinpath('replacements.json'))

        for rset in rt_builtin.sets:
            for key, val in rset.replace.items():
                self.assertFalse(is_suspicious(val), 'Suspicious rtab entry in set %s: %s => %s' % (rset.path, key, val))
