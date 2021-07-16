import json
import os

import click

from spotify_gender_ex import gh_issue
from spotify_gender_ex.replacement_table import ReplacementTable


@click.command()
@click.argument('replacement_table', type=click.Path(True))
def run(replacement_table):
    event_json = os.environ.get('GITHUB_EVENT')
    event = json.loads(event_json)

    issue_body = event['issue']['body']
    comment_body = event['comment']['body']
    rtable = ReplacementTable.from_file(replacement_table)

    try:
        has_changed, n_entries, spotify_version = gh_issue.parse_issue(rtable, issue_body, comment_body)
    except Exception as e:
        raise click.ClickException(str(e))

    click.echo(rtable.to_string())

    # Add spotify version to GitHub env
    if os.environ.get('CI'):
        os.system('echo "n_replacements=%d" >> $GITHUB_ENV' % n_entries)
        os.system('echo "spotify_version=%s" >> $GITHUB_ENV' % spotify_version)
        click.echo('Set spotify version to %s' % spotify_version)

    if not has_changed:
        raise click.ClickException('No changes detected.')

    # If there were changes, increase RT version and write to file
    rtable.version += 1
    rtable.to_file()
    click.echo('Changes written to replacement table')


if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    run()
