# rep0st

Das ist die Weiterführung von rep0st von User mopsalarm (https://github.com/mopsalarm/rep0st). Eine laufende Kopie steht under http://rep0st.rene8888.at zur Verfügung.

## Entwicklungsumgebung aufsetzen
Vagrant installieren: https://www.vagrantup.com/  

VM aufsetzen und provisionieren: (Dauerte bei mir ca 20 Minuten)
```
vagrant up
```
In VM einloggen und zum Shared Folder navigieren:
```
vagrant ssh
cd /vagrant
```
Am Host System kann man die Python Datein bearbeiten, sie werden daraufhin automatisch auf die VM übertragen.

Es wird ein Dump des Index und Featurevektor aller sfw/nsfw Bilder bis circa 648000 von meinem Server geladen. Ist nur 61MB groß und reicht um das Programm zu testen und daran zu arbeiten.

## Befehle für rep0st
```
# Startet eine rep0st instanz auf Port 1576
# Wenn Vagrant benutzt wird, kann man am Hostsystem zu folgender URL navigieren: 192.168.1.10:1576
env/bin/python -m rep0st.start

# Erzeugt zuerst einen Index aller sfw und nsfw Bilder, ladet dann alle Bilder herunter(70GB!)
# Wenn schon ein Index besteht und oder Bilder bestehen, werden fehlende Bilder nachgeladen
env/bin/python -m rep0st.download

# Analysiert alle Bilder und berechnet Feature Vektoren
# Kann nur gemacht werden, wenn zuerst ein Download ausgeführt wurde
env/bin/python -m rep0st.analyze
```

## Lizenz
The MIT License (MIT)

Copyright (c) 2015 mopsalarm

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
