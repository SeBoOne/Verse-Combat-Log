"""
Verse Combat Log - Statistics Manager v4.1
Verwaltet Session- und Gesamtstatistiken pro Version
WICHTIG: Speichert INTERNE Namen, Display-Namen werden im Frontend gemappt
"""

import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict
from utils import get_data_file_path


class StatsManager:
    """Verwaltet Statistiken für eine SC Version"""

    def __init__(self, version: str):
        self.version = version
        self.stats_file = get_data_file_path(f"stats_{version.lower()}.json")

        self.session = self._create_empty_stats()
        self.total = self._create_empty_stats()
        self.session_start = datetime.now()

        # Lazy-loaded VehicleDatabase für Aggregation (nur einmal instanziieren)
        self._vehicle_db = None

        self.load()
    
    def _create_empty_stats(self) -> Dict:
        """Erstellt leere Statistik-Struktur"""
        return {
            'session_id': '',  # Session ID wird hier gespeichert
            'pve_kills': 0,
            'pvp_kills': 0,
            'deaths': 0,
            'weapon_kills': {},  # Internal Name -> Count
            'pvp_victims': {},  # Player Name -> [Internal Weapon Names]
            'death_weapons': {},  # Internal Name -> Count
            'death_by_players': {},  # Player Name -> Count
            'vehicle_kills': {},  # Internal Vehicle Name -> Count
            'vehicle_losses_by_player': {}  # Player Name -> {Internal Vehicle Name -> Count}
        }
    
    def add_kill(self, is_pvp: bool, weapon_internal: str, victim_name: str = None):
        """
        Fügt einen Kill hinzu
        
        Args:
            is_pvp: Ob PvP Kill
            weapon_internal: INTERNER Waffenname aus Log
            victim_name: Name des Opfers (bei PvP)
        """
        if is_pvp:
            self.session['pvp_kills'] += 1
            self.total['pvp_kills'] += 1
            if victim_name:
                if victim_name not in self.session['pvp_victims']:
                    self.session['pvp_victims'][victim_name] = []
                if victim_name not in self.total['pvp_victims']:
                    self.total['pvp_victims'][victim_name] = []
                
                self.session['pvp_victims'][victim_name].append(weapon_internal)
                self.total['pvp_victims'][victim_name].append(weapon_internal)
        else:
            self.session['pve_kills'] += 1
            self.total['pve_kills'] += 1
        
        # Waffen-Tracking (intern)
        self.session['weapon_kills'][weapon_internal] = \
            self.session['weapon_kills'].get(weapon_internal, 0) + 1
        self.total['weapon_kills'][weapon_internal] = \
            self.total['weapon_kills'].get(weapon_internal, 0) + 1
        
        self.save()
    
    def add_death(self, weapon_internal: str, killer_name: str = None):
        """
        Fügt einen Tod hinzu
        
        Args:
            weapon_internal: INTERNER Waffenname
            killer_name: Name des Killers (bei PvP)
        """
        self.session['deaths'] += 1
        self.total['deaths'] += 1
        
        self.session['death_weapons'][weapon_internal] = \
            self.session['death_weapons'].get(weapon_internal, 0) + 1
        self.total['death_weapons'][weapon_internal] = \
            self.total['death_weapons'].get(weapon_internal, 0) + 1
        
        if killer_name:
            self.session['death_by_players'][killer_name] = \
                self.session['death_by_players'].get(killer_name, 0) + 1
            self.total['death_by_players'][killer_name] = \
                self.total['death_by_players'].get(killer_name, 0) + 1
        
        self.save()
    
    def add_vehicle_kill(self, vehicle_internal: str):
        """
        Fügt Fahrzeug-Kill hinzu

        Args:
            vehicle_internal: INTERNER Fahrzeugname (normalisiert, ohne ID)
        """
        self.session['vehicle_kills'][vehicle_internal] = \
            self.session['vehicle_kills'].get(vehicle_internal, 0) + 1
        self.total['vehicle_kills'][vehicle_internal] = \
            self.total['vehicle_kills'].get(vehicle_internal, 0) + 1

        self.save()

    def add_vehicle_loss(self, vehicle_internal: str, destroyer_name: str):
        """
        Fügt Verlust eines eigenen Fahrzeugs hinzu

        Args:
            vehicle_internal: INTERNER Fahrzeugname (normalisiert, ohne ID)
            destroyer_name: Name des Spielers der das Fahrzeug zerstört hat
        """
        # Session
        if destroyer_name not in self.session['vehicle_losses_by_player']:
            self.session['vehicle_losses_by_player'][destroyer_name] = {}
        self.session['vehicle_losses_by_player'][destroyer_name][vehicle_internal] = \
            self.session['vehicle_losses_by_player'][destroyer_name].get(vehicle_internal, 0) + 1

        # Total
        if destroyer_name not in self.total['vehicle_losses_by_player']:
            self.total['vehicle_losses_by_player'][destroyer_name] = {}
        self.total['vehicle_losses_by_player'][destroyer_name][vehicle_internal] = \
            self.total['vehicle_losses_by_player'][destroyer_name].get(vehicle_internal, 0) + 1

        self.save()
    
    def reset_session(self, remove_from_total: bool = False):
        """Setzt Session zurück"""
        if remove_from_total:
            # Entferne Session-Daten aus Total
            self.total['pve_kills'] = max(0, self.total['pve_kills'] - self.session['pve_kills'])
            self.total['pvp_kills'] = max(0, self.total['pvp_kills'] - self.session['pvp_kills'])
            self.total['deaths'] = max(0, self.total['deaths'] - self.session['deaths'])
            
            # Waffen
            for weapon, count in self.session['weapon_kills'].items():
                self.total['weapon_kills'][weapon] = \
                    self.total['weapon_kills'].get(weapon, 0) - count
                if self.total['weapon_kills'][weapon] <= 0:
                    del self.total['weapon_kills'][weapon]
            
            for weapon, count in self.session['death_weapons'].items():
                self.total['death_weapons'][weapon] = \
                    self.total['death_weapons'].get(weapon, 0) - count
                if self.total['death_weapons'][weapon] <= 0:
                    del self.total['death_weapons'][weapon]
            
            # Killer
            for killer, count in self.session['death_by_players'].items():
                self.total['death_by_players'][killer] = \
                    self.total['death_by_players'].get(killer, 0) - count
                if self.total['death_by_players'][killer] <= 0:
                    del self.total['death_by_players'][killer]
            
            # Vehicles
            for vehicle, count in self.session['vehicle_kills'].items():
                self.total['vehicle_kills'][vehicle] = \
                    self.total['vehicle_kills'].get(vehicle, 0) - count
                if self.total['vehicle_kills'][vehicle] <= 0:
                    del self.total['vehicle_kills'][vehicle]

            # Vehicle Losses
            for player, vehicles in self.session['vehicle_losses_by_player'].items():
                if player in self.total['vehicle_losses_by_player']:
                    for vehicle, count in vehicles.items():
                        self.total['vehicle_losses_by_player'][player][vehicle] = \
                            self.total['vehicle_losses_by_player'][player].get(vehicle, 0) - count
                        if self.total['vehicle_losses_by_player'][player][vehicle] <= 0:
                            del self.total['vehicle_losses_by_player'][player][vehicle]
                    # Entferne Spieler wenn keine Fahrzeuge mehr
                    if not self.total['vehicle_losses_by_player'][player]:
                        del self.total['vehicle_losses_by_player'][player]

        self.session = self._create_empty_stats()
        self.session_start = datetime.now()
        self.save()
    
    def merge_session_to_total(self):
        """Merged Session in Total (Server-Swap)"""
        self.save()

    def get_session_id(self) -> str:
        """Gibt aktuelle Session-ID zurück"""
        return self.session.get('session_id', '')

    def set_session_id(self, session_id: str):
        """Setzt Session-ID"""
        self.session['session_id'] = session_id
        self.save()

    def recalculate_npc_stats(self, npc_db):
        """
        Bewertet alle Stats neu basierend auf aktuellen NPC-Patterns

        Args:
            npc_db: NPCDatabase Instanz mit aktuellen Patterns
        """
        for stats_type in ['session', 'total']:
            stats = self.session if stats_type == 'session' else self.total

            # Finde alle Spieler in pvp_victims die jetzt als NPCs erkannt werden
            npcs_in_victims = []
            for victim_name in list(stats['pvp_victims'].keys()):
                if npc_db.is_npc(victim_name):
                    npcs_in_victims.append(victim_name)

            # Korrigiere pvp_victims
            for npc_name in npcs_in_victims:
                weapon_list = stats['pvp_victims'][npc_name]
                # Reduziere PvP Kills um Anzahl der Kills
                stats['pvp_kills'] = max(0, stats['pvp_kills'] - len(weapon_list))
                # Erhöhe PvE Kills
                stats['pve_kills'] += len(weapon_list)
                # Entferne aus pvp_victims
                del stats['pvp_victims'][npc_name]

            # Finde alle NPCs in death_by_players
            npcs_in_deaths = []
            for killer_name in list(stats['death_by_players'].keys()):
                if npc_db.is_npc(killer_name):
                    npcs_in_deaths.append(killer_name)

            # Korrigiere death_by_players
            for npc_name in npcs_in_deaths:
                # Entferne aus death_by_players
                del stats['death_by_players'][npc_name]

            # Finde alle NPCs in vehicle_losses_by_player
            npcs_in_vehicle_losses = []
            for destroyer_name in list(stats['vehicle_losses_by_player'].keys()):
                if npc_db.is_npc(destroyer_name):
                    npcs_in_vehicle_losses.append(destroyer_name)

            # Korrigiere vehicle_losses_by_player
            for npc_name in npcs_in_vehicle_losses:
                del stats['vehicle_losses_by_player'][npc_name]

        # Bereinige auch die Spielerdatenbank
        from player_database import PlayerDatabase
        player_db = PlayerDatabase()
        removed_count = player_db.remove_npcs(npc_db)

        self.save()
        print(f"[{self.version}] Stats neu bewertet basierend auf NPC-Patterns")
        if removed_count > 0:
            print(f"[{self.version}] {removed_count} NPCs aus Spielerdatenbank entfernt")
    
    def get_all_stats(self) -> Dict:
        """Gibt alle Statistiken zurück (INTERNE Namen!)"""
        return {
            'session': self._format_stats(self.session),
            'total': self._format_stats(self.total),
            'session_start': self.session_start.isoformat(),
            'session_id': self.session.get('session_id', '')
        }
    
    def _format_stats(self, stats: Dict) -> Dict:
        """Formatiert Statistiken für JSON (mit Parent-Vehicle-Aggregation!)"""
        total_kills = stats['pve_kills'] + stats['pvp_kills']
        total_deaths = stats['deaths']

        # Berechne PvP Deaths (Anzahl der Tode durch Spieler)
        pvp_deaths = sum(stats['death_by_players'].values())

        kd_ratio = 0.0
        if total_deaths > 0:
            kd_ratio = round(total_kills / total_deaths, 2)

        # Aggregiere vehicle_kills nach parent_vehicle
        aggregated_vehicle_kills = self._aggregate_vehicle_kills(stats['vehicle_kills'])

        # Aggregiere vehicle_losses_by_player
        aggregated_vehicle_losses = {}
        for player, vehicles in stats['vehicle_losses_by_player'].items():
            aggregated_vehicles = self._aggregate_vehicle_kills(vehicles)
            aggregated_vehicle_losses[player] = aggregated_vehicles

        return {
            'session_id': stats.get('session_id', ''),
            'pve_kills': stats['pve_kills'],
            'pvp_kills': stats['pvp_kills'],
            'total_kills': total_kills,
            'deaths': total_deaths,
            'pvp_deaths': pvp_deaths,
            'kd_ratio': kd_ratio,
            'weapon_kills': stats['weapon_kills'],  # INTERN!
            'pvp_victims': stats['pvp_victims'],  # Victims -> [INTERNE Waffen]
            'death_weapons': stats['death_weapons'],  # INTERN!
            'death_by_players': stats['death_by_players'],
            'vehicle_kills': aggregated_vehicle_kills,  # AGGREGIERT!
            'vehicle_losses_by_player': aggregated_vehicle_losses  # AGGREGIERT!
        }

    def _aggregate_vehicle_kills(self, vehicle_kills: Dict[str, int]) -> Dict[str, int]:
        """
        Aggregiert Fahrzeug-Kills nach Parent-Vehicle

        Args:
            vehicle_kills: Dict mit vehicle_internal -> count

        Returns:
            Dict mit parent_vehicle -> aggregated_count
        """
        # Lazy-load VehicleDatabase (nur beim ersten Aufruf instanziieren)
        if self._vehicle_db is None:
            from vehicle_database import VehicleDatabase
            self._vehicle_db = VehicleDatabase()

        aggregated = {}
        for vehicle_internal, count in vehicle_kills.items():
            # Hole Parent-Vehicle (falls vorhanden, sonst vehicle selbst)
            parent = self._vehicle_db.get_parent_vehicle(vehicle_internal)
            # Addiere zum Parent
            aggregated[parent] = aggregated.get(parent, 0) + count

        return aggregated
    
    def save(self):
        """Speichert Statistiken"""
        data = {
            'last_updated': datetime.now().isoformat(),
            'session_start': self.session_start.isoformat(),
            'session': {
                'session_id': self.session.get('session_id', ''),
                'pve_kills': self.session['pve_kills'],
                'pvp_kills': self.session['pvp_kills'],
                'deaths': self.session['deaths'],
                'weapon_kills': self.session['weapon_kills'],
                'pvp_victims': self.session['pvp_victims'],
                'death_weapons': self.session['death_weapons'],
                'death_by_players': self.session['death_by_players'],
                'vehicle_kills': self.session['vehicle_kills'],
                'vehicle_losses_by_player': self.session['vehicle_losses_by_player']
            },
            'total': {
                'pve_kills': self.total['pve_kills'],
                'pvp_kills': self.total['pvp_kills'],
                'deaths': self.total['deaths'],
                'weapon_kills': self.total['weapon_kills'],
                'pvp_victims': self.total['pvp_victims'],
                'death_weapons': self.total['death_weapons'],
                'death_by_players': self.total['death_by_players'],
                'vehicle_kills': self.total['vehicle_kills'],
                'vehicle_losses_by_player': self.total['vehicle_losses_by_player']
            }
        }
        
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Fehler beim Speichern: {e}")
    
    def load(self):
        """Lädt Statistiken"""
        if not os.path.exists(self.stats_file):
            return
        
        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Session
            session_data = data.get('session', {})
            self.session['session_id'] = session_data.get('session_id', '')
            self.session['pve_kills'] = session_data.get('pve_kills', 0)
            self.session['pvp_kills'] = session_data.get('pvp_kills', 0)
            self.session['deaths'] = session_data.get('deaths', 0)
            self.session['weapon_kills'] = session_data.get('weapon_kills', {})
            self.session['pvp_victims'] = session_data.get('pvp_victims', {})
            self.session['death_weapons'] = session_data.get('death_weapons', {})
            self.session['death_by_players'] = session_data.get('death_by_players', {})
            self.session['vehicle_kills'] = session_data.get('vehicle_kills', {})
            self.session['vehicle_losses_by_player'] = session_data.get('vehicle_losses_by_player', {})

            # Total
            total_data = data.get('total', {})
            self.total['pve_kills'] = total_data.get('pve_kills', 0)
            self.total['pvp_kills'] = total_data.get('pvp_kills', 0)
            self.total['deaths'] = total_data.get('deaths', 0)
            self.total['weapon_kills'] = total_data.get('weapon_kills', {})
            self.total['pvp_victims'] = total_data.get('pvp_victims', {})
            self.total['death_weapons'] = total_data.get('death_weapons', {})
            self.total['death_by_players'] = total_data.get('death_by_players', {})
            self.total['vehicle_kills'] = total_data.get('vehicle_kills', {})
            self.total['vehicle_losses_by_player'] = total_data.get('vehicle_losses_by_player', {})

            # Session Start
            if 'session_start' in data:
                try:
                    self.session_start = datetime.fromisoformat(data['session_start'])
                except:
                    pass
        
        except Exception as e:
            print(f"Fehler beim Laden: {e}")