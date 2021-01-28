# coding=utf-8
import json
import os
from .lang_file import LangFile, LangField


class ReplacementTable:
    """
    A ReplacementTable contains multiple replacement sets as well as version information
    and a list of compatible Spotify versions.
    """

    def __init__(self, version, spotify_versions, files):
        self.version = version
        self.spotify_versions = spotify_versions
        self.files = [ReplacementSet(**f) for f in files]

    @classmethod
    def from_file(cls, file):
        with open(file, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
            return cls(**data)

    @classmethod
    def from_string(cls, string):
        data = json.loads(string)
        return cls(**data)

    def to_file(self, file):
        with open(file, 'w', encoding='utf-8') as outfile:
            json.dump(self, outfile,
                      default=lambda obj: getattr(obj.__class__, "to_json")(obj), indent=2, ensure_ascii=False)

    def to_string(self):
        return json.dumps(self,
                          default=lambda obj: getattr(obj.__class__, "to_json")(obj), indent=2, ensure_ascii=False)

    def spotify_compatible(self, version):
        return version in self.spotify_versions

    def do_replace(self, root_path):
        n_replace = 0
        n_original_changed = 0
        n_suspicious = 0

        for s in self.files:
            nr, no, ns, __ = s.do_replace(root_path)
            n_replace += nr
            n_original_changed += no
            n_suspicious += ns

        return n_replace, n_original_changed, n_suspicious

    def write_files(self, root_path):
        for f in self.files:
            f.write_file(root_path)

    def to_json(self):
        return self.__dict__


class ReplacementSet:
    """
    A ReplacementSet consists of multiple replacements. It also includes the path
    of the language file it will run the replacements on.
    """

    def __init__(self, path, replace):
        self.path = path
        self.realpath = os.path.join(*path.split('/'))

        self.replace = [Replacement(**r) for r in replace]
        self.lang_file = None

    def add(self, replacement):
        self.replace.append(replacement)

    def do_replace(self, root_path):
        # Open language file
        self.lang_file = LangFile.from_file(os.path.join(root_path, self.realpath))

        # Apply all replacements
        for r in self.replace:
            # Look for a language field matching the key
            field = self.lang_file.get_field(r.key_list)
            if field:
                r.try_replace(field)

        # Verify language file
        n_replace = 0
        n_original_changed = 0
        n_suspicious = 0
        new_replacements = []

        for f in self.lang_file.fields:
            if f.res == ReplacementResult.REPLACED:
                n_replace += 1
            elif f.is_suspicious():
                if f.res == ReplacementResult.ORIGINAL_CHANGED:
                    n_original_changed += 1
                    new_replacements.append(Replacement.from_langfield(f, ' EDIT'))
                else:
                    n_suspicious += 1
                    new_replacements.append(Replacement.from_langfield(f, ' EDIT'))

        self.replace += new_replacements

        return n_replace, n_original_changed, n_suspicious, new_replacements

    def write_file(self, base_path):
        file = os.path.join(base_path, self.realpath)
        self.lang_file.to_file(file)

    def to_json(self):
        return {'path': self.path, 'replace': self.replace}


class Replacement:
    """
    A replacement includes a list of keys to identify the field in the language file.
    It also holds the old value that has to be replaced as well as the new value.
    """

    def __init__(self, key, old: str, new: str):
        self.key_list = key.split('/')
        self.old = old
        self.new = new

    @classmethod
    def from_langfield(cls, lang_field: LangField, mark=''):
        return cls('/'.join(lang_field.key_list), lang_field.old, lang_field.old + mark)

    def __repr__(self):
        return '/'.join(self.key_list) + ': ' + self.old + ' -> ' + self.new

    def match_key(self, key_list):
        return self.key_list == key_list

    def try_replace(self, lang_field: LangField):
        """Tries to replace the value in the language file."""

        # Key of Replacement has to match
        if self.key_list != lang_field.key_list:
            res = ReplacementResult.KEYS_DONT_MATCH

        # If the original value in the language file has changed, dont replace
        elif self.old != lang_field.old:
            res = ReplacementResult.ORIGINAL_CHANGED

        # Replace it
        else:
            lang_field.new = self.new
            res = ReplacementResult.REPLACED

        lang_field.res = max(lang_field.res, res)
        return res

    def to_json(self):
        return {
            'key': '/'.join(self.key_list),
            'old': self.old,
            'new': self.new
        }


class ReplacementResult:
    KEYS_DONT_MATCH = 0
    ORIGINAL_CHANGED = 1
    REPLACED = 2
