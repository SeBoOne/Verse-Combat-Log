// Verse Combat Log v1.1 - Frontend JavaScript

let socket;
let currentVersion = 'LIVE';
let currentLanguage = 'de';
let i18n = {};  // Translations
let playerInfo = {};
let eventTimers = {};
let loadingTimeout = null;

// Name Mappings (Cache)
let weaponNames = {};
let vehicleNames = {};

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadLanguage();  // Sprache zuerst laden
    checkForUpdates();
    initSocket();
    initUI();
    loadConfig();
    loadNameMappings();
});

// Check for Updates on Page Load
async function checkForUpdates() {
    // Zeige Ladebildschirm immer beim Start für Update-Check
    showLoadingOverlay('loading.checking_updates');

    // Verstecke nach kurzer Zeit, falls kein Update kommt
    loadingTimeout = setTimeout(() => {
        // Wird durch ini_updated Event überschrieben, falls Update läuft
        hideLoadingOverlay();
    }, 1000);
}

// Show/Hide Loading Overlay
function showLoadingOverlay(message) {
    const overlay = document.getElementById('loadingOverlay');
    const messageEl = document.getElementById('loadingMessage');
    if (overlay && messageEl) {
        // Versuche zu übersetzen, falls es ein i18n-Key ist
        const translatedMessage = getI18nText(message) || message;
        messageEl.textContent = translatedMessage;
        overlay.style.display = 'flex';
    }
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

// Socket.IO Connection
function initSocket() {
    socket = io();
    
    socket.on('connect', () => {
        console.log('Connected to server');
        // Status wird über sc_status_changed vom Server gesetzt
    });
    
    socket.on('disconnect', () => {
        updateStatus('🔴', 'status.disconnected');
    });
    
    socket.on('config_update', (data) => {
        currentVersion = data.current_version;
        playerInfo = data.player_info;
        updatePlayerInfo();
    });
    
    socket.on('stats_updated', (data) => {
        if (data.version === currentVersion) {
            updateStats(data.stats);
        }
    });
    
    socket.on('new_event', (data) => {
        if (data.version === currentVersion) {
            addEvent(data.event);
        }
    });
    
    socket.on('player_info_updated', (data) => {
        if (data.version === currentVersion) {
            playerInfo = data;
            updatePlayerInfo();
        }
    });
    
    socket.on('server_swap_detected', (data) => {
        if (data.version === currentVersion) {
            addEvent({
                type: 'server',
                message: data.message,
                timestamp: new Date().toISOString()
            });
        }
    });
    
    socket.on('initial_scan_complete', () => {
        // Status wird jetzt über sc_status_changed gesetzt
        // Hier könnte man später zusätzliche Aktionen durchführen
    });

    socket.on('sc_status_changed', (data) => {
        console.log('SC Status changed:', data);
        if (data.version === currentVersion) {
            if (data.running) {
                updateStatus('🟢', 'status.monitoring');
            } else {
                updateStatus('🟠', 'status.waiting');
            }
        } else {
            console.log('Ignoriere SC Status für Version:', data.version, 'current:', currentVersion);
        }
    });

    socket.on('session_changed', (data) => {
        if (data.version === currentVersion) {
            handleSessionChange(data);
        }
    });

    socket.on('session_change_processed', (data) => {
        if (data.version === currentVersion) {
            console.log('Session wechsel verarbeitet:', data.action, data.message);
        }
    });

    socket.on('ini_updated', (data) => {
        console.log('INI aktualisiert:', data.message);

        // Abbrechen des Auto-Hide Timeouts
        if (loadingTimeout) {
            clearTimeout(loadingTimeout);
            loadingTimeout = null;
        }

        // Ladebildschirm verstecken
        hideLoadingOverlay();
        showNotification('notifications.names_updated', 'success', false);
        loadNameMappings();  // Reload cached names
    });
}

// Load Name Mappings
async function loadNameMappings() {
    try {
        // Waffen
        const weaponsResp = await fetch('/api/weapons');
        const weaponsData = await weaponsResp.json();
        weaponNames = weaponsData.weapons || {};
        
        // Fahrzeuge
        const vehiclesResp = await fetch('/api/vehicles');
        const vehiclesData = await vehiclesResp.json();
        vehicleNames = vehiclesData.vehicles || {};
        
        console.log('Neue Anzeigenamen geladen:', {
            weapons: Object.keys(weaponNames).length,
            vehicles: Object.keys(vehicleNames).length
        });
        
    } catch (error) {
        console.error('Fehler beim Laden der Anzeigenamen:', error);
    }
}

// Map internal name to display name
function getWeaponDisplayName(internal) {
    return weaponNames[internal] || internal;
}

function getVehicleDisplayName(internal) {
    return vehicleNames[internal] || internal;
}

// UI Initialization
function initUI() {
    // Version Selector
    document.getElementById('versionSelect').addEventListener('change', (e) => {
        switchVersion(e.target.value);
    });
    
    // Tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            switchTab(tab.dataset.tab);
        });
    });
    
    // Buttons
    document.getElementById('resetSession').addEventListener('click', resetSession);
    document.getElementById('openSettings').addEventListener('click', () => openModal('settingsModal'));
    document.getElementById('clearEvents').addEventListener('click', clearEvents);

    // Settings Tabs
    document.querySelectorAll('.settings-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            switchSettingsTab(this.dataset.settingsTab);
        });
    });

    // Modals
    document.querySelectorAll('.close').forEach(btn => {
        btn.addEventListener('click', function() {
            this.parentElement.parentElement.classList.remove('show');
        });
    });

    // Click outside modal to close
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.classList.remove('show');
        }
    });
    
    // Settings
    document.getElementById('saveSettings').addEventListener('click', saveSettings);

    // Language Selector
    document.getElementById('settingsLanguage').addEventListener('change', function() {
        changeLanguage(this.value);
    });

    // Weapons & Vehicles Add Buttons
    document.getElementById('addWeaponBtn').addEventListener('click', showAddWeaponDialog);
    document.getElementById('addVehicleBtn').addEventListener('click', showAddVehicleDialog);

    // NPCs
    document.getElementById('addNPCPattern').addEventListener('click', addNPCPattern);

    // Search fields
    document.getElementById('weaponSearch').addEventListener('input', filterWeapons);
    document.getElementById('vehicleSearch').addEventListener('input', filterVehicles);

    // Start timers
    setInterval(updateEventTimers, 1000);
}

// Load Config
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();
        
        currentVersion = data.current_version;
        playerInfo = data.player_info;
        
        document.getElementById('versionSelect').value = currentVersion;
        updatePlayerInfo();
        
        loadStats(currentVersion);
        
    } catch (error) {
        console.error('Error loading config:', error);
    }
}

