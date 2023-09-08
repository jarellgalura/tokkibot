from flask import Flask, request, redirect
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime, timedelta
import threading

app = Flask(__name__)

# Discord bot token and Spotify API credentials (use the same values as in hanni_spotify.py)
TOKEN = 'MTE0NDE2NDM4ODE1NzI3MjEzNw.G9QUlB.UfLDKULtmSlbrb33YT1mCJ7n1sEb8puQobX_jI'
SPOTIPY_CLIENT_ID = 'af74290356b04ceaa1d039600b12f93d'
SPOTIPY_CLIENT_SECRET = 'c97a59c90e9c4449b3938cccd40a4f37'
SPOTIPY_REDIRECT_URI = 'http://localhost:5000/callback'
# Initialize Spotipy with OAuth2
sp_oauth = SpotifyOAuth(SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI,
                        scope='user-library-read user-read-recently-played user-top-read user-read-playback-state')


@app.route('/callback')
def callback():
    auth_code = request.args.get('code')
    token_info = sp_oauth.get_access_token(auth_code)
    if 'error' in token_info:
        return f"Authorization failed: {token_info['error']}"
    return "Authorization successful. You can now close this page."


def run_flask():
    app.run(host='0.0.0.0', port=5000)


if __name__ == '__main__':
    # Start the Flask web server
    threading.Thread(target=run_flask).start()
