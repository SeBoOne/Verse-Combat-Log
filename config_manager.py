"""
Verse Combat Log - Configuration Manager
Verwaltet Einstellungen für alle Spiel-Versionen
"""

import json
import os
from typing import Dict, List, Optional
from utils import get_data_file_path


class ConfigManager:
    """Verwaltet Konfiguration für alle SC Versionen"""
    
    VERSIONS = ['LIVE', 'PTU', 'EPTU', 'TECH-PREVIEW']
    DEFAULT_PATHS = {
        'LIVE': r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\Game.log",
        'PTU': r"C:\Program Files\Roberts Space Industries\StarCitizen\PTU\Game.log",
        'EPTU': r"C:\Program Files\Roberts Space Industries\StarCitizen\EPTU\Game.log",
        'TECH-PREVIEW': r"C:\Program Files\Roberts Space Industries\StarCitizen\TECH-PREVIEW\Game.log"
    }
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = get_data_file_path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Lädt Konfiguration aus Datei"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Fehler beim Laden der Config: {e}")
        
        # Standard-Konfiguration
        return {
            'current_version': 'LIVE',
            'language': 'de',  # Default: Deutsch
            'versions': {
                version: {
                    'log_path': self.DEFAULT_PATHS[version],
                    'player_name': '',
                    'player_id': '',
                    'game_version': '',
                    'avatar_url': ''
                }
                for version in self.VERSIONS
            }
        }
    
    def _save_config(self):
        """Speichert Konfiguration"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Fehler beim Speichern der Config: {e}")
    
    def get_versions(self) -> List[str]:
        """Gibt alle verfügbaren Versionen zurück"""
        return self.VERSIONS
    
    def get_current_version(self) -> str:
        """Gibt die aktuell ausgewählte Version zurück"""
        return self.config.get('current_version', 'LIVE')
    
    def set_current_version(self, version: str):
        """Setzt die aktuelle Version"""
        if version in self.VERSIONS:
            self.config['current_version'] = version
            self._save_config()
    
    def get_log_path(self, version: str) -> str:
        """Gibt Log-Pfad für Version zurück"""
        return self.config['versions'].get(version, {}).get('log_path', '')
    
    def set_log_path(self, version: str, path: str):
        """Setzt Log-Pfad für Version"""
        if version in self.config['versions']:
            self.config['versions'][version]['log_path'] = path
            self._save_config()
    
    def get_log_paths(self) -> Dict[str, str]:
        """Gibt alle Log-Pfade zurück"""
        return {
            version: data.get('log_path', '')
            for version, data in self.config['versions'].items()
        }
    
    def get_player_name(self, version: str) -> str:
        """Gibt Spielernamen für Version zurück"""
        return self.config['versions'].get(version, {}).get('player_name', '')
    
    def get_player_id(self, version: str) -> str:
        """Gibt Spieler-ID für Version zurück"""
        return self.config['versions'].get(version, {}).get('player_id', '')
    
    def get_game_version(self, version: str) -> str:
        """Gibt Game-Version zurück"""
        return self.config['versions'].get(version, {}).get('game_version', '')

    def set_player_info(self, version: str, name: str, player_id: str):
        """Setzt Spieler-Informationen"""
        if version in self.config['versions']:
            self.config['versions'][version]['player_name'] = name
            self.config['versions'][version]['player_id'] = player_id
            self._save_config()
    
    def set_game_version(self, version: str, game_version: str):
        """Setzt Game-Version"""
        if version in self.config['versions']:
            self.config['versions'][version]['game_version'] = game_version
            self._save_config()

    def get_player_info(self, version: str) -> Dict:
        """Gibt vollständige Spieler-Info zurück"""
        version_data = self.config['versions'].get(version, {})
        return {
            'name': version_data.get('player_name', ''),
            'id': version_data.get('player_id', ''),
            'game_version': version_data.get('game_version', ''),
            'avatar_url': version_data.get('avatar_url', '')
        }

    def get_avatar_url(self, version: str) -> str:
        """Gibt Avatar-URL für Version zurück"""
        return self.config['versions'].get(version, {}).get('avatar_url', '')

    def set_avatar_url(self, version: str, avatar_url: str):
        """Setzt Avatar-URL für Version"""
        if version in self.config['versions']:
            self.config['versions'][version]['avatar_url'] = avatar_url
            self._save_config()

    def get_language(self) -> str:
        """Gibt aktuelle Sprache zurück"""
        return self.config.get('language', 'de')

    def set_language(self, language: str):
        """Setzt Sprache"""
        if language in ['de', 'en']:
            self.config['language'] = language
            self._save_config()