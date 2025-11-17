"""
Verse Combat Log v1.1
Main Flask Application
"""

import sys
import io

# Prüfe --debug Argument GANZ am Anfang (vor allen Imports)
DEBUG_MODE = '--debug' in sys.argv

# Bei Debug in EXE: Konsole sofort allozieren
if DEBUG_MODE and getattr(sys, 'frozen', False) and sys.stdout is None:
    import ctypes
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.AllocConsole()
    # Leite stdout/stderr zur neuen Konsole um
    sys.stdout = open('CONOUT$', 'w', encoding='utf-8', buffering=1)
    sys.stderr = sys.stdout

# Sichere Print-Funktion für EXE ohne Konsole
import builtins
_original_print = builtins.print

def safe_print(*args, **kwargs):
    """Print, der auch ohne Konsole funktioniert"""
    try:
        if sys.stdout is not None:
            _original_print(*args, **kwargs, flush=True)
    except:
        pass

# Überschreibe built-in print GLOBAL für alle Module
builtins.print = safe_print
print = safe_print

# UTF-8 Encoding für Windows-Konsole (nur wenn stdout/stderr existieren)
if sys.platform == 'win32' and sys.stdout is not None and not DEBUG_MODE:
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

# Gevent monkey patching VOR allen anderen Imports (für Production Server)
# WICHTIG: Nicht threading patchen, da pywebview das braucht
from gevent import monkey
monkey.patch_all(thread=False, select=False)

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import json
import os
import threading
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
from log_parser import LogParser
from stats_manager import StatsManager
from config_manager import ConfigManager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'verse-combat-log-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# Globale Instanzen
config_manager = ConfigManager()
stats_managers = {}
log_parsers = {}
monitoring_threads = {}
monitoring_active = {}

# Initialisiere für alle Versionen
for version in config_manager.get_versions():
    stats_managers[version] = StatsManager(version)
    log_parsers[version] = LogParser(
        version=version,
        stats_manager=stats_managers[version],
        config_manager=config_manager,
        socketio=socketio
    )
    monitoring_active[version] = False

current_version = config_manager.get_current_version()


@app.route('/')
def index():
    """Hauptseite"""
    return render_template('index.html')


@app.route('/loading')
def loading():
    """Ladebildschirm"""
    status = request.args.get('status', 'loading')
    message = request.args.get('message', 'Initialisiere...')
    return render_template('loading.html', status=status, message=message)


@app.route('/api/config')
def get_config():
    """Gibt Konfiguration zurück"""
    return jsonify({
        'versions': config_manager.get_versions(),
        'current_version': config_manager.get_current_version(),
        'log_paths': config_manager.get_log_paths(),
        'player_info': config_manager.get_player_info(current_version),
        'language': config_manager.get_language()
    })


@app.route('/api/update_status')
def get_update_status():
    """Gibt Update-Status zurück"""
    # Update läuft immer im Hintergrund beim Start, daher immer False zurückgeben
    return jsonify({
        'updating': False
    })


@app.route('/api/config/version', methods=['POST'])
def switch_version():
    """Wechselt Version"""
    global current_version
    data = request.json
    new_version = data.get('version')

    if new_version in config_manager.get_versions():
        old_version = current_version
        current_version = new_version
        config_manager.set_current_version(new_version)

        # Stoppe Monitoring der alten Version
        if old_version in monitoring_active:
            stop_monitoring(old_version)

        # Starte Monitoring der neuen Version
        log_path = config_manager.get_log_path(new_version)
        if log_path and Path(log_path).exists():
            if new_version not in monitoring_active or not monitoring_active[new_version]:
                print(f"[{new_version}] Starte Monitoring...")
                monitoring_active[new_version] = True
                thread = threading.Thread(target=monitor_log, args=(new_version,), daemon=True)
                monitoring_threads[new_version] = thread
                thread.start()

        socketio.emit('version_changed', {'version': new_version})

        # Sende SC-Status für neue Version
        sc_running = is_star_citizen_running()
        socketio.emit('sc_status_changed', {
            'running': sc_running,
            'version': new_version
        })

        return jsonify({'success': True, 'version': new_version})

    return jsonify({'success': False, 'error': 'Invalid version'}), 400


