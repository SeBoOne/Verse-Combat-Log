# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('internalNames.ini', '.'),
    ],
    hiddenimports=[
        'flask',
        'flask_socketio',
        'socketio',
        'engineio',
        'engineio.async_drivers.gevent',
        'gevent',
        'gevent.monkey',
        'gevent._socket3',
        'gevent.select',
        'gevent.queue',
        'gevent.event',
        'gevent.lock',
        'gevent.hub',
        'gevent.greenlet',
        'gevent.resolver.thread',
        'gevent.resolver.ares',
        'gevent_websocket',
        'webview',
        'psutil',
        'requests',
        'bs4',
        'lxml',
        'zope.interface',
        'zope.event',
        'filter_ini',  # INI Konvertierungs-Script
        'ini_updater',  # Auto-Update System
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VerseCombatLog',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX deaktiviert - reduziert False-Positives bei Antivirus
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Konsole standardmäßig versteckt (--debug aktiviert sie)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='vcl-icon.ico',  # VCL Logo als Icon
    version='version_info.txt',  # Version-Info für professionelle EXE-Metadaten
)
