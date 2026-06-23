from fastapi import APIRouter
import requests
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

YOUTUBE_API_KEY = os.getenv(
    "YOUTUBE_API_KEY"
)


@router.get("/videos")
def search_videos(topic: str):

    url = (
        "https://www.googleapis.com/youtube/v3/search"
    )

    params = {
        "part": "snippet",
        "q": topic,
        "type": "video",
        "maxResults": 5,
        "key": YOUTUBE_API_KEY
    }

    response = requests.get(
        url,
        params=params
    )

    data = response.json()

    videos = []

    for item in data.get(
        "items",
        []
    ):

        videos.append({

            "videoId":
            item["id"]["videoId"],

            "title":
            item["snippet"]["title"],

            "thumbnail":
            item["snippet"]["thumbnails"]
            ["high"]["url"],

            "channel":
            item["snippet"]["channelTitle"]
        })

    return {
        "videos": videos
    }