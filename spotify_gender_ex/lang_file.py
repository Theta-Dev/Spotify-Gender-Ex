# coding=utf-8
import xml.etree.ElementTree as ET
import re


class LangFile:
    def __init__(self, path, fields=None):
        self.path = path
        if fields:
            self.fields = [LangField(**f) for f in fields]
        else:
            self.fields = []

    @classmethod
    def from_file(cls, file):
        lang_file = cls(file)
        
        xmlp = ET.XMLParser(encoding="utf-8")
        tree = ET.parse(file, parser=xmlp)
        lang_file._walk_tree(tree.getroot(), [])

        return lang_file

    def add(self, field):
        self.fields.append(field)

    def _walk_tree(self, tree, key_list):
        for elm in tree:
            if len(elm.attrib) > 0:
                nkl = key_list + [list(elm.attrib.values())[0]]

                if elm.text.strip():
                    self.add(LangField(nkl, elm.text))
                else:
                    self._walk_tree(elm, nkl)

    def to_file(self, file):
        xml = ET.parse(self.path)
        tree = xml.getroot()

        # Apply all replacements
        for field in list(filter(lambda f: f.res == 2, self.fields)):
            elm = self._find_in_tree(tree, field.key_list, [])
            elm.text = field.new

        xml.write(file, xml_declaration=True, encoding='utf-8')

    def _find_in_tree(self, tree, key_to_find, key_list):
        for elm in tree:
            if len(elm.attrib) > 0:
                nkl = key_list + [list(elm.attrib.values())[0]]

                if nkl == key_to_find:
                    return elm
                elif key_to_find[:len(nkl)] == nkl:
                    res = self._find_in_tree(elm, key_to_find, nkl)
                    if res is not None:
                        return res

    def get_field(self, key_list):
        """Get field matching a certain key"""
        fields = list(filter(lambda r: r.key_list == key_list, self.fields))

        if not fields:
            return None
        if len(fields) > 1:
            raise Exception('Mehr als 1 Feld für', '/'.join(key_list), 'gefunden')
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
        return bool(re.search(r'(\*[iIrRnN])|(\([rRnN]\))|([a-zß-ü][IRN])|(:[iIrRnN])', self.new))
