"""
Verse Combat Log - Vehicle Database
"""

import json
import os
import re
from typing import Dict
from utils import get_data_file_path


class VehicleDatabase:
    """Verwaltet Fahrzeug Custom-Namen"""

    def __init__(self, db_file: str = "vehicles_db.json"):
        self.db_file = get_data_file_path(db_file)
        self.custom_names: Dict[str, str] = {}
        self.parent_vehicles: Dict[str, str] = {}  # vehicle -> parent_vehicle (für Statistik-Aggregation)

        # Vorkompiliertes Regex-Pattern für Performance
        self._entity_id_pattern = re.compile(r'_\d{13}$')

        # Event-Suffixe die automatisch zur Basis führen sollen
        self.event_suffixes = [
            '_PU_AI_NT', '_PU_AI_CRIM', '_PU_AI',
            '_NT', '_NonLethal', '_QIG', '_Event',
            '_Temp', '_Stealth'
        ]

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
                    self.parent_vehicles = data.get('parent_vehicles', {})
            except Exception as e:
                print(f"Fehler beim Laden der Fahrzeug-DB: {e}")

    def save(self):
        """Speichert Datenbank"""
        # Nur speichern wenn es etwas zu speichern gibt
        if not self.custom_names and not self.parent_vehicles:
            return

        data = {
            'custom_names': self.custom_names,
            'parent_vehicles': self.parent_vehicles
        }

        try:
            # Erstelle Verzeichnis falls nicht vorhanden
            os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Fehler beim Speichern der Fahrzeug-DB: {e}")
    
    def normalize_vehicle_name(self, full_name: str) -> str:
        """
        Normalisiert Fahrzeugnamen (entfernt ID)

        Args:
            full_name: z.B. "DRAK_Cutlass_Black_PU_AI_CRIM_QIG_7232617732776"

        Returns:
            Normalisiert: "DRAK_Cutlass_Black_PU_AI_CRIM_QIG"
        """
        # Entferne 13-stellige ID am Ende
        return self._entity_id_pattern.sub('', full_name)
    
    def get_display_name(self, internal_name: str) -> str:
        """
        Gibt Anzeigenamen zurück (Custom > INI > Intelligent Search > Auto-Generated)

        Hybrid-Ansatz mit intelligenter Event-Suffix-Erkennung:
        1. Custom-Name prüfen
        2. Direkt in INI suchen
        3. Event-Suffixe entfernen und erneut suchen
        4. Rückwärts-Suche durch alle Unterstriche
        5. Auto-generierter Name als Fallback

        Parent-Vehicles werden NUR gespeichert wenn eine Aggregation gefunden wurde!
        """
        # Normalisiere zuerst (entfernt Entity-IDs)
        normalized = self.normalize_vehicle_name(internal_name)

        # Filtere ungültige Namen (Default_XXXXX, etc.)
        if normalized.startswith('Default_') or normalized.startswith('Unknown_'):
            return normalized  # Keine Speicherung!

        # 1. Custom Name
        if normalized in self.custom_names:
            return self.custom_names[normalized]

        # 2. Aus internalNames.ini (direkt)
        ini_name = self.names_parser.get_vehicle_name(normalized)
        if ini_name:
            # Direkt gefunden - KEIN parent speichern (redundant)
            return ini_name

        # 3. Intelligente Event-Suffix-Erkennung
        # Prüfe ob bekannte Event-Suffixe vorhanden sind und entferne sie zuerst
        for suffix in self.event_suffixes:
            if normalized.endswith(suffix):
                base_candidate = normalized[:-len(suffix)]
                # Prüfe ob Basis in INI existiert
                ini_name = self.names_parser.get_vehicle_name(base_candidate)
                if ini_name:
                    # Gefunden! Speichere BEIDES: Custom-Name UND Parent
                    self.custom_names[normalized] = ini_name
                    self.parent_vehicles[normalized] = base_candidate  # Parent = Basis
                    self.save()
                    return ini_name
                # Wenn Basis nicht in INI, weitermachen mit Rückwärts-Suche
                break  # Nur ersten passenden Suffix behandeln

        # 4. Rückwärts-Suche durch Unterstriche (falls Event-Suffixe nicht erkannt)
        parts = normalized.split('_')
        if len(parts) > 2:  # Mindestens 3 Teile (z.B. MISC_Prospector_XX)
            # Von hinten nach vorne durch alle Kombinationen
            for i in range(len(parts) - 1, 1, -1):
                shortened = '_'.join(parts[:i])
                ini_name = self.names_parser.get_vehicle_name(shortened)
                if ini_name:
                    # Gefunden! Speichere BEIDES: Custom-Name UND Parent
                    self.custom_names[normalized] = ini_name
                    self.parent_vehicles[normalized] = shortened  # Parent = gefundene Basis
                    self.save()
                    return ini_name

        # 5. Auto-Generate (erste 3 Teile) als letzter Fallback
        # Keine Basis gefunden - KEIN parent speichern (bleibt separat)
        parts = normalized.split('_')
        display_name = ' '.join(parts[:min(3, len(parts))])
        return display_name
    
    def set_custom_name(self, internal_name: str, display_name: str):
        """Setzt einen Custom-Namen"""
        normalized = self.normalize_vehicle_name(internal_name)
        self.custom_names[normalized] = display_name
        self.save()

    def get_parent_vehicle(self, internal_name: str) -> str:
        """
        Gibt Parent-Vehicle zurück (für Statistik-Aggregation)

        Args:
            internal_name: Interner Fahrzeugname

        Returns:
            Parent-Vehicle interner Name (falls aggregiert), sonst normalisierter Name
        """
        normalized = self.normalize_vehicle_name(internal_name)

        # Falls parent explizit gesetzt ist, verwende diesen
        if normalized in self.parent_vehicles:
            return self.parent_vehicles[normalized]

        # Falls nicht: Führe get_display_name aus um parent evtl. automatisch zu setzen
        self.get_display_name(internal_name)

        # Falls jetzt parent gesetzt wurde (durch Aggregation), verwende diesen
        # Sonst: normalized (= keine Aggregation, Fahrzeug zählt für sich selbst)
        return self.parent_vehicles.get(normalized, normalized)

    def set_parent_vehicle(self, internal_name: str, parent_name: str):
        """
        Setzt Parent-Vehicle manuell

        Args:
            internal_name: Fahrzeug das zugeordnet werden soll
            parent_name: Parent-Fahrzeug (interner Name oder leer für "sich selbst")
        """
        normalized = self.normalize_vehicle_name(internal_name)

        if not parent_name or parent_name.strip() == '':
            # Leer = auf sich selbst setzen (keine Aggregation)
            self.parent_vehicles[normalized] = normalized
        else:
            # Normalisiere auch parent_name
            parent_normalized = self.normalize_vehicle_name(parent_name)
            self.parent_vehicles[normalized] = parent_normalized

        self.save()
        print(f"📊 Parent-Vehicle gesetzt: {normalized} -> {self.parent_vehicles[normalized]}")
    
    def get_all_vehicles(self, used_vehicles: list = None) -> Dict[str, str]:
        """
        Gibt alle bekannten Fahrzeuge zurück

        Args:
            used_vehicles: Liste von internen Fahrzeugnamen (normalisiert), die verwendet wurden

        Returns:
            Dict mit internal_name -> display_name
        """
        all_vehicles = {}

        # 1. Aus INI
        ini_vehicles = self.names_parser.get_all_vehicle_names()
        all_vehicles.update(ini_vehicles)

        # 2. Custom überschreibt
        all_vehicles.update(self.custom_names)

        # 3. Füge verwendete Fahrzeuge hinzu (mit Auto-Generate falls nicht in INI/Custom)
        if used_vehicles:
            for internal_name in used_vehicles:
                normalized = self.normalize_vehicle_name(internal_name)
                if normalized not in all_vehicles:
                    # Auto-generiere Namen für unbekannte, aber verwendete Fahrzeuge
                    parts = normalized.split('_')
                    all_vehicles[normalized] = ' '.join(parts[:min(3, len(parts))])

        return all_vehicles