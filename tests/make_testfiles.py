import copy
import os
import random
from xml.etree import ElementTree

import tests
from spotify_gender_ex import replacement_table

"""
This program can be used to generate language files and replacement tables
filled with mock data. Useful for testing.
"""


def fantasy_string(min_len, max_len):
    vovels = 'aeiou'
    consonants = 'bcdfghjklmnoprstvwxyz'

    res = ''

    for i in range(random.randint(min_len, max_len)):
        if random.randint(0, 2) == 0:
            res += random.choice(vovels)
        else:
            res += random.choice(consonants)

    return res


def fantasy_key():
    res = ''

    for i in range(random.randint(2, 4)):
        res += fantasy_string(5, 15)
        res += '_'

    return res[:-1]


def fantasy_word():
    return fantasy_string(6, 12).capitalize()


def make_testfiles(length, gender_ratio, n_tables):
    tables = []
    sets = []

    langdata = {}
    langdata_nogender = {}
    ngender = 0

    for i in range(n_tables):
        table = replacement_table.ReplacementTable(1, ['unittest'], [])
        rset = replacement_table.ReplacementSet('lang.xml', dict())
        table.sets.append(rset)

        tables.append(table)
        sets.append(rset)

    for i in range(length):
        key = fantasy_key()
        word_original = fantasy_word()
        word_replace = word_original

        if random.random() < gender_ratio:
            word_original = word_original + '*innen'
            random.choice(sets).add(key, word_original, word_replace)
            ngender += 1

        langdata[key] = word_original
        langdata_nogender[key] = word_replace

    i = 1
    for table in tables:
        table.to_file(os.path.join(tests.DIR_MAKE, 'replacements_%d.json' % i))
        i += i

    root = ElementTree.Element('resources')
    ElementTree.SubElement(root, 'info', {'n_total': str(length), 'n_gender': str(ngender)})

    root_nogender = copy.deepcopy(root)

    for key in langdata:
        el = ElementTree.SubElement(root, 'string', {'name': key})
        el.text = langdata[key]

    for key in langdata_nogender:
        el = ElementTree.SubElement(root_nogender, 'string', {'name': key})
        el.text = langdata_nogender[key]

    tree = ElementTree.ElementTree(root)
    tree.write(os.path.join(tests.DIR_MAKE, 'lang.xml'), xml_declaration=True, encoding='utf-8')

    tree = ElementTree.ElementTree(root_nogender)
    tree.write(os.path.join(tests.DIR_MAKE, 'lang_nogender.xml'), xml_declaration=True, encoding='utf-8')


if __name__ == '__main__':
    make_testfiles(100000, 0.1, 2)
