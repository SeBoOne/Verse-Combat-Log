"""
Verse Combat Log - Player Database
Speichert detaillierte Informationen über alle Spieler-Interaktionen
"""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime
from utils import get_data_file_path


class PlayerDatabase:
    """Verwaltet detaillierte Spieler-Statistiken"""

    def __init__(self, db_file: str = "players_db.json"):
        self.db_file = get_data_file_path(db_file)
        # player_name -> PlayerData
        self.players: Dict[str, dict] = {}
        self.load()

    def load(self):
        """Lädt Datenbank"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.players = data.get('players', {})
            except Exception as e:
                print(f"Fehler beim Laden der Spieler-DB: {e}")

    def save(self):
        """Speichert Datenbank"""
        data = {
            'last_updated': datetime.now().isoformat(),
            'players': self.players
        }

        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Fehler beim Speichern der Spieler-DB: {e}")

    def _ensure_player_exists(self, player_name: str):
        """Stellt sicher dass ein Spieler existiert"""
        if player_name not in self.players:
            self.players[player_name] = {
                'kills_by_me': {
                    'total': 0,
                    'weapons': {}  # weapon_internal -> count
                },
                'deaths_by_them': {
                    'total': 0,
                    'weapons': {}  # weapon_internal -> count
                },
                'my_vehicles_destroyed_by_them': {},  # vehicle_internal -> count
                'first_encounter': datetime.now().isoformat(),
                'last_encounter': datetime.now().isoformat(),
                'avatar_url': None  # Cache für RSI Avatar
            }

    def add_kill_by_me(self, player_name: str, weapon_internal: str):
        """
        Registriert dass ich einen Spieler getötet habe

        Args:
            player_name: Name des getöteten Spielers
            weapon_internal: Interne Waffenbezeichnung
        """
        self._ensure_player_exists(player_name)

        player = self.players[player_name]
        player['kills_by_me']['total'] += 1
        player['kills_by_me']['weapons'][weapon_internal] = \
            player['kills_by_me']['weapons'].get(weapon_internal, 0) + 1
        player['last_encounter'] = datetime.now().isoformat()

        self.save()

    def add_death_by_them(self, player_name: str, weapon_internal: str):
        """
        Registriert dass ein Spieler mich getötet hat

        Args:
            player_name: Name des Killers
            weapon_internal: Interne Waffenbezeichnung
        """
        self._ensure_player_exists(player_name)

        player = self.players[player_name]
        player['deaths_by_them']['total'] += 1
        player['deaths_by_them']['weapons'][weapon_internal] = \
            player['deaths_by_them']['weapons'].get(weapon_internal, 0) + 1
        player['last_encounter'] = datetime.now().isoformat()

        self.save()

    def add_my_vehicle_destroyed_by_them(self, player_name: str, vehicle_internal: str):
        """
        Registriert dass ein Spieler mein Fahrzeug zerstört hat

        Args:
            player_name: Name des Zerstörers
            vehicle_internal: Interner Fahrzeugname (normalisiert)
        """
        self._ensure_player_exists(player_name)

        player = self.players[player_name]
        player['my_vehicles_destroyed_by_them'][vehicle_internal] = \
            player['my_vehicles_destroyed_by_them'].get(vehicle_internal, 0) + 1
        player['last_encounter'] = datetime.now().isoformat()

        self.save()

    def get_player_stats(self, player_name: str) -> Optional[dict]:
        """
        Gibt detaillierte Stats für einen Spieler zurück

        Args:
            player_name: Name des Spielers

        Returns:
            Dict mit allen Stats oder None wenn Spieler unbekannt
        """
        return self.players.get(player_name)

    def get_all_players(self) -> Dict[str, dict]:
        """Gibt alle Spieler zurück"""
        return self.players

    def get_player_summary(self, player_name: str) -> Optional[dict]:
        """
        Gibt zusammengefasste Stats für einen Spieler zurück

        Args:
            player_name: Name des Spielers

        Returns:
            Dict mit zusammengefassten Stats
        """
        if player_name not in self.players:
            return None

        player = self.players[player_name]

        kills_by_me = player['kills_by_me']['total']
        deaths_by_them = player['deaths_by_them']['total']

        # K/D Ratio
        kd_ratio = kills_by_me / deaths_by_them if deaths_by_them > 0 else kills_by_me

        return {
            'player_name': player_name,
            'kills_by_me': kills_by_me,
            'deaths_by_them': deaths_by_them,
            'kd_ratio': round(kd_ratio, 2),
            'total_my_vehicles_destroyed_by_them': sum(player['my_vehicles_destroyed_by_them'].values()),
            'first_encounter': player['first_encounter'],
            'last_encounter': player['last_encounter'],
            'avatar_url': player.get('avatar_url')
        }

    def get_top_killers(self, limit: int = 10) -> List[dict]:
        """
        Gibt die Top-Killer zurück (Spieler die mich am meisten getötet haben)

        Args:
            limit: Maximale Anzahl

        Returns:
            Liste von Spieler-Summaries, sortiert nach deaths_by_them
        """
        summaries = [self.get_player_summary(name) for name in self.players.keys()]
        summaries.sort(key=lambda x: x['deaths_by_them'], reverse=True)
        return summaries[:limit]

    def get_top_victims(self, limit: int = 10) -> List[dict]:
        """
        Gibt die Top-Victims zurück (Spieler die ich am meisten getötet habe)

        Args:
            limit: Maximale Anzahl

        Returns:
            Liste von Spieler-Summaries, sortiert nach kills_by_me
        """
        summaries = [self.get_player_summary(name) for name in self.players.keys()]
        summaries.sort(key=lambda x: x['kills_by_me'], reverse=True)
        return summaries[:limit]

    def get_rivalries(self, min_encounters: int = 3) -> List[dict]:
        """
        Gibt Rivalitäten zurück (Spieler mit denen ich oft kämpfe)

        Args:
            min_encounters: Minimale Anzahl an Begegnungen

        Returns:
            Liste von Spieler-Summaries mit mindestens min_encounters Kämpfen
        """
        rivalries = []

        for name in self.players.keys():
            summary = self.get_player_summary(name)
            total_encounters = summary['kills_by_me'] + summary['deaths_by_them']

            if total_encounters >= min_encounters:
                summary['total_encounters'] = total_encounters
                rivalries.append(summary)

        rivalries.sort(key=lambda x: x['total_encounters'], reverse=True)
        return rivalries

    def remove_player(self, player_name: str):
        """Entfernt einen Spieler aus der Datenbank"""
        if player_name in self.players:
            del self.players[player_name]
            self.save()

    def remove_npcs(self, npc_db):
        """
        Entfernt alle NPCs aus der Spielerdatenbank

        Args:
            npc_db: NPCDatabase Instanz mit aktuellen Patterns

        Returns:
            int: Anzahl der entfernten NPCs
        """
        npcs_found = []

        for player_name in list(self.players.keys()):
            if npc_db.is_npc(player_name):
                npcs_found.append(player_name)

        # Entferne alle gefundenen NPCs
        for npc_name in npcs_found:
            del self.players[npc_name]

        if npcs_found:
            self.save()
            print(f"Spielerdatenbank bereinigt: {len(npcs_found)} NPCs entfernt")

        return len(npcs_found)

    def reset_all(self):
        """Löscht alle Spieler-Daten"""
        self.players = {}
        self.save()

    def set_avatar_url(self, player_name: str, avatar_url: str):
        """
        Setzt die Avatar-URL für einen Spieler

        Args:
            player_name: Name des Spielers
            avatar_url: URL zum RSI Avatar
        """
        self._ensure_player_exists(player_name)
        self.players[player_name]['avatar_url'] = avatar_url
        self.save()

    def get_avatar_url(self, player_name: str) -> Optional[str]:
        """
        Gibt die gespeicherte Avatar-URL zurück

        Args:
            player_name: Name des Spielers

        Returns:
            Avatar URL oder None
        """
        if player_name in self.players:
            return self.players[player_name].get('avatar_url')
        return None

    def has_avatar(self, player_name: str) -> bool:
        """
        Prüft ob ein Avatar bereits gecached ist

        Args:
            player_name: Name des Spielers

        Returns:
            True wenn Avatar vorhanden, sonst False
        """
        return player_name in self.players and self.players[player_name].get('avatar_url') is not None
