# Changelog

All notable changes to Verse Combat Log will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 13-11-2025

### 🎉 Initial Release

First public release of Verse Combat Log!

### ✨ Features

#### Combat Tracking
- Real-time kill/death tracking from Star Citizen game logs
- K/D ratio calculation (PvP and total kills)
- Event timeline with timestamps and event types
- Session-based and all-time statistics
- Session reset functionality

#### Weapon & Vehicle Statistics
- Comprehensive weapon tracking with kill counts
- Vehicle kill tracking with variant aggregation system
- Custom display names for weapons and vehicles
- Blacklist system to hide unwanted weapons
- Parent-vehicle assignment for combining variants (e.g., all Hornet types)
- Visual indicators for aggregated vehicles

#### Player Profiles
- Persistent player database across sessions
- Player cards showing kill/death records
- RSI profile integration (avatar, organization, bio)
- Automatic avatar caching
- Click-to-view detailed player profiles
- Own player exclusion from database

#### Multi-Version Support
- Support for LIVE, PTU, EPTU, and TECH-PREVIEW versions
- Separate statistics per game version
- Version-specific log path configuration
- Automatic version detection and switching

#### User Interface
- Modern dark theme with smooth animations
- Responsive design optimized for desktop
- Three main tabs: Session, Total, and Players
- Comprehensive settings modal with multiple tabs
- Real-time updates via WebSocket
- Loading screen during initialization
- Text selection and copying enabled
- **Multi-language support (German/English)** with live switching

#### Settings & Customization
- General settings: Version selection and log path configuration
- Weapon settings: Custom names, blacklist management, search functionality
- Vehicle settings: Custom names, parent-vehicle assignment, search
- NPC pattern filtering for cleaner kill statistics
- Info tab with creator information and legal disclaimer

#### Auto-Update System
- Automatic internalNames.ini updates from GitHub
- Visual loading indicator during updates
- Fallback to embedded names if download fails
- Support for custom user INI files

#### Technical Features
- Flask + SocketIO backend for real-time communication
- PyWebView for native desktop window
- Gevent-based production server
- Singleton pattern for efficient resource usage
- Lazy loading for performance optimization
- Precompiled regex patterns for faster parsing
- Persistent JSON-based data storage
- Debug mode with console output

### 🔧 Technical Details

#### Stack
- Backend: Python 3.10+ with Flask, Flask-SocketIO, Gevent
- Frontend: Vanilla JavaScript, HTML5, CSS3
- Desktop: PyWebView (uses system WebView)
- Data Storage: JSON files
- Web Scraping: BeautifulSoup4, lxml, Requests

#### Build System
- PyInstaller for EXE creation
- Version info with metadata
- Custom icon (VCL logo)
- UPX compression disabled for reduced false-positives
- Automated build script with SHA256 hash generation

### 📝 Known Issues

- Some antivirus programs may show false positives (PyInstaller)
- Windows SmartScreen may warn about unsigned executable

### 🔒 Security

- Local server bound to 127.0.0.1 only (not network-accessible)
- Read-only access to Game.log
- No game file modifications
- No admin rights required

---

**Note**: Version numbers follow Semantic Versioning (MAJOR.MINOR.PATCH)
- MAJOR: Incompatible API/data structure changes
- MINOR: New features in a backwards-compatible manner
- PATCH: Backwards-compatible bug fixes
