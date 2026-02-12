import os
import time
import schedule
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime
from dotenv import load_dotenv

# ================= НАСТРОЙКИ =================
# Поставь True для самого первого запуска, чтобы заполнить плейлист.
# После успешного заполнения поменяй на False.
FIRST_RUN_MODE = True  

# Имя файла базы данных
DATABASE_FILE = "bot_data.json"
# =============================================

# Загрузка переменных окружения
load_dotenv()

# Конфигурация из .env
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
PLAYLIST_ID = os.getenv("PLAYLIST_ID")

# Права доступа
SCOPE = "user-follow-read playlist-modify-public playlist-modify-private"

def get_spotify_client():
    """Авторизация. open_browser=False критично для VPS."""
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        open_browser=False,  # Не открывать браузер автоматически
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
    """Получает полный список подписок (с обходом страниц)"""
    artists = []
    results = sp.current_user_followed_artists(limit=50)
    artists.extend(results['artists']['items'])
    
    while results['artists']['cursors']['after']:
        results = sp.current_user_followed_artists(
            limit=50, 
            after=results['artists']['cursors']['after']
        )
        artists.extend(results['artists']['items'])
    return artists

def get_latest_track_for_artist(sp, artist_id):
    """Находит самый новый трек артиста"""
    try:
        # Берем альбомы и синглы, доступные в Украине
        albums = sp.artist_albums(artist_id, album_type='album,single', country="UA", limit=5)
        if not albums['items']:
            return None, None
        
        # Сортируем релизы по дате (свежие сверху)
        sorted_albums = sorted(albums['items'], key=lambda x: x['release_date'], reverse=True)
        latest_album = sorted_albums[0]
        
        # Берем первый трек из этого релиза
        tracks = sp.album_tracks(latest_album['id'], limit=1)
        if tracks['items']:
            return tracks['items'][0]['uri'], latest_album['release_date']
    except Exception as e:
        print(f"Ошибка при поиске трека: {e}")
    return None, None

def initial_fill_playlist():
    """
    РЕЖИМ ПЕРВОГО ЗАПУСКА:
    Проходит по всем подпискам и добавляет по 1 последнему треку.
    """
    print("\n=== ЗАПУЩЕН РЕЖИМ ПЕРВИЧНОГО ЗАПОЛНЕНИЯ ===")
    print("Это может занять время, если подписок много...\n")
    
    sp = get_spotify_client()
    artists = get_all_followed_artists(sp)
    print(f"Всего подписок: {len(artists)}")
    
    tracks_to_add = []
    latest_global_date = "2000-01-01"
    
    for i, artist in enumerate(artists):
        print(f"[{i+1}/{len(artists)}] Проверка: {artist['name']}...", end="\r")
        track_uri, release_date = get_latest_track_for_artist(sp, artist['id'])
        
        if track_uri:
            tracks_to_add.append(track_uri)
            if release_date > latest_global_date:
                latest_global_date = release_date
        
        # Небольшая задержка, чтобы API не ругался
        if i % 10 == 0:
            time.sleep(0.5)

    print(f"\nНайдено треков для добавления: {len(tracks_to_add)}")
    
    # Добавляем пачками по 100 (лимит Spotify)
    if tracks_to_add:
        unique_uris = list(set(tracks_to_add))
        for i in range(0, len(unique_uris), 100):
            batch = unique_uris[i:i+100]
            try:
                sp.playlist_add_items(PLAYLIST_ID, batch)
                print(f"Добавлена пачка {i} - {i+len(batch)}")
            except Exception as e:
                print(f"Ошибка при добавлении в плейлист: {e}")
        
        # Сохраняем дату самого свежего найденного трека
        save_data(latest_global_date)
        print(f"\n✅ Готово! Плейлист заполнен. Дата обновлена на: {latest_global_date}")
        print("ВАЖНО: Теперь открой код и поменяй FIRST_RUN_MODE = False")
        sys.exit(0) # Завершаем работу, чтобы юзер поменял настройку
    else:
        print("Треков не найдено.")

def check_new_releases():
    """Обычный режим: проверка новинок"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Проверка новых релизов...")
    
    try:
        sp = get_spotify_client()
        data = load_data()
        last_date = data["last_checked_date"]
        
        artists = get_all_followed_artists(sp)
        new_tracks = []
        new_max_date = last_date
        
        print(f"Сканирую {len(artists)} артистов (ищем новее {last_date})...")
        
        for artist in artists:
            albums = sp.artist_albums(artist['id'], limit=5, country="UA")
            for album in albums['items']:
                if album['release_date'] > last_date:
                    print(f"НОВИНКА: {artist['name']} - {album['name']} ({album['release_date']})")
                    
                    tracks = sp.album_tracks(album['id'])
                    for track in tracks['items']:
                        new_tracks.append(track['uri'])
                    
                    if album['release_date'] > new_max_date:
                        new_max_date = album['release_date']

        if new_tracks:
            unique_uris = list(set(new_tracks))
            for i in range(0, len(unique_uris), 100):
                sp.playlist_add_items(PLAYLIST_ID, unique_uris[i:i+100])
            
            save_data(new_max_date)
            print(f"Добавлено {len(unique_uris)} новых треков.")
        else:
            print("Новинок нет.")
            
    except Exception as e:
        print(f"Ошибка проверки: {e}")

if __name__ == "__main__":
    import sys
    
    if FIRST_RUN_MODE:
        initial_fill_playlist()
    else:
        print("Бот запущен в режиме наблюдения.")
        print("Расписание: 09:00 и 21:00.")
        
        # Сразу проверяем при запуске
        check_new_releases()

        schedule.every().day.at("09:00").do(check_new_releases)
        schedule.every().day.at("21:00").do(check_new_releases)

        while True:
            schedule.run_pending()
            time.sleep(60)