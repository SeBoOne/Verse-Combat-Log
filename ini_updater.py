"""
Verse Combat Log - INI Auto-Updater
Lädt global.ini von GitHub, prüft Version und erstellt internalNames.ini
"""

import os
import requests
from typing import Optional, Tuple
from utils import get_user_data_dir


class INIUpdater:
    """Verwaltet Auto-Update der internalNames.ini"""

    GITHUB_URL = "https://raw.githubusercontent.com/SeBoOne/verse-combat-log/main/data/global.ini"

    def __init__(self):
        self.user_data_dir = get_user_data_dir()
        self.global_ini_path = os.path.join(self.user_data_dir, "global.ini")
        self.internal_names_path = os.path.join(self.user_data_dir, "internalNames.ini")

    def check_and_update(self) -> Tuple[bool, str]:
        """
        Prüft und aktualisiert INI-Dateien

        Returns:
            (needs_restart, message): Tuple mit Restart-Flag und Status-Nachricht
        """
        try:
            # 1. Prüfe ob global.ini existiert
            if not os.path.exists(self.global_ini_path):
                print("📥 global.ini nicht gefunden - lade von GitHub...")
                return self._download_and_convert()

            # 2. Hole aktuelle Version von GitHub
            print("🔍 Prüfe auf Updates...")
            remote_version = self._get_remote_version()
            if not remote_version:
                print("⚠️  Konnte Remote-Version nicht abrufen")
                # Wenn keine Remote-Version verfügbar, aber lokale INI existiert
                if os.path.exists(self.internal_names_path):
                    return False, "Verwende lokale INI (Update-Check fehlgeschlagen)"
                else:
                    # Erstelle aus bestehender global.ini
                    return self._convert_existing_global_ini()

            # 3. Hole lokale Version
            local_version = self._get_local_version()

            # 4. Vergleiche Versionen
            if local_version != remote_version:
                print(f"🆕 Neue Version gefunden: {remote_version} (Lokal: {local_version})")
                return self._download_and_convert()
            else:
                print(f"✅ INI ist aktuell (Version: {local_version})")
                # Prüfe ob internalNames.ini existiert
                if not os.path.exists(self.internal_names_path):
                    print("⚠️  internalNames.ini fehlt - erstelle neu...")
                    return self._convert_existing_global_ini()
                return False, f"INI aktuell (Version: {local_version})"

        except Exception as e:
            print(f"❌ Fehler beim Update-Check: {e}")
            # Fallback: Wenn internalNames.ini existiert, verwende diese
            if os.path.exists(self.internal_names_path):
                return False, f"Verwende lokale INI (Fehler: {e})"
            return False, f"Update-Fehler: {e}"

    def _get_remote_version(self) -> Optional[str]:
        """Holt Frontend_PU_Version aus GitHub global.ini"""
        try:
            response = requests.get(self.GITHUB_URL, timeout=10)
            response.raise_for_status()

            # Suche nach Frontend_PU_Version
            for line in response.text.splitlines():
                if line.startswith('Frontend_PU_Version'):
                    if '=' in line:
                        return line.split('=', 1)[1].strip()

            return None
        except Exception as e:
            print(f"❌ Fehler beim Abrufen der Remote-Version: {e}")
            return None

    def _get_local_version(self) -> Optional[str]:
        """Liest Frontend_PU_Version aus lokaler global.ini"""
        try:
            if not os.path.exists(self.global_ini_path):
                return None

            with open(self.global_ini_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('Frontend_PU_Version'):
                        if '=' in line:
                            return line.split('=', 1)[1].strip()

            return None
        except Exception as e:
            print(f"❌ Fehler beim Lesen der lokalen Version: {e}")
            return None

    def _download_and_convert(self) -> Tuple[bool, str]:
        """Lädt global.ini von GitHub und konvertiert zu internalNames.ini"""
        try:
            # Download
            print("📥 Lade global.ini von GitHub...")
            response = requests.get(self.GITHUB_URL, timeout=30)
            response.raise_for_status()

            # Speichere global.ini
            with open(self.global_ini_path, 'w', encoding='utf-8') as f:
                f.write(response.text)

            print("✅ global.ini heruntergeladen")

            # Konvertiere zu internalNames.ini
            return self._convert_existing_global_ini()

        except Exception as e:
            print(f"❌ Fehler beim Download: {e}")
            return False, f"Download-Fehler: {e}"

    def _convert_existing_global_ini(self) -> Tuple[bool, str]:
        """Konvertiert bestehende global.ini zu internalNames.ini"""
        try:
            print("🔄 Konvertiere global.ini zu internalNames.ini...")

            # Importiere filter_ini Funktion
            from filter_ini import filter_ini_file_with_paths

            # Konvertiere
            filter_ini_file_with_paths(self.global_ini_path, self.internal_names_path)

            version = self._get_local_version() or "Unbekannt"
            print(f"✅ internalNames.ini erstellt (Version: {version})")

            return True, f"INI aktualisiert (Version: {version})"

        except Exception as e:
            print(f"❌ Fehler bei der Konvertierung: {e}")
            return False, f"Konvertierungs-Fehler: {e}"


# Hilfsfunktion für schnellen Check
def check_ini_update() -> Tuple[bool, str]:
    """
    Prüft und aktualisiert INI-Dateien

    Returns:
        (needs_restart, message): Tuple mit Restart-Flag und Status-Nachricht
    """
    updater = INIUpdater()
    return updater.check_and_update()
