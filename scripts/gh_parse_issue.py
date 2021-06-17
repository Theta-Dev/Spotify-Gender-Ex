import json
import os
import re

import click

from spotify_gender_ex.replacement_table import ReplacementTable


def parse_block(input_str, name):
    res = []
    state = False

    for line in input_str.split('\n'):
        line = line.strip()

        if line == '[BEGIN %s]' % name:
            state = True
        elif state and line == '[END %s]' % name:
            break
        elif state and line:
            res.append(line)
    return res


@click.command()
@click.argument('replacement_table', type=click.Path(True))
def run(replacement_table):
    event_json = os.environ.get('GITHUB_EVENT')
    event = json.loads(event_json)

    issue_body = event['issue']['body']
    comment_body = event['comment']['body']

    spotify_version = re.search(r'''SPOTIFY_VERSION *= *(.+)''', issue_body).group(1).strip()
    entries = parse_block(issue_body, 'ENTRIES')
    original_values = parse_block(issue_body, 'VALUES')
    new_values = parse_block(comment_body, 'VALUES')

    if not spotify_version or not entries or not original_values or not new_values:
        raise click.ClickException('Missing input data')

    if len(entries) != len(original_values) or len(entries) != len(new_values):
        raise click.ClickException('Inconsistent input data lengths')

    rtable = ReplacementTable.from_file(replacement_table)
    rtable_original_json = rtable.to_string()

    rtable.spotify_addversion(spotify_version)

    for i in range(len(entries)):
        file, key = entries[i].split('|', 2)
        if not file or not key:
            raise click.ClickException('Invalid entry: ' + entries[i])

        original_val = original_values[i]
        new_val = new_values[i]

        rset = rtable.set_from_langfile(file)
        rset.add(key, original_val, new_val)

    click.echo(rtable.to_string())

    # Add spotify version to GitHub env
    if os.environ.get('CI'):
        os.system('echo "n_replacements=%d" >> $GITHUB_ENV' % len(entries))
        os.system('echo "spotify_version=%s" >> $GITHUB_ENV' % spotify_version)
        click.echo('Set spotify version to %s' % spotify_version)

    if rtable.to_string() == rtable_original_json:
        raise click.ClickException('No changes detected.')

    rtable.version += 1
    rtable.to_file()
    click.echo('Changes written to replacement table')


if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    run()