// Switch Version
async function switchVersion(version) {
    try {
        const response = await fetch('/api/config/version', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ version })
        });
        
        if (response.ok) {
            currentVersion = version;
            clearEvents();
            loadStats(version);
            loadConfig();
        }
    } catch (error) {
        console.error('Fehler beim Wechseln der Version:', error);
    }
}

// Load Stats
async function loadStats(version) {
    try {
        const response = await fetch(`/api/stats/${version}`);
        const data = await response.json();
        updateStats(data);
    } catch (error) {
        console.error('Fehler beim Laden der Statistiken:', error);
    }
}

// Update Stats Display
function updateStats(stats) {
    if (!stats) return;
    
    updateStatsSection('session', stats.session);
    updateStatsSection('total', stats.total);
    updatePlayersTab(stats.total);
}

function updateStatsSection(type, data) {
    if (!data) return;
    
    const prefix = type === 'session' ? 'session' : 'total';
    
    // K/D
    document.getElementById(`${prefix}Kills`).textContent =
        `${data.total_kills} (${data.pvp_kills} PvP)`;
    document.getElementById(`${prefix}Deaths`).textContent =
        `${data.deaths} (${data.pvp_deaths} PvP)`;
    document.getElementById(`${prefix}KDRatio`).textContent = data.kd_ratio.toFixed(2);
    
    // Waffen (mit Display-Namen)
    const weaponsContainer = document.getElementById(`${prefix}Weapons`);
    weaponsContainer.innerHTML = '';
    
    if (data.weapon_kills && Object.keys(data.weapon_kills).length > 0) {
        const sortedWeapons = Object.entries(data.weapon_kills)
            .sort((a, b) => b[1] - a[1]);
        
        sortedWeapons.forEach(([internalName, kills]) => {
            const displayName = getWeaponDisplayName(internalName);
            const percentage = data.total_kills > 0 ? 
                ((kills / data.total_kills) * 100).toFixed(1) : 0;
            
            const div = document.createElement('div');
            div.className = 'weapon-item';
            div.innerHTML = `${displayName} <span style="float:right">${kills} (${percentage}%)</span>`;
            weaponsContainer.appendChild(div);
        });
    }
    
    // Fahrzeuge (mit Display-Namen) - nur in Session
    if (type === 'session' || type === 'total') {
        const vehiclesContainer = document.getElementById(`${prefix}Vehicles`);
        if (vehiclesContainer) {
            vehiclesContainer.innerHTML = '';
            
            if (data.vehicle_kills && Object.keys(data.vehicle_kills).length > 0) {
                const sortedVehicles = Object.entries(data.vehicle_kills)
                    .sort((a, b) => b[1] - a[1]);
                
                sortedVehicles.forEach(([internalName, kills]) => {
                    const displayName = getVehicleDisplayName(internalName);
                    
                    const div = document.createElement('div');
                    div.className = 'weapon-item';
                    div.innerHTML = `${displayName} <span style="float:right">${kills}x</span>`;
                    vehiclesContainer.appendChild(div);
                });
            }
        }
    }
    
    // PvP Victims (nur in Session)
    if (type === 'session') {
        const victimsContainer = document.getElementById(`${prefix}Victims`);
        victimsContainer.innerHTML = '';
        
        if (data.pvp_victims && Object.keys(data.pvp_victims).length > 0) {
            Object.entries(data.pvp_victims).forEach(([victim, weapons]) => {
                const div = document.createElement('div');
                div.className = 'victim-item';
                
                // Map weapons to display names
                const weaponCounts = {};
                weapons.forEach(w => {
                    const display = getWeaponDisplayName(w);
                    weaponCounts[display] = (weaponCounts[display] || 0) + 1;
                });
                
                const weaponStr = Object.entries(weaponCounts)
                    .map(([w, c]) => `${w} (${c}x)`)
                    .join(', ');
                
                div.innerHTML = `<strong>${victim}</strong> (${weapons.length}x)<br>
                                <small style="color: var(--text-secondary)">${weaponStr}</small>`;
                victimsContainer.appendChild(div);
            });
        }
    }
    
    // Deaths (nur in Session)
    if (type === 'session') {
        const deathsContainer = document.getElementById(`${prefix}DeathInfo`);
        deathsContainer.innerHTML = '';
        
        // Death by players
        if (data.death_by_players && Object.keys(data.death_by_players).length > 0) {
            const header = document.createElement('div');
            header.innerHTML = '<strong>Getötet von (PvP):</strong>';
            header.style.marginBottom = '10px';
            deathsContainer.appendChild(header);
            
            Object.entries(data.death_by_players)
                .sort((a, b) => b[1] - a[1])
                .forEach(([killer, count]) => {
                    const div = document.createElement('div');
                    div.className = 'death-item';
                    div.innerHTML = `${killer} <span style="float:right">${count}x</span>`;
                    deathsContainer.appendChild(div);
                });
        }
        
        // Death weapons
        if (data.death_weapons && Object.keys(data.death_weapons).length > 0) {
            const header = document.createElement('div');
            header.innerHTML = '<strong style="margin-top: 15px; display: block">Getötet durch:</strong>';
            deathsContainer.appendChild(header);
            
            Object.entries(data.death_weapons)
                .sort((a, b) => b[1] - a[1])
                .forEach(([internalName, count]) => {
                    const displayName = getWeaponDisplayName(internalName);
                    const percentage = data.deaths > 0 ? 
                        ((count / data.deaths) * 100).toFixed(1) : 0;
                    
                    const div = document.createElement('div');
                    div.className = 'death-item';
                    div.innerHTML = `${displayName} <span style="float:right">${count} (${percentage}%)</span>`;
                    deathsContainer.appendChild(div);
                });
        }
    }
}

// Event Timeline
function addEvent(event) {
    const container = document.getElementById('eventsContainer');
    const div = document.createElement('div');
    div.className = `event ${event.type}`;

    // Übersetze Message wenn message_key vorhanden ist
    let message;
    if (event.message_key && event.params) {
        message = getI18nText(event.message_key, event.params);
    } else if (event.message_key) {
        message = getI18nText(event.message_key);
    } else {
        // Fallback: Nutze direkte Message (für Abwärtskompatibilität)
        message = event.message;
    }

    // Konvertiere Spielernamen in Links
    message = linkifyPlayerNames(message);

    if (event.with_timer && event.player_id) {
        eventTimers[event.player_id] = {
            start: event.timer_start || event.timestamp,
            element: div
        };
        div.innerHTML = `<span class="event-timer">(0s)</span> ${message}`;
    } else {
        const time = new Date(event.timestamp).toLocaleTimeString('de-DE');
        div.innerHTML = `<span class="event-timer">[${time}]</span> ${message}`;
    }

    container.insertBefore(div, container.firstChild);

    while (container.children.length > 50) {
        container.removeChild(container.lastChild);
    }
}

