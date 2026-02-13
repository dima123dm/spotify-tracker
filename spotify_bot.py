import os
import time
import schedule
import json
import sys
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime
from dotenv import load_dotenv

# ================= НАСТРОЙКИ =================
FIRST_RUN_MODE = True  
DATABASE_FILE = "bot_data.json"

# !!! ОГРАНИЧИТЕЛЬ ДЛЯ ТЕСТА !!!
# Если True, бот проверит только 3-х артистов и остановится.
# Если всё ок — поменяешь на False, чтобы он работал дальше.
TEST_LIMIT_ENABLED = True 
# =============================================

load_dotenv()

CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
PLAYLIST_ID = os.getenv("PLAYLIST_ID")

SCOPE = "user-follow-read playlist-modify-public playlist-modify-private"

def get_spotify_client():
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        open_browser=False,
        cache_handler=spotipy.cache_handler.CacheFileHandler(cache_path=".cache")
    )
    return spotipy.Spotify(auth_manager=auth_manager)

def load_data():
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'r') as f:
            return json.load(f)
    return {"last_checked_date": "2000-01-01"}

def save_data(date_str):
    with open(DATABASE_FILE, 'w') as f:
        json.dump({"last_checked_date": date_str}, f)

def get_all_followed_artists(sp):
    artists = []
    try:
        results = sp.current_user_followed_artists(limit=50)
        artists.extend(results['artists']['items'])
        # Если включен тест, нам не нужны ВСЕ страницы, хватит первой
        if not TEST_LIMIT_ENABLED:
            while results['artists']['cursors']['after']:
                results = sp.current_user_followed_artists(
                    limit=50, 
                    after=results['artists']['cursors']['after']
                )
                artists.extend(results['artists']['items'])
    except Exception as e:
        print(f"Ошибка получения подписок: {e}")
    return artists

def get_latest_track_for_artist(sp, artist_id):
    try:
        albums = sp.artist_albums(artist_id, album_type='album,single', country="UA", limit=1)
        if not albums['items']:
            return None, None
        
        latest_album = albums['items'][0]
        tracks = sp.album_tracks(latest_album['id'], limit=1)
        if tracks['items']:
            return tracks['items'][0]['uri'], latest_album['release_date']
    except:
        pass
    return None, None

def add_tracks_force(sp, playlist_id, track_uris):
    if not track_uris: return
    
    print(f"   > Попытка добавить {len(track_uris)} трек(ов)...")
    
    # Прямой метод (самый надежный для новых API)
    try:
        url = f"playlists/{playlist_id}/tracks"
        sp._post(url, payload={"uris": track_uris}) 
        print("   ✅ УСПЕШНО ДОБАВЛЕНО! (Direct API)")
    except Exception as e:
        print(f"   ❌ Ошибка добавления: {e}")
        try:
            # Запасной вариант (библиотечный)
            sp.playlist_add_items(playlist_id, track_uris)
            print("   ✅ УСПЕШНО ДОБАВЛЕНО! (Lib method)")
        except Exception as e2:
             print(f"   ❌ И запасной метод не сработал: {e2}")

def initial_fill_playlist():
    print("\n=== ЗАПУСК: БЕЗОПАСНЫЙ ТЕСТ ===")
    sp = get_spotify_client()
    
    # Проверка прав сразу
    try:
        me = sp.current_user()
        print(f"Авторизован как: {me['display_name']}")
    except:
        print("ОШИБКА АВТОРИЗАЦИИ. Удали .cache")
        return

    artists = get_all_followed_artists(sp)
    print(f"Всего подписок найдено: {len(artists)}")
    
    # === ЛИМИТ ДЛЯ ТЕСТА ===
    if TEST_LIMIT_ENABLED:
        artists = artists[:3]
        print(f"⚠️ ТЕСТОВЫЙ РЕЖИМ: Проверяем только первых 3 артистов!")
    # =======================
    
    latest_global_date = "2000-01-01"
    
    for i, artist in enumerate(artists):
        print(f"[{i+1}/{len(artists)}] {artist['name']}...", end=" ")
        
        track_uri, release_date = get_latest_track_for_artist(sp, artist['id'])
        
        if track_uri:
            print(f"Нашел трек! Пробую добавить...")
            # В ТЕСТЕ ДОБАВЛЯЕМ СРАЗУ ПО ОДНОМУ, ЧТОБЫ ВИДЕТЬ РЕЗУЛЬТАТ
            add_tracks_force(sp, PLAYLIST_ID, [track_uri])
            
            if release_date > latest_global_date:
                latest_global_date = release_date
        else:
            print("Нет треков.")

        # БОЛЬШАЯ ПАУЗА ДЛЯ БЕЗОПАСНОСТИ
        time.sleep(3)

    print("\n=== ТЕСТ ЗАВЕРШЕН ===")
    print("Если ты увидел 'УСПЕШНО ДОБАВЛЕНО', значит всё работает.")
    print("Теперь можно отключить TEST_LIMIT_ENABLED в коде, но лучше делать это завтра,")
    print("либо запускать очень осторожно.")
    
    if not TEST_LIMIT_ENABLED:
        save_data(latest_global_date)

if __name__ == "__main__":
    if FIRST_RUN_MODE:
        initial_fill_playlist()
    else:
        # Тут код для обычной работы
        pass