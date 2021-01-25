import json


class Replacements:
    def __init__(self, genderex, files):
        self.version = genderex.get('version')
        self.spotify_versions = genderex.get('spotify_versions')
        self.files = [File(**f) for f in files]

    @classmethod
    def from_file(cls, file):
        with open(file) as json_file:
            data = json.load(json_file)
            return cls(**data)


class File:
    def __init__(self, path, replace):
        self.path = path
        self.replace = [Replacement(**r) for r in replace]


class Replacement:
    def __init__(self, key, old, new):
        self.key_list = key.split('/')
        self.old = old
        self.new = new