// HTML Escape für sichere Verwendung in Attributen
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Konvertiert Spielernamen in klickbare Profile-Links
function linkifyPlayerNames(message) {
    // Patterns für verschiedene Event-Typen (sprachunabhängig durch Emojis)
    const patterns = [
        // "Getötet von/Killed by SPIELER mit/with ..." oder "von/by SPIELER mit/with"
        /(?:von|by) ([^\s]+) (?:mit|with)/g,
        // "🎯 SPIELER mit/with ..." (PvP Kill)
        /🎯 ([^\s]+) (?:mit|with)/g,
        // "durch/by SPIELER)" (Fahrzeug zerstört)
        /(?:durch|by) ([^\s]+)\)/g,
        // "🔄 SPIELER ist respawnt/respawned"
        /🔄 ([^\s]+) (?:ist respawnt|respawned)/g,
        // "☠️ SPIELER's Körper/body"
        /☠️ ([^\s]+)'s /g,
        // "👁️ SPIELER wurde/spotted"
        /👁️ ([^\s]+) (?:wurde|spotted)/g
    ];

    let result = message;

    patterns.forEach(pattern => {
        result = result.replace(pattern, (match, playerName) => {
            // Nicht verlinken: NPC, PDC (automatische Geschütze)
            if (playerName === 'NPC' || playerName === 'PDC') {
                return match; // Keine Verlinkung
            }

            // Erstelle klickbaren Link mit onclick Handler
            const playerLink = `<a href="#" onclick="handlePlayerClick('${escapeHtml(playerName)}'); return false;" class="player-link">${playerName}</a>`;

            // Ersetze nur den Spielernamen, behalte den Rest
            return match.replace(playerName, playerLink);
        });
    });

    return result;
}

function updateEventTimers() {
    const now = new Date();
    
    for (const [playerId, timer] of Object.entries(eventTimers)) {
        const startTime = new Date(timer.start);
        const elapsed = Math.floor((now - startTime) / 1000);
        
        if (timer.element) {
            const timerSpan = timer.element.querySelector('.event-timer');
            if (timerSpan) {
                timerSpan.textContent = `(${elapsed}s)`;
            }
        }
    }
}

function clearEvents() {
    document.getElementById('eventsContainer').innerHTML = '';
    eventTimers = {};
}

// Update UI Elements
function updateStatus(indicator, textKey) {
    document.getElementById('statusIndicator').textContent = indicator;
    // Verwende getI18nText um den übersetzten Text zu bekommen
    const translatedText = getI18nText(textKey) || textKey;
    document.getElementById('statusText').textContent = translatedText;
}

function updatePlayerInfo() {
    // Name
    if (playerInfo.name) {
        document.getElementById('playerName').textContent = `${playerInfo.name}`;
        // Lade RSI-Profilbild
        fetchPlayerAvatar(playerInfo.name);
    } else {
        document.getElementById('playerName').textContent = 'Unbekannt';
        // Setze Platzhalter-Avatar
        document.getElementById('playerInfoAvatar').src = '/static/media/avatar_default_big.jpg';
    }

    // ID
    if (playerInfo.id) {
        document.getElementById('playerId').textContent = `[ID: ${playerInfo.id}]`;
    } else {
        document.getElementById('playerId').textContent = '';
    }

    // Game Version
    if (playerInfo.game_version) {
        document.getElementById('gameVersion').textContent = playerInfo.game_version;
    } else {
        document.getElementById('gameVersion').textContent = '';
    }

    // Current Vehicle
    if (playerInfo.current_vehicle) {
        document.getElementById('currentVehicle').textContent = `${playerInfo.current_vehicle}`;
    } else {
        document.getElementById('currentVehicle').textContent = '';
    }
}

// Lade Player Avatar aus RSI-Profil
async function fetchPlayerAvatar(playerName) {
    try {
        // Prüfe ob Avatar bereits in playerInfo gecached ist
        if (playerInfo.avatar_url) {
            document.getElementById('playerInfoAvatar').src = playerInfo.avatar_url;
            return;
        }

        // Lade nur Avatar-URL vom neuen lightweight Endpoint
        const response = await fetch(`/api/player/avatar/${playerName}?version=${currentVersion}`);
        const data = await response.json();

        if (data.success && data.avatar) {
            document.getElementById('playerInfoAvatar').src = data.avatar;
            // Cache in playerInfo
            playerInfo.avatar_url = data.avatar;
        } else {
            // Fallback zu Platzhalter
            document.getElementById('playerInfoAvatar').src = '/static/media/avatar_default_big.jpg';
        }
    } catch (error) {
        console.error('Fehler beim Laden des Avatars:', error);
        document.getElementById('playerInfoAvatar').src = '/static/media/avatar_default_big.jpg';
    }
}