@app.route('/api/config/log_path', methods=['POST'])
def update_log_path():
    """Aktualisiert Log-Pfad und erstellt Parser neu"""
    data = request.json
    version = data.get('version')
    path = data.get('path')

    if version and path:
        # Speichere neuen Pfad
        config_manager.set_log_path(version, path)

        # Erstelle Parser mit neuem Pfad neu
        log_parsers[version] = LogParser(
            version=version,
            stats_manager=stats_managers[version],
            config_manager=config_manager,
            socketio=socketio
        )

        print(f"[{version}] Parser mit neuem Pfad erstellt: {path}")

        return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Invalid data'}), 400


@app.route('/api/config/language', methods=['POST'])
def update_language():
    """Aktualisiert Sprache"""
    data = request.json
    language = data.get('language')

    if language and language in ['de', 'en']:
        config_manager.set_language(language)
        print(f"Sprache geändert zu: {language}")
        return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Invalid language'}), 400


@app.route('/api/stats/<version>')
def get_stats(version):
    """Gibt Statistiken zurück"""
    if version not in stats_managers:
        return jsonify({'error': 'Invalid version'}), 400

    from weapon_database import WeaponDatabase
    from vehicle_database import VehicleDatabase

    weapon_db = WeaponDatabase()
    vehicle_db = VehicleDatabase()

    # Stats enthalten INTERNE Namen
    stats = stats_managers[version].get_all_stats()

    # Konvertiere interne Namen zu Display-Namen
    for stats_type in ['session', 'total']:
        if stats_type in stats:
            # Waffen-Kills
            if 'weapon_kills' in stats[stats_type]:
                stats[stats_type]['weapon_kills'] = {
                    weapon_db.get_display_name(internal): count
                    for internal, count in stats[stats_type]['weapon_kills'].items()
                }

            # Death-Waffen
            if 'death_weapons' in stats[stats_type]:
                stats[stats_type]['death_weapons'] = {
                    weapon_db.get_display_name(internal): count
                    for internal, count in stats[stats_type]['death_weapons'].items()
                }

            # Fahrzeug-Kills
            if 'vehicle_kills' in stats[stats_type]:
                stats[stats_type]['vehicle_kills'] = {
                    vehicle_db.get_display_name(internal): count
                    for internal, count in stats[stats_type]['vehicle_kills'].items()
                }

            # PvP Victims Waffen
            if 'pvp_victims' in stats[stats_type]:
                stats[stats_type]['pvp_victims'] = {
                    victim: [weapon_db.get_display_name(w) for w in weapons]
                    for victim, weapons in stats[stats_type]['pvp_victims'].items()
                }

            # Fahrzeugverluste durch Spieler
            if 'vehicle_losses_by_player' in stats[stats_type]:
                stats[stats_type]['vehicle_losses_by_player'] = {
                    player: {
                        vehicle_db.get_display_name(vehicle_internal): count
                        for vehicle_internal, count in vehicles.items()
                    }
                    for player, vehicles in stats[stats_type]['vehicle_losses_by_player'].items()
                }

    return jsonify(stats)


@app.route('/api/stats/<version>/reset_session', methods=['POST'])
def reset_session(version):
    """Setzt Session zurück"""
    if version not in stats_managers:
        return jsonify({'error': 'Invalid version'}), 400
    
    data = request.json
    remove_from_total = data.get('remove_from_total', False)
    
    stats_managers[version].reset_session(remove_from_total)
    
    socketio.emit('stats_updated', {
        'version': version,
        'stats': stats_managers[version].get_all_stats()
    })
    
    return jsonify({'success': True})


@app.route('/api/events/<version>')
def get_events(version):
    """Gibt Events zurück"""
    if version not in log_parsers:
        return jsonify({'error': 'Invalid version'}), 400
    
    return jsonify({
        'events': log_parsers[version].get_recent_events(50)
    })


