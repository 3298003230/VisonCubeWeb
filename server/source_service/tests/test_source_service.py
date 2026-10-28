from __future__ import annotations

import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import SourceRequestHandler, SourceService, UpstreamError


class FakeArchive:
    def __init__(self) -> None:
        self.search_calls: list[tuple[str, int, int]] = []
        self.metadata_calls: list[str] = []

    def search(self, query: str, page: int, rows: int):
        self.search_calls.append((query, page, rows))
        return {
            "response": {
                "numFound": 21,
                "docs": [
                    {
                        "identifier": "public-film",
                        "title": "Public Film",
                        "date": "1954-01-01",
                        "creator": ["Example Studio"],
                        "description": "<p>A public archive film.</p>",
                    },
                    {"identifier": "../invalid", "title": "Invalid"},
                ],
            }
        }

    def metadata(self, identifier: str):
        self.metadata_calls.append(identifier)
        return {
            "metadata": {
                "identifier": identifier,
                "title": "Public Film",
                "date": "1954",
                "creator": "Example Studio",
                "description": "<b>Archive description</b>",
            },
            "files": [
                {"name": "Public Film.mp4", "format": "h.264", "source": "original"},
                {"name": "Public Film_thumb.mp4", "format": "h.264", "source": "derivative"},
                {"name": "readme.txt", "format": "Text"},
            ],
        }


class SourceServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.archive = FakeArchive()
        self.service = SourceService(self.archive)

    def test_home_returns_types_and_safe_cards(self) -> None:
        result = self.service.handle({"filter": ["true"]})
        self.assertEqual([item["type_id"] for item in result["class"]], [
            "open",
            "nasa",
            "fedflix",
            "prelinger",
            "computer",
        ])
        self.assertEqual(result["list"][0]["vod_id"], "open_sintel")
        self.assertEqual(len(result["list"]), 2)
        self.assertEqual(result["pagecount"], 1)

    def test_category_uses_requested_page_and_unknown_is_empty(self) -> None:
        result = self.service.handle({"ac": ["detail"], "t": ["fedflix"], "pg": ["2"]})
        self.assertEqual(result["page"], 2)
        self.assertIn("collection:FedFlix", self.archive.search_calls[-1][0])
        self.assertIn("format:MPEG4", self.archive.search_calls[-1][0])

        empty = self.service.handle({"ac": ["detail"], "t": ["unknown"], "pg": ["9999"]})
        self.assertEqual(empty["page"], 100)
        self.assertEqual(empty["list"], [])

    def test_search_escapes_input_and_limits_page(self) -> None:
        result = self.service.handle({"wd": ['film" OR *:*'], "pg": ["not-a-number"]})
        query, page, _ = self.archive.search_calls[-1]
        self.assertIn('film\\" OR *:*', query)
        self.assertIn("collection:nasa", query)
        self.assertIn("format:MPEG4", query)
        self.assertEqual(page, 1)
        self.assertEqual(result["list"][0]["vod_name"], "Public Film")

        offline = SourceService(self.archive, archive_enabled=False)
        static_result = offline.handle({"wd": ["Sintel"]})
        self.assertEqual(static_result["list"][0]["vod_id"], "open_sintel")
        self.assertEqual(offline.handle({"wd": ["missing"]})["list"], [])

    def test_detail_emits_only_playable_mp4_and_no_danmaku(self) -> None:
        result = self.service.handle({"ac": ["detail"], "ids": ["public-film"]})
        vod = result["list"][0]
        self.assertEqual(vod["vod_play_from"], "Internet Archive")
        self.assertIn("Public%20Film.mp4", vod["vod_play_url"])
        self.assertNotIn("thumb", vod["vod_play_url"])
        self.assertNotIn("danmaku", json.dumps(result))

        invalid = self.service.handle({"ids": ["../invalid"]})
        self.assertEqual(invalid["list"], [])
        self.assertEqual(self.archive.metadata_calls, ["public-film"])

        class EmptyArchive(FakeArchive):
            def metadata(self, identifier: str):
                return {"metadata": {"identifier": identifier}, "files": []}

        unavailable = SourceService(EmptyArchive()).handle({"ids": ["public-film"]})
        self.assertEqual(unavailable["list"], [])
        self.assertIn("没有可直接播放", unavailable["msg"])

        static_detail = self.service.handle({"ids": ["open_sintel"]})
        self.assertIn("download.blender.org", static_detail["list"][0]["vod_play_url"])
        self.assertNotIn("play_url", static_detail["list"][0])

    def test_player_accepts_only_generated_archive_download_urls(self) -> None:
        trusted = self.service.handle({"play": ["https://archive.org/download/item/video.mp4"]})
        self.assertEqual(trusted["parse"], 0)
        self.assertEqual(trusted["url"], "https://archive.org/download/item/video.mp4")

        open_movie = self.service.handle(
            {"play": ["https://media.w3.org/2010/05/bunny/trailer.mp4"]}
        )
        self.assertEqual(open_movie["parse"], 0)

        for url in (
            "http://archive.org/download/item/video.mp4",
            "https://archive.org.evil.test/download/item/video.mp4",
            "https://archive.org/details/item",
            "https://media.w3.org/2010/05/bunny/trailer.webm",
        ):
            blocked = self.service.handle({"play": [url]})
            self.assertEqual(blocked["url"], "")

    def test_http_routes_and_not_found(self) -> None:
        handler = type("TestHandler", (SourceRequestHandler,), {"service": self.service})
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            with urllib.request.urlopen(f"{base}/health", timeout=2) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(json.load(response)["status"], "ok")
            with urllib.request.urlopen(f"{base}/api/source?filter=true", timeout=2) as response:
                self.assertEqual(response.headers.get_content_type(), "application/json")
                self.assertEqual(json.load(response)["class"][0]["type_id"], "open")
            with urllib.request.urlopen(f"{base}/config.json", timeout=2) as response:
                config = json.load(response)
            self.assertEqual(len(config["sites"]), 1)
            self.assertEqual(config["sites"][0]["type"], 4)
            self.assertEqual(config["sites"][0]["danmaku"], 0)
            self.assertEqual(
                config["sites"][0]["api"],
                f"http://127.0.0.1:{server.server_port}/api/source",
            )
            with self.assertRaises(urllib.error.HTTPError) as missing:
                urllib.request.urlopen(f"{base}/missing", timeout=2)
            self.assertEqual(missing.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_config_rejects_invalid_host_header(self) -> None:
        handler = type("ConfigHandler", (SourceRequestHandler,), {"service": self.service})
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{server.server_port}/config.json",
                headers={"Host": "bad host"},
            )
            with urllib.request.urlopen(request, timeout=2) as response:
                config = json.load(response)
            self.assertEqual(config["sites"][0]["api"], "http://127.0.0.1:8765/api/source")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_http_converts_upstream_failure_to_safe_empty_result(self) -> None:
        class FailingService:
            def handle(self, _params):
                raise UpstreamError("公共档案服务暂时不可用")

        handler = type("FailingHandler", (SourceRequestHandler,), {"service": FailingService()})
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/api/source?filter=true"
            with urllib.request.urlopen(url, timeout=2) as response:
                result = json.load(response)
            self.assertEqual(result["list"], [])
            self.assertEqual(result["msg"], "公共档案服务暂时不可用")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
