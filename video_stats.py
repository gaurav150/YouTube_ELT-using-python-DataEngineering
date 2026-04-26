import os
from dotenv import load_dotenv
import requests

load_dotenv(dotenv_path="./.env")
API_KEY = os.getenv("API_KEY")
CHANNEL_HANDLE = "MrBeast"
MAX_RESULTS = 60


def get_playlist_id(channel_handle, api_key=API_KEY):
    """
    Resolves a channel's **uploads** playlist ID from its YouTube handle.

    Calls the YouTube Data API v3 ``channels.list`` endpoint with
    ``part=contentDetails`` and ``forHandle``, then reads
    ``contentDetails.relatedPlaylists.uploads`` from the first channel in
    ``items``. That playlist ID is what you pass to ``playlistItems.list`` to
    enumerate videos the channel has uploaded.

    @param channel_handle: YouTube @handle without the leading ``@`` (e.g. ``"MrBeast"``).
    @param api_key: YouTube Data API v3 key (defaults to ``API_KEY`` from environment).
    @return: The uploads playlist ID as a string (e.g. ``"UU..."``).
    @throws requests.exceptions.RequestException: If the HTTP request fails or the response is not successful (4xx/5xx).
    @throws (KeyError, IndexError): If the JSON has no ``items``, empty ``items``, or missing nested keys.
    """
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
    """
    Fetches **all** video IDs from a YouTube playlist using paginated API calls.

    Repeatedly requests ``playlistItems.list`` using the query string embedded in
    ``base_url`` (which must already include ``playlistId``, ``key``,
    ``part=contentDetails``, ``maxResults``, etc.). When the API returns a
    ``nextPageToken``, appends ``&pageToken=...`` and continues until no token
    remains. Collects ``contentDetails.videoId`` from every item on every page.

    @param base_url: Full URL for the first ``playlistItems`` request, including all required query parameters except ``pageToken`` (that is added automatically for later pages).
    @return: List of video ID strings, in playlist order, across all pages.
    @throws requests.exceptions.RequestException: If any HTTP request fails or the response is not successful (4xx/5xx).
    @throws KeyError: If a response item is missing ``contentDetails`` or ``videoId``.
    """
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