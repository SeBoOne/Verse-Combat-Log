"""
Parser für internalNames.ini
Liest Fallback-Namen für Waffen und Fahrzeuge
Implementiert als Singleton für Performance
"""

import os
from typing import Dict, Optional


class NamesParser:
    """Parst internalNames.ini für Waffen und Fahrzeug-Namen (Singleton)"""

    _instance = None
    _initialized = False

    def __new__(cls, ini_file: str = "internalNames.ini"):
        """Singleton: Gibt immer dieselbe Instanz zurück"""
        if cls._instance is None:
            cls._instance = super(NamesParser, cls).__new__(cls)
        return cls._instance

    def __init__(self, ini_file: str = "internalNames.ini"):
        # Nur einmal initialisieren
        if NamesParser._initialized:
            return

        import sys
        from utils import get_user_data_dir

        # Prüfe ob INI im User-Data-Verzeichnis existiert (hat Vorrang)
        user_ini = os.path.join(get_user_data_dir(), ini_file)

        # Fallback: Im App-Verzeichnis (gebundelt mit EXE oder Development)
        if getattr(sys, 'frozen', False):
            # PyInstaller EXE: Im _MEIPASS temp directory
            app_ini = os.path.join(sys._MEIPASS, ini_file)
        else:
            # Development: Im aktuellen Verzeichnis
            app_ini = ini_file

        # User-INI hat Vorrang, falls vorhanden
        if os.path.exists(user_ini):
            self.ini_file = user_ini
            print(f"ℹ️  Verwende User-INI: {user_ini}")
        else:
            self.ini_file = app_ini
            print(f"ℹ️  Verwende App-INI: {app_ini}")

        self.names: Dict[str, str] = {}  # Aus INI
        self.load()

        NamesParser._initialized = True
    
    def load(self):
        """Lädt die INI-Datei"""
        if not os.path.exists(self.ini_file):
            print(f"⚠️  {self.ini_file} nicht gefunden - verwende Fallback-Namen")
            return
        
        try:
            with open(self.ini_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        self.names[key.strip()] = value.strip()
            
            print(f"✅ {len(self.names)} Namen aus {self.ini_file} geladen")
        
        except Exception as e:
            print(f"❌ Fehler beim Laden von {self.ini_file}: {e}")

    def get_weapon_name(self, internal_name: str) -> Optional[str]:
        """
        Gibt den Display-Namen einer Waffe zurück

        Args:
            internal_name: Interner Name aus Log (z.B. "none_lmg_ballistic_01_store01")

        Returns:
            Display-Name oder None
        """
        # Entferne numerische IDs am Ende
        clean_name = self._remove_numeric_suffix(internal_name)

        # Konstruiere Lookup-Key
        key = f"item_Name{clean_name}"

        # Aus INI
        return self.names.get(key)
    
    def get_vehicle_name(self, internal_name: str) -> Optional[str]:
        """
        Gibt den Display-Namen eines Fahrzeugs zurück (nur exakte Matches!)

        Args:
            internal_name: Interner Name aus Log (z.B. "DRAK_Cutlass_Black")

        Returns:
            Display-Name oder None

        WICHTIG: Diese Methode macht KEINE intelligente Suche mehr!
        Die Rückwärts-Suche und Event-Suffix-Erkennung erfolgt in vehicle_database.py
        """
        # Nur exakter Match!
        key = f"vehicle_Name{internal_name}"
        return self.names.get(key)
    
    def _remove_numeric_suffix(self, name: str) -> str:
        """Entfernt numerische Suffixe wie _7093438445660"""
        import re
        return re.sub(r'_\d{10,}$', '', name)
    
    def get_all_weapon_names(self) -> Dict[str, str]:
        """Gibt alle Waffen-Namen aus der INI zurück"""
        return {
            k.replace('item_Name', ''): v
            for k, v in self.names.items()
            if k.startswith('item_Name')
        }

    def get_all_vehicle_names(self) -> Dict[str, str]:
        """Gibt alle Fahrzeug-Namen aus der INI zurück"""
        return {
            k.replace('vehicle_Name', ''): v
            for k, v in self.names.items()
            if k.startswith('vehicle_Name')
        }