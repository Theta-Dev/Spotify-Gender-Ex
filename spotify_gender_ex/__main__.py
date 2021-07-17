# coding=utf-8
import os

import click

from spotify_gender_ex import __version__, genderex, gh_issue


def start_genderex(apk_file='', directory='.', replacement_table='', builtin=False, no_internal=False,
                   ks_password='', key_password='', no_interaction=False, force=False, no_verify=False, gh_token=''):
    on_gh_actions = bool(os.environ.get('GITHUB_ACTIONS'))

    click.echo('0. INFO')
    if not os.path.isdir(directory):
        click.echo('Keine Eingabedaten')
        return

    gex = genderex.GenderEx(apk_file, directory, replacement_table, builtin, no_internal, no_interaction,
                            ks_password, key_password)

    click.echo('Spotify-Gender-Ex Version: %s' % __version__)
    click.echo('Aktuelle Spotify-Version: %s' % gex.latest_spotify)
    click.echo('Ersetzungstabellen: %s' % gex.rtm.get_rt_versions())

    if on_gh_actions:
        click.echo('GenderEx läuft auf GitHub Actions.')

    # Non-interactive mode is meant for automation.
    # In this case, dont process the same spotify version multiple times
    if gex.is_latest_spotify_processed():
        click.echo('Du hast bereits die aktuellste Spotify-Version degenderifiziert.')
        if no_interaction and not force:
            click.echo('Vielen Dank.')
            return

    gex.wait_for_enter('Drücke Enter zum Starten...')

    click.echo('1. HERUNTERLADEN')
    if not gex.download():
        return

    click.echo('2. VERIFIZIEREN')
    if no_verify:
        click.echo('Übersprungen.')
    else:
        gex.verify()

    click.echo('3. DEKOMPILIEREN')
    gex.decompile()
    gex.check_compatibility()

    click.echo('4. DEGENDERIFIZIEREN')
    gex.replace()
    gex.add_credits()

    click.echo('5. REKOMPILIEREN')
    gex.recompile()

    click.echo('6. SIGNIEREN')
    gex.sign()

    if gh_token and not builtin and not replacement_table and not gex.rtm.new_replacements.is_empty():
        click.echo('7. NEUE ERSETZUNGEN ÜBERMITTELN')

        if gh_issue.create_issue(gex.rtm.new_replacements, gex.spotify_version, gh_token):
            click.echo('GitHub-Issue erstellt')
        else:
            click.echo('GitHub-Issue wurde nicht erstellt. Existiert bereits oder Fehler.')

    click.echo('Degenderifizierung abgeschlossen. Vielen Dank.')
    click.echo('Deine Spotify-App befindet sich hier:')
    click.echo(gex.file_apkout)

    if on_gh_actions:
        gex.set_github_vars()


@click.command()
@click.option('-a',
              help='Spotify-App (APK). Ohne diese Option wird die aktuellste Version von uptodown.com heruntergeladen.',
              default='', type=click.Path())
@click.option('-d', help='GenderEx-Arbeitsverzeichnis. Standard: ./GenderEx', default='.', type=click.Path())
@click.option('-rt', help='Zusätzliche Ersetzungstabellen', type=click.Path(exists=True), multiple=True)
@click.option('--builtin', help='Interne Ersetzungstabelle nicht von GitHub beziehen', is_flag=True)
@click.option('--no-internal', help='Die interne Ersetzungstabelle nicht verwenden (Erfordert -rt).', is_flag=True)
@click.option('--kspw', help='Signer: Passwort für den Keystore.', default='', type=click.STRING)
@click.option('--kypw', help='Signer: Passwort für den Key (genderex).', default='', type=click.STRING)
@click.option('--noia', help='Keine Interaktion: Deaktiviert Eingabeaufforderungen (für Automatisierung)', is_flag=True)
@click.option('--force',
              help='(Nur mit --noia) Durchlauf erzwingen, auch wenn die aktuelle Spotify-Version bereits verarbeitet wurde',
              is_flag=True)
@click.option('--noverify',
              help='Spotify-App-Signatur nicht verifizieren. Nur dann aktivieren, wenn du nicht die Original-Spotify-App verarbeitest.',
              is_flag=True)
@click.option('--gh-token', help='GitHub-Token, um neue Ersetzungsregeln zu übermitteln', default='', type=click.STRING)
def run(a, d, rt, builtin, no_internal, kspw, kypw, noia, force, noverify, gh_token):
    """Entferne die Gendersternchen (z.B. Künstler*innen) aus der Spotify-App für Android!"""
    start_genderex(a, d, rt, builtin, no_internal, kspw, kypw, noia, force, noverify, gh_token)


if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    run()
