from flask import Flask, render_template, request, redirect, url_for, session
import requests
import openai
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import urllib.request
import json
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Use environment variables


# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'pleaseletthiswork'

# API Keys (Replace with actual keys)
ACC_WEATHER_API_KEY = os.getenv('ACC_WEATHER_API_KEY')
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
REDIRECT_URI = 'https://theratunes1-638d9fb1fbf8.herokuapp.com/callback'
SCOPE = 'playlist-modify-public'



sp_oauth = spotipy.SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                        client_secret=SPOTIFY_CLIENT_SECRET,
                        redirect_uri=REDIRECT_URI,
                        scope=SCOPE)


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect(url_for('mood'))

@app.route('/mood', methods=['GET', 'POST'])
def mood():
    if request.method == 'POST':
        city = request.form.get('city')
        weather = get_weather(city)
    else:
        city = None
        weather = None
    return render_template('mood.html', city=city, weather=weather)

@app.route('/generate', methods=['POST'])
def generate():
    mood = request.form.get('mood')
    city = request.form.get('city')
    if not city or not mood:
        return "Missing city or mood", 400  # Return a 400 Bad Request error if city or mood is missing

    weather = get_weather(city)

    # Retrieve the access token from the session
    token_info = session.get('token_info', None)
    if not token_info:
        # Redirect to login if there is no token_info in session
        return redirect(url_for('login'))
    access_token = token_info.get('access_token')

    song_list = generate_song_list(mood, weather)
    playlist_link = create_spotify_playlist(song_list, access_token)
    return render_template('playlist.html', playlist_link=playlist_link, weather=weather)

def urlifier(rawCity):
    city = ""
    for c in rawCity:
        if c == " ":
            city+="%20"
        elif c ==",":
            city+="%2C"
        else:
            city += c
    return city

def get_weather(city):
    url = "http://dataservice.accuweather.com/locations/v1/cities/search?apikey="+ACC_WEATHER_API_KEY+"&q=" + urlifier(city)
    with urllib.request.urlopen(url) as url:
        data=json.loads(url.read().decode())
    try:
        loc_key = data[0]['Key']
    except:
        print("Invalid Location. Please enter another:")


    weathUrl = "http://dataservice.accuweather.com/currentconditions/v1/"+loc_key+"?apikey=" + ACC_WEATHER_API_KEY
    with urllib.request.urlopen(weathUrl) as weather:
        data=json.loads(weather.read().decode())
    conditions = data[0]['WeatherText']
    temp = data[0]['Temperature']['Imperial']['Value']

    return "It is " + str(temp) + " degrees Farenheit and " + conditions

def generate_song_list(mood, weather):
    openai.api_key = OPENAI_API_KEY
    response = openai.Completion.create(
      model="text-davinci-003",
      prompt=f"Create a playlist with 20 songs for mood: {mood}, and weather: {weather}.",
      max_tokens=100
    )
    songs = response.choices[0].text.strip().split('\n')
    return songs

def create_spotify_playlist(song_list, access_token):
    if not access_token:  # Check if the access token is provided
        raise Exception("Access token must be provided.")
    if not song_list:
        return None
    spotify = spotipy.Spotify(auth=access_token)
    user_id = spotify.me()['id']  # This line will raise an error if the access token is invalid or expired
    playlist = spotify.user_playlist_create(user_id, "Generated Playlist", public=True)
    track_ids = []
    for song in song_list:
        if song:
            search_result = spotify.search(q=song, type='track', limit=1)
            if search_result['tracks']['items']:
                track_id = search_result['tracks']['items'][0]['id']
                track_ids.append(track_id)
    if track_ids:
        spotify.user_playlist_add_tracks(user_id, playlist['id'], track_ids)
    return playlist['external_urls']['spotify']
if __name__ == "__main__":
    app.run(debug=True)

