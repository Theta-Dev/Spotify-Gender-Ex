# coding=utf-8
import hashlib
import json
import os
from typing import Optional, Tuple, Dict, Callable

import click

from spotify_gender_ex import lang_file


class ReplacementManager:
    """ReplacementManager holds multiple ReplacementTables"""

    def __init__(self, dir_apk: str, get_missing_replacement: Optional[Callable] = None):
        self._rtabs = {}
        self.dir_apk = dir_apk
        self.new_replacements = ReplacementTable.from_scratch()

        # Replacement counters
        self.n_replaced = 0
        self.n_newrpl = 0

        if callable(get_missing_replacement):
            self.get_missing_replacement = get_missing_replacement
        else:
            self.get_missing_replacement = self._missing_replacement_default

    def add_rtab(self, rtab: 'ReplacementTable', name: str):
        """
        Adds a ReplacementTable to the manager.
        Sets the mutable replacement table if specified.
        """
        self._rtabs[name] = rtab

    def get_replacement(self, lfpath: str, key: str, old: str) -> str:
        for rtab in self._rtabs.values():
            rset = rtab.set_from_langfile(lfpath)
            if rset:
                new_string = rset.get_replacement(key, old)
                if new_string:
                    return new_string

    def insert_replacement(self, lfpath: str, key: str, old: str, new: str):
        """Inserts a new replacement into the mutable replacement table"""
        rset = self.new_replacements.make_set_from_langfile(lfpath)
        rset.add(key, old, new)

    def check_compatibility(self, spotify_version: str) -> bool:
        """
        Returns True if all loaded replacement tables are compatible to the Spotify version.
        Outputs incompatibility messages via the console, too.
        """
        res = True

        for rtab_name, rtab in self._rtabs.items():
            if not rtab.spotify_compatible(spotify_version):
                msg = 'Ersetzungstabelle %s ist nicht mit Spotify %s kompatibel.' % (rtab_name, spotify_version)
                click.echo(msg)
                res = False
        return res

    def get_rt_versions(self, verbose=False) -> str:
        """Gets a version string of all replacement tables (e.g. b3c0)"""
        vstring = ''

        for rtab_name in self._rtabs:
            rtab = self._rtabs.get(rtab_name)
            if not rtab.is_empty():
                vstring += rtab_name[0] + str(rtab.version)

                if verbose:
                    vstring += ' (%s), ' % rtab.md5_hash()[:8]

        return vstring.rstrip(', ')

    def get_new_repl_string(self) -> str:
        """Gets a string with the number of new/suspicious replacement items"""
        count = self.new_replacements.n_replacements()
        sus = self.new_replacements.n_suspicious()
        new = count - sus
        res = ''

        if new > 0:
            res += '%dN' % new
        if sus > 0:
            res += '%dS' % sus

        return res

    def get_version_string(self) -> str:
        res = self.get_rt_versions()
        repl = self.get_new_repl_string()

        if repl:
            res += '_' + repl
        return res

    @staticmethod
    def _missing_replacement_default(key: str, old: str) -> str:
        click.echo('Verdächtig: %s' % old)
        return old

    def do_replace(self, dir_out=None) -> Tuple[int, int]:
        """
        Iterates through all language files.
        For each language field in every file, it tries to find a replacement.
        If the field could not be replaced and seems suspicious (gender*),
        it will call the get_missing_replacement(langfield) function and creates a new
        replacement with the return value (used for prompting).

        The new replacements can be written back into the replacement table
        using write_replacement_table(spotify_version).

        Returns a tuple: (Number of replaced fields, Number of new replacements)
        """

        self.n_replaced = 0
        self.n_newrpl = 0

        # Accumulate language files
        lfpaths = set()
        for rtab in self._rtabs.values():
            for s in rtab.sets:
                lfpaths.add(s.path)

        # Iterate through all language files
        for lfpath in lfpaths:
            # Get language file
            langfile = lang_file.LangFile(os.path.join(self.dir_apk, ReplacementSet.get_realpath(lfpath)))

            def fun_replace(key: str, old: str) -> str:
                new_string = self.get_replacement(lfpath, key, old)
                if new_string:
                    self.n_replaced += 1
                    return new_string

                if lang_file.is_suspicious(old):
                    # Create a new replacement and obtain the new value
                    new_string = str(self.get_missing_replacement(key, old))

                    # Replace using new replacement and add it to the table
                    self.insert_replacement(lfpath, key, old, new_string)

                    self.n_replaced += 1
                    self.n_newrpl += 1
                    return new_string

            # Do the replacement
            langfile.replace_tree(fun_replace)

            # Write back modified language file
            target_file = None
            if dir_out:
                target_file = os.path.join(dir_out, os.path.basename(ReplacementSet.get_realpath(lfpath)))

            langfile.to_file(target_file)

        return self.n_replaced, self.n_newrpl

    def write_new_replacements(self, spotify_version: str, file: str) -> bool:
        """Write back new replacements if there are any"""
        if not self.new_replacements.is_empty():
            self.new_replacements.spotify_addversion(spotify_version)
            self.new_replacements.to_file(file)
            return True
        return False


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
    def from_file(cls, file: str) -> 'ReplacementTable':
        if os.path.isfile(file):
            with open(file, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                rtab = cls(**data)
        else:
            rtab = cls.from_scratch()

        rtab.path = file
        return rtab

    @classmethod
    def from_string(cls, string: str) -> 'ReplacementTable':
        data = json.loads(string)
        return cls(**data)

    @classmethod
    def from_scratch(cls) -> 'ReplacementTable':
        return cls(1, [], [])

    def set_from_langfile(self, path: str) -> Optional['ReplacementSet']:
        """Returns ReplacemenSet that matches the (os-agnostic) path of the language file."""
        try:
            return next(filter(lambda s: s.path == path, self.sets))
        except StopIteration:
            return None

    def make_set_from_langfile(self, path: str) -> 'ReplacementSet':
        """
        Returns ReplacemenSet that matches the (os-agnostic) path of the language file
        or creates one if it doesn't exist.
        """
        rset = self.set_from_langfile(path)
        if not rset:
            rset = ReplacementSet(path, dict())
            self.sets.append(rset)
            self.sets.sort(key=lambda s: s.path)
        return rset

    def to_file(self, file: str = None):
        if not file:
            file = self.path

        with open(file, 'w', encoding='utf-8') as outfile:
            json.dump(self, outfile,
                      default=lambda obj: getattr(obj.__class__, "to_json")(obj), indent=2, ensure_ascii=False)

    def to_string(self) -> str:
        return json.dumps(self,
                          default=lambda obj: getattr(obj.__class__, "to_json")(obj), indent=2, ensure_ascii=False)

    def spotify_compatible(self, version: str) -> bool:
        return version in self.spotify_versions or self.is_empty()

    def spotify_addversion(self, version: str):
        if version not in self.spotify_versions:
            self.spotify_versions.append(version)

    def is_empty(self) -> bool:
        for rset in self.sets:
            if not rset.is_empty():
                return False
        return True

    def n_replacements(self) -> int:
        n = 0

        for rset in self.sets:
            n += rset.n_replacements()
        return n

    def n_suspicious(self) -> int:
        n = 0

        for rset in self.sets:
            n += rset.n_suspicious()
        return n

    def md5_hash(self) -> str:
        return hashlib.md5(self.to_string().encode('utf-8')).hexdigest()

    def to_json(self) -> dict:
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

    def __init__(self, path: str, replace: Dict[str, str]):
        self.path = path
        self.realpath = self.get_realpath(path)
        self.replace = replace

    @staticmethod
    def get_realpath(path: str) -> str:
        return os.path.join(*path.split('/'))

    @staticmethod
    def _get_key(key: str, old: str) -> str:
        return key + '|' + old

    def add(self, key: str, old: str, new: str):
        self.replace[self._get_key(key, old)] = new

    def get_replacement(self, key: str, old: str) -> str:
        return self.replace.get(self._get_key(key, old))

    def is_empty(self) -> bool:
        return not bool(self.replace)

    def n_replacements(self) -> int:
        return len(self.replace.items())

    def n_suspicious(self) -> int:
        n = 0

        for _, val in self.replace.items():
            if lang_file.is_suspicious(val):
                n += 1
        return n

    def to_json(self) -> dict:
        return {'path': self.path, 'replace': self.replace}
