import os
from dotenv import load_dotenv
import requests

load_dotenv(dotenv_path="./.env")
API_KEY = os.getenv("API_KEY")
CHANNEL_HANDLE = "MrBeast"
MAX_RESULTS = 60
def get_playlist_id(channel_handle, api_key=API_KEY):
    try:
        url = f"https://youtube.googleapis.com/youtube/v3/channels?part=contentDetails&forHandle={channel_handle}&key={api_key}"
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        data = response.json()
        channel_items = data["items"]
        channel_playlist_id = channel_items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        return channel_playlist_id 
    except requests.exceptions.RequestException as e:
        raise e


def get_video_ids(base_url):
    page_token = None
    all_video_ids = []
    try:
        while True:
            url = base_url
            if page_token:
                url += f"&pageToken={page_token}"

            response = requests.get(url)

            response.raise_for_status()  # Check if the request was successful
            data = response.json()
            all_video_ids.extend(
                item["contentDetails"]["videoId"] for item in data["items"]
            )
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return all_video_ids
    except requests.exceptions.RequestException as e:
        raise e

if __name__ == "__main__":
    playlist_id = get_playlist_id(CHANNEL_HANDLE, API_KEY)
    print("Upload Playlist ID from function: " + playlist_id)
    base_url = f"https://youtube.googleapis.com/youtube/v3/playlistItems?part=contentDetails&maxResults={MAX_RESULTS}&playlistId={playlist_id}&key={API_KEY}"
    video_ids = get_video_ids(base_url)
    print("Video IDs from function: " + str(video_ids))