@app.route('/api/weapons')
def get_weapons():
    """Gibt Waffen-Datenbank zurück"""
    from weapon_database import WeaponDatabase
    weapon_db = WeaponDatabase()

    # Sammle alle verwendeten Waffen aus allen Stats
    used_weapons = set()
    for stats_mgr in stats_managers.values():
        all_stats = stats_mgr.get_all_stats()
        # Aus weapon_kills
        used_weapons.update(all_stats['session']['weapon_kills'].keys())
        used_weapons.update(all_stats['total']['weapon_kills'].keys())
        # Aus death_weapons
        used_weapons.update(all_stats['session']['death_weapons'].keys())
        used_weapons.update(all_stats['total']['death_weapons'].keys())

    return jsonify({
        'weapons': weapon_db.get_all_weapons(list(used_weapons)),
        'blacklist': weapon_db.get_blacklist(),
        'custom_names': weapon_db.custom_names
    })


@app.route('/api/weapons/update', methods=['POST'])
def update_weapon():
    """Aktualisiert Waffennamen"""
    from weapon_database import WeaponDatabase
    weapon_db = WeaponDatabase()
    
    data = request.json
    internal_name = data.get('internal_name')
    display_name = data.get('display_name')
    
    if internal_name and display_name:
        weapon_db.set_custom_name(internal_name, display_name)
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 400


@app.route('/api/weapons/blacklist', methods=['POST'])
def toggle_weapon_blacklist():
    """Togglet Blacklist"""
    from weapon_database import WeaponDatabase
    weapon_db = WeaponDatabase()

    data = request.json
    internal_name = data.get('internal_name')
    blacklisted = data.get('blacklisted')

    if internal_name is not None:
        if blacklisted:
            weapon_db.add_to_blacklist(internal_name)
        else:
            weapon_db.remove_from_blacklist(internal_name)
        return jsonify({'success': True})

    return jsonify({'success': False}), 400


@app.route('/api/weapons/custom', methods=['POST'])
def add_weapon_custom():
    """Fügt Custom-Waffennamen hinzu"""
    from weapon_database import WeaponDatabase
    weapon_db = WeaponDatabase()

    data = request.json
    internal_name = data.get('internal_name')
    display_name = data.get('display_name')

    if internal_name and display_name:
        weapon_db.set_custom_name(internal_name, display_name)
        return jsonify({'success': True})

    return jsonify({'success': False}), 400


@app.route('/api/weapons/custom', methods=['DELETE'])
def delete_weapon_custom():
    """Löscht Custom-Waffennamen"""
    from weapon_database import WeaponDatabase
    weapon_db = WeaponDatabase()

    data = request.json
    internal_name = data.get('internal_name')

    if internal_name and internal_name in weapon_db.custom_names:
        del weapon_db.custom_names[internal_name]
        weapon_db.save()
        return jsonify({'success': True})

    return jsonify({'success': False}), 400


@app.route('/api/vehicles')
def get_vehicles():
    """Gibt Fahrzeug-Datenbank zurück"""
    from vehicle_database import VehicleDatabase
    vehicle_db = VehicleDatabase()

    # Sammle alle verwendeten Fahrzeuge aus allen Stats
    used_vehicles = set()
    for stats_mgr in stats_managers.values():
        all_stats = stats_mgr.get_all_stats()
        # Aus vehicle_kills
        used_vehicles.update(all_stats['session']['vehicle_kills'].keys())
        used_vehicles.update(all_stats['total']['vehicle_kills'].keys())

    return jsonify({
        'vehicles': vehicle_db.get_all_vehicles(list(used_vehicles)),
        'custom_names': vehicle_db.custom_names,
        'parent_vehicles': vehicle_db.parent_vehicles
    })


@app.route('/api/vehicles/update', methods=['POST'])
def update_vehicle():
    """Aktualisiert Fahrzeugnamen"""
    from vehicle_database import VehicleDatabase
    vehicle_db = VehicleDatabase()

    data = request.json
    internal_name = data.get('internal_name')
    display_name = data.get('display_name')

    if internal_name and display_name:
        vehicle_db.set_custom_name(internal_name, display_name)
        return jsonify({'success': True})

    return jsonify({'success': False}), 400


