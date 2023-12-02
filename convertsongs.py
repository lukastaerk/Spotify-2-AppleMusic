import argparse
from sys import argv
import csv
import urllib.parse, urllib.request
import json
from time import sleep
import requests
import os

SLEEPING_SEC = 1
BASE_URL_AM = "https://amp-api.music.apple.com/v1"
# Checking if the command is correct
if len(argv) > 1 and argv[1]:
    pass
else:
    print('\nCommand usage:\npython3 convertsongs.py yourplaylist.csv\nMore info at https://github.com/therealmarius/Spotify-2-AppleMusic')
    exit()

# Function to get contents of file if it exists
def get_connection_data(f,prompt):
    if os.path.exists(f):
        with open(f,'r') as file:
            return file.read().rstrip('\n')
    else:
            return input(prompt)

def get_all_my_playlists(session):
    url = f"{BASE_URL_AM}/me/library/playlists"
    all_playlists = {}
    limit = 100  # Adjust as per API's allowed maximum
    offset = 0

    while True:
        params = {'limit': limit, 'offset': offset}
        response = session.get(url, params=params)
        if response.status_code != 200:
            break

        data = response.json()
        playlists = data.get('data', [])
        all_playlists.update([(pl['attributes']['name'], pl['id']) for pl in playlists])

        if len(playlists) < limit:
            break  # No more playlists to fetch
        offset += limit

    return all_playlists

def create_apple_music_playlist(session, playlist_name, all_my_playlists, description="A new playlist created via API"):
    url = f"{BASE_URL_AM}/me/library/playlists"
    data = {
        'attributes': {
            'name': playlist_name,
            'description': description,
        }
    }
    
    if playlist_name in all_my_playlists:
        print(f"Playlist {playlist_name} already exists!")
        return all_my_playlists[playlist_name]
    
    response = session.post(url, json=data)
    if response.status_code == 201:
        sleep(SLEEPING_SEC)
        return response.json()['data'][0]['id']
    else:
        raise Exception(f"Error {response.status_code} while creating playlist {playlist_name}!")
        return None
    
# Getting user's data for the connection
token = get_connection_data("token.dat", "\nPlease enter your Apple Music Authorization (Bearer token):\n")
media_user_token = get_connection_data("media_user_token.dat", "\nPlease enter your media user token:\n")
cookies = get_connection_data("cookies.dat", "\nPlease enter your cookies:\n")

# playlist_identifier = input("\nPlease enter the playlist identifier:\n")

# function to escape apostrophes
def escape_apostrophes(s):
    return s.replace("'", "\\'")

