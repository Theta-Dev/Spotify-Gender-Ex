import random
import re
from typing import Tuple, List

import click
import github3
from github3 import exceptions

from spotify_gender_ex.replacement_table import ReplacementTable

REPO_OWNER = 'Theta-Dev'
REPO_NAME = 'Spotify-Gender-Ex'

PHRASES = [
    'Es wurden neue Gendersternchen entdeckt!',
    'Ein wildes Gendersternchen erscheint!',
    'Und täglich grüßt das Gendersternchen...',
    'Wie es aussieht ist Spotify mal wieder linguistisch kreativ unterwegs gewesen.',
    'Grüße gehen raus an alle Sprachkünstler &ast;RÜLPS&ast; INNEN',
]


def _escape_nl(text):
    """Escape newline characters with ``\\n``"""
    return str(text).replace('\n', '\\n')


def _unescape_nl(text):
    """Convert escaped newline characters ``\\n`` back into newlines"""
    return str(text).replace('\\n', '\n')


def create_issue(rtable: ReplacementTable, spotify_version: str, token: str) -> bool:
    """
    Take a replacement table object and write the data into a new GitHub issue.

    :param rtable: ReplacementTable object
    :param spotify_version: Current Spotify version
    :param token: GitHub token
    :return: True if issue created successfully
    """

    phrase = random.choice(PHRASES)
    entries = []
    values = []

    for rset in rtable.sets:
        for replace in rset.replace:
            key, value = replace.split('|', 2)

            entries.append('%s|%s' % (rset.path, key))
            values.append(_escape_nl(value))

    issue_title = 'Neue Ersetzungsregeln (Spotify %s)' % spotify_version

    issue_body = '''\
%s

**Metainformationen:**

```
SPOTIFY_VERSION = %s

[BEGIN ENTRIES]
%s
[END ENTRIES]
```

**Spracheinträge:**

Kopiere diesen Block (MIT dem BEGIN/END-Tag) in deine Antwort, entferne die Gendersternchen und sende die Antwort ab.

```
[BEGIN VALUES]
%s
[END VALUES]
```

Daraufhin wird eine neue PR mit den Änderungen an der Ersetzungstabelle erzeugt.''' % \
                 (phrase, spotify_version, '\n'.join(entries), '\n'.join(values))

    try:
        gh = github3.login(token=token)
        if gh is None:
            click.echo('Could not obtain GH instance')
            return False

        # Dont create an issue if one exists with the same title
        if any(gh.search_issues('repo:%s/%s is:issue is:open in:title %s' % (REPO_OWNER, REPO_NAME, issue_title))):
            return False

        gh.create_issue(REPO_OWNER, REPO_NAME, issue_title, issue_body)

        return True
    except exceptions.GitHubException as e:
        click.echo(e)
        return False


def _parse_block(input_str, name) -> List[str]:
    """
    Parse a block from the GitHub issue/comment body.
    Blocks begin with a ``[BEGIN XYZ]`` tag and end with a ``[END XYZ]`` tag.

    :param input_str: Input text
    :param name: Block name
    :return: List of lines from the block
    """
    res = []
    state = False

    for line in input_str.split('\n'):
        line = _unescape_nl(line.strip())

        if line == '[BEGIN %s]' % name:
            state = True
        elif state and line == '[END %s]' % name:
            break
        elif state and line:
            res.append(line)
    return res


def parse_issue(rtable: ReplacementTable, issue_body: str, comment_body: str) -> Tuple[bool, int, str]:
    """
    Parse issue data from GitHub and add the new replacements to a ReplacementTable object

    :param rtable: Replacement table object where the new entries are added
    :param issue_body: Text of the original issue (contains meta info and language entries)
    :param comment_body: Text of the issue comment (containing replaced language entries)
    :return: has_changed, n_new_entries, spotify_version
    """

    spotify_version = re.search(r'''SPOTIFY_VERSION *= *(.+)''', issue_body).group(1).strip()
    entries = _parse_block(issue_body, 'ENTRIES')
    original_values = _parse_block(issue_body, 'VALUES')
    new_values = _parse_block(comment_body, 'VALUES')

    if not spotify_version or not entries or not original_values or not new_values:
        raise Exception('Missing input data')

    if len(entries) != len(original_values) or len(entries) != len(new_values):
        raise Exception('Inconsistent input data lengths')

    rtable_original_json = rtable.to_string()

    rtable.spotify_addversion(spotify_version)

    for i in range(len(entries)):
        file, key = entries[i].split('|', 2)
        if not file or not key:
            raise Exception('Invalid entry: ' + entries[i])

        original_val = original_values[i]
        new_val = new_values[i]

        rset = rtable.make_set_from_langfile(file)
        rset.add(key, original_val, new_val)

    return rtable_original_json != rtable.to_string(), len(entries), spotify_version