// Tabs
function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}Stats`).classList.add('active');
}

// Modals
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.add('show');

    if (modalId === 'settingsModal') {
        // Öffne immer mit "General" Tab
        switchSettingsTab('general');
        loadSettingsForm();
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.remove('show');
}

// Settings Tabs
function switchSettingsTab(tabName) {
    // Deaktiviere alle Tabs
    document.querySelectorAll('.settings-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.settings-tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // Aktiviere gewählten Tab
    document.querySelector(`[data-settings-tab="${tabName}"]`).classList.add('active');
    document.getElementById(`${tabName}Settings`).classList.add('active');

    // Lade Daten für den jeweiligen Tab
    if (tabName === 'weapons') {
        document.getElementById('weaponSearch').value = '';
        loadWeapons();
    } else if (tabName === 'vehicles') {
        document.getElementById('vehicleSearch').value = '';
        loadVehicles();
    } else if (tabName === 'npcs') {
        loadNPCs();
    } else if (tabName === 'general') {
        loadSettingsForm();
    }
}

// Settings
function loadSettingsForm() {
    fetch('/api/config')
        .then(r => r.json())
        .then(data => {
            document.getElementById('settingsVersion').value = currentVersion;
            document.getElementById('logPath').value = data.log_paths[currentVersion] || '';
        });
}

async function saveSettings() {
    const version = document.getElementById('settingsVersion').value;
    const path = document.getElementById('logPath').value;

    try {
        const response = await fetch('/api/config/log_path', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ version, path })
        });

        if (response.ok) {
            // Wenn die gespeicherte Version die aktuell aktive ist, neu starten
            if (version === currentVersion) {
                showNotification('notifications.settings_saved_restart', 'success', true);

                // Löse Versions-Wechsel aus (wechselt zur selben Version, startet Monitoring neu)
                const switchResponse = await fetch('/api/config/version', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ version: currentVersion })
                });

                if (switchResponse.ok) {
                    // Lade Stats neu
                    await loadStats(currentVersion);
                }
            } else {
                showNotification('notifications.settings_saved', 'success', true);
            }

            // Schließe Modal korrekt
            closeModal('settingsModal');
        }
    } catch (error) {
        console.error('Fehler beim Speichern der Einstellungen:', error);
        showNotification('notifications.save_error', 'error', false);
    }
}

// Weapons
async function loadWeapons() {
    try {
        const response = await fetch('/api/weapons');
        const data = await response.json();

        const container = document.getElementById('weaponsList');
        container.innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Interner Name</th>
                        <th>Anzeigename</th>
                        <th>Blacklist</th>
                        <th>Aktionen</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        `;
        
        const tbody = container.querySelector('tbody');
        
        // Sortiere Waffen
        const sortedWeapons = Object.entries(data.weapons).sort((a, b) => 
            a[1].localeCompare(b[1])
        );
        
        sortedWeapons.forEach(([internal, display]) => {
            const tr = document.createElement('tr');
            const isBlacklisted = data.blacklist.includes(internal);
            const isCustom = data.custom_names && data.custom_names[internal];

            tr.innerHTML = `
                <td style="font-family: monospace; font-size: 0.85rem">${escapeHtml(internal)}</td>
                <td><input type="text" value="${escapeHtml(display)}" data-internal="${escapeHtml(internal)}" class="weapon-name-input"></td>
                <td style="text-align: center"><input type="checkbox" ${isBlacklisted ? 'checked' : ''} data-internal="${escapeHtml(internal)}" class="weapon-blacklist"></td>
                <td style="text-align: center">
                    ${isCustom ? `<button class="table-delete-btn weapon-delete" data-internal="${escapeHtml(internal)}">Löschen</button>` : ''}
                </td>
            `;

            tbody.appendChild(tr);
        });

        // Event listeners
        container.querySelectorAll('.weapon-name-input').forEach(input => {
            input.addEventListener('change', function() {
                updateWeaponName(this.dataset.internal, this.value);
            });
        });

        container.querySelectorAll('.weapon-blacklist').forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                toggleWeaponBlacklist(this.dataset.internal, this.checked);
            });
        });

        container.querySelectorAll('.weapon-delete').forEach(btn => {
            btn.addEventListener('click', function() {
                if (confirm(`Custom-Name für "${this.dataset.internal}" löschen?`)) {
                    deleteWeaponCustomName(this.dataset.internal);
                }
            });
        });
        
    } catch (error) {
        console.error('Fehler beim Laden der Waffen:', error);
    }
}

async function updateWeaponName(internal, display) {
    try {
        await fetch('/api/weapons/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ internal_name: internal, display_name: display })
        });
        
        // Update cache
        weaponNames[internal] = display;
        
        // Reload stats
        loadStats(currentVersion);
    } catch (error) {
        console.error('Fehler beim Aktualisieren der Waffe:', error);
    }
}

async function toggleWeaponBlacklist(internal, blacklisted) {
    try {
        await fetch('/api/weapons/blacklist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ internal_name: internal, blacklisted })
        });

        // Reload stats
        loadStats(currentVersion);
    } catch (error) {
        console.error('Fehler beim Blacklisten:', error);
    }
}

async function deleteWeaponCustomName(internal) {
    try {
        await fetch('/api/weapons/custom', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ internal_name: internal })
        });

        showNotification('notifications.custom_name_deleted', 'success');
        loadWeapons(); // Reload weapon list
        loadStats(currentVersion); // Reload stats
    } catch (error) {
        console.error('Fehler beim Löschen des Custom-Namens:', error);
        showNotification('notifications.delete_error', 'error');
    }
}

function showAddWeaponDialog() {
    const internal = prompt('Interner Waffenname:\n(z.B. KSAR_ScatterGun_S1)');
    if (!internal) return;

    const display = prompt(`Anzeigename für "${internal}":`);
    if (!display) return;

    addWeaponCustomName(internal, display);
}

async function addWeaponCustomName(internal, display) {
    try {
        await fetch('/api/weapons/custom', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ internal_name: internal, display_name: display })
        });

        showNotification('notifications.custom_name_added', 'success');
        loadWeapons(); // Reload weapon list
        loadStats(currentVersion); // Reload stats
    } catch (error) {
        console.error('Fehler beim Hinzufügen des Custom-Namens:', error);
        showNotification('notifications.add_error', 'error');
    }
}

