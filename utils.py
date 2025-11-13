"""
Verse Combat Log - Utilities
Zentrale Hilfsfunktionen
"""

import os
import sys
from pathlib import Path


def get_user_data_dir() -> str:
    """
    Gibt das Verzeichnis für Benutzerdaten zurück.

    Bei EXE-Deployment: %LOCALAPPDATA%/VCL-Files
    Bei Entwicklung: ./VCL-Files (im Projektverzeichnis)

    Returns:
        Absoluter Pfad zum Datenverzeichnis
    """
    # Prüfe ob wir als EXE laufen (PyInstaller)
    if getattr(sys, 'frozen', False):
        # Als EXE: Verwende AppData/Local
        appdata_local = os.getenv('LOCALAPPDATA')
        if appdata_local:
            data_dir = os.path.join(appdata_local, 'VCL-Files')
        else:
            # Fallback wenn LOCALAPPDATA nicht verfügbar
            data_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'VCL-Files')
    else:
        # Entwicklungsmodus: Im Projektverzeichnis
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(script_dir, 'VCL-Files')

    # Erstelle Verzeichnis falls nicht vorhanden
    os.makedirs(data_dir, exist_ok=True)

    return data_dir


def get_data_file_path(filename: str) -> str:
    """
    Gibt den vollständigen Pfad für eine Datendatei zurück.

    Args:
        filename: Name der Datei (z.B. 'config.json')

    Returns:
        Absoluter Pfad zur Datei im Datenverzeichnis
    """
    return os.path.join(get_user_data_dir(), filename)
