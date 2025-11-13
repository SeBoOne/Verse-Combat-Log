# Verse Combat Log v1.0

**Unofficial Star Citizen Combat Statistics Tracker**

Track your kills, deaths, weapons, and vehicles in Star Citizen with real-time statistics and player profiles.

---

## ⚠️ Windows SmartScreen Warnung

Beim ersten Download kann Windows SmartScreen eine Warnung anzeigen:

```
"Windows hat diesen PC geschützt"
```

**Das ist normal bei unsignierten Programmen!**

### So führst du das Tool aus:

1. Klicke auf **"Weitere Informationen"**
2. Klicke auf **"Trotzdem ausführen"**

### Warum diese Warnung?

- Die App ist **nicht signiert** (Code-Signing-Zertifikate kosten ~300€/Jahr)
- Windows zeigt diese Warnung bei allen unsignierten Anwendungen
- Das Tool ist **Open Source** und vollständig transparent
- Der Source Code ist auf GitHub einsehbar

### Ist das Tool sicher?

✅ **Ja!** Das Tool ist:
- Open Source (Code auf GitHub)
- Lokal auf deinem PC (kein Internet-Zugriff außer RSI-Profile)
- Keine Datensammlung
- Keine Telemetrie
- Liest nur Game.log (Read-Only)

---

## 🛡️ Antivirus False-Positives

Einige Antivirus-Programme könnten die EXE als verdächtig markieren. Dies ist ein **False-Positive**!

### Warum passiert das?

- Python-EXEs werden oft fälschlicherweise erkannt
- PyInstaller wird auch von Malware genutzt
- Neue Dateien ohne Reputation werden als verdächtig eingestuft

### Was kannst du tun?

1. **VirusTotal Check**: Lade die EXE auf [VirusTotal.com](https://virustotal.com) hoch
   - Sieh dir die Ergebnisse an (ein paar False-Positives sind normal)
   - Die meisten großen Antivirus-Programme sollten "sauber" zeigen

2. **Verifiziere die Datei**:
   - Prüfe den SHA256-Hash (siehe unten)
   - Vergleiche mit dem offiziellen Release-Hash

3. **Antivirus-Ausnahme hinzufügen**:
   - Füge `VerseCombatLog.exe` zur Ausnahmeliste deines Antivirus hinzu

4. **Source Code prüfen**:
   - Der vollständige Source Code ist auf GitHub verfügbar
   - Du kannst selbst die EXE bauen, wenn du willst

---

## 📦 Installation

1. **Download**: `VerseCombatLog.exe` herunterladen
2. **Platzierung**: In einen beliebigen Ordner verschieben
3. **Start**: Doppelklick auf `VerseCombatLog.exe`

### Erster Start:

- Das Tool erstellt automatisch Konfigurationsdateien
- Optional: `internalNames.ini` für deutsche Waffennamen (wird automatisch heruntergeladen)

---

## 🚀 Verwendung

1. **Version auswählen**: LIVE, PTU, EPTU oder TECH-PREVIEW
2. **Log-Pfad einstellen**: Einstellungen → Log-Pfad angeben
3. **Spielen**: Das Tool trackt automatisch deine Combat-Events
4. **Statistiken ansehen**: Session und Gesamt-Stats

### Features:

- ✅ Echtzeit Kill/Death Tracking
- ✅ Waffen-Statistiken
- ✅ Fahrzeug-Statistiken (mit Varianten-Aggregation)
- ✅ Spieler-Profile mit RSI-Daten
- ✅ Event-Timeline
- ✅ Custom-Namen für Waffen/Fahrzeuge
- ✅ NPC-Pattern-Filterung
- ✅ Multi-Version Support (LIVE/PTU/EPTU/TECH-PREVIEW)
- ✅ Multi-Language Support (Deutsch/English)

---

## 🔒 Datenschutz & Sicherheit

### Was das Tool macht:

- ✅ Liest `Game.log` (Read-Only)
- ✅ Speichert Statistiken lokal in JSON-Dateien
- ✅ Lädt RSI-Profile von robertsspaceindustries.com (optional, nur wenn Profil geöffnet)
- ✅ Lädt `internalNames.ini` von GitHub (einmalig, optional)

### Was das Tool NICHT macht:

- ❌ Keine Datensammlung
- ❌ Keine Telemetrie
- ❌ Kein Internet-Zugriff außer RSI-Profile & INI-Update
- ❌ Keine Änderungen an Spieldateien
- ❌ Keine Admin-Rechte benötigt

### Lokaler Server:

- Das Tool startet einen **lokalen** Flask-Server auf `127.0.0.1:5000`
- Server ist **NUR** von deinem PC erreichbar (nicht aus dem Netzwerk)
- Kein Sicherheitsrisiko

---

## 🐛 Debugging

Bei Problemen starte das Tool mit Debug-Modus:

```bash
VerseCombatLog.exe --debug
```

Dies öffnet eine Konsole mit detaillierten Logs.

---

## 📝 Disclaimer

**This is an unofficial Star Citizen fansite, not affiliated with the Cloud Imperium group of companies.**

All content on this site not authored by its host or users are property of their respective owners.

**Star Citizen®, Roberts Space Industries® and Cloud Imperium®** are registered trademarks of Cloud Imperium Rights LLC.

---

## 👨‍💻 Creator

**Created by SeBoOne**

- GitHub: https://github.com/SeBoOne/verse-combat-log
- Community Tool for Star Citizen Players

---

## 📄 Lizenz

**VerseCombatLog © 2025 by SeBoOne** is licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)

- ✅ Frei nutzbar und modifizierbar (mit Namensnennung)
- 🚫 Nicht für kommerzielle Zwecke

---

## ✨ Support

Bei Fragen oder Problemen:
- GitHub Issues: https://github.com/SeBoOne/verse-combat-log/issues
- GitHub Repository: https://github.com/SeBoOne/verse-combat-log

**Viel Spaß beim Tracken deiner Combat-Stats! o7**
