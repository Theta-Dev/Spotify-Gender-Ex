import random

import click
from github3 import login, exceptions

from spotify_gender_ex.replacement_table import ReplacementTable

REPO_OWNER = 'Theta-Dev'
REPO_NAME = 'Spotify-Gender-Ex'

PHRASES = [
    'Es wurden neue Gendersternchen entdeckt!',
    'Ein wildes Gendersternchen erscheint!',
    'Und täglich grüßt das Gendersternchen...',
    'Wie es aussieht war Spotify mal wieder linguistisch kreativ unterwegs gewesen.',
    'Grüße gehen raus an alle Sprachkünstler &ast;RÜLPS&ast; INNEN',
]


@click.command()
@click.argument('replacement_table', type=click.Path(True))
@click.option('--token', help='GitHub token', type=click.STRING)
def run(replacement_table, token):
    rtable = ReplacementTable.from_file(replacement_table)

    phrase = random.choice(PHRASES)
    spotify_version = rtable.spotify_versions[-1]
    entries = []
    values = []

    for rset in rtable.sets:
        for replace in rset.replace:
            key, value = replace.split('|', 2)

            entries.append('%s|%s' % (rset.path, key))
            values.append(value)

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

    click.echo(issue_body)

    try:
        gh = login(token=token)
        if gh is None:
            raise click.ClickException('GH login failed')

        gh.create_issue(REPO_OWNER, REPO_NAME, issue_title, issue_body)
    except exceptions.GitHubException as e:
        raise click.ClickException(e)


if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    run()
