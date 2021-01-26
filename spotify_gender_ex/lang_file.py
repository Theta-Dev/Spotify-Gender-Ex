import xml.etree.ElementTree as ET
import re

class LangFile:
    def __init__(self, fields):
        self.fields = [LangField(**f) for f in fields]

    @classmethod
    def from_file(cls, file):
        lang_file = cls([])

        tree = ET.parse(file)
        lang_file.walk_tree(tree.getroot(), [])

        return lang_file

    def add(self, field):
        self.fields.append(field)

    def walk_tree(self, tree, key_list):
        for elm in tree:
            if len(elm.attrib) == 1:
                nkl = key_list + [list(elm.attrib.values())[0]]

                if elm.text.strip():
                    self.add(LangField(nkl, elm.text))
                else:
                    self.walk_tree(elm, nkl)

    def get_field(self, key_list):
        """Get field matching a certain key"""
        fields = list(filter(lambda r: r.key_list == key_list, self.fields))

        if not fields:
            return None
        if len(fields) > 1:
            print('Warnung: mehr als 1 Feld für', '/'.join(key_list), 'gefunden')
        return fields[0]

    def reset(self):
        """Resets all fields back to their original values"""
        for f in self.fields:
            f.reset()


class LangField:
    def __init__(self, key_list, value):
        self.key_list = key_list
        self.old = value
        self.new = value
        self.res = 0

    def __repr__(self):
        return self.old + ' -> ' + self.new

    def reset(self):
        self.new = self.old
        self.res = 0

    def is_suspicious(self):
        if re.search('spotify:internal', self.new):
            return False
        return bool(re.search('(\*[iIrRnN])|(\([rRnN]\))|([a-zß-ü][IRN])|(:[iIrRnN])', self.new))

