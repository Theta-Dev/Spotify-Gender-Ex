# coding=utf-8
import click
import json
import os
from spotify_gender_ex.lang_file import LangFile, LangField
from spotify_gender_ex.workdir import Workdir


class ReplacementManager:
    """
    ReplacementManager holds multiple ReplacementTables
    """

    def __init__(self, workdir: Workdir, get_missing_replacement=None):
        self._rtabs = {}
        self.workdir = workdir
        self.mutable_rtab = None
        self.rtab_modified = False

        if callable(get_missing_replacement):
            self.get_missing_replacement = get_missing_replacement
        else:
            self.get_missing_replacement = lambda lf: lf.old

    def add_rtab(self, rtab, name, is_mutable=False):
        self._rtabs[name] = rtab
        if is_mutable:
            self.mutable_rtab = rtab

    def insert_replacement(self, lfpath, replacement):
        if self.mutable_rtab:
            rset = self.mutable_rtab.set_from_langfile(lfpath)
            if rset:
                rset.add(replacement)
                self.rtab_modified = True

    def check_compatibility(self, spotify_version):
        res = True

        for rtab_name in self._rtabs:
            if not self._rtabs.get(rtab_name).spotify_compatible:
                click.echo('Ersetzungstabelle %s ist nicht mit Spotify %s kompatibel.' % (rtab_name, spotify_version))
                res = False
        return res

    def get_rt_versions(self):
        vstring = ''

        for rtab_name in self._rtabs:
            rtab = self._rtabs.get(rtab_name)
            vstring += rtab_name[0] + str(rtab.version)

        return vstring

    def do_replace(self):
        # Accumulate language files
        lfpaths = set()
        for rtab in self._rtabs.values():
            for s in rtab.sets:
                lfpaths.add(s.realpath)

        # Do the replacements
        n_replaced = 0
        n_newrpl = 0

        # Iterate through all language files
        for lfpath in lfpaths:
            # Get language file
            langfile = LangFile.from_file(os.path.join(self.workdir.dir_apk, lfpath))

            # For each language field in file:
            for langfield in langfile.fields:
                # go through all replacement tables
                replaced = False
                for rtab in self._rtabs.values():
                    rset = rtab.set_from_langfile(lfpath)
                    if not rset:
                        continue

                    if rset.try_replace(langfield):
                        replaced = True
                        n_replaced += 1
                        break

                if not replaced and langfield.is_suspicious():
                    # Create a new replacement and obtain the new value
                    new_replacement = Replacement.from_langfield(langfield)
                    new_replacement.new = str(self.get_missing_replacement(langfield))
                    # Replace using new replacement and add it to the table
                    new_replacement.try_replace(langfield)
                    self.insert_replacement(lfpath, new_replacement)

                    n_replaced += 1
                    n_newrpl += 1

            # Write back modified language file
            langfile.to_file()
        # Write back modified replacement table
        if self.rtab_modified:
            self.mutable_rtab.version += 1
            self.mutable_rtab.to_file()

        return n_replaced, n_newrpl


class ReplacementTable:
    """
    A ReplacementTable contains multiple replacement sets as well as version information
    and a list of compatible Spotify versions.
    """

    def __init__(self, version: int, spotify_versions: list, files: list):
        self.version = version
        self.spotify_versions = spotify_versions
        self.sets = [ReplacementSet(**f) for f in files]
        self.path = None

    @classmethod
    def from_file(cls, file):
        if os.path.isfile(file):
            with open(file, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                rtab = cls(**data)
        else:
            rtab = cls(0, [], [])

        rtab.path = file
        return rtab

    @classmethod
    def from_string(cls, string):
        data = json.loads(string)
        return cls(**data)

    def set_from_langfile(self, realpath):
        try:
            return next(filter(lambda s: s.realpath == realpath, self.sets))
        except StopIteration:
            return None

    def to_file(self, file=None):
        if not file:
            file = self.path

        with open(file, 'w', encoding='utf-8') as outfile:
            json.dump(self, outfile,
                      default=lambda obj: getattr(obj.__class__, "to_json")(obj), indent=2, ensure_ascii=False)

    def to_string(self):
        return json.dumps(self,
                          default=lambda obj: getattr(obj.__class__, "to_json")(obj), indent=2, ensure_ascii=False)

    def spotify_compatible(self, version):
        return version in self.spotify_versions

    def spotify_addversion(self, version):
        if not version in self.spotify_versions:
            self.spotify_versions.append(version)

    def write_files(self, root_path):
        for f in self.sets:
            f.write_file(root_path)

    def to_json(self):
        return {
            'version': self.version,
            'spotify_versions': self.spotify_versions,
            'files': self.sets
        }


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

    def try_replace(self, langfield: LangField):
        for r in self.replace:
            if r.try_replace(langfield):
                return True
        return False

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

    def __init__(self, key, old: str, new: str, inserted: bool = False):
        self.key_list = key.split('/')
        self.old = old
        self.new = new
        self.inserted = inserted

    @classmethod
    def from_langfield(cls, lang_field: LangField):
        return cls('/'.join(lang_field.key_list), lang_field.old, lang_field.old, True)

    def __repr__(self):
        return '/'.join(self.key_list) + ': ' + self.old + ' -> ' + self.new

    def match_key(self, key_list):
        return self.key_list == key_list

    def match(self, langfield: LangField):
        return self.key_list == langfield.key_list and self.old == langfield.old

    def try_replace(self, lang_field: LangField):
        """Tries to replace the value in the language file."""
        if not lang_field.is_replaced():
            # Key of Replacement and old values have to match
            if self.key_list != lang_field.key_list or self.old != lang_field.old:
                return False

            # Replace it
            lang_field.new = self.new
            return True
        return True

    def to_json(self):
        res = {
            'key': '/'.join(self.key_list),
            'old': self.old,
            'new': self.new
        }
        if self.inserted:
            res['inserted'] = True

        return res
