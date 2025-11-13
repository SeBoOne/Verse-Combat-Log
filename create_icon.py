"""
Konvertiert PNG zu ICO für Windows Icon
"""
from PIL import Image

# Lade PNG
img = Image.open('static/media/vcl-logo-icon.png')

# Speichere als ICO mit mehreren Größen
img.save('vcl-icon.ico', format='ICO', sizes=[
    (256, 256),
    (128, 128),
    (64, 64),
    (48, 48),
    (32, 32),
    (16, 16)
])

print("vcl-icon.ico erfolgreich erstellt!")
