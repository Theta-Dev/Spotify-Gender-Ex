Dies eine Sammlung von Notizen, die ich für die Entwicklung von GenderEx V1.0.0 verwendet habe.
Für die fertige Dokumentation siehe README.

# Ordnerstruktur

```text
|_ GenderEx
  |_ genderex.keystore (Keystore)
  |_ hook.py (eventuell)
  |_ replacements.json (zusätzliche Ersetzungstabelle)
  |_ replacements_updated.json (zusammengeführte Ersetzungstabelle)
  |_ tmp (wird vor jeder Ausführung gelöscht)
  | |_ app.apk
  | |_ app
  |   |_ ... dekompilierte Dateien
  |_ output
    |_ spotify-8-6-0-830-genderex-1.apk
    |_ ...
```

# Ablauf

1. Aufruf des Befehls `spotify-gender-ex`
2. Suche nach GenderEx-Ordner, erstelle ihn wenn er nicht existiert (Konfigurationsdatei, Keystore, tmp-Ordner)
3. Aktuelle Spotify-Version abrufen und überprüfen
4. Spotify-APK nach `tmp/app.apk` herunterladen
5. Aktuelle Ersetzungstabelle herunterladen
6. Spotify nach `tmp/app/` dekompilieren
7. Ersetzungen durchführen:

   Für jedes Feld in der Sprachdatei: Suche 1. in `replacements.json` und 2. in der heruntergeladenen Ersetzungstabelle.

   Wurde keine Ersetzung gefunden, prüfe, ob Gendersternchen im Feld enthalten sind. Ist das der Fall, fordere den
   Nutzer auf, das Feld manuell anzupassen.

   Die manuell angepassten Ersetzungen werden in die `replacements.json` geschrieben. In `replacements_updated.json`
   sollte die Zusammenführung aus den beiden Ersetzungstabellen geschrieben werden (zur einfacheren Aktualisierung der
   eingebauten Ersetzungstabelle).

8. Spotify nach `tmp/xxx.apk` rekompilieren, signieren und die fertige apk in den `output`-Ordner kopieren.

   Dateinamenformat: `spotify-x-x-x-xxx-genderex-[RT-Version].apk`

# Ersetzungstabelle

GenderEx-Ersetzungstabellen sind im json-Format und enthalten die folgenden Daten:

```json
{
  "version": 1,
  "spotify_versions": [
    "8.5.89.901",
    "8.5.93.445",
    "8.5.94.839",
    "8.5.96.936",
    "8.5.98.984",
    "8.6.0.830"
  ],
  "files": [
    {
      "path": "res/values-de/plurals.xml",
      "replace": [
        {
          "key": "home_inline_onboarding_header_title/other",
          "old": "Folge %1$d Künstler*innen, um speziell für dich ausgewählte Musik zu erhalten.",
          "new": "Folge %1$d Künstlern, um speziell für dich ausgewählte Musik zu erhalten."
        },
        {
          "key": "home_inline_onboarding_header_title/one",
          "old": "Folge %1$d Künstler*in, um speziell für dich ausgewählte Musik zu erhalten.",
          "new": "Folge %1$d Künstler, um speziell für dich ausgewählte Musik zu erhalten."
        }
      ]
    }
  ]
}
```

`version` ist eine laufende Versionsnummer, die bei jedem Update inkrementiert wird.

Wird neben der eingebauten Ersetzungstabelle eine selbst erstellte (`replacements.json`) verwendet,
so erhält diese ebenfalls eine Versionsnummer, die unabhängig von der Version der eingebauen Tabelle ist.

Die Ersetzungstabellen-Version, die in diesem Fall an den App-Namen angefügt wird, setzt sich aus beiden
zusammen (z.B. `b2c1`, b für builtin und c für custom).

Die Hashes wurden durch das bessere Versionssystem quasi überflüssig und sind deswegen ab Version 1.x.x
nicht mehr enthalten.
