# coding=utf-8
from xml.etree import ElementTree
import re


class LangFile:
    def __init__(self, path):
        self.path = path
        xmlp = ElementTree.XMLParser(encoding="utf-8")
        self.tree = ElementTree.parse(self.path, parser=xmlp)

    def replace_tree(self, fun_repl):
        self._walk_tree(self.tree.getroot(), [], fun_repl)

    def _walk_tree(self, tree, key_list, fun_repl):
        for elm in tree:
            if len(elm.attrib) > 0:
                nkl = key_list + [list(elm.attrib.values())[0]]

                if elm.text and elm.text.strip():
                    res = fun_repl('/'.join(nkl), elm.text.strip())
                    if res:
                        elm.text = res
                else:
                    self._walk_tree(elm, nkl, fun_repl)

    def to_file(self, file=None):
        if not file:
            file = self.path

        self.tree.write(file, xml_declaration=True, encoding='utf-8')


def is_suspicious(string):
    if re.search('spotify:internal', string):
        return False
    return bool(re.search(r'(\*[iIrRnN])|(\([rRnN]\))|([a-zß-ü][IRN])|(:[iIrRnN])', string))
