"""
Profile Fetcher für RSI Spielerprofile
Holt Avatar-URLs von der RSI Website
"""

import requests
from bs4 import BeautifulSoup
from typing import Optional


def fetch_avatar_url(player_handle: str) -> Optional[str]:
    """
    Holt die Avatar-URL eines Spielers von der RSI Website

    Args:
        player_handle: Star Citizen Handle/Spielername

    Returns:
        Avatar URL oder None bei Fehler
    """
    try:
        url = f"https://robertsspaceindustries.com/citizens/{player_handle}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        response = requests.get(url, headers=headers, timeout=5)

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        # Public Profile Container
        profile_container = soup.find('div', {'id': 'public-profile'})

        if not profile_container:
            return None

        # Left Column - Avatar
        left_col = profile_container.find('div', class_='profile left-col')
        if left_col:
            avatar_img = left_col.find('img')
            if avatar_img and avatar_img.get('src'):
                avatar_url = avatar_img['src']
                # Relative URL zu absoluter URL konvertieren
                if avatar_url.startswith('/'):
                    avatar_url = f"https://robertsspaceindustries.com{avatar_url}"
                return avatar_url

        return None

    except Exception as e:
        print(f"[Profile Fetcher] Fehler beim Abrufen von Avatar für {player_handle}: {e}")
        return None
