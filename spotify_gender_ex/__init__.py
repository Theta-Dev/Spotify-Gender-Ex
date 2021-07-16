# coding=utf-8
import click
import os
from spotify_gender_ex import genderex, gh_issue


def start_genderex(apk_file='', directory='.', replacement_table='', builtin=False, ks_password='', key_password='',
                   no_interaction=False, force=False, cleanup_max_files=0, debug=False, no_verify=False, gh_token=''):
    click.echo('0. INFO')
    if not os.path.isdir(directory):
        click.echo('Keine Eingabedaten')
        return

    gex = genderex.GenderEx(apk_file, directory, replacement_table, builtin, no_interaction, debug,
                            ks_password, key_password)

    click.echo('Spotify-Gender-Ex Version: %s' % genderex.VERSION)
    click.echo('Aktuelle Spotify-Version: %s' % gex.latest_spotify)
    click.echo('Ersetzungstabellen: %s' % gex.rtm.get_rt_versions())

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

    if gh_token and not gex.rtm.new_replacements.is_empty():
        click.echo('7. NEUE ERSETZUNGEN ÜBERMITTELN')

        if gh_issue.create_issue(gex.rtm.new_replacements, gex.spotify_version, gh_token):
            click.echo('GitHub-Issue erstellt')

    click.echo('Degenderifizierung abgeschlossen. Vielen Dank.')
    click.echo('Deine Spotify-App befindet sich hier:')
    click.echo(gex.file_apkout)

    gex.workdir.cleanup(cleanup_max_files)


@click.command()
@click.option('-a',
              help='Spotify-App (APK). Ohne diese Option wird die aktuellste Version von uptodown.com heruntergeladen.',
              default='', type=click.Path())
@click.option('-d', help='GenderEx-Ordner. Standard: ./GenderEx', default='.', type=click.Path())
@click.option('-rt', help='Spezifizierte Ersetzungstabelle.', type=click.Path(exists=True))
@click.option('--builtin', help='Benutze die eingebaute Ersetzungstabelle', is_flag=True)
@click.option('--kspw', help='Signer: Passwort für den Keystore.', default='', type=click.STRING)
@click.option('--kypw', help='Signer: Passwort für den Key (genderex).', default='', type=click.STRING)
@click.option('--noia', help='Keine Interaktion: Deaktiviert Eingabeaufforderungen (für Automatisierung)', is_flag=True)
@click.option('--force',
              help='(Nur mit --noia) Durchlauf erzwingen, auch wenn die aktuelle Spotify-Version bereits verarbeitet wurde',
              is_flag=True)
@click.option('--cleanup',
              help='Säuberung am Ende: Maximale Anzahl Dateien im Ausgabeordner (die ältesten Versionen werden gelöscht)',
              default=0, type=click.INT)
@click.option('--debug', help='Debug-Informationen in die Logdatei schreiben', is_flag=True)
@click.option('--noverify',
              help='Spotify-App-Signatur nicht verifizieren. Nur dann aktivieren, wenn du nicht die Original-Spotify-App verarbeitest.',
              is_flag=True)
@click.option('--gh-token', help='GitHub-Token, um neue Ersetzungsregeln zu übermitteln', default='', type=click.STRING)
def run(a, d, rt, builtin, kspw, kypw, noia, force, cleanup, debug, noverify, gh_token):
    """Entferne die Gendersternchen (z.B. Künstler*innen) aus der Spotify-App für Android!"""
    start_genderex(a, d, rt, builtin, kspw, kypw, noia, force, cleanup, debug, noverify, gh_token)


if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    run()