// Vehicles
async function loadVehicles() {
    try {
        const response = await fetch('/api/vehicles');
        const data = await response.json();

        const container = document.getElementById('vehiclesList');
        container.innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Interner Name</th>
                        <th>Anzeigename</th>
                        <th>Parent-Vehicle<br><small style="font-weight: normal;">(für Statistik)</small></th>
                        <th>Aktionen</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        `;
        
        const tbody = container.querySelector('tbody');
        
        const sortedVehicles = Object.entries(data.vehicles).sort((a, b) => 
            a[1].localeCompare(b[1])
        );
        
        sortedVehicles.forEach(([internal, display]) => {
            const tr = document.createElement('tr');
            const isCustom = data.custom_names && data.custom_names[internal];
            const parentVehicle = data.parent_vehicles && data.parent_vehicles[internal] ? data.parent_vehicles[internal] : internal;
            const isAggregated = parentVehicle !== internal;

            tr.innerHTML = `
                <td style="font-family: monospace; font-size: 0.85rem">${escapeHtml(internal)}</td>
                <td><input type="text" value="${escapeHtml(display)}" data-internal="${escapeHtml(internal)}" class="vehicle-name-input"></td>
                <td>
                    <input type="text"
                           value="${escapeHtml(parentVehicle)}"
                           data-internal="${escapeHtml(internal)}"
                           class="vehicle-parent-input"
                           placeholder="${escapeHtml(internal)}"
                           title="Interner Name des Parent-Fahrzeugs (leer = separat zählen)"
                           style="font-family: monospace; font-size: 0.85rem; ${isAggregated ? 'background: rgba(255, 165, 0, 0.1);' : ''}">
                </td>
                <td style="text-align: center">
                    ${isCustom ? `<button class="table-delete-btn vehicle-delete" data-internal="${escapeHtml(internal)}">Löschen</button>` : ''}
                </td>
            `;

            tbody.appendChild(tr);
        });

        container.querySelectorAll('.vehicle-name-input').forEach(input => {
            input.addEventListener('change', function() {
                updateVehicleName(this.dataset.internal, this.value);
            });
        });

        container.querySelectorAll('.vehicle-parent-input').forEach(input => {
            input.addEventListener('change', function() {
                updateVehicleParent(this.dataset.internal, this.value);
            });
        });

        container.querySelectorAll('.vehicle-delete').forEach(btn => {
            btn.addEventListener('click', function() {
                if (confirm(`Custom-Name für "${this.dataset.internal}" löschen?`)) {
                    deleteVehicleCustomName(this.dataset.internal);
                }
            });
        });
        
    } catch (error) {
        console.error('Fehler beim Laden der Fahrzeuge:', error);
    }
}

async function updateVehicleName(internal, display) {
    try {
        await fetch('/api/vehicles/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ internal_name: internal, display_name: display })
        });

        vehicleNames[internal] = display;
        loadStats(currentVersion);
    } catch (error) {
        console.error('Fehler beim Aktualisieren des Fahrzeugs:', error);
    }
}

async function updateVehicleParent(internal, parent) {
    try {
        await fetch('/api/vehicles/parent', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ internal_name: internal, parent_name: parent })
        });

        showNotification('notifications.parent_vehicle_updated', 'info', false);
        loadStats(currentVersion); // Reload stats (Aggregation ändert sich!)
    } catch (error) {
        console.error('Fehler beim Setzen des Parent-Vehicles:', error);
        showNotification('notifications.set_error', 'error');
    }
}

async function deleteVehicleCustomName(internal) {
    try {
        await fetch('/api/vehicles/custom', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ internal_name: internal })
        });

        showNotification('notifications.custom_name_deleted', 'success');
        loadVehicles(); // Reload vehicle list
        loadStats(currentVersion); // Reload stats
    } catch (error) {
        console.error('Fehler beim Löschen des Custom-Namens:', error);
        showNotification('notifications.delete_error', 'error');
    }
}

function showAddVehicleDialog() {
    const internal = prompt('Interner Fahrzeugname:\n(z.B. DRAK_Cutlass_Black)');
    if (!internal) return;

    const display = prompt(`Anzeigename für "${internal}":`);
    if (!display) return;

    addVehicleCustomName(internal, display);
}

async function addVehicleCustomName(internal, display) {
    try {
        await fetch('/api/vehicles/custom', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ internal_name: internal, display_name: display })
        });

        showNotification('notifications.custom_name_added', 'success');
        loadVehicles(); // Reload vehicle list
        loadStats(currentVersion); // Reload stats
    } catch (error) {
        console.error('Fehler beim Hinzufügen des Custom-Namens:', error);
        showNotification('notifications.add_error', 'error');
    }
}

// NPCs
async function loadNPCs() {
    try {
        const response = await fetch('/api/npcs');
        const data = await response.json();
        
        const container = document.getElementById('npcsList');
        container.innerHTML = '';
        
        data.patterns.forEach(pattern => {
            const div = document.createElement('div');
            div.style.cssText = 'display: flex; justify-content: space-between; padding: 10px; background: var(--bg-card); margin: 5px 0; border-radius: 8px;';
            div.innerHTML = `
                <span>${pattern}</span>
                <button onclick="removeNPCPattern('${pattern}')" class="btn-small" style="background: var(--danger)">Löschen</button>
            `;
            container.appendChild(div);
        });
    } catch (error) {
        console.error('Error loading NPCs:', error);
    }
}

async function addNPCPattern() {
    const input = document.getElementById('npcPattern');
    const pattern = input.value.trim();
    
    if (!pattern) return;
    
    try {
        const response = await fetch('/api/npcs/pattern', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pattern })
        });
        
        if (response.ok) {
            input.value = '';
            loadNPCs();
        }
    } catch (error) {
        console.error('Fehler beim Hinzufügen des NPC-Musters:', error);
    }
}

async function removeNPCPattern(pattern) {
    try {
        const response = await fetch(`/api/npcs/pattern/${encodeURIComponent(pattern)}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadNPCs();
        }
    } catch (error) {
        console.error('Fehler beim Entfernen des NPC-Musters:', error);
    }
}

// Players Tab
async function updatePlayersTab() {
    const playersGrid = document.getElementById('playersGrid');
    playersGrid.innerHTML = '<div style="text-align:center; padding:20px;">Lade Spielerdaten...</div>';

    try {
        // Lade Spielerdaten von neuer API
        const response = await fetch(`/api/players/${currentVersion}`);
        const data = await response.json();

        playersGrid.innerHTML = '';

        const players = data.players || {};
        const playerList = Object.entries(players).map(([name, stats]) => ({
            name,
            ...stats
        }));

        // Sortiere nach Gesamtbegegnungen
        const sortedPlayers = playerList.sort((a, b) => {
            const aTotal = a.kills_by_me.total + a.deaths_by_them.total;
            const bTotal = b.kills_by_me.total + b.deaths_by_them.total;
            return bTotal - aTotal;
        });

        // Setup search
        const searchInput = document.getElementById('playerSearch');
        searchInput.addEventListener('input', () => {
            const query = searchInput.value.toLowerCase();
            document.querySelectorAll('.player-card').forEach(card => {
                const name = card.dataset.playerName.toLowerCase();
                card.style.display = name.includes(query) ? 'block' : 'none';
            });
        });

        if (sortedPlayers.length === 0) {
            playersGrid.innerHTML = '<div class="no-players" data-i18n="players_tab.no_players">Keine Spieler-Begegnungen</div>';
            return;
        }

        sortedPlayers.forEach(player => {
            const card = document.createElement('div');
            card.className = 'player-card';
            card.dataset.playerName = player.name;

            const myKills = player.kills_by_me.total;
            const myDeaths = player.deaths_by_them.total;
            const kd = myDeaths > 0 ? (myKills / myDeaths).toFixed(2) : myKills;

            // Avatar
            let avatarHtml = '';
            if (player.avatar_url && player.avatar_url !== 'null' && player.avatar_url !== null) {
                avatarHtml = `<img src="${player.avatar_url}" class="player-card-avatar" alt="${player.name}">`;
            }

            card.innerHTML = `
                <div class="player-card-header">
                    ${avatarHtml}
                    <div class="player-name">${player.name}</div>
                </div>
                <div class="player-stats">
                    <div class="player-stat">
                        <span class="player-stat-label">Kills</span>
                        <span class="player-stat-value">${myKills}</span>
                    </div>
                    <div class="player-stat">
                        <span class="player-stat-label">Deaths</span>
                        <span class="player-stat-value">${myDeaths}</span>
                    </div>
                    <div class="player-stat player-stat-kd">
                        <span class="player-stat-label">K/D</span>
                        <span class="player-stat-value">${kd}</span>
                    </div>
                </div>
            `;

            // Click to open profile
            card.addEventListener('click', () => {
                openPlayerProfile(player.name);
            });

            playersGrid.appendChild(card);

            // Fetch Avatar im Hintergrund wenn nicht vorhanden
            if (!player.avatar_url || player.avatar_url === 'null' || player.avatar_url === null) {
                fetchPlayerAvatar(player.name);
            }
        });
    } catch (error) {
        console.error('Fehler beim Laden der Spielerdaten:', error);
        playersGrid.innerHTML = '<div class="no-players">Fehler beim Laden der Spielerdaten</div>';
    }
}

