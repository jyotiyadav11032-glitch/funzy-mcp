import os
import httpx
from mcp.server.fastmcp import FastMCP

API_KEY = os.environ["YOUTUBE_API_KEY"]
DEFAULT_HANDLE = os.environ.get("CHANNEL_HANDLE", "@FunzyShorts1j")
BASE = "https://www.googleapis.com/youtube/v3"

mcp = FastMCP(
    "youtube-channel",
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8000)),
)


def yt(path: str, **params):
    params["key"] = API_KEY
    r = httpx.get(f"{BASE}/{path}", params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def _channel(handle: str):
    data = yt(
        "channels",
        part="snippet,statistics,contentDetails",
        forHandle=handle,
    )
    items = data.get("items", [])
    if not items:
        raise ValueError(f"Channel not found: {handle}")
    return items[0]


@mcp.tool()
def get_channel_stats(handle: str = DEFAULT_HANDLE) -> dict:
    """Channel ke subscribers, total views aur video count."""
    c = _channel(handle)
    s = c["statistics"]
    return {
        "title": c["snippet"]["title"],
        "description": c["snippet"].get("description", ""),
        "subscribers": s.get("subscriberCount"),
        "total_views": s.get("viewCount"),
        "video_count": s.get("videoCount"),
        "created": c["snippet"].get("publishedAt"),
    }


@mcp.tool()
def list_recent_videos(handle: str = DEFAULT_HANDLE, max_results: int = 10) -> list:
    """Channel ke latest videos/Shorts, views, likes aur comments ke saath."""
    c = _channel(handle)
    uploads = c["contentDetails"]["relatedPlaylists"]["uploads"]
    pl = yt(
        "playlistItems",
        part="contentDetails",
        playlistId=uploads,
        maxResults=min(max_results, 50),
    )
    ids = [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
    if not ids:
        return []
    vids = yt("videos", part="snippet,statistics,contentDetails", id=",".join(ids))
    out = []
    for v in vids.get("items", []):
        st = v.get("statistics", {})
        out.append(
            {
                "video_id": v["id"],
                "title": v["snippet"]["title"],
                "published": v["snippet"]["publishedAt"],
                "duration": v["contentDetails"]["duration"],
                "views": st.get("viewCount"),
                "likes": st.get("likeCount"),
                "comments": st.get("commentCount"),
            }
        )
    return out


@mcp.tool()
def get_video_stats(video_id: str) -> dict:
    """Ek video ke title, tags, description aur stats."""
    data = yt("videos", part="snippet,statistics", id=video_id)
    items = data.get("items", [])
    if not items:
        raise ValueError("Video not found")
    v = items[0]
    return {
        "title": v["snippet"]["title"],
        "description": v["snippet"].get("description", ""),
        "tags": v["snippet"].get("tags", []),
        "published": v["snippet"]["publishedAt"],
        "stats": v.get("statistics", {}),
    }


@mcp.tool()
def search_channel_videos(query: str, handle: str = DEFAULT_HANDLE) -> list:
    """Channel ke andar title/keyword se video dhoondo."""
    c = _channel(handle)
    data = yt(
        "search",
        part="snippet",
        channelId=c["id"],
        q=query,
        type="video",
        maxResults=10,
    )
    return [
        {"video_id": i["id"]["videoId"], "title": i["snippet"]["title"]}
        for i in data.get("items", [])
    ]


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
