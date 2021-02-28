# coding=utf-8
import click
import os
from spotify_gender_ex import genderex


def start_genderex(apk_file='', directory='.', replacement_table='', builtin=False, ks_password='', key_password='',
                   ignore_ssl=False, no_interaction=False, force=False, cleanup_max_files=0, debug=False,
                   no_compile=False, no_logfile=False):
    click.echo('0. INFO')
    if not os.path.isdir(directory):
        click.echo('Keine Eingabedaten')
        return

    gex = genderex.GenderEx(apk_file, directory, replacement_table, builtin, no_interaction, debug, ks_password,
                            key_password, ignore_ssl, no_logfile)

    click.echo('Spotify-Gender-Ex Version: %s' % genderex.VERSION)
    click.echo('Aktuelle Spotify-Version: %s' % gex.latest_spotify)

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

    click.echo('2. DEKOMPILIEREN')
    gex.decompile()
    gex.check_compatibility()

    click.echo('3. DEGENDERIFIZIEREN')
    gex.replace()
    gex.add_credits()

    # This is only for reducing test time
    if no_compile:
        return

    click.echo('4. REKOMPILIEREN')
    gex.recompile()

    click.echo('5. SIGNIEREN')
    gex.sign()

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
@click.option('--nossl', help='SSL-Verifizierung deaktivieren', is_flag=True)
@click.option('--noia', help='Keine Interaktion: Deaktiviert Eingabeaufforderungen (für Automatisierung)', is_flag=True)
@click.option('--force',
              help='(Nur mit --noia) Durchlauf erzwingen, auch wenn die aktuelle Spotify-Version bereits verarbeitet wurde',
              is_flag=True)
@click.option('--cleanup',
              help='Säuberung am Ende: Maximale Anzahl Dateien im Ausgabeordner (die ältesten Versionen werden gelöscht)',
              default=0, type=click.INT)
@click.option('--debug', help='Debug-Informationen in die Logdatei schreiben', is_flag=True)
def run(a, d, rt, builtin, kspw, kypw, nossl, noia, force, cleanup, debug):
    """Entferne die Gendersternchen (z.B. Künstler*innen) aus der Spotify-App für Android!"""
    start_genderex(a, d, rt, builtin, kspw, kypw, nossl, noia, force, cleanup, debug)


if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    run()