// Handler für Spieler-Klick in Timeline
async function handlePlayerClick(playerName) {
    try {
        // Prüfe ob Spieler in Datenbank ist
        const response = await fetch(`/api/players/${currentVersion}`);
        const data = await response.json();

        if (data.players && data.players[playerName]) {
            // Spieler ist bekannt -> vollständiges Profil
            openPlayerProfile(playerName);
        } else {
            // Spieler ist unbekannt -> Light-Profil (nur RSI Daten)
            openLightPlayerProfile(playerName);
        }
    } catch (error) {
        console.error('Fehler beim Überprüfen des Spielers:', error);
        // Bei Fehler -> Light-Profil
        openLightPlayerProfile(playerName);
    }
}

// Light Player Profile (nur RSI Daten, ohne Stats)
async function openLightPlayerProfile(playerName) {
    const modal = document.getElementById('playerProfileModal');
    const content = document.getElementById('playerProfileContent');

    content.innerHTML = '<div style="text-align:center; padding:40px;">Lädt RSI-Profil...</div>';
    modal.classList.add('show');

    try {
        // Lade nur RSI Profil (mit version Parameter)
        const profileResponse = await fetch(`/api/player/profile/${encodeURIComponent(playerName)}?version=${currentVersion}`);
        const profileData = await profileResponse.json();

        // Erstelle Light-Profil-Ansicht
        let html = '<div class="profile-header">';

        // Avatar
        if (profileData.avatar) {
            html += `<img src="${profileData.avatar}" class="profile-avatar" alt="${playerName}">`;
        }

        // Basis-Info
        html += '<div class="profile-info">';
        html += `<h2>${playerName}</h2>`;
        if (profileData.moniker) {
            html += `<div class="profile-moniker">${profileData.moniker}</div>`;
        }

        // Organisation
        if (profileData.org && !profileData.org.no_org) {
            html += '<div class="profile-org">';
            if (profileData.org.logo) {
                html += `<img src="${profileData.org.logo}" class="profile-org-logo">`;
            }
            if (profileData.org.redacted) {
                html += '<span style="color: var(--danger)">Redacted</span>';
            } else if (profileData.org.name) {
                html += `<a href="${profileData.org.url}" target="_blank" class="profile-org-name">${profileData.org.name}</a>`;
            }
            html += '</div>';
        }

        html += '</div></div>';

        // Info-Hinweis statt Stats
        html += '<div class="profile-stats">';
        html += '<div class="profile-stat-card" style="text-align: center;">';
        html += '<h3>ℹ️ Keine Begegnungen</h3>';
        html += '<p style="color: var(--text-secondary)">Du hattest noch keine Begegnungen mit diesem Spieler.</p>';
        html += '</div>';

        // Link zum RSI-Profil
        html += '<div class="profile-stat-card" style="text-align: center;">';
        html += '<h3>🔗 RSI Profil</h3>';
        const rsiUrl = `https://robertsspaceindustries.com/citizens/${encodeURIComponent(playerName)}`;
        html += `<a href="${rsiUrl}" target="_blank" class="btn" style="display: inline-block; margin-top: 10px;">Profil auf RSI öffnen</a>`;
        html += '</div>';

        html += '</div>';

        content.innerHTML = html;

    } catch (error) {
        console.error('Error loading light player profile:', error);
        content.innerHTML = `
            <div style="text-align:center; padding:40px; color: var(--danger)">
                <h2>Fehler beim Laden</h2>
                <p>RSI-Profil konnte nicht geladen werden.</p>
                <p style="font-size: 0.9rem; color: var(--text-secondary)">${error.message}</p>
            </div>
        `;
    }
}

// Player Profile (vollständig mit Stats)
async function openPlayerProfile(playerName) {
    const modal = document.getElementById('playerProfileModal');
    const content = document.getElementById('playerProfileContent');

    content.innerHTML = '<div style="text-align:center; padding:40px;" data-i18n="profile.loading">Lade Profil...</div>';
    modal.classList.add('show');

    try {
        // Lade detaillierte Spielerdaten von neuer API
        const playerResponse = await fetch(`/api/players/${currentVersion}/${encodeURIComponent(playerName)}`);
        const playerData = await playerResponse.json();

        // Lade RSI Profil (parallel, mit version Parameter)
        const profileResponse = await fetch(`/api/player/profile/${encodeURIComponent(playerName)}?version=${currentVersion}`);
        const profileData = await profileResponse.json();

        // Erstelle Profil-Ansicht
        let html = '<div class="profile-header">';

        // Avatar (aus Player DB oder RSI)
        const avatarUrl = playerData.avatar_url || profileData.avatar;
        if (avatarUrl) {
            html += `<img src="${avatarUrl}" class="profile-avatar" alt="${playerName}">`;
        }

        // Basis-Info
        html += '<div class="profile-info">';
        html += `<h2>${playerName}</h2>`;
        if (profileData.moniker) {
            html += `<div class="profile-moniker">${profileData.moniker}</div>`;
        }

        // Organisation
        if (profileData.org && !profileData.org.no_org) {
            html += '<div class="profile-org">';
            if (profileData.org.logo) {
                html += `<img src="${profileData.org.logo}" class="profile-org-logo">`;
            }
            if (profileData.org.redacted) {
                html += '<span style="color: var(--danger)">Redacted</span>';
            } else if (profileData.org.name) {
                html += `<a href="${profileData.org.url}" target="_blank" class="profile-org-name">${profileData.org.name}</a>`;
            }
            html += '</div>';
        }

        html += '</div></div>';

        // Stats
        html += '<div class="profile-stats">';

        // Meine Stats
        const myKills = playerData.kills_by_me.total;
        const myDeaths = playerData.deaths_by_them.total;
        const kd = myDeaths > 0 ? (myKills / myDeaths).toFixed(2) : myKills;

        html += '<div class="profile-stat-card">';
        html += '<h3 data-i18n="profile.my_stats">Meine Statistik</h3>';
        html += `<p>Kills: <strong style="color: var(--success)">${myKills}</strong></p>`;
        html += `<p>Deaths: <strong style="color: var(--danger)">${myDeaths}</strong></p>`;
        html += `<p>K/D: <strong style="color: var(--accent)">${kd}</strong></p>`;
        html += '</div>';

        // Meine Waffen
        const myWeapons = playerData.kills_by_me.weapons || {};
        if (Object.keys(myWeapons).length > 0) {
            html += '<div class="profile-stat-card">';
            html += '<h3 data-i18n="profile.my_used_weapons">Womit Ihn gekillt</h3>';

            Object.entries(myWeapons)
                .sort((a, b) => b[1] - a[1])
                .forEach(([weapon, count]) => {
                    html += `<p>${weapon}: ${count}x</p>`;
                });

            html += '</div>';
        }

        // Gegner-Waffen
        const theirWeapons = playerData.deaths_by_them.weapons || {};
        if (Object.keys(theirWeapons).length > 0) {
            html += '<div class="profile-stat-card">';
            html += '<h3 data-i18n="profile.oponent_used_weapons">Womit mich gekillt</h3>';

            Object.entries(theirWeapons)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5)
                .forEach(([weapon, count]) => {
                    html += `<p>${weapon}: ${count}x</p>`;
                });

            html += '</div>';
        }

        // Fahrzeugverluste
        const vehicleLosses = playerData.my_vehicles_destroyed_by_them || {};
        if (Object.keys(vehicleLosses).length > 0) {
            html += '<div class="profile-stat-card">';
            html += '<h3 data-i18n="profile.vehicle_losses">Hat zerstört meine</h3>';

            Object.entries(vehicleLosses)
                .sort((a, b) => b[1] - a[1])
                .forEach(([vehicle, count]) => {
                    html += `<p>${vehicle}: ${count}x</p>`;
                });

            html += '</div>';
        }

        // Zeitstempel
        html += '<div class="profile-stat-card">';
        html += '<h3 data-i18n="profile.encounters">Begegnungen</h3>';
        html += `<p><span data-i18n="profile.first_encounter">Erste:</span> ${new Date(playerData.first_encounter).toLocaleString('de-DE')}</p>`;
        html += `<p><span data-i18n="profile.last_encounter">Letzte:</span> ${new Date(playerData.last_encounter).toLocaleString('de-DE')}</p>`;
        html += '</div>';

        html += '</div>';

        content.innerHTML = html;

    } catch (error) {
        console.error('Error loading player profile:', error);
        content.innerHTML = `
            <div style="text-align:center; padding:40px; color: var(--danger)">
                <h2 data-i18n="profile.errorLoading">Fehler beim Laden</h2>
                <p data-i18n="profile.error">Profil konnte nicht geladen werden.</p>
                <p style="font-size: 0.9rem; color: var(--text-secondary)">${error.message}</p>
            </div>
        `;
    }
}

