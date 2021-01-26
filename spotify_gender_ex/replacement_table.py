import json
from os import path
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
        with open(file) as json_file:
            data = json.load(json_file)
            return cls(**data)

    @classmethod
    def from_string(cls, string):
        data = json.loads(string)
        return cls(**data)

    def to_file(self, file):
        with open(file, 'w') as outfile:
            json.dump(self, outfile, default=lambda o: o.__dict__, indent=2, ensure_ascii=False)

    def to_string(self):
        return json.dumps(self, default=lambda o: o.__dict__, indent=2, ensure_ascii=False)

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


class ReplacementSet:
    """
    A ReplacementSet consists of multiple replacements. It also includes the path
    of the language file it will run the replacements on.
    """

    def __init__(self, path, replace):
        self.path = path
        self.replace = [Replacement(**r) for r in replace]

    def add(self, replacement):
        self.replace.append(replacement)

    def do_replace(self, root_path):
        # Open language file
        lang_file = LangFile.from_file(path.join(root_path, self.path))

        # Apply all replacements
        for r in self.replace:
            # Look for a language field matching the key
            field = lang_file.get_field(r.key_list())
            r.try_replace(field)

        # Verify language file
        n_replace = 0
        n_original_changed = 0
        n_suspicious = 0
        new_replacements = []

        for f in lang_file.fields:
            if f.res == ReplacementResult.REPLACED:
                n_replace += 1
            elif f.res == ReplacementResult.ORIGINAL_CHANGED:
                n_original_changed += 1
                new_replacements.append(Replacement.from_langfield(f, ' EDIT'))
            elif f.is_suspicious():
                n_suspicious += 1
                new_replacements.append(Replacement.from_langfield(f, ' EDIT'))

        self.replace += new_replacements

        return n_replace, n_original_changed, n_suspicious, new_replacements


class Replacement:
    """
    A replacement includes a list of keys to identify the field in the language file.
    It also holds the old value that has to be replaced as well as the new value.
    """

    def __init__(self, key, old: str, new: str):
        self.key = key
        self.old = old
        self.new = new

    @classmethod
    def from_langfield(cls, lang_field: LangField, mark=''):
        return cls('/'.join(lang_field.key_list), lang_field.old, lang_field.old + mark)

    def __repr__(self):
        return self.key + ': ' + self.old + ' -> ' + self.new

    def key_list(self):
        return self.key.split('/')

    def match_key(self, key_list):
        return self.key_list() == key_list

    def try_replace(self, lang_field: LangField):
        """Tries to replace the value in the language file."""

        # Key of Replacement has to match
        if self.key_list() != lang_field.key_list:
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


class ReplacementResult:
    KEYS_DONT_MATCH = 0
    ORIGINAL_CHANGED = 1
    REPLACED = 2