@app.route('/api/vehicles/custom', methods=['POST'])
def add_vehicle_custom():
    """Fügt Custom-Fahrzeugnamen hinzu"""
    from vehicle_database import VehicleDatabase
    vehicle_db = VehicleDatabase()

    data = request.json
    internal_name = data.get('internal_name')
    display_name = data.get('display_name')

    if internal_name and display_name:
        vehicle_db.set_custom_name(internal_name, display_name)
        return jsonify({'success': True})

    return jsonify({'success': False}), 400


@app.route('/api/vehicles/custom', methods=['DELETE'])
def delete_vehicle_custom():
    """Löscht Custom-Fahrzeugnamen"""
    from vehicle_database import VehicleDatabase
    vehicle_db = VehicleDatabase()

    data = request.json
    internal_name = data.get('internal_name')

    if internal_name and internal_name in vehicle_db.custom_names:
        del vehicle_db.custom_names[internal_name]
        vehicle_db.save()
        return jsonify({'success': True})

    return jsonify({'success': False}), 400


@app.route('/api/vehicles/parent', methods=['POST'])
def set_vehicle_parent():
    """Setzt Parent-Vehicle für Statistik-Aggregation"""
    from vehicle_database import VehicleDatabase
    vehicle_db = VehicleDatabase()

    data = request.json
    internal_name = data.get('internal_name')
    parent_name = data.get('parent_name', '')

    if internal_name:
        vehicle_db.set_parent_vehicle(internal_name, parent_name)
        return jsonify({'success': True})

    return jsonify({'success': False}), 400


@app.route('/api/players/<version>')
def get_players(version):
    """Gibt Player Database zurück"""
    if version not in log_parsers:
        return jsonify({'error': 'Invalid version'}), 400

    from weapon_database import WeaponDatabase
    from vehicle_database import VehicleDatabase

    weapon_db = WeaponDatabase()
    vehicle_db = VehicleDatabase()
    player_db = log_parsers[version].player_db

    # Hole alle Spieler
    all_players = player_db.get_all_players()

    # Konvertiere interne Namen zu Display-Namen
    players_display = {}
    for player_name, data in all_players.items():
        players_display[player_name] = {
            'kills_by_me': {
                'total': data['kills_by_me']['total'],
                'weapons': {
                    weapon_db.get_display_name(internal): count
                    for internal, count in data['kills_by_me']['weapons'].items()
                }
            },
            'deaths_by_them': {
                'total': data['deaths_by_them']['total'],
                'weapons': {
                    weapon_db.get_display_name(internal): count
                    for internal, count in data['deaths_by_them']['weapons'].items()
                }
            },
            'my_vehicles_destroyed_by_them': {
                vehicle_db.get_display_name(internal): count
                for internal, count in data['my_vehicles_destroyed_by_them'].items()
            },
            'first_encounter': data['first_encounter'],
            'last_encounter': data['last_encounter'],
            'avatar_url': data.get('avatar_url')
        }

    return jsonify({
        'players': players_display,
        'top_killers': player_db.get_top_killers(10),
        'top_victims': player_db.get_top_victims(10),
        'rivalries': player_db.get_rivalries(3)
    })


@app.route('/api/players/<version>/<player_name>')
def get_player_detail(version, player_name):
    """Gibt detaillierte Infos zu einem Spieler zurück"""
    if version not in log_parsers:
        return jsonify({'error': 'Invalid version'}), 400

    from weapon_database import WeaponDatabase
    from vehicle_database import VehicleDatabase

    weapon_db = WeaponDatabase()
    vehicle_db = VehicleDatabase()
    player_db = log_parsers[version].player_db

    stats = player_db.get_player_stats(player_name)
    if not stats:
        return jsonify({'error': 'Player not found'}), 404

    # Konvertiere zu Display-Namen
    stats_display = {
        'kills_by_me': {
            'total': stats['kills_by_me']['total'],
            'weapons': {
                weapon_db.get_display_name(internal): count
                for internal, count in stats['kills_by_me']['weapons'].items()
            }
        },
        'deaths_by_them': {
            'total': stats['deaths_by_them']['total'],
            'weapons': {
                weapon_db.get_display_name(internal): count
                for internal, count in stats['deaths_by_them']['weapons'].items()
            }
        },
        'my_vehicles_destroyed_by_them': {
            vehicle_db.get_display_name(internal): count
            for internal, count in stats['my_vehicles_destroyed_by_them'].items()
        },
        'first_encounter': stats['first_encounter'],
        'last_encounter': stats['last_encounter'],
        'avatar_url': stats.get('avatar_url'),
        'summary': player_db.get_player_summary(player_name)
    }

    return jsonify(stats_display)


