### REGEX:
```
(\*[iIrRnN])|(\([rRnN]\))|([a-zß-ü][IRN])|((:[iIrRnN])(?![\w:]+\\"))
```

### Tests:
```
# Binnen-I
KünstlerIn
Alle KünstlerInnen anzeigen
DieseN KünstlerIn nicht spielen
JedeR kann die Musik

# Gendersternchen
Künstler*in
Alle Künstler*innen anzeigen
KÜNSTLER*INNEN
Diese(n) Künstler*in nicht spielen
Jede*r kann die Musik

# Gender-Doppelpunkt
Künstler:in
Alle Künstler:innen anzeigen
KÜNSTLER:INNEN
Jede:r kann die Musik

# Großbuchstaben (negativ)
KÜNSTLERINNEN

# Spotify-InternalLink (negativ)
<a href=\"spotify:internal:signup:thirdparty\">
```

[regexr.com/5klgm](regexr.com/5klgm)