"""
Verse Combat Log - NPC Database
"""

import json
import os
from typing import List
from utils import get_data_file_path


class NPCDatabase:
    """Verwaltet NPC-Patterns"""
    
    def __init__(self, db_file: str = "npc_db.json"):
        self.db_file = get_data_file_path(db_file)
        self.patterns: List[str] = []
        self.load()
    
    def load(self):
        """Lädt Datenbank"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.patterns = data.get('patterns', [])
            except Exception as e:
                print(f"Fehler beim Laden der NPC-DB: {e}")
        
        # Standard-Patterns
        if not self.patterns:
            self.patterns = [
                'PU_Human_Enemy',
                '_NPC_',
                'yormandi_',
                '_Elite_',
                '_grunt_',
                '_sniper_',
                '_juggernaut_',
                '_cqc_',
                'Ninetails',
                'Dusters',
                'XenoThreat',
                'ASD_',
                "Kopion_",
                "StreamingSOC_",
                "vlk_juvenile_",
                "PU_Human-NineTails",
                "vlk_adult_",
                "_irradiated_",
                "_sentry_",
                "PU_Pilots",
                "-Human-Criminal-",
                "-Human-Civilian-",
                "MissionEntityStreamable_",
                "AIModule_",
                "_Unmanned_PU_PDC_",
                "-StormBreaker-",
                "PU_Human-",
                "-Populace-Engineer-",
                "NPC_Archetypes_"
            ]
            self.save()
    
    def save(self):
        """Speichert Datenbank"""
        data = {
            'patterns': self.patterns
        }
        
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Fehler beim Speichern der NPC-DB: {e}")
    
    def is_npc(self, name: str) -> bool:
        """Prüft ob Name ein NPC ist"""
        return any(pattern in name for pattern in self.patterns)
    
    def add_pattern(self, pattern: str):
        """Fügt Pattern hinzu"""
        if pattern and pattern not in self.patterns:
            self.patterns.append(pattern)
            self.save()
    
    def remove_pattern(self, pattern: str):
        """Entfernt Pattern"""
        if pattern in self.patterns:
            self.patterns.remove(pattern)
            self.save()
    
    def get_patterns(self) -> List[str]:
        """Gibt alle Patterns zurück"""
        return self.patterns