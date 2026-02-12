import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os
import time
import sys

load_dotenv()

# --- КОНФИГУРАЦИЯ ---
NEW_PLAYLIST_NAME = "My Spotify Tracker"  # Имя нового плейлиста
# --------------------

def get_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope="user-follow-read playlist-modify-public playlist-modify-private",
        open_browser=False,
        cache_handler=spotipy.cache_handler.CacheFileHandler(cache_path=".cache")
    ))

def create_playlist_force(sp, user_id):
    """Создает плейлист через прямой запрос (обход багов библиотеки)"""
    print(f"🔨 Создаю новый плейлист: '{NEW_PLAYLIST_NAME}'...")
    payload = {
        "name": NEW_PLAYLIST_NAME,
        "public": False, # Создаем ПРИВАТНЫЙ (меньше ошибок с правами)
        "description": "Created by Bot"
    }
    try:
        # Прямой запрос к API (New Endpoint)
        res = sp._post("me/playlists", payload=payload)
        return res['id']
    except Exception as e:
        print(f"❌ Ошибка создания плейлиста: {e}")
        sys.exit(1)

def get_latest_tracks(sp):
    print("🔍 Сканирую подписки (это займет время)...")
    tracks = []
    
    # Получаем подписки
    artists = []
    results = sp.current_user_followed_artists(limit=50)
    artists.extend(results['artists']['items'])
    while results['artists']['cursors']['after']:
        results = sp.current_user_followed_artists(limit=50, after=results['artists']['cursors']['after'])
        artists.extend(results['artists']['items'])
        
    print(f"Найдено подписок: {len(artists)}")

    # Собираем треки
    for i, artist in enumerate(artists):
        try:
            # Берем альбомы и синглы
            albums = sp.artist_albums(artist['id'], album_type='album,single', country="UA", limit=1)
            if albums['items']:
                latest = albums['items'][0]
                # Берем треки
                t = sp.album_tracks(latest['id'], limit=1)
                if t['items']:
                    tracks.append(t['items'][0]['uri'])
        except:
            pass
        
        # Индикатор прогресса
        if i % 5 == 0:
            print(f"Обработано {i}/{len(artists)}...", end="\r")
            
    return list(set(tracks))

def main():
    sp = get_spotify_client()
    user_id = sp.current_user()['id']
    print(f"👤 Авторизован как: {user_id}")

    # 1. Собираем треки
    tracks = get_latest_tracks(sp)
    print(f"\n🎵 Найдено треков для добавления: {len(tracks)}")

    if not tracks:
        print("Нет треков для добавления. Выход.")
        return

    # 2. Создаем НОВЫЙ плейлист
    new_playlist_id = create_playlist_force(sp, user_id)
    print(f"✅ Плейлист создан! ID: {new_playlist_id}")

    # 3. Заливаем треки
    print("🚀 Добавляю треки...")
    for i in range(0, len(tracks), 50):
        chunk = tracks[i:i+50]
        try:
            sp.playlist_add_items(new_playlist_id, chunk)
            print(f"   Добавлена пачка {i}-{i+len(chunk)}")
        except Exception as e:
            print(f"   ❌ Ошибка добавления: {e}")
            
    print("\n" + "="*50)
    print("🎉 ВСЁ ГОТОВО! ТЕПЕРЬ САМОЕ ВАЖНОЕ:")
    print("="*50)
    print("1. Скопируйте этот ID:")
    print(f"\n{new_playlist_id}\n")
    print("2. Откройте файл .env (nano .env)")
    print("3. Замените старый PLAYLIST_ID на этот новый.")
    print("4. Запустите основного бота (spotify_bot.py).")
    print("="*50)

if __name__ == "__main__":
    main()