# Function to get the iTunes ID of a song
def get_itunes_id(title, artist, album):
    BASE_URL = "https://itunes.apple.com/search?country=FR&media=music&entity=song&limit=5&term="
    # Search the iTunes catalog for a song
    try:
        # Search for the title + artist + album
        url = BASE_URL + urllib.parse.quote(title + " " + artist + " " + album)
        request = urllib.request.Request(url)
        response = urllib.request.urlopen(request)
        data = json.loads(response.read().decode('utf-8'))
        # If no result, search for the title + artist
        if data['resultCount'] == 0:
            url = BASE_URL + urllib.parse.quote(title + " " + artist)
            request = urllib.request.Request(url)
            response = urllib.request.urlopen(request)
            data = json.loads(response.read().decode('utf-8'))
            # If no result, search for the title + album
            if data['resultCount'] == 0:
                url = BASE_URL + urllib.parse.quote(title + " " + album)
                request = urllib.request.Request(url)
                response = urllib.request.urlopen(request)
                data = json.loads(response.read().decode('utf-8'))
                # If no result, search for the title
                if data['resultCount'] == 0:
                    url = BASE_URL + urllib.parse.quote(title)
                    request = urllib.request.Request(url)
                    response = urllib.request.urlopen(request)
                    data = json.loads(response.read().decode('utf-8'))
    except:
        return print("An error occured with the request.")
    
    # Try to match the song with the results
    try:
        response = urllib.request.urlopen(request)
        data = json.loads(response.read().decode('utf-8'))
        
        for each in data['results']:
            #Trying to match with the exact track name, the artist name and the album name
            if each['trackName'].lower() == title.lower() and each['artistName'].lower() == artist.lower() and each['collectionName'].lower() == album.lower():
                return each['trackId']           
            #Trying to match with the exact track name and the artist name
            elif each['trackName'].lower() == title.lower() and each['artistName'].lower() == artist.lower():
                return each['trackId']
            #Trying to match with the exact track name and the album name
            elif each['trackName'].lower() == title.lower() and each['collectionName'].lower() == album.lower():
                return each['trackId']
            #Trying to match with the exact track name and the artist name, in the case artist name are different between Spotify and Apple Music
            elif each['trackName'].lower() == title.lower() and (each["artistName"].lower() in artist.lower() or artist.lower() in each["artistName"].lower()):
                return each['trackId']
            #Trying to match with the exact track name and the album name, in the case album name are different between Spotify and Apple Music
            elif each['trackName'].lower() == title.lower() and (each["collectionName"].lower() in album.lower() or album.lower() in each["collectionName"].lower()):
                return each['trackId']  
            #Trying to match with the exact track name
            elif each['trackName'].lower() == title.lower():
                return each['trackId']        
            #Trying to match with the track name, in the case track name are different between Spotify and Apple Music
            elif title.lower() in each['trackName'] or each['trackName'].lower() in title.lower():
                return each['trackId']
        try:
            #If no result, return the first result
            return data['results'][0]['trackId']
        except:
            #If no result, return None
            return None
    except:
        #The error is handled later in the code
        return None

# Function to add a song to a playlist
def add_song_to_playlist(session, song_id, playlist_id, playlist_name):
    try:   
        request = session.post(f"{BASE_URL_AM}/me/library/playlists/{playlist_id}/tracks", json={"data":[{"id":f"{song_id}","type":"songs"}]})
        # Checking if the request is successful
        if requests.codes.ok:
            print(f"Song {song_id} added to playlist {playlist_name}!")
            return True
        # If not, print the error code
        else: 
            print(f"Error {request.status_code} while adding song {song_id} to playlist {playlist_name}!")
            return False
    except:
        print(f"HOST ERROR: Apple Music might have blocked the connection during the add of {song_id} to playlist {playlist_name}!\nPlease wait a few minutes and try again.\nIf the problem persists, please contact the developer.")
        return False

def get_playlist_track_ids(session, playlist_id):
    # test if song is already in playlist
    try:
        response = session.get(f"{BASE_URL_AM}/me/library/playlists/{playlist_id}/tracks")
        if response.status_code == 200:
            #print(response.json()['data'])
            return [track['attributes']['playParams']['catalogId'] for track in response.json()['data']]
        elif response.status_code == 404:
            return []
        else:
            raise Exception(f"Error {response.status_code} while getting playlist {playlist_id}!")
            return None
    except:
        raise Exception(f"Error while getting playlist {playlist_id}!")
        return None
# Opening session
def create_playlist_and_add_song(session, file, all_my_playlists):
    
    # Getting the playlist name
    playlist_name = os.path.basename(file)
    playlist_name = playlist_name.split('.')
    playlist_name = playlist_name[0]

    playlist_identifier = create_apple_music_playlist(session, playlist_name, all_my_playlists)

    playlist_track_ids = get_playlist_track_ids(session, playlist_identifier)
    print(playlist_track_ids)
    # Opening the inputed CSV file
    with open(str(file), encoding='utf-8') as file:
        file = csv.reader(file)
        next(file)
        # Initializing variables for the stats
        n = 0
        converted = 0
        failed = 0
        # Looping through the CSV file
        for row in file:
            n += 1
            # Trying to get the iTunes ID of the song
            title, artist, album = escape_apostrophes(
                row[1]), escape_apostrophes(row[3]), escape_apostrophes(row[5])
            track_id = get_itunes_id(title, artist, album)
            # If the song is found, add it to the playlist
            if track_id:
                if str(track_id) in playlist_track_ids:
                    print(f'\nN°{n} | {title} | {artist} | {album} => {track_id}')
                    print(f"Song {track_id} already in playlist {playlist_name}!")
                    failed += 1
                    continue
                print(f'\nN°{n} | {title} | {artist} | {album} => {track_id}')
                if add_song_to_playlist(s, track_id, playlist_identifier, playlist_name):
                    converted += 1
                else:
                    failed += 1
            # If not, write it in a file
            else:
                print(f'N°{n} | {title} | {artist} | {album} => NOT FOUND')
                with open(f'noresult.csv', 'a+', encoding='utf-8') as f:
                    f.write(f'{playlist_name};{title};{artist};{album}; NOT FOUND\n')
                failed += 1
            sleep(SLEEPING_SEC)
    # Printing the stats report
    print(f'\n - STAT REPORT -\nPlaylist Songs: {n}\nConverted Songs: {converted}\nFailed Songs: {failed}\nPlaylist converted at {round(converted/n*100)}%')