// Custom Notification (ersetzt alert)
function showNotification(message, type = 'info', autoClose = true) {
    // Versuche zu übersetzen, falls es ein i18n-Key ist
    const translatedMessage = getI18nText(message) || message;

    const dialog = document.createElement('div');
    dialog.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    const box = document.createElement('div');
    box.style.cssText = `
        background: #1a1a1a;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 24px;
        max-width: 400px;
        color: #fff;
    `;

    // Icon basierend auf Typ
    let icon = 'ℹ️';
    let iconColor = '#0066cc';
    if (type === 'success') {
        icon = '✓';
        iconColor = '#00cc66';
    } else if (type === 'error') {
        icon = '✗';
        iconColor = '#cc3333';
    }

    box.innerHTML = `
        <div style="display: flex; align-items: start; gap: 16px;">
            <div style="font-size: 24px; color: ${iconColor};">${icon}</div>
            <div style="flex: 1;">
                <p style="margin: 0; color: #fff;">${translatedMessage}</p>
            </div>
        </div>
        <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px;">
            <button id="notificationOk" style="padding: 8px 16px; background: ${iconColor}; border: 1px solid ${iconColor}; border-radius: 4px; color: #fff; cursor: pointer;">OK</button>
        </div>
    `;

    dialog.appendChild(box);
    document.body.appendChild(dialog);

    // Auto-close bei Auto-Close UND wenn ein Modal geschlossen wird
    let closeOnModalClose = false;

    const cleanup = () => {
        if (dialog.parentNode) {
            document.body.removeChild(dialog);
        }
    };

    // Promise für OK-Button
    const promise = new Promise(resolve => {
        document.getElementById('notificationOk').onclick = () => {
            cleanup();
            resolve();
        };

        // Auto-Close wenn Settings-Modal geschlossen wird
        if (autoClose) {
            closeOnModalClose = true;
            const settingsModal = document.getElementById('settingsModal');
            if (settingsModal) {
                const observer = new MutationObserver(() => {
                    if (settingsModal.style.display === 'none' && closeOnModalClose) {
                        cleanup();
                        resolve();
                    }
                });
                observer.observe(settingsModal, { attributes: true, attributeFilter: ['style'] });
            }
        }
    });

    return promise;
}

// Handle Session Change (automatisch bei Session-Wechsel)
async function handleSessionChange(data) {
    const { new_session_id, version } = data;

    // Erstelle Custom Dialog mit Auto-Timeout
    const dialog = document.createElement('div');
    dialog.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    const box = document.createElement('div');
    box.style.cssText = `
        background: #1a1a1a;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 24px;
        max-width: 400px;
        color: #fff;
    `;

    box.innerHTML = `
        <h3 style="margin: 0 0 16px 0; color: #fff;">Neue Session erkannt</h3>
        <p style="margin: 0 0 16px 0; color: #ccc;">Das Spiel hat eine neue Session gestartet.</p>
        <p style="margin: 0 0 24px 0; color: #ccc;"><strong>Stats aus letzter Session übernehmen?</strong></p>
        <div style="display: flex; gap: 8px; justify-content: flex-end; align-items: center;">
            <span id="countdown" style="color: #888; margin-right: auto;">Auto-Auswahl in <strong>5</strong>s</span>
            <button id="dialogYes" style="padding: 8px 16px; background: #0066cc; border: 1px solid #0066cc; border-radius: 4px; color: #fff; cursor: pointer;">Ja</button>
            <button id="dialogNo" style="padding: 8px 16px; background: #cc3333; border: 1px solid #cc3333; border-radius: 4px; color: #fff; cursor: pointer; font-weight: bold;">Nein</button>
        </div>
    `;

    dialog.appendChild(box);
    document.body.appendChild(dialog);

    // Auto-Timeout (5 Sekunden)
    let timeLeft = 5;
    const countdownElement = document.getElementById('countdown');
    let autoSelectTimeout;
    let countdownInterval;

    const cleanup = () => {
        clearTimeout(autoSelectTimeout);
        clearInterval(countdownInterval);
        if (dialog.parentNode) {
            document.body.removeChild(dialog);
        }
    };

    // Countdown anzeigen
    countdownInterval = setInterval(() => {
        timeLeft--;
        if (timeLeft > 0 && countdownElement) {
            countdownElement.innerHTML = `Auto-Auswahl in <strong>${timeLeft}</strong>s`;
        }
    }, 1000);

    // Auto-Select nach 5 Sekunden
    autoSelectTimeout = setTimeout(() => {
        cleanup();
        // "Nein" wird automatisch gewählt
        socket.emit('session_change_response', {
            version: version,
            keep_stats: false,
            new_session_id: new_session_id
        });
    }, 5000);

    // Warte auf Benutzer-Auswahl
    const choice = await new Promise(resolve => {
        document.getElementById('dialogYes').onclick = () => {
            cleanup();
            resolve('yes');
        };
        document.getElementById('dialogNo').onclick = () => {
            cleanup();
            resolve('no');
        };
    });

    // Sende Antwort an Backend
    socket.emit('session_change_response', {
        version: version,
        keep_stats: choice === 'yes',
        new_session_id: new_session_id
    });

    // Lade Stats neu
    if (choice === 'no') {
        loadStats(currentVersion);
    }
}

