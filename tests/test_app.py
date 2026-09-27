import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from main import app, CookieRotator
from platforms.Youtube import YouTubeAPI, get_session, close_session

client = TestClient(app)


def test_cookie_rotator(tmp_path):
    cookies_dir = tmp_path / "cookies"
    cookies_dir.mkdir()
    c1 = cookies_dir / "cookie1.txt"
    c2 = cookies_dir / "cookie2.txt"
    c1.write_text("cookie1")
    c2.write_text("cookie2")

    rotator = CookieRotator(cookies_dir=str(cookies_dir))
    valid = rotator.get_valid_cookie_files()
    assert len(valid) == 2

    cookie = rotator.get_cookie()
    assert cookie in [str(c1), str(c2)]

    rotator.mark_bad(str(c1))
    valid = rotator.get_valid_cookie_files()
    assert len(valid) == 1
    assert str(c1) not in valid
    assert str(c1) + ".bad" in [str(p) for p in cookies_dir.glob("*")]


@patch("main.extract_sync")
def test_extract_endpoint_success(mock_extract):
    mock_extract.return_value = {
        "id": "abc12345",
        "title": "Test Song",
        "duration": 180,
        "thumbnail": "http://example.com/thumb.jpg",
        "url": "http://stream.url/audio.m4a",
        "uploader": "Test Uploader",
        "formats": [
            {
                "format_id": "140",
                "url": "http://stream.url/audio.m4a",
                "ext": "m4a",
                "acodec": "mp4a.40.2",
                "vcodec": "none",
            }
        ],
    }

    response = client.get("/extract?url=https://www.youtube.com/watch?v=abc12345")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert json_data["id"] == "abc12345"
    assert json_data["stream_url"] == "http://stream.url/audio.m4a"


@pytest.mark.asyncio
async def test_youtube_platform_search():
    yt_api = YouTubeAPI()
    url = await yt_api.search_youtube("https://www.youtube.com/watch?v=abc12345")
    assert url == "https://www.youtube.com/watch?v=abc12345"

    with patch("platforms.Youtube.VideosSearch") as MockVideosSearch:
        mock_instance = AsyncMock()
        mock_instance.next.return_value = {
            "result": [{"link": "https://www.youtube.com/watch?v=searched_id"}]
        }
        MockVideosSearch.return_value = mock_instance

        res = await yt_api.search_youtube("Tum Hi Ho")
        assert res == "https://www.youtube.com/watch?v=searched_id"


@pytest.mark.asyncio
async def test_youtube_platform_extract_stream():
    yt_api = YouTubeAPI()
    with patch.object(yt_api, "search_youtube", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = "https://www.youtube.com/watch?v=searched_id"
        mock_session = MagicMock()
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = {"status": "success", "stream_url": "http://stream.url"}

        # Async context manager mock
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_resp
        mock_session.get.return_value = mock_cm

        with patch("platforms.Youtube.get_session", return_value=mock_session):
            res = await yt_api.extract_stream("Tum Hi Ho")
            assert res is not None
            assert res["stream_url"] == "http://stream.url"

    await close_session()