def add_albums_to_library(session, albums):
    for item in albums:
        album = item['album']
        artist = item['artist']
        album_id = get_album_id(session, album, artist)
        if album_id:
            ans = session.post(f"{BASE_URL_AM}/me/library?ids[albums]={album_id}", json=[])  
            if ans.status_code == 202:
                print(f"Album {album} by {artist} added to library!")
            else:
                print(f"Error {ans.status_code} while adding album {album} by {artist} to library!")
        else:
            print(f"Album {album} by {artist} not found!")
            with open(f'albums_noresult.csv', 'a+', encoding='utf-8') as f:
                f.write(f'{album};{artist}; NOT FOUND\n')
            continue
        
def get_album_id(session, album_name, artist_name):
    storefront = "us"  # change to the appropriate country or region code
    base_url = f"{BASE_URL_AM}/catalog/{storefront}/search"
    query = {
        'term': f'{album_name} {artist_name}',
        'types': 'albums',
        'limit': 5  # assuming you want the first match
    }
    response = session.get(base_url, params=query)
    if response.status_code == 200:
        results = response.json().get('results', {}).get('albums', {}).get('data', [])
        if results:
            return results[0]['id']  # returns the ID of the first album found
        else:
            return None
    else:
        print(f"Error {response.status_code} while getting album {album_name} by {artist_name}!")
        return None
    
def argument_parsing():
    parser = argparse.ArgumentParser(description='Convert a Spotify playlist, your liked albums or artists to Apple Music.')
    parser.add_argument('-p', '--playlist', type=str, help='playlist csv-file or directory containing playlist csv-files')
    parser.add_argument('-a', '--albums', type=str, help='YourLibrary.json from your Spotify data')
    return parser.parse_args()

if __name__ == "__main__":
    args = argument_parsing()
    with requests.Session() as s:
        s.headers.update({"Authorization": f"{token}",
                    "media-user-token": f"{media_user_token}",
                    "Cookie": f"{cookies}",
                    "Host": "amp-api.music.apple.com",
                    "Accept-Encoding":"gzip, deflate, br",
                    "Referer": "https://music.apple.com/",
                    "Origin": "https://music.apple.com",
                    "Content-Length": "45",
                    "Connection": "keep-alive",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-site",
                    "TE": "trailers"})
        
    if args.playlist:
        all_my_playlists = get_all_my_playlists(s)
        if ".csv" in args.playlist:
            create_playlist_and_add_song(s, args.playlist, all_my_playlists)
        else:
            # get all csv files in the directory argv[1]
            files = [f for f in os.listdir(args.playlist) if os.path.isfile(os.path.join(args.playlist, f))]
            # loop through all csv files
            for file in files:
                if ".csv" in file:
                    create_playlist_and_add_song(s, os.path.join(args.playlist, file), all_my_playlists)
    if args.albums:
        json_file = open(args.albums, encoding='utf-8')
        json_data = json.load(json_file)
        json_file.close()
        albums = json_data['albums']
        add_albums_to_library(s, albums)

# Developped by @therealmarius on GitHub
# Based on the work of @simonschellaert on GitHub
# Github project page: https://github.com/therealmarius/Spotify-2-AppleMusic