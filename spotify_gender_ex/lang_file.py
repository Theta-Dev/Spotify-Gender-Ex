# coding=utf-8
import re
from typing import Callable, List, Optional
from xml.etree import ElementTree

GENDER_REGEX = re.compile(r'''(\*[iIrRnN])|(\([rRnN]\))|([a-zß-ü][IRN])|(:[iIrRnN](?!nternal))''')


class LangFile:
    def __init__(self, path: str):
        """Open language file at the given path and read its contents"""
        self.path = path
        xmlp = ElementTree.XMLParser(encoding="utf-8")
        self.tree = ElementTree.parse(self.path, parser=xmlp)

    def replace_tree(self, fun_repl: Callable):
        """
        Walk through the XML tree of the language file and replace values
        with the given function.

        :param fun_repl: Replace function: fun(key, old_value) -> new_value
        """
        self._walk_tree(self.tree.getroot(), [], fun_repl)

    def _walk_tree(self, tree_node: ElementTree.Element, key_list: List[str], fun_repl: Callable):
        """
        Internal recursive function for walking through the XML tree
        and replacing language values.
        
        :param tree_node: Current tree node
        :param key_list: List of keys to address the current node
        :param fun_repl: Replace function: fun(key, old_value) -> new_value
        """
        for elm in tree_node:
            # All XML tags from the language file have an attribute,
            # either 'name' or 'quantity' (plural file).
            if len(elm.attrib) > 0:
                # The first attribute (there is only one) becomes the key to identify the node
                # This key gets appended to the key_list to form a new key list
                nkl = key_list + [list(elm.attrib.values())[0]]

                # If the current node contains non-whitespace text, we have found a language field
                # Call the replacement function with the key and old value
                if elm.text and elm.text.strip():
                    res = fun_repl('/'.join(nkl), elm.text.strip())
                    if res:
                        elm.text = res
                # Otherwise we need to go deeper
                else:
                    self._walk_tree(elm, nkl, fun_repl)

    def to_file(self, file: Optional[str] = None):
        if not file:
            file = self.path

        self.tree.write(file, xml_declaration=True, encoding='utf-8')


def is_suspicious(string: str) -> bool:
    return bool(GENDER_REGEX.search(string))