@app.route('/api/npcs')
def get_npcs():
    """Gibt NPC-Patterns zurück"""
    from npc_database import NPCDatabase
    npc_db = NPCDatabase()

    return jsonify({
        'patterns': npc_db.get_patterns()
    })


@app.route('/api/npcs/pattern', methods=['POST'])
def add_npc_pattern():
    """Fügt NPC-Pattern hinzu"""
    from npc_database import NPCDatabase
    npc_db = NPCDatabase()

    data = request.json
    pattern = data.get('pattern')

    if pattern:
        npc_db.add_pattern(pattern)

        # Berechne Stats für alle Versionen neu UND bereinige Player-Datenbank
        for version in config_manager.get_versions():
            stats_managers[version].recalculate_npc_stats(npc_db)

            # Bereinige Player-Datenbank von NPCs
            if version in log_parsers:
                player_db = log_parsers[version].player_db
                removed_count = player_db.remove_npcs(npc_db)
                if removed_count > 0:
                    print(f"[{version}] {removed_count} NPCs aus Spielerdatenbank entfernt")
                    # Sende Player-Update an Frontend
                    socketio.emit('players_updated', {
                        'version': version,
                        'message': f'{removed_count} NPCs entfernt'
                    })

            # Sende Update an Frontend
            socketio.emit('stats_updated', {
                'version': version,
                'stats': stats_managers[version].get_all_stats()
            })

        return jsonify({'success': True})

    return jsonify({'success': False}), 400


@app.route('/api/npcs/pattern/<pattern>', methods=['DELETE'])
def remove_npc_pattern(pattern):
    """Entfernt NPC-Pattern"""
    from npc_database import NPCDatabase
    npc_db = NPCDatabase()

    npc_db.remove_pattern(pattern)

    # Berechne Stats für alle Versionen neu
    # WICHTIG: Nach dem Entfernen eines Patterns könnten ehemalige NPCs
    # jetzt als Spieler zählen - aber wir korrigieren nur in eine Richtung
    # (NPCs die als PVP gespeichert sind werden zu PVE, nicht umgekehrt)
    for version in config_manager.get_versions():
        stats_managers[version].recalculate_npc_stats(npc_db)

        # Sende Update an Frontend
        socketio.emit('stats_updated', {
            'version': version,
            'stats': stats_managers[version].get_all_stats()
        })

    return jsonify({'success': True})


