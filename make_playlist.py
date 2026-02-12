import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os

load_dotenv()

# Название нового плейлиста
NEW_PLAYLIST_NAME = "Spotify Tracker Music"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="user-follow-read playlist-modify-public playlist-modify-private",
    open_browser=False,
    cache_handler=spotipy.cache_handler.CacheFileHandler(cache_path=".cache")
))

try:
    user_id = sp.current_user()['id']

    # Создаем плейлист (приватный, чтобы точно не было ошибок прав)
    playlist = sp.user_playlist_create(user_id, NEW_PLAYLIST_NAME, public=False, description="Плейлист создан ботом")

    print("\n" + "="*40)
    print(f"✅ УСПЕШНО! Плейлист '{NEW_PLAYLIST_NAME}' создан.")
    print("="*40)
    print(f"ЕГО ID: {playlist['id']}")
    print("="*40)
    print("Скопируйте этот ID и вставьте в файл .env вместо старого!")
    print("="*40 + "\n")

except Exception as e:
    print(f"Ошибка: {e}")