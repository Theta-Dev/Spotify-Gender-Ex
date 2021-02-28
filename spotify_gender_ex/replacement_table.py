# coding=utf-8
import click
import json
import os
import logging
from spotify_gender_ex import lang_file


class ReplacementManager:
    """ReplacementManager holds multiple ReplacementTables"""

    def __init__(self, dir_apk, get_missing_replacement=None):
        self._rtabs = {}
        self.dir_apk = dir_apk
        self._mutable_rtab = None
        self.rtab_modified = False

        # Replacement counters
        self.n_replaced = 0
        self.n_newrpl = 0

        if callable(get_missing_replacement):
            self.get_missing_replacement = get_missing_replacement
        else:
            self.get_missing_replacement = self._missing_replacement_default

    def add_rtab(self, rtab, name, is_mutable=False):
        """
        Adds a ReplacementTable to the manager.
        Sets the mutable replacement table if specified.
        """
        self._rtabs[name] = rtab
        if is_mutable:
            self._mutable_rtab = rtab

    def get_replacement(self, lfpath, key, old):
        for rtab in self._rtabs.values():
            rset = rtab.set_from_langfile(lfpath)
            if rset:
                new_string = rset.get_replacement(key, old)
                if new_string:
                    return new_string

    def insert_replacement(self, lfpath, key, old, new):
        """Inserts a new replacement into the mutable replacement table"""
        if self._mutable_rtab:
            rset = self._mutable_rtab.make_set_from_langfile(lfpath)
            rset.add(key, old, new)

            self.rtab_modified = True

    def check_compatibility(self, spotify_version):
        """
        Returns True if all loaded replacement tables are compatible to the Spotify version.
        Outputs incompatibility messages via the console, too.
        """
        res = True

        for rtab_name in self._rtabs:
            if not self._rtabs.get(rtab_name).spotify_compatible(spotify_version):
                msg = 'Ersetzungstabelle %s ist nicht mit Spotify %s kompatibel.' % (rtab_name, spotify_version)
                click.echo(msg)
                logging.info(msg)
                res = False
        return res

    def get_rt_versions(self):
        """Gets a version string of all replacement tables (e.g. b3c0)"""
        vstring = ''

        for rtab_name in self._rtabs:
            rtab = self._rtabs.get(rtab_name)
            if not rtab.is_empty():
                vstring += rtab_name[0] + str(rtab.version)

        return vstring

    @staticmethod
    def _missing_replacement_default(key, old):
        logging.info('Diese Zeile zu deiner Ersetzungstabelle hinzufügen und anpassen.')
        logging.info('"%s|%s": "%s"' % (key, old, old))
        return old

    def do_replace(self, dir_out=None):
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

            def fun_replace(key, old):
                new_string = self.get_replacement(lfpath, key, old)
                if new_string:
                    self.n_replaced += 1
                    return new_string

                if lang_file.is_suspicious(old):
                    logging.info('Verdächtig: ' + old)

                    # Create a new replacement and obtain the new value
                    new_string = str(self.get_missing_replacement(key, old))
                    logging.info('Neue Ersetzungsregel: ' + new_string)

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

        logging.info('%d Ersetzungen vorgenommen' % self.n_replaced)
        logging.info('%d neue Ersetungsregeln' % self.n_newrpl)
        return self.n_replaced, self.n_newrpl

    def write_replacement_table(self, spotify_version=''):
        """If modified, write back replacement table"""
        if self.rtab_modified:
            self._mutable_rtab.version += 1
            if spotify_version:
                self._mutable_rtab.spotify_addversion(spotify_version)
            self._mutable_rtab.to_file()

            logging.info('Benutzerdefinierte Ersetzungstabelle gespeichert')


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

        # Check for deprecated replacement sets
        for rset in rtab.sets:
            if rset.deprecated:
                logging.warning('Format of replacement table %s is deprecated. Converting.' % file)
                rtab.to_file()

        return rtab

    @classmethod
    def from_string(cls, string):
        data = json.loads(string)
        return cls(**data)

    def set_from_langfile(self, path):
        """Returns ReplacemenSet that matches the (os-agnostic) path of the language file."""
        try:
            return next(filter(lambda s: s.path == path, self.sets))
        except StopIteration:
            return None

    def make_set_from_langfile(self, path):
        """
        Returns ReplacemenSet that matches the (os-agnostic) path of the language file
        or creates one if it doesn't exist.
        """
        rset = self.set_from_langfile(path)
        if not rset:
            rset = ReplacementSet(path, [])
            self.sets.append(rset)
        return rset

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
        return version in self.spotify_versions or self.is_empty()

    def spotify_addversion(self, version):
        if version not in self.spotify_versions:
            self.spotify_versions.append(version)

    def is_empty(self):
        for rset in self.sets:
            if not rset.is_empty():
                return False
        return True

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
        self.realpath = self.get_realpath(path)
        self.deprecated = False

        if isinstance(replace, dict):
            self.replace = replace
        else:
            # Backwards-compatibility for lists
            self.deprecated = True
            self.replace = {}
            for item in replace:
                self.replace[self._get_key(item.get('key'), item.get('old'))] = item.get('new')

    @staticmethod
    def get_realpath(path):
        return os.path.join(*path.split('/'))

    @staticmethod
    def _get_key(key, old):
        return key + '|' + old

    def add(self, key, old, new):
        self.replace[self._get_key(key, old)] = new

    def get_replacement(self, key, old):
        return self.replace.get(self._get_key(key, old))

    def is_empty(self):
        return not bool(self.replace)

    def to_json(self):
        return {'path': self.path, 'replace': self.replace}
