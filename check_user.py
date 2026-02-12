import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os

load_dotenv()

# Настройки авторизации
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="user-follow-read playlist-modify-public playlist-modify-private",
    open_browser=False,
    cache_handler=spotipy.cache_handler.CacheFileHandler(cache_path=".cache")
))

try:
    # 1. Кто сейчас авторизован?
    current_user = sp.current_user()
    user_id = current_user['id']
    user_name = current_user['display_name']
    
    # 2. Чей плейлист?
    playlist_id = os.getenv("PLAYLIST_ID")
    playlist = sp.playlist(playlist_id)
    owner_id = playlist['owner']['id']
    owner_name = playlist['owner']['display_name']

    print("\n" + "="*30)
    print("       РЕЗУЛЬТАТЫ ПРОВЕРКИ")
    print("="*30)
    print(f"Вы авторизовали бота как:   {user_name} (ID: {user_id})")
    print(f"Владелец плейлиста:         {owner_name} (ID: {owner_id})")
    print("-" * 30)

    if user_id != owner_id:
        print("❌ ОШИБКА: ЭТО РАЗНЫЕ АККАУНТЫ!")
        print("Вы вошли в браузере не в тот аккаунт, на котором создан плейлист.")
        print("РЕШЕНИЕ: Выйди из Spotify в браузере и авторизуйся заново.")
    else:
        print("✅ Аккаунты совпадают.")
        print("❌ Если ошибка 403 осталась, значит вы не дали права (галочки) при входе.")
        print("РЕШЕНИЕ: Удалите .cache и примите соглашение заново ВНИМАТЕЛЬНО.")
    print("="*30 + "\n")

except Exception as e:
    print(f"Ошибка проверки: {e}")