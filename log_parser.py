"""
Verse Combat Log - Log Parser v3.1
Trackt: Kills, Deaths, Vehicles, Vehicle Control
"""

import re
import os
import json
from pathlib import Path
from datetime import datetime
from collections import deque
from typing import Optional, Dict, List


class LogParser:
    """Parst Star Citizen Game.log Dateien"""
    
    # Regex Patterns
    PATTERNS = {
        'session': re.compile(r"@session:\s+'([a-f0-9\-]+)'"),
        'login_character': re.compile(r"<AccountLoginCharacterStatus_Character>.*?geid (\d+).*?name ([^\s]+)"),
        'env_session': re.compile(r"@env_session:\s+'[^-]+-[^-]+-alpha-(\d+)-(\d+)'"),
        
        # Kill Events
        'kill': re.compile(
            r"CActor::Kill: '([^']+)' \[(\d+)\].*?killed by '([^']+)' \[(\d+)\].*?"
            r"using '([^']+)' \[Class ([^\]]+)\].*?damage type '([^']+)'"
        ),
        
        # Vehicle Destruction
        'vehicle_destroy': re.compile(
            r"CVehicle::OnAdvanceDestroyLevel: Vehicle '([^']+)' \[(\d+)\].*?"
            r"advanced from destroy level (\d+) to (\d+) caused by '([^']+)' \[(\d+)\]"
        ),
        
        # Vehicle Control (Ein/Aussteigen)
        'vehicle_enter': re.compile(
            r"CVehicle::Initialize::<lambda_1>::operator \(\): Local client node \[(\d+)\].*?"
            r"granted control token for '([^']+)' \[(\d+)\]"
        ),
        'vehicle_exit': re.compile(
            r"CVehicleMovementBase::ClearDriver: Local client node \[(\d+)\].*?"
            r"releasing control token for '([^']+)' \[(\d+)\]"
        ),
        
        # Spawn Events
        'respawn': re.compile(
            r"CSCPlayerPUSpawningComponent::UnregisterFromExternalSystems: "
            r"Player '([^']+)' \[(\d+)\].*?lost reservation for spawnpoint ([^\s]+) \[(\d+)\]"
        ),
        'corpse': re.compile(
            r"\[ACTOR STATE\]\[SSCActorStateCVars::LogCorpse\] Player '([^']+)' <remote client>: "
            r"(IsCorpseEnabled: No\.|Running corpsify for corpse\.)"
        ),
        'actor_stall': re.compile(
            r"<Actor stall> Actor stall detected, Player: ([^,]+), Type: downstream"
        ),
        
        # Server Info
        'server_id': re.compile(r"Server.*?ID[:\s]+([a-f0-9\-]+)", re.IGNORECASE),
    }
    
    MAX_EVENTS = 400
    
    def __init__(self, version: str, stats_manager, config_manager, socketio):
        self.version = version
        self.stats = stats_manager
        self.config = config_manager
        self.socketio = socketio

        from utils import get_data_file_path

        self.log_path = Path(config_manager.get_log_path(version))
        self.position_file = get_data_file_path(f"log_position_{version.lower()}.json")
        self.last_position = 0
        self.session_id = None
        self.server_id = None
        self.game_version = None
        self.current_vehicle = None  # Aktuelles Fahrzeug

        # Fahrzeug-Eigentum Tracking
        # vehicle_id -> {'internal_name': str, 'last_exit': datetime, 'softdead': bool}
        self.owned_vehicles = {}

        # Event Timeline
        self.events = deque(maxlen=self.MAX_EVENTS)

        # Player Tracking
        self.players_alive = {}
        self.players_dead = {}
        self.spawn_timers = {}

        # Respawn Cooldown Tracking (verhindert doppelte Respawn-Events)
        self.last_respawn_times = {}  # player_name -> datetime

        # Datenbanken
        from weapon_database import WeaponDatabase
        from vehicle_database import VehicleDatabase
        from npc_database import NPCDatabase
        from player_database import PlayerDatabase

        self.weapon_db = WeaponDatabase()
        self.vehicle_db = VehicleDatabase()
        self.npc_db = NPCDatabase()
        self.player_db = PlayerDatabase(f"players_db_{version.lower()}.json")

        # Bereinige player_db: Entferne eigenen Spieler falls vorhanden
        self._cleanup_own_player()

        # Lade letzte Position
        self._load_position()
    
    def initial_scan(self):
        """Initiales vollständiges Scannen der Log-Datei"""
        if not self.log_path.exists():
            self.add_event('error', f'Log-Datei nicht gefunden: {self.log_path}')
            return

        try:
            with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Header (erste 500 Zeilen) - immer parsen für Session/Version/Player Info
                for i in range(500):
                    line = f.readline()
                    if not line:
                        break
                    self._parse_header_line(line)

                # Wenn Position wiederhergestellt wurde, springe dorthin
                if self.last_position > 0:
                    f.seek(self.last_position)
                    self.add_event('info', message=f'[{self.version}] Fortsetzen ab Position {self.last_position}',
                          message_key='events.session_resumed',
                          params={'version': self.version, 'last_position': self.last_position})
                    line_count = 0
                else:
                    # Komplettes Scannen von Anfang
                    f.seek(0)
                    self.add_event('info', message=f'[{self.version}] Starte vollständiges Scannen',
                          message_key='events.session_full_scan',
                          params={'version': self.version})
                    line_count = 0

                    for line in f:
                        self._parse_line(line)
                        line_count += 1

                    self.last_position = f.tell()
                    self.add_event('info', message=f'[{self.version}] Initiales Scannen: {line_count} Zeilen',
                          message_key='events.initial_scan',
                          params={'version': self.version, 'line_count': line_count})

                # Speichere Position
                self._save_position()

        except Exception as e:
            self.add_event('error', f'Fehler beim initialen Scannen: {e}')
    
    def _parse_header_line(self, line: str):
        """Parst Header-Zeilen"""
        # Session ID
        match = self.PATTERNS['session'].search(line)
        if match:
            new_session_id = match.group(1)
            if self.session_id != new_session_id:
                self.session_id = new_session_id

                # Prüfe ob Session-Wechsel (nicht initiales Laden)
                stored_session_id = self.stats.get_session_id()
                if stored_session_id and stored_session_id != new_session_id:
                    # Session hat gewechselt - frage Benutzer
                    print(f"[{self.version}] Session-Wechsel erkannt: {stored_session_id[:8]}... -> {new_session_id[:8]}...")
                    self.socketio.emit('session_changed', {
                        'version': self.version,
                        'old_session_id': stored_session_id,
                        'new_session_id': new_session_id
                    })
                    # Warte NICHT auf Antwort hier - wird asynchron behandelt
                else:
                    # Erste Session oder gleiches Game - einfach setzen
                    self.stats.set_session_id(new_session_id)

                self.add_event('info', f'Session: {new_session_id[:8]}...')

        # Game Version und Build aus @env_session
        match = self.PATTERNS['env_session'].search(line)
        if match:
            version_raw = match.group(1)  # z.B. "432"
            build = match.group(2)  # z.B. "10452200"

            # Formatiere Version (432 -> 4.3.2)
            version_formatted = f"{version_raw[0]}.{version_raw[1]}.{version_raw[2]}"
            self.game_version = f"{version_formatted} (Build {build})"
            self.config.set_game_version(self.version, self.game_version)
        
        # Player Info
        match = self.PATTERNS['login_character'].search(line)
        if match:
            player_id = match.group(1)
            player_name = match.group(2)
            self.config.set_player_info(self.version, player_name, player_id)
            self.add_event('player',
                          message=f'👤 {player_name} [ID: {player_id}]',
                          message_key='events.player_identified',
                          params={'player': player_name, 'id': player_id})
            
            self.socketio.emit('player_info_updated', {
                'version': self.version,
                'name': player_name,
                'id': player_id,
                'game_version': self.game_version,
                'current_vehicle': self.current_vehicle
            })
    
    def parse_new_lines(self):
        """Parst neue Zeilen"""
        if not self.log_path.exists():
            return
        
        try:
            file_size = self.log_path.stat().st_size
            
            if file_size < self.last_position:
                self.last_position = 0
                self.initial_scan()
                return
            
            with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self.last_position)
                new_lines = f.readlines()
                self.last_position = f.tell()

                for line in new_lines:
                    self._parse_line(line)

                # Speichere Position nach dem Parsen
                if new_lines:
                    self._save_position()

        except Exception as e:
            print(f"Fehler beim Parsen: {e}")
    
    def _parse_line(self, line: str):
        """Parst eine einzelne Log-Zeile"""
        timestamp = self._extract_timestamp(line)
        
        if not self.session_id or not self.game_version:
            self._parse_header_line(line)
        
        # Kill Events
        self._parse_kill_event(line, timestamp)
        
        # Vehicle Events
        self._parse_vehicle_destruction(line, timestamp)
        self._parse_vehicle_control(line, timestamp)
        
        # Spawn Events
        self._parse_spawn_events(line)
    
    def _extract_timestamp(self, line: str) -> Optional[datetime]:
        """Extrahiert Timestamp"""
        match = re.match(r'<(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)>', line)
        if match:
            try:
                return datetime.fromisoformat(match.group(1).replace('Z', '+00:00'))
            except:
                pass
        return None
    
    def _parse_kill_event(self, line: str, timestamp: Optional[datetime]):
        """Parst Kill/Death Events"""
        match = self.PATTERNS['kill'].search(line)
        if not match:
            return
        
        victim_name = match.group(1)
        victim_id = match.group(2)
        killer_name = match.group(3)
        killer_id = match.group(4)
        weapon_full = match.group(5)
        weapon_class = match.group(6)
        damage_type = match.group(7)

        player_id = self.config.get_player_id(self.version)
        if not player_id:
            return

        # Waffenname bestimmen
        # Bei Class unknown: Prüfe ob weapon_full eine echte Waffe enthält
        # Fälle: VehicleDestruction, Explosion, etc.
        if weapon_class.lower() == 'unknown':
            if weapon_full and weapon_full.lower() not in ['unknown', '0', '']:
                # weapon_full enthält echte Waffe -> verwende diese
                # Beispiele:
                # - GLSN_BallisticGatling_S4_7376494911512 (VehicleDestruction)
                # - lbco_sniper_energy_01_7299497977400 (Explosion)
                weapon_internal = self.weapon_db.normalize_weapon_name(weapon_full)
            elif damage_type:
                # Kein weapon_full -> verwende damage_type als Fallback
                weapon_internal = damage_type
            else:
                weapon_internal = 'unknown'
        else:
            weapon_internal = weapon_class

        if self.weapon_db.is_blacklisted(weapon_internal):
            return
        
        # Suicide
        if victim_id == killer_id == player_id:
            self.stats.add_death(weapon_internal, None)
            weapon_display = self.weapon_db.get_display_name(weapon_internal)
            self.add_event('death',
                          message=f'💀 Suicide mit {weapon_display}',
                          message_key='events.suicide',
                          params={'weapon': weapon_display})
            self._send_stats_update()
            return
        
        # Eigener Kill
        if killer_id == player_id and victim_id != player_id:
            # Prüfe ob Opfer ein ARGO_ATLS Exoskelett ist
            if victim_name.startswith('ARGO_ATLS'):
                # Als Fahrzeugabschuss behandeln
                vehicle_internal = self.vehicle_db.normalize_vehicle_name(victim_name)
                vehicle_display = self.vehicle_db.get_display_name(vehicle_internal)
                vehicle_parent = self.vehicle_db.get_parent_vehicle(vehicle_internal)
                # Verwende parent_vehicle für Statistik (Aggregation)
                self.stats.add_vehicle_kill(vehicle_parent)
                self.add_event('vehicle',
                              message=f'🚀 {vehicle_display} zerstört',
                              message_key='events.vehicle_destroyed',
                              params={'vehicle': vehicle_display})
                self._send_stats_update()
                return

            is_pvp = not self.npc_db.is_npc(victim_name)
            self.stats.add_kill(is_pvp, weapon_internal, victim_name if is_pvp else None)

            # Player Database Update (nur bei PvP)
            if is_pvp:
                self.player_db.add_kill_by_me(victim_name, weapon_internal)

            weapon_display = self.weapon_db.get_display_name(weapon_internal)
            if is_pvp:
                self.add_event('pvp_kill',
                              message=f'🎯 {victim_name} mit {weapon_display}',
                              message_key='events.pvp_kill',
                              params={'victim': victim_name, 'weapon': weapon_display})
            else:
                self.add_event('pve_kill',
                              message=f'⚔️  PvE Kill mit {weapon_display}',
                              message_key='events.pve_kill',
                              params={'weapon': weapon_display})

            self._send_stats_update()
            return
        
        # Eigener Tod
        if victim_id == player_id and killer_id != player_id:
            # Prüfe ob Umwelttod (alle 4 Kriterien müssen zutreffen)
            is_environmental_death = (
                killer_name.lower() == "unknown" and
                killer_id == "0" and
                weapon_class.lower() == "unknown" and
                damage_type.lower() == "hazard"
            )

            if is_environmental_death:
                # Umwelttod - als PvE zählen
                is_killer_player = False
                killer = None
            else:
                # Normaler Tod - prüfe ob Killer ein Spieler ist
                is_killer_player = not self.npc_db.is_npc(killer_name)
                killer = killer_name if is_killer_player else None

            self.stats.add_death(weapon_internal, killer)

            # Player Database Update (nur bei Spieler-Killer)
            if is_killer_player:
                self.player_db.add_death_by_them(killer_name, weapon_internal)

            weapon_display = self.weapon_db.get_display_name(weapon_internal)
            if is_killer_player:
                self.add_event('death',
                              message=f'💀 Getötet von {killer_name} mit {weapon_display}',
                              message_key='events.death_by_player',
                              params={'killer': killer_name, 'weapon': weapon_display})
            elif is_environmental_death:
                self.add_event('death',
                              message=f'💀 Getötet durch Umwelteinflüsse ({weapon_display})',
                              message_key='events.death_environmental',
                              params={'weapon': weapon_display})
            else:
                self.add_event('death',
                              message=f'💀 Getötet durch NPC mit {weapon_display}',
                              message_key='events.death_by_npc',
                              params={'weapon': weapon_display})

            self._send_stats_update()
    
    def _parse_vehicle_destruction(self, line: str, timestamp: Optional[datetime]):
        """Parst Fahrzeugzerstörung"""
        match = self.PATTERNS['vehicle_destroy'].search(line)
        if not match:
            return
        
        vehicle_full_name = match.group(1)
        vehicle_id = match.group(2)
        from_level = int(match.group(3))
        to_level = int(match.group(4))
        caused_by = match.group(5)
        caused_by_id = match.group(6)
        
        player_id = self.config.get_player_id(self.version)
        
        # Status bestimmen
        if to_level == 1:
            status = "Softdead"
        elif to_level == 2:
            status = "Fulldead"
        else:
            status = f"Level {to_level}"
        
        # Normalisiere Fahrzeugname (ohne ID)
        vehicle_internal = self.vehicle_db.normalize_vehicle_name(vehicle_full_name)
        vehicle_display = self.vehicle_db.get_display_name(vehicle_internal)

        # Hole Parent-Vehicle für Statistik-Aggregation
        vehicle_parent = self.vehicle_db.get_parent_vehicle(vehicle_internal)

        # Prüfe ob eigenes Fahrzeug
        is_own_vehicle = vehicle_id in self.owned_vehicles

        # Softdead zählt als Kill
        if to_level == 1:  # Softdead
            if caused_by_id == player_id and not is_own_vehicle:
                # Eigener Kill an fremdem Fahrzeug
                # Verwende parent_vehicle für Statistik (Aggregation)
                self.stats.add_vehicle_kill(vehicle_parent)
                self.add_event('vehicle',
                              message=f'🚀 {vehicle_display} zerstört',
                              message_key='events.vehicle_destroyed',
                              params={'vehicle': vehicle_display})
                self._send_stats_update()
            elif is_own_vehicle:
                # Eigenes Fahrzeug wurde zerstört
                # Prüfe wer es zerstört hat (NPC, PDC oder Spieler)
                if self.npc_db.is_npc(caused_by):
                    # NPC oder PDC
                    if '_PDC_' in caused_by:
                        destroyer_display = 'PDC'
                    else:
                        destroyer_display = 'NPC'
                    self.add_event('vehicle-ownSD',
                                  message=f'💥 Eigenes Fahrzeug {vehicle_display} ist Softdead (durch {destroyer_display})',
                                  message_key='events.own_vehicle_softdead',
                                  params={'vehicle': vehicle_display, 'destroyer': destroyer_display})
                else:
                    # Spieler
                    self.add_event('vehicle-ownSD',
                                  message=f'💥 Eigenes Fahrzeug {vehicle_display} ist Softdead (durch {caused_by})',
                                  message_key='events.own_vehicle_softdead',
                                  params={'vehicle': vehicle_display, 'destroyer': caused_by})
                    # Tracking: Wer hat mein Fahrzeug zerstört?
                    # Verwende parent_vehicle für Statistik (Aggregation)
                    self.stats.add_vehicle_loss(vehicle_parent, caused_by)
                    # Player Database Update
                    self.player_db.add_my_vehicle_destroyed_by_them(caused_by, vehicle_parent)
                    self._send_stats_update()

                # Markiere als Softdead
                self.owned_vehicles[vehicle_id]['softdead'] = True
            else:
                # Anderes Fahrzeug
                # Prüfe wer es zerstört hat (NPC, PDC oder Spieler)
                if self.npc_db.is_npc(caused_by):
                    # NPC oder PDC
                    if '_PDC_' in caused_by:
                        destroyer_display = 'PDC'
                    else:
                        destroyer_display = 'NPC'
                    self.add_event('vehicle',
                                  message=f'🚀 {vehicle_display} ist {status} (durch {destroyer_display})',
                                  message_key='events.vehicle_softdead',
                                  params={'vehicle': vehicle_display, 'status': status, 'destroyer': destroyer_display})
                else:
                    # Spieler
                    self.add_event('vehicle',
                                  message=f'🚀 {vehicle_display} ist {status} (durch {caused_by})',
                                  message_key='events.vehicle_softdead',
                                  params={'vehicle': vehicle_display, 'status': status, 'destroyer': caused_by})

        elif to_level == 2:  # Fulldead
            if is_own_vehicle and not self.owned_vehicles[vehicle_id].get('softdead', False):
                # Eigenes Fahrzeug direkt zu Fulldead ohne Softdead
                # Prüfe wer es zerstört hat (NPC, PDC oder Spieler)
                if self.npc_db.is_npc(caused_by):
                    # NPC oder PDC
                    if '_PDC_' in caused_by:
                        destroyer_display = 'PDC'
                    else:
                        destroyer_display = 'NPC'
                    self.add_event('vehicle-ownFD',
                                  message=f'💥 Eigenes Fahrzeug {vehicle_display} zerstört (durch {destroyer_display})',
                                  message_key='events.own_vehicle_fulldead',
                                  params={'vehicle': vehicle_display, 'destroyer': destroyer_display})
                else:
                    # Spieler
                    self.add_event('vehicle-ownFD',
                                  message=f'💥 Eigenes Fahrzeug {vehicle_display} zerstört (durch {caused_by})',
                                  message_key='events.own_vehicle_fulldead',
                                  params={'vehicle': vehicle_display, 'destroyer': caused_by})
                del self.owned_vehicles[vehicle_id]
            elif is_own_vehicle:
                # War bereits Softdead, jetzt Fulldead
                self.add_event('vehicle-ownFD',
                              message=f'🔥 {vehicle_display} ist Fulldead',
                              message_key='events.own_vehicle_fulldead_final',
                              params={'vehicle': vehicle_display})
                del self.owned_vehicles[vehicle_id]
            else:
                # Fremdes Fahrzeug Fulldead (nur Timeline-Erwähnung wenn nicht schon bei Softdead gezählt)
                self.add_event('vehicle',
                              message=f'🔥 {vehicle_display} ist Fulldead',
                              message_key='events.vehicle_fulldead',
                              params={'vehicle': vehicle_display})

        self.socketio.emit('vehicle_destroyed', {
            'version': self.version,
            'vehicle': vehicle_display,
            'status': status,
            'caused_by': caused_by,
            'is_own': is_own_vehicle
        })
    
    def _parse_vehicle_control(self, line: str, timestamp: Optional[datetime]):
        """Parst Vehicle Control (Ein/Aussteigen)"""
        player_id = self.config.get_player_id(self.version)
        if not player_id:
            return
        
        # Einsteigen
        match = self.PATTERNS['vehicle_enter'].search(line)
        if match:
            client_id = match.group(1)
            vehicle_full_name = match.group(2)
            vehicle_id = match.group(3)

            if client_id == player_id:
                vehicle_internal = self.vehicle_db.normalize_vehicle_name(vehicle_full_name)
                vehicle_display = self.vehicle_db.get_display_name(vehicle_internal)

                self.current_vehicle = vehicle_display
                self.add_event('vehicle-mount',
                              message=f'🚁 Eingestiegen in {vehicle_display}',
                              message_key='events.vehicle_mount',
                              params={'vehicle': vehicle_display})

                # Registriere Fahrzeug-Eigentum
                current_time = timestamp or datetime.now()

                # Prüfe 45-Minuten-Timeout für bereits registrierte Fahrzeuge
                self._cleanup_expired_vehicles(current_time)

                # Registriere oder aktualisiere Fahrzeug-Eigentum
                self.owned_vehicles[vehicle_id] = {
                    'internal_name': vehicle_internal,
                    'last_exit': None,
                    'softdead': False
                }

                # Update Player Info
                player_info = self.config.get_player_info(self.version)
                self.socketio.emit('player_info_updated', {
                    'version': self.version,
                    'name': player_info.get('name'),
                    'id': player_info.get('id'),
                    'game_version': self.game_version,
                    'current_vehicle': vehicle_display
                })
        
        # Aussteigen
        match = self.PATTERNS['vehicle_exit'].search(line)
        if match:
            client_id = match.group(1)
            vehicle_full_name = match.group(2)
            vehicle_id = match.group(3)

            if client_id == player_id:
                vehicle_internal = self.vehicle_db.normalize_vehicle_name(vehicle_full_name)
                vehicle_display = self.vehicle_db.get_display_name(vehicle_internal)

                self.current_vehicle = None
                self.add_event('vehicle-mount',
                              message=f'🚪 Ausgestiegen aus {vehicle_display}',
                              message_key='events.vehicle_dismount',
                              params={'vehicle': vehicle_display})

                # Markiere Ausstiegszeit für 45-Minuten-Timeout
                if vehicle_id in self.owned_vehicles:
                    self.owned_vehicles[vehicle_id]['last_exit'] = timestamp or datetime.now()

                # Update Player Info
                player_info = self.config.get_player_info(self.version)
                self.socketio.emit('player_info_updated', {
                    'version': self.version,
                    'name': player_info.get('name'),
                    'id': player_info.get('id'),
                    'game_version': self.game_version,
                    'current_vehicle': None
                })
    
    def _parse_spawn_events(self, line: str):
        """Parst Spawn Events"""
        player_name_local = self.config.get_player_name(self.version)
        if not player_name_local:
            return

        # Respawn Detection
        match = self.PATTERNS['respawn'].search(line)
        if match:
            player_name = match.group(1)
            spawnpoint_name = match.group(3)

            # Ignoriere eigenen Spieler
            if player_name == player_name_local:
                return

            # Ignoriere wenn Spawnpoint "Unknown" ist
            if spawnpoint_name.lower() == 'unknown':
                return

            # Prüfe 30-Sekunden-Cooldown (verhindert doppelte Respawn-Events)
            current_time = datetime.now()
            if player_name in self.last_respawn_times:
                time_diff = (current_time - self.last_respawn_times[player_name]).total_seconds()
                if time_diff < 30:
                    return  # Ignoriere Duplikat innerhalb von 30 Sekunden

            # Speichere Zeitpunkt und zeige Event
            self.last_respawn_times[player_name] = current_time
            self.add_event('spawn',
                          message=f'🔄 {player_name} ist respawnt in {spawnpoint_name}',
                          message_key='events.player_respawn',
                          params={'player': player_name, 'location': spawnpoint_name})
            return

        # Corpse Detection
        match = self.PATTERNS['corpse'].search(line)
        if match:
            player_name = match.group(1)

            # Ignoriere eigenen Spieler
            if player_name == player_name_local:
                return

            # Zeige Corpse in Timeline
            self.add_event('corpse',
                          message=f'☠️ {player_name}\'s Körper hat nun Leichenstatus',
                          message_key='events.player_corpse',
                          params={'player': player_name})
            return

        # Actor Stall Detection (Spieler in der Nähe gesichtet)
        match = self.PATTERNS['actor_stall'].search(line)
        if match:
            player_name = match.group(1)

            # Ignoriere eigenen Spieler
            if player_name == player_name_local:
                return

            # Zeige in Timeline
            self.add_event('player_spotted',
                          message=f'👁️ {player_name} wurde in der Umgebung gesichtet',
                          message_key='events.player_spotted',
                          params={'player': player_name})
    
    def check_server_swap(self) -> bool:
        """Prüft auf Server-Wechsel"""
        current_server = self._get_current_server_id()
        
        if current_server and self.server_id and current_server != self.server_id:
            self.add_event('server',
                          message=f'🔄 Server-Swap erkannt',
                          message_key='events.server_swap')
            
            self.stats.merge_session_to_total()
            self.stats.reset_session(remove_from_total=False)
            
            self.server_id = current_server
            
            self.players_alive.clear()
            self.players_dead.clear()
            self.spawn_timers.clear()
            self.current_vehicle = None
            
            return True
        
        return False
    
    def _get_current_server_id(self) -> Optional[str]:
        """Liest aktuelle Server-ID"""
        if not self.log_path.exists():
            return None
        
        try:
            with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(0, 2)
                file_size = f.tell()
                
                seek_pos = max(0, file_size - 50000)
                f.seek(seek_pos)
                
                lines = f.readlines()[-100:]
                
                for line in reversed(lines):
                    match = self.PATTERNS['server_id'].search(line)
                    if match:
                        return match.group(1)
        except:
            pass
        
        return None
    
    def add_event(self, event_type: str, message: str = None, with_timer: bool = False, player_id: str = None, message_key: str = None, params: dict = None):
        """Fügt Event zur Timeline hinzu

        Args:
            event_type: Typ des Events
            message: Fallback-Message (für Abwärtskompatibilität)
            with_timer: Ob ein Timer angezeigt werden soll
            player_id: Player ID für Timer
            message_key: i18n-Key für Übersetzung (z.B. 'events.pvp_kill')
            params: Parameter für die Übersetzung (z.B. {'victim': 'PlayerName', 'weapon': 'Shotgun'})
        """
        event = {
            'type': event_type,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'with_timer': with_timer,
            'player_id': player_id,
            'timer_start': self.spawn_timers.get(player_id).isoformat() if player_id and player_id in self.spawn_timers else None
        }

        # Füge i18n-Daten hinzu wenn vorhanden
        if message_key:
            event['message_key'] = message_key
        if params:
            event['params'] = params

        self.events.append(event)

        self.socketio.emit('new_event', {
            'version': self.version,
            'event': event
        })
    
    def get_recent_events(self, count: int = 50) -> List[Dict]:
        """Gibt letzte Events zurück"""
        return list(self.events)[-count:]
    
    def _send_stats_update(self):
        """Sendet Stats-Update"""
        self.socketio.emit('stats_updated', {
            'version': self.version,
            'stats': self.stats.get_all_stats()
        })

    def _load_position(self):
        """Lädt letzte Position"""
        if not os.path.exists(self.position_file):
            return

        try:
            with open(self.position_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            saved_position = data.get('last_position', 0)

            # Prüfe ob Log-Datei existiert und Position gültig ist
            if self.log_path.exists():
                current_size = self.log_path.stat().st_size

                if current_size >= saved_position:
                    # Log-Datei ist gleich oder größer -> Position wiederherstellen
                    self.last_position = saved_position
                    print(f"[{self.version}] Position wiederhergestellt: {saved_position} bytes")
                else:
                    # Log-Datei ist kleiner -> wurde neu erstellt
                    print(f"[{self.version}] Log-Datei wurde neu erstellt, starte von vorne")
            else:
                print(f"[{self.version}] Log-Datei nicht gefunden")

        except Exception as e:
            print(f"[{self.version}] Fehler beim Laden der Position: {e}")

    def _save_position(self):
        """Speichert aktuelle Position (ohne log_path - wird in config gespeichert)"""
        try:
            data = {
                'last_position': self.last_position,
                'last_updated': datetime.now().isoformat()
            }

            with open(self.position_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"[{self.version}] Fehler beim Speichern der Position: {e}")

    def _cleanup_own_player(self):
        """
        Entfernt den eigenen Spieler aus der player_database falls vorhanden.
        Der eigene Spieler sollte nicht in der DB sein, da er keine Interaktionen mit sich selbst hat.
        """
        own_player_name = self.config.get_player_name(self.version)
        if own_player_name and own_player_name in self.player_db.players:
            self.player_db.remove_player(own_player_name)
            print(f"[{self.version}] Eigener Spieler '{own_player_name}' aus player_db entfernt")

    def _cleanup_expired_vehicles(self, current_time: datetime):
        """Entfernt Fahrzeuge die länger als 45 Minuten nicht benutzt wurden"""
        from datetime import timedelta

        timeout = timedelta(minutes=45)
        expired_ids = []

        for vehicle_id, data in self.owned_vehicles.items():
            last_exit = data.get('last_exit')
            # Wenn ausgestiegen und mehr als 45 Minuten vergangen
            if last_exit and (current_time - last_exit) > timeout:
                expired_ids.append(vehicle_id)

        for vehicle_id in expired_ids:
            del self.owned_vehicles[vehicle_id]

        if expired_ids:
            print(f"[{self.version}] {len(expired_ids)} Fahrzeug-Eigentum(e) nach 45min Timeout entfernt")