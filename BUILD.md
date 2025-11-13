# Build Anleitung für Verse Combat Log

## Voraussetzungen

1. Python 3.10 oder höher installiert
2. Alle Dependencies installiert: `pip install -r requirements.txt`
3. PyInstaller installiert: `pip install pyinstaller`

## EXE erstellen

### Option 1: Mit vorbereiteter Spec-Datei (empfohlen)

```bash
pyinstaller build_exe.spec
```

Die fertige EXE befindet sich dann in `dist/VerseCombatLog.exe`

### Option 2: Manueller Build-Befehl

```bash
pyinstaller --onefile --windowed --name VerseCombatLog ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --add-data "internalNames.ini;." ^
  --hidden-import eventlet.hubs.epolls ^
  --hidden-import eventlet.hubs.kqueue ^
  --hidden-import eventlet.hubs.selects ^
  --hidden-import dns ^
  --hidden-import webview ^
  app.py
```

## Build-Optionen anpassen

In der `build_exe.spec` Datei können Sie folgendes anpassen:

- **`console=False`**: Konsole ist standardmäßig versteckt
  - Zum Debugging mit Konsole: `VerseCombatLog.exe --debug` ausführen
  - Im Debug-Modus wird automatisch eine Konsole angezeigt

- **`icon='vcl-icon.ico'`**: VCL Logo wird als Icon verwendet
  - Icon wird automatisch aus `static/media/vcl-logo-icon.png` generiert
  - Zum Ändern: `python create_icon.py` mit neuem PNG ausführen

- **`upx=True/False`**:
  - `True` = Komprimiert EXE (kleinere Datei)
  - `False` = Keine Komprimierung (schnellerer Start)

## Hinweise

- Die erste Build kann einige Minuten dauern
- Die EXE-Größe beträgt ca. 30-50 MB
- Bei Problemen mit Antivirus: EXE als Ausnahme hinzufügen
- Die EXE ist vollständig standalone:
  - `internalNames.ini` wird automatisch in die EXE eingebettet
  - Alle Konfigurationen und Datenbanken werden in `%LOCALAPPDATA%\VCL-Files\` gespeichert
  - Die EXE kann von jedem Ort ausgeführt werden

## Icon erstellen

Das Icon wird automatisch aus dem PNG-Logo generiert:

```bash
python create_icon.py
```

Dies erstellt `vcl-icon.ico` aus `static/media/vcl-logo-icon.png` mit mehreren Auflösungen (16x16 bis 256x256).

## Entwicklungsmodus

Für die Entwicklung einfach normal starten:

```bash
python app.py
```

Mit Debug-Ausgabe:

```bash
python app.py --debug
```

Die Anwendung öffnet sich dann in einem eigenen Desktop-Fenster.

## Troubleshooting

### "Module not found" Fehler
Fügen Sie fehlende Module unter `hiddenimports` in der `build_exe.spec` hinzu.

### EXE startet nicht
Starten Sie die EXE mit `--debug` Parameter, um Fehlermeldungen in der Konsole zu sehen:
```bash
VerseCombatLog.exe --debug
```

### Antivirus blockiert EXE
Fügen Sie die EXE als Ausnahme hinzu oder signieren Sie die EXE digital.
