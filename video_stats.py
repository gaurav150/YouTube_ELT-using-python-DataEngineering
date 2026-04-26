import json
import os
from dotenv import load_dotenv
import requests
from datetime import date


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

def extract_video_ids(video_ids, api_key=API_KEY):
    """
    Loads snippet and statistics for each video ID via ``videos.list`` (batched).

    YouTube allows at most **50** ``id`` values per ``videos.list`` request; IDs are
    split into chunks of that size automatically.

    @param video_ids: List of YouTube video ID strings from ``get_video_ids``.
    @param api_key: YouTube Data API v3 key.
    @return: List of dicts with ``video_id``, ``title``, ``published_at``,
        ``view_count``, ``like_count``, ``comment_count`` (counts may be ``None``
        if the API omits them, e.g. likes hidden on some videos).
    @throws requests.exceptions.RequestException: If an HTTP request fails.
    @throws KeyError: If an item lacks ``id`` or ``snippet`` keys, or ``title`` /
        ``publishedAt`` under ``snippet`` (``statistics`` is read via ``.get`` and
        may be absent without raising).
    """
    extract_data = []

    def batch_list(video_list, batch_size=50):
        """Yields successive slices of ``video_list`` of length up to ``batch_size``."""
        for i in range(0, len(video_list), batch_size):
            yield video_list[i : i + batch_size]

    # videos.list allows at most 50 id values per call (playlistItems maxResults can differ).
    try:
        for batch in batch_list(video_ids, 50):
            video_ids_str = ",".join(batch)
            url = (
                "https://youtube.googleapis.com/youtube/v3/videos?"
                f"part=snippet&part=statistics&id={video_ids_str}&key={api_key}"
            )
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            for item in data.get("items", []):
                video_id = item["id"]
                title = item["snippet"]["title"]
                published_at = item["snippet"]["publishedAt"]
                statistics = item.get("statistics", {})

                extract_data.append(
                    {
                        "video_id": video_id,
                        "title": title,
                        "published_at": published_at,
                        "view_count": statistics.get("viewCount"),
                        "like_count": statistics.get("likeCount"),
                        "comment_count": statistics.get("commentCount"),
                    }
                )
    except requests.exceptions.RequestException as e:
        raise e

    return extract_data

def save_to_json(extracted_data):
    """
    Serializes ``extracted_data`` to a dated JSON file under ``./data/``.

    Output path is ``./data/YT_data_<YYYY-MM-DD>.json``, where the date is
    ``date.today()`` (local date). Writes with ``json.dump`` using ``indent=4``
    and ``ensure_ascii=False`` so the file is indented and non-ASCII characters
    (e.g. in titles) are stored as Unicode rather than ``\\u`` escapes.

    @param extracted_data: JSON-serializable payload, typically the list of dicts
        produced by ``extract_video_ids``.
    @return: ``None`` (side effect only: creates or overwrites the file).
    @throws OSError: If ``./data`` is not present (``open`` does not create it), the path is
        invalid, or the file cannot be written (permissions, disk full, etc.).
    @throws TypeError: If ``extracted_data`` contains objects that are not JSON-serializable.
    """
    file_path = f"./data/YT_data_{date.today()}.json"
    with open(file_path, "w") as json_file:
        json.dump(extracted_data, json_file, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    playlist_id = get_playlist_id(CHANNEL_HANDLE, API_KEY)
    base_url = f"https://youtube.googleapis.com/youtube/v3/playlistItems?part=contentDetails&maxResults={MAX_RESULTS}&playlistId={playlist_id}&key={API_KEY}"
    video_ids = get_video_ids(base_url)
    extracted_data = extract_video_ids(video_ids, API_KEY)
    save_to_json(extracted_data)
