import sys # for sys.exit
import argparse # for cmd line args, like host mode
import socket # server system
import json # for serializing and deserializing data
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pprint import pprint
import requests
from time import sleep
import datetime
import threading


#TODO: add functionality for passing IP and port with cmd line args, for connecting as well as hosting
#TODO: multiple client support https://stackoverflow.com/a/61918942

scope = "user-read-playback-state user-modify-playback-state user-read-currently-playing user-read-playback-position streaming"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id="952433cc2fe94c069626be1bf33cddea", client_secret="2519a53239ca4c339728a611c8e7059d", redirect_uri="http://localhost:8080/", scope=scope))

def handle_client(conn): # https://stackoverflow.com/a/61918942
    connected_users = []
    username = conn.recv(1024).decode()
    connected_users.append(username)
    print(f"\r[!] {username} has connected to the session" + " " * 55)  

    data_string = json.dumps(sp.current_playback()) # Playback data serialized
    conn.send(data_string.encode()) # Send playback data to client for initial sync on connect
    # print("\nConnected users:\n")
    print(f"\nConnected users: {', '.join(str(user) for user in connected_users)}", end="\r")
    while True: # Keep sending playback data of the host so client can stay synced
        data_string = json.dumps(sp.current_playback()) # Playback data serialized
        try:
            conn.send(data_string.encode())
            # print("Sent playback data to client") # debug
            desync_ms = conn.recv(1024).decode()
            # print(desync_ms)
             # https://stackoverflow.com/a/42757074
            sleep(1)
            
                        
        except ConnectionAbortedError: # Remote client has aborted the connection
            print(f"\r[!] {username} has left the session", flush=True)
            connected_users.remove(username)
            if connected_users: # If there are still connected users after a client disconnects
                print(f"\nConnected users: {', '.join(str(user) for user in connected_users)}", end="\r", flush=True) # https://stackoverflow.com/a/42757074
            else:
                print("\nThis session is currently empty. Invite people by sharing the remote client connect address.", end="\r")
            # print(f"{', '.join(str(user) for user in connected_users)}", end="\r", flush=True) # https://stackoverflow.com/a/42757074

            break


def host_session():
    # global connected_users
    
    # pprint(sp.current_playback());exit()
    local_ip = "192.168.2.6"
    public_ip = requests.get("http://v4.ident.me").text
    port = 35484
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((local_ip, port))
        print(f"[*] Server started on {local_ip}:{port}")
        print(f"[*] Connect address for remote clients is {public_ip}:{port}")
        print("======================================\n")

        s.listen()
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client,args=(conn,), daemon=True).start() 


def connect(ip="84.87.107.139", port=35484):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((ip, port))

        except TimeoutError:
            print("\n[!] Unable to connect to session.\n")
            sys.exit()

        print(f"[*] Connected to session")
        print("======================================\n")
        username = sp.me()["display_name"]
        s.sendall(username.encode())
        margin_pos = 500 # Amount of desync in ms allowed before resyncing to host
        margin_neg = -500

        playback_data = s.recv(32768) # Host playback data, used in client for syncing
        playback_data = json.loads(playback_data.decode()) # Reserialize the data

        if not playback_data: # Host currently not playing track
            print("Host is currently not playing a track, exiting." + " " * 20)
            sys.exit()

        current_track_uri = playback_data["item"]["uri"]
        host_progress = playback_data["progress_ms"] # Deserialized playback data

        sp.start_playback(uris=[current_track_uri], position_ms=host_progress) # Sync to host on joining session
        print("\nCurrently playing:\n") # Outside the loop because this only needs to be printed once

        while True:
            try: # Wrap in try/except to catch KeyboardInterrupt
                playback_data = s.recv(32768) # Receive new host playback data every second
                try:
                    playback_data = json.loads(playback_data.decode())
                except:
                    print("Host has ended the session or the session has been forcibly closed, exiting." + " " * 20)
                    sys.exit()

                current_track_uri = playback_data["item"]["uri"]
                host_progress = playback_data["progress_ms"] # Deserialized playback data
                client_progress = sp.current_playback()["progress_ms"] # Client track progress in ms
                track_duration = playback_data["item"]["duration_ms"] # Track duration in ms
                desync_ms = host_progress - client_progress # Amount of desync in ms

                if desync_ms > margin_pos or desync_ms < margin_neg: # If desync is more than allowed amount, resync client to host's track and track progress
                    sp.start_playback(uris=[current_track_uri], position_ms=host_progress)

                s.sendall(str(desync_ms).encode()) # Send desync to server for monitoring

                print(f"{track_progress(host_progress, track_duration)} {get_artists_and_name(playback_data)}", end="\r") # Currently playing track and its progress

                sleep(1)
            except KeyboardInterrupt:
                print("Keyboard interrupt received, exiting." + " " * 40)
                sys.exit()

def get_artists_and_name(songdata:dict):
    """
    Get a string that contains the artist(s) and the track name from the dictionary of playback info
    Returns a string in the form of Artist 1, Artist 2 - Track name
    """
    artists = ""
    for artist in songdata["item"]["artists"]:
        artists += artist["name"] + ", "
    
    artists = artists[:-2] # Remove trailing comma and whitespace
    song_name = songdata["item"]["name"]
    
    return f"{artists} - {song_name}" + " " * 40 # Adding 40 trailing spaces to make sure the previous track is completely overwritten by the current one

def track_progress(progress_ms, duration_ms):
    """
    Converts track progress and duration from ms to minutes and seconds
    """
    progress_mins = datetime.datetime.fromtimestamp(progress_ms/1000.0).strftime('%M:%S') # https://stackoverflow.com/a/56286922
    duration_mins = datetime.datetime.fromtimestamp(duration_ms/1000.0).strftime('%M:%S')

    return f"[{progress_mins} / {duration_mins}]"




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spotify sync listener")
    parser.add_argument("-H", "--host", action="store_true", help="Start the program in host mode")
    # parser.add_argument("-C", "--connect", type=str, help="Host to connect to, specify IP address and port number seperated by a space")
    parser.add_argument("-C", "--connect", action="store_true", help="Host to connect to, specify IP address and port number seperated by a colon") # temp version

    # IP and port args too maybe?

    args = parser.parse_args()

    print("""
   _____                  _  __       
  / ____|                (_)/ _|      
 | (___  _   _ _ __   ___ _| |_ _   _ 
  \___ \| | | | '_ \ / __| |  _| | | |
  ____) | |_| | | | | (__| | | | |_| |
 |_____/ \__, |_| |_|\___|_|_|  \__, |
          __/ |                  __/ |
         |___/                  |___/ 

======================================""")

    if args.host:
        host_session()

    if args.connect:
        connect()
