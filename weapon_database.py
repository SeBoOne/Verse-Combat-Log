"""
Verse Combat Log - Weapon Database
Speichert nur Custom-Namen, Fallback kommt aus internalNames.ini
"""

import json
import os
import re
from typing import Dict, List
from utils import get_data_file_path


class WeaponDatabase:
    """Verwaltet Custom-Waffennamen und Blacklist"""

    def __init__(self, db_file: str = "weapons_db.json"):
        self.db_file = get_data_file_path(db_file)
        self.custom_names: Dict[str, str] = {}  # Nur custom Namen
        self.blacklist: List[str] = []

        # Vorkompilierte Regex-Patterns für Performance
        self._entity_id_pattern = re.compile(r'_\d{10,}$')
        self._number_pattern = re.compile(r'_\d+')
        self._store_pattern = re.compile(r'_(store|chromic|imp)\d+')

        self.load()

        # Lade Names Parser für Fallback
        from names_parser import NamesParser
        self.names_parser = NamesParser()
    
    def load(self):
        """Lädt Datenbank"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.custom_names = data.get('custom_names', {})
                    self.blacklist = data.get('blacklist', [])
            except Exception as e:
                print(f"Fehler beim Laden der Waffen-DB: {e}")
    
    def save(self):
        """Speichert Datenbank"""
        data = {
            'custom_names': self.custom_names,
            'blacklist': self.blacklist
        }
        
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Fehler beim Speichern der Waffen-DB: {e}")
    
    def get_display_name(self, internal_name: str) -> str:
        """Gibt Anzeigenamen zurück (Custom > INI > Auto-Generated)"""
        # 1. Custom Name
        if internal_name in self.custom_names:
            return self.custom_names[internal_name]

        # 2. Aus internalNames.ini
        ini_name = self.names_parser.get_weapon_name(internal_name)
        if ini_name:
            return ini_name

        # 3. Auto-Generate (Fallback)
        display_name = self._create_display_name(internal_name)
        return display_name
    
    def normalize_weapon_name(self, weapon_full: str) -> str:
        """
        Normalisiert Waffennamen, entfernt Entity-IDs

        Beispiel: GLSN_BallisticGatling_S4_7376494911512 -> GLSN_BallisticGatling_S4

        Args:
            weapon_full: Voller Waffenname mit Entity-ID

        Returns:
            Normalisierter Waffenname ohne ID
        """
        # Entferne lange Zahlen-IDs am Ende (Entity-IDs, z.B. _7376494911512)
        return self._entity_id_pattern.sub('', weapon_full)

    def _create_display_name(self, internal_name: str) -> str:
        """Erstellt automatisch Anzeigenamen als Fallback"""
        name = self._number_pattern.sub('', internal_name)
        name = self._store_pattern.sub('', name)

        parts = name.split('_')
        filtered = [p for p in parts if p not in ['none', '01', '02', '03', 'store', 'chromic', 'imp'] and not p.isdigit()]

        if filtered:
            return ' '.join(word.capitalize() for word in filtered)

        return internal_name
    
    def set_custom_name(self, internal_name: str, display_name: str):
        """Setzt einen Custom-Namen"""
        self.custom_names[internal_name] = display_name
        self.save()

    def is_blacklisted(self, internal_name: str) -> bool:
        """Prüft Blacklist-Status"""
        return internal_name in self.blacklist
    
    def add_to_blacklist(self, internal_name: str):
        """Fügt zur Blacklist hinzu"""
        if internal_name not in self.blacklist:
            self.blacklist.append(internal_name)
            self.save()
    
    def remove_from_blacklist(self, internal_name: str):
        """Entfernt von Blacklist"""
        if internal_name in self.blacklist:
            self.blacklist.remove(internal_name)
            self.save()
    
    def get_all_weapons(self, used_weapons: list = None) -> Dict[str, str]:
        """
        Gibt alle bekannten Waffen mit Display-Namen zurück

        Args:
            used_weapons: Liste von internen Waffennamen, die verwendet wurden

        Returns:
            Dict mit internal_name -> display_name
        """
        all_weapons = {}

        # 1. Aus INI
        ini_weapons = self.names_parser.get_all_weapon_names()
        all_weapons.update(ini_weapons)

        # 2. Custom überschreibt INI
        all_weapons.update(self.custom_names)

        # 3. Füge verwendete Waffen hinzu (mit Auto-Generate falls nicht in INI/Custom)
        if used_weapons:
            for internal_name in used_weapons:
                if internal_name not in all_weapons:
                    # Auto-generiere Namen für unbekannte, aber verwendete Waffen
                    all_weapons[internal_name] = self._create_display_name(internal_name)

        return all_weapons
    
    def get_blacklist(self) -> List[str]:
        """Gibt Blacklist zurück"""
        return self.blacklist