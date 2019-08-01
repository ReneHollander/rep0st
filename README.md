rep0st
======
Sourcecode von rep0st, der Bilder Suchmaschine für [pr0gramm](https://pr0gramm.com). Erreichbar unter [rep0st.rene8888.at](https://rep0st.rene8888.at/)

# Autoren
- Rene Hollander ([user/Rene8888](http://pr0gramm.com/user/Rene8888))
- Patrick Malik
- mopsalarm ([user/mopsalarm](http://pr0gramm.com/user/mopsalarm))
- Vanilla-Chan ([user/TollesEinhorn](https://pr0gramm.com/user/TollesEinhorn)): API für URL Suche 

## Documentation
* [API](docs/api): Documentation of the rep0st API.

## Entwickeln
Entweder Virtuelle Maschine verwenden oder unter Linux versuchen aufzusetzen.

### Virtuelle Maschine
Download: [rep0st.ova](https://files.rene8888.at/rep0st/rep0st.ova)

#### Einstellungen (Virtual Box)
##### Gemeinsame Ordner

| Name | Pfad (Beispiel) | Verwendung |
| ------------- | ------------- | ------------- |
| pr0gramm  | E:\pr0gramm  | Speicherort der heruntergeladenen Bilder. |
| rep0st  | C:\Users\Rene Hollander\repositories\rep0st | Pfad zum Workspace. |

##### Netzwerk

| Typ | IPv4 Adresse | IPv4 Netzmaske | DHCP |
| ------------- | ------------- | ------------- | ------------- |
| Host Only  | 192.168.10.100 | 255.255.255.0 | deaktiviert  |

#### Verwedung
##### Logins

| Wofür | Name | Passwort |
| ------------- | ------------- | ------------- | 
| User  | root  | root |
| User  | rene | rene |
| MySQL | root | root |
| MySQL | rep0st | rep0stpw |

##### Starten
1. VM Starten
2. Mit PuTTY verbinden
   - Adresse: 192.168.10.20
   - User: rene
   - Passwort: rene
3. Einmalig den folgenden Befehl ausführen: mkdir /media/pr0gramm/images
4. `cd rep0st/`: Hier wird der gemeinsame Ordner gemounted.
5. `./run background_job`: Macht ein Update vom Index und provisioniert Redis (Kann durch große Anzahl an Bildern sehr lange dauern!). Nachdem der Index gebaut wurde kann mit CTRL+C beendet werden.
6. `./run site`: Frontend starten. Nach jeder Änderung am Code einfach neu starten.
7. Wenn fertig, Zustand der VM speichern, dann muss beim nächsten Start der Background Job nicht ausgeführt werden.

### Abhängigkeiten
- MariaDB
- Redis
- Python 3.6
```
pip install -U annoy cymysql Flask Logbook msgpack-numpy msgpack-python PyWavelets redis requests schedule SQLAlchemy opencv-python numpy simplejson
```

## Lizenz
```
The MIT License (MIT)

Copyright (c) 2015-2019 mopsalarm, Rene Hollander, Patrick Malik and contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