@app.route('/api/player/profile/<handle>')
def get_player_profile(handle):
    """
    Holt Spieler-Profil von RSI Website

    Args:
        handle: Star Citizen Handle/Spielername
    
    Returns:
        JSON mit Profildaten
    """
    version = request.args.get('version', current_version)

    try:
        url = f"https://robertsspaceindustries.com/citizens/{handle}"
        
        # User-Agent setzen um wie normaler Browser zu erscheinen
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': 'Profile not found'
            }), 404
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Public Profile Container
        profile_container = soup.find('div', {'id': 'public-profile'})
        
        if not profile_container:
            return jsonify({
                'success': False,
                'error': 'Profile data not accessible'
            }), 404
        
        profile_data = {
            'handle': handle,
            'moniker': None,
            'avatar': None,
            'org': {
                'name': None,
                'logo': None,
                'url': None,
                'redacted': False,
                'no_org': True
            }
        }
        
        # Left Column - Avatar und Moniker
        left_col = profile_container.find('div', class_='profile left-col')
        if left_col:
            # Avatar
            avatar_img = left_col.find('img')
            if avatar_img and avatar_img.get('src'):
                avatar_url = avatar_img['src']
                # Relative URL zu absoluter URL konvertieren
                if avatar_url.startswith('/'):
                    avatar_url = f"https://robertsspaceindustries.com{avatar_url}"
                profile_data['avatar'] = avatar_url
            
            # Moniker
            info_div = left_col.find('div', class_='info')
            if info_div:
                moniker_tag = info_div.find('strong', class_='value')
                if moniker_tag:
                    profile_data['moniker'] = moniker_tag.text.strip()
        
        # Right Column - Organisation
        right_col = profile_container.find('div', class_=lambda x: x and 'main-org' in x and 'right-col' in x)
        if right_col:
            classes = right_col.get('class', [])
            
            # Prüfe Visibility
            if 'visibility-V' in classes:
                # Org ist sichtbar
                profile_data['org']['no_org'] = False

                # Org Logo
                org_logo = right_col.find('img')
                if org_logo and org_logo.get('src'):
                    logo_url = org_logo['src']
                    # Relative URL zu absoluter URL konvertieren
                    if logo_url.startswith('/'):
                        logo_url = f"https://robertsspaceindustries.com{logo_url}"
                    profile_data['org']['logo'] = logo_url
                
                # Org Name und Link
                entry_p = right_col.find('p', class_='entry')
                if entry_p:
                    org_link = entry_p.find('a')
                    if org_link:
                        profile_data['org']['name'] = org_link.text.strip()
                        org_url = org_link.get('href')
                        # Relative URL zu absoluter URL konvertieren
                        if org_url:
                            if not org_url.startswith('http'):
                                # Relative URL
                                org_url = f"https://robertsspaceindustries.com{org_url}"
                        profile_data['org']['url'] = org_url
            
            elif 'visibility-R' in classes:
                # Org ist Redacted
                profile_data['org']['no_org'] = False
                profile_data['org']['redacted'] = True
                profile_data['org']['name'] = 'Redacted'
            
            # else: visibility- = Keine Org

        # Speichere Avatar in player_database falls gefunden (aber nicht für eigenen Spieler)
        if profile_data.get('avatar') and version in log_parsers:
            own_player_name = config_manager.get_player_name(version)
            # Nur speichern wenn es NICHT der eigene Spieler ist
            if handle != own_player_name:
                player_db = log_parsers[version].player_db
                player_db.set_avatar_url(handle, profile_data['avatar'])

        profile_data['success'] = True
        return jsonify(profile_data)
    
    except requests.Timeout:
        return jsonify({
            'success': False,
            'error': 'Request timeout'
        }), 504
    
    except Exception as e:
        print(f"Error fetching profile for {handle}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/player/avatar/<handle>')
def get_player_avatar(handle):
    """
    Holt nur den Avatar vom RSI Profil und speichert ihn in der player_database

    Args:
        handle: Star Citizen Handle/Spielername

    Returns:
        JSON mit Avatar URL
    """
    try:
        version = request.args.get('version', current_version)

        # Prüfe ob Avatar bereits in player_database gespeichert ist
        if version in log_parsers:
            player_db = log_parsers[version].player_db
            cached_avatar = player_db.get_avatar_url(handle)

            if cached_avatar:
                return jsonify({
                    'success': True,
                    'avatar': cached_avatar
                })

        # Wenn nicht gecached, hole von RSI
        url = f"https://robertsspaceindustries.com/citizens/{handle}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': 'Profile not found'
            }), 404

        soup = BeautifulSoup(response.content, 'html.parser')

        # Public Profile Container
        profile_container = soup.find('div', {'id': 'public-profile'})

        if not profile_container:
            return jsonify({
                'success': False,
                'error': 'Profile data not accessible'
            }), 404

        # Finde Avatar
        left_col = profile_container.find('div', class_='profile left-col')
        avatar_url = None

        if left_col:
            avatar_img = left_col.find('img')
            if avatar_img and avatar_img.get('src'):
                avatar_url = avatar_img['src']
                # Relative URL zu absoluter URL konvertieren
                if avatar_url.startswith('/'):
                    avatar_url = f"https://robertsspaceindustries.com{avatar_url}"

        if avatar_url:
            # Speichere Avatar URL in player_database (aber nicht für eigenen Spieler)
            if version in log_parsers:
                own_player_name = config_manager.get_player_name(version)
                # Nur speichern wenn es NICHT der eigene Spieler ist
                if handle != own_player_name:
                    player_db = log_parsers[version].player_db
                    player_db.set_avatar_url(handle, avatar_url)

            return jsonify({
                'success': True,
                'avatar': avatar_url
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Avatar not found'
            }), 404

    except requests.Timeout:
        return jsonify({
            'success': False,
            'error': 'Request timeout'
        }), 504

    except Exception as e:
        print(f"Error fetching avatar for {handle}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@socketio.on('connect')
def handle_connect():
    """Client verbunden"""
    print('Client connected')

    emit('config_update', {
        'versions': config_manager.get_versions(),
        'current_version': current_version,
        'player_info': config_manager.get_player_info(current_version)
    })

    emit('stats_updated', {
        'version': current_version,
        'stats': stats_managers[current_version].get_all_stats()
    })

    # Sende aktuellen Star Citizen Status
    sc_running = is_star_citizen_running()
    emit('sc_status_changed', {
        'running': sc_running,
        'version': current_version
    })
    print(f'[Connect] Sende SC-Status an Client: {sc_running}', flush=True)


@socketio.on('disconnect')
def handle_disconnect():
    """Client getrennt"""
    print('Client disconnected')


@socketio.on('start_monitoring')
def handle_start_monitoring(data):
    """Startet Monitoring"""
    version = data.get('version', current_version)
    
    if version not in log_parsers:
        return
    
    if not monitoring_active.get(version, False):
        monitoring_active[version] = True
        thread = threading.Thread(target=monitor_log, args=(version,), daemon=True)
        monitoring_threads[version] = thread
        thread.start()
        
        emit('monitoring_started', {'version': version})


@socketio.on('stop_monitoring')
def handle_stop_monitoring(data):
    """Stoppt Monitoring"""
    version = data.get('version', current_version)
    monitoring_active[version] = False

    emit('monitoring_stopped', {'version': version})


@socketio.on('session_change_response')
def handle_session_change_response(data):
    """Behandelt Session-Wechsel Antwort vom Frontend"""
    version = data.get('version')
    keep_stats = data.get('keep_stats', False)
    new_session_id = data.get('new_session_id')

    if not version or not new_session_id:
        return

    parser = log_parsers.get(version)
    if not parser:
        return

    print(f"[{version}] Session-Wechsel Antwort: {'Stats übernehmen' if keep_stats else 'Stats zurücksetzen'}")

    if keep_stats:
        # Behalte Session-Stats, setze nur neue Session-ID
        parser.stats.set_session_id(new_session_id)
        emit('session_change_processed', {
            'version': version,
            'action': 'kept',
            'message': 'Session-Stats wurden übernommen'
        })
    else:
        # Setze Session-Stats zurück
        parser.stats.reset_session(remove_from_total=False)
        parser.stats.set_session_id(new_session_id)
        parser.stats.session_start = datetime.now()

        # Sende Stats-Update
        socketio.emit('stats_updated', {
            'version': version,
            'stats': parser.stats.get_all_stats()
        })

        emit('session_change_processed', {
            'version': version,
            'action': 'reset',
            'message': 'Session-Stats wurden zurückgesetzt'
        })


def is_star_citizen_running():
    """Prüft ob Star Citizen läuft"""
    import psutil
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and 'StarCitizen.exe' in proc.info['name']:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


def monitor_log(version):
    """Monitoring-Loop"""
    parser = log_parsers[version]

    print(f"[{version}] Starte initiales Scannen...", flush=True)
    parser.initial_scan()
    print(f"[{version}] Initiales Scannen abgeschlossen", flush=True)

    socketio.emit('initial_scan_complete', {'version': version})

    # Initialer SC-Status check
    last_sc_status = is_star_citizen_running()
    socketio.emit('sc_status_changed', {
        'running': last_sc_status,
        'version': version
    })
    print(f"[{version}] Star Citizen Status: {'Running' if last_sc_status else 'Not Running'}", flush=True)

    while monitoring_active.get(version, False):
        try:
            # Prüfe Star Citizen Status
            sc_running = is_star_citizen_running()
            if sc_running != last_sc_status:
                last_sc_status = sc_running
                print(f"[{version}] SC Status changed: {'Running' if sc_running else 'Not Running'}")
                socketio.emit('sc_status_changed', {
                    'running': sc_running,
                    'version': version
                })

            if parser.check_server_swap():
                socketio.emit('server_swap_detected', {
                    'version': version,
                    'message': 'Server-Wechsel erkannt - Session übernommen'
                })

            parser.parse_new_lines()

            time.sleep(2)

        except Exception as e:
            print(f"[{version}] Monitoring-Fehler: {e}")
            time.sleep(5)

    print(f"[{version}] Monitoring gestoppt")


def stop_monitoring(version: str):
    """Stoppt Monitoring für eine Version"""
    if version in monitoring_active:
        monitoring_active[version] = False
        print(f"[{version}] Stoppe Monitoring...")

        # Warte kurz auf Thread-Beendigung
        if version in monitoring_threads:
            thread = monitoring_threads[version]
            if thread.is_alive():
                thread.join(timeout=2)


def start_initial_monitoring():
    """Startet initiales Monitoring nur für die aktuell ausgewählte Version"""
    version = current_version
    log_path = config_manager.get_log_path(version)

    if log_path and Path(log_path).exists():
        print(f"[{version}] Starte Monitoring...")
        monitoring_active[version] = True
        thread = threading.Thread(target=monitor_log, args=(version,), daemon=True)
        monitoring_threads[version] = thread
        thread.start()
    else:
        print(f"⚠️  [{version}] Log-Datei nicht gefunden: {log_path}")


def start_server():
    """Startet Flask Server mit Production WSGI Server"""
    import logging
    import warnings

    # Unterdrücke alle Warnings
    warnings.filterwarnings('ignore')

    # Unterdrücke Werkzeug Development Server Warning komplett
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    # Unterdrücke auch andere Flask/SocketIO Logs
    logging.getLogger('socketio').setLevel(logging.ERROR)
    logging.getLogger('engineio').setLevel(logging.ERROR)

    start_initial_monitoring()

    # SocketIO.run() mit eventlet für Production
    print("Starte Production Server auf http://127.0.0.1:5000")
    socketio.run(app, host='127.0.0.1', port=5000, debug=False, use_reloader=False, log_output=False)


if __name__ == '__main__':
    print("=" * 50)
    print("Verse Combat Log v1.1")
    if DEBUG_MODE:
        print("DEBUG-MODUS AKTIVIERT")
        print("Entwicklertools: Rechtsklick → Inspect / F12")
    print("=" * 50)

    import webview

    # Starte INI-Update im Hintergrund (asynchron)
    print("\n🔍 Starte INI-Update-Check im Hintergrund...")
    def background_ini_update():
        start_time = time.time()
        try:
            from ini_updater import check_ini_update
            needs_reload, message = check_ini_update()
            print(f"✅ {message}")

            if needs_reload:
                # Mindestens 3 Sekunden warten, damit Ladebildschirm sichtbar ist
                elapsed = time.time() - start_time
                min_display_time = 3.0
                if elapsed < min_display_time:
                    time.sleep(min_display_time - elapsed)

                # Kurz warten bis Frontend bereit ist
                time.sleep(1)

                # Sende Event an Frontend dass Namen aktualisiert wurden
                socketio.emit('ini_updated', {
                    'message': message
                })
        except Exception as e:
            print(f"⚠️  Update-Check Fehler: {e}")

    # Starte Update-Thread
    update_thread = threading.Thread(target=background_ini_update, daemon=True)
    update_thread.start()

    print("\n🚀 Starte Anwendung...")

    # Starte Flask Server in separatem Thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Warte kurz bis Server bereit ist
    print("Warte auf Server-Start...")
    time.sleep(2)

    # Erstelle Desktop-Fenster
    print("Öffne Desktop-Fenster...")
    window = webview.create_window(
        'Verse Combat Log v1.1',
        'http://127.0.0.1:5000',
        width=1400,
        height=900,
        resizable=True,
        fullscreen=False,
        min_size=(420, 768),
        text_select=True,
        frameless=False
    )

    # Starte mit Debug-Modus im Development
    webview.start(debug=DEBUG_MODE)

    print("Anwendung beendet.")