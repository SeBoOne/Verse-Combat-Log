#!/usr/bin/env python3

def filter_ini_file_with_paths(input_file: str, output_file: str):
    """
    Filtert die global.ini Datei nach folgenden Regeln:
    - Behält nur Zeilen, die mit 'vehicle_Name' oder 'item_Name' anfangen
    - Entfernt Zeilen, die '_short' vor '=' oder ',P=' enthalten
    - Speichert Ergebnis in internalNames.ini

    Args:
        input_file: Pfad zur global.ini
        output_file: Pfad zur internalNames.ini
    """

    kept_lines = 0
    deleted_lines = 0

    # Liste der erlaubten Begriffe (case-insensitive prüfbar)
    allowed_terms = {
        t.lower() for t in (
            'pistol', 'smg', 'rifle', 'sniper', 'lmg', 'special', 'LaserCannon', 'LaserRepeater', 'LaserScattergun',
            'DistortionScatterGun', 'BallisticScatterGun', 'ScatterGun', 'DistortionRepeater', 'BallisticRepeater',
            'NeutronRepeater', 'BallisticGatling', 'LaserGatling', 'DistortionCannon', 'BallisticCannon',
            'PlasmaCannon', 'TachyonCannon', 'LaserBeam', 'MassDriver', 'glauncher', 'melee'
        )
    }

    with open(input_file, 'r', encoding='utf-8') as infile:
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for line in infile:
                line = line.rstrip('\n')

                # Nur Zeilen, die mit vehicle_Name oder item_Name (groß-/kleinschreibung unkritisch) anfangen
                low = line.lower()
                if not (low.startswith('vehicle_name') or low.startswith('item_name')):
                    deleted_lines += 1
                    continue

                # Entferne Zeilen mit _short= oder _short,P= (wie vorher, case-insensitive)
                if '_short=' in low or '_short,p=' in low:
                    deleted_lines += 1
                    continue

                # Key / Value trennen
                if '=' in line:
                    key, val = line.split('=', 1)
                else:
                    key = line
                    val = ''

                key_stripped = key.strip()
                val_stripped = val.strip()

                # Falls item_Name (case-insensitive), spezielle Filter anwenden
                if key_stripped.lower().startswith('item_name'):
                    # 1) Entferne leere item_Name= (kein Wert hinter '=')
                    if val_stripped == '':
                        deleted_lines += 1
                        continue

                    # 2) item_namePlayer=none -> item_namePlayer=BackSpace (case-insensitive match auf 'none')
                    if key_stripped.lower().startswith('item_nameplayer') and val_stripped.lower() == 'none':
                        outfile.write(f"{key_stripped}=BackSpace\n")
                        kept_lines += 1
                        continue

                    # 3) Behalte alle Zeilen, die '_grenade_' enthalten und kein '_ammo'
                    if '_grenade_' in key_stripped.lower() and '_ammo' not in key_stripped.lower():
                        outfile.write(line + '\n')
                        kept_lines += 1
                        continue

                    # 4) Behalte Zeilen, die direkt nach item_Name mit MISL_ weitergehen
                    #    (d.h. der Teil zwischen 2. und 3. Unterstrich ist 'MISL')
                    parts = key_stripped.split('_')
                    # parts[0] == 'item', parts[1] == 'Name' in normaler Struktur
                    candidate = None
                    candidate2 = None
                    if len(parts) > 2:
                        candidate = parts[2].lower()
                    if len(parts) > 3:
                        candidate2 = parts[3].lower()

                    if candidate and candidate.startswith('misl'):
                        outfile.write(line + '\n')
                        kept_lines += 1
                        continue

                    # 5) Prüfe ob einer der erlaubten Begriffe an der Stelle zwischen 2. und 3. oder 3. und 4. Unterstrich steht
                    matched = False
                    if candidate and candidate in allowed_terms:
                        matched = True
                    if not matched and candidate2 and candidate2 in allowed_terms:
                        matched = True

                    if matched:
                        outfile.write(line + '\n')
                        kept_lines += 1
                        continue

                    # Sonst löschen
                    deleted_lines += 1
                    continue

                else:
                    # vehicle_Name oder andere Fälle (ohne '=') einfach behalten
                    outfile.write(line + '\n')
                    kept_lines += 1

    
    print(f"✓ Fertig!")
    print(f"  Behalten: {kept_lines} Zeilen")
    print(f"  Gelöscht: {deleted_lines} Zeilen")
    print(f"  Ausgabe: {output_file}")


def filter_ini_file():
    """
    Filtert die global.ini Datei (lokale Verwendung)
    Verwendet aktuelle Verzeichnis-Pfade
    """
    input_file = "global.ini"
    output_file = "internalNames.ini"
    filter_ini_file_with_paths(input_file, output_file)


if __name__ == "__main__":
    try:
        filter_ini_file()
    except FileNotFoundError:
        print("Fehler: global.ini nicht gefunden!")
    except Exception as e:
        print(f"Fehler: {e}")