// Reset Session
async function resetSession() {
    // Erstelle Custom Dialog mit 3 Optionen
    const dialog = document.createElement('div');
    dialog.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    const box = document.createElement('div');
    box.style.cssText = `
        background: #1a1a1a;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 24px;
        max-width: 400px;
        color: #fff;
    `;

    box.innerHTML = `
        <h3 style="margin: 0 0 16px 0; color: #fff;">Session zurücksetzen</h3>
        <p style="margin: 0 0 24px 0; color: #ccc;">Sollen die Session-Daten auch aus der Gesamtstatistik entfernt werden?</p>
        <div style="display: flex; gap: 8px; justify-content: flex-end;">
            <button id="dialogYes" style="padding: 8px 16px; background: #cc3333; border: 1px solid #cc3333; border-radius: 4px; color: #fff; cursor: pointer;">Ja</button>
            <button id="dialogNo" style="padding: 8px 16px; background: #0066cc; border: 1px solid #0066cc; border-radius: 4px; color: #fff; cursor: pointer;">Nein</button>
            <button id="dialogCancel" style="padding: 8px 16px; background: #333; border: 1px solid #555; border-radius: 4px; color: #fff; cursor: pointer;">Abbrechen</button>
        </div>
    `;

    dialog.appendChild(box);
    document.body.appendChild(dialog);

    // Warte auf Benutzer-Auswahl
    const choice = await new Promise(resolve => {
        document.getElementById('dialogCancel').onclick = () => resolve('cancel');
        document.getElementById('dialogNo').onclick = () => resolve('no');
        document.getElementById('dialogYes').onclick = () => resolve('yes');
    });

    // Entferne Dialog
    document.body.removeChild(dialog);

    // Abbruch
    if (choice === 'cancel') return;

    // API Call
    try {
        const response = await fetch(`/api/stats/${currentVersion}/reset_session`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ remove_from_total: choice === 'yes' })
        });

        if (response.ok) {
            showNotification('notifications.session_reset', 'success', false);
            loadStats(currentVersion);
        }
    } catch (error) {
        console.error('Error resetting session:', error);
        showNotification('notifications.reset_error', 'error', false);
    }
}

// Filter Weapons
function filterWeapons() {
    const searchTerm = document.getElementById('weaponSearch').value.toLowerCase();
    const table = document.querySelector('#weaponsList table');

    if (!table) return;

    const rows = table.querySelectorAll('tbody tr');

    rows.forEach(row => {
        const internalName = row.querySelector('td:nth-child(1)').textContent.toLowerCase();
        const displayInput = row.querySelector('.weapon-name-input');
        const displayName = displayInput ? displayInput.value.toLowerCase() : '';

        // Zeige Zeile wenn Suchbegriff in internem Namen ODER Anzeigenamen vorkommt
        if (internalName.includes(searchTerm) || displayName.includes(searchTerm)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// Filter Vehicles
function filterVehicles() {
    const searchTerm = document.getElementById('vehicleSearch').value.toLowerCase();
    const table = document.querySelector('#vehiclesList table');

    if (!table) return;

    const rows = table.querySelectorAll('tbody tr');

    rows.forEach(row => {
        const internalName = row.querySelector('td:nth-child(1)').textContent.toLowerCase();
        const displayInput = row.querySelector('.vehicle-name-input');
        const displayName = displayInput ? displayInput.value.toLowerCase() : '';

        // Zeige Zeile wenn Suchbegriff in internem Namen ODER Anzeigenamen vorkommt
        if (internalName.includes(searchTerm) || displayName.includes(searchTerm)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// ========================================
// Language System
// ========================================

async function loadLanguage(lang = null) {
    try {
        // Lade Config um Sprache zu bekommen
        if (!lang) {
            const response = await fetch('/api/config');
            const data = await response.json();
            lang = data.language || 'de';
        }

        currentLanguage = lang;

        // Lade Sprachdatei
        const langResponse = await fetch(`/static/lang/${lang}.json`);
        i18n = await langResponse.json();

        // Aktualisiere UI-Texte
        updateUITexts();

        // Update Language selector wenn vorhanden
        const langSelect = document.getElementById('settingsLanguage');
        if (langSelect) {
            langSelect.value = lang;
        }

    } catch (error) {
        console.error('Fehler beim Laden der Sprache:', error);
        // Fallback zu Deutsch
        if (lang !== 'de') {
            await loadLanguage('de');
        }
    }
}

function updateUITexts() {
    // Update alle Elemente mit data-i18n Attribut
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        const text = getI18nText(key);
        if (text) {
            if (el.tagName === 'INPUT' && el.type !== 'button') {
                el.placeholder = text;
            } else {
                el.textContent = text;
            }
        }
    });
}

function getI18nText(key, params = {}) {
    // Navigiere durch verschachtelte Keys (z.B. "settings.general.version")
    const keys = key.split('.');
    let value = i18n;
    for (const k of keys) {
        value = value?.[k];
    }

    let text = value || key;  // Fallback zum Key wenn Text nicht gefunden

    // Ersetze Parameter-Platzhalter {param} mit tatsächlichen Werten
    if (params && typeof text === 'string') {
        Object.keys(params).forEach(param => {
            text = text.replace(new RegExp(`\\{${param}\\}`, 'g'), params[param]);
        });
    }

    return text;
}

async function changeLanguage(lang) {
    try {
        // Speichere Sprache im Backend
        await fetch('/api/config/language', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ language: lang })
        });

        // Lade neue Sprache
        await loadLanguage(lang);

        showNotification(i18n.notifications?.settings_saved || 'Einstellungen gespeichert', 'success');
    } catch (error) {
        console.error('Fehler beim Ändern der Sprache:', error);
        showNotification(i18n.notifications?.error || 'Fehler', 'error');
    }
}
