from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping, Protocol, Sequence


ARCHIVE_BASE = "https://archive.org"
SEARCH_URL = f"{ARCHIVE_BASE}/advancedsearch.php"
METADATA_URL = f"{ARCHIVE_BASE}/metadata"
USER_AGENT = "VisonCubeSourcePrototype/0.1 (+https://visoncube.cn)"
REQUEST_TIMEOUT_SECONDS = 8.0
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
PAGE_SIZE = 20
MAX_PAGE = 100
MAX_SEARCH_LENGTH = 80
MAX_PLAYABLE_FILES = 20
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
HOST_PATTERN = re.compile(r"^[A-Za-z0-9.:[\]-]{1,255}$")


@dataclass(frozen=True)
class Category:
    type_id: str
    name: str
    query: str


CATEGORIES = (
    Category("nasa", "NASA 影像", "collection:nasa AND mediatype:movies AND format:MPEG4"),
    Category("fedflix", "公共教育", "collection:FedFlix AND mediatype:movies AND format:MPEG4"),
    Category("prelinger", "历史档案", "collection:prelinger AND mediatype:movies AND format:MPEG4"),
    Category("computer", "科技史", "collection:computerchronicles AND mediatype:movies AND format:MPEG4"),
)
CATEGORY_BY_ID = {item.type_id: item for item in CATEGORIES}
SEARCH_SCOPE = "(collection:nasa OR collection:FedFlix OR collection:prelinger OR collection:computerchronicles)"
OPEN_CATEGORY = Category("open", "开放短片", "")
OPEN_ITEMS = (
    {
        "vod_id": "open_sintel",
        "vod_name": "Sintel",
        "vod_pic": "https://media.w3.org/2010/05/sintel/poster.png",
        "vod_remarks": "CC BY 3.0",
        "vod_year": "2010",
        "vod_area": "Blender Open Movie",
        "vod_director": "Blender Foundation",
        "vod_actor": "",
        "vod_content": "Blender Foundation 制作的开放电影短片。",
        "play_url": "https://download.blender.org/durian/trailer/sintel_trailer-480p.mp4",
    },
    {
        "vod_id": "open_big_buck_bunny",
        "vod_name": "Big Buck Bunny",
        "vod_pic": "https://media.w3.org/2010/05/bunny/poster.png",
        "vod_remarks": "CC BY 3.0",
        "vod_year": "2008",
        "vod_area": "Blender Open Movie",
        "vod_director": "Blender Foundation",
        "vod_actor": "",
        "vod_content": "Blender Foundation 制作的开放动画短片。",
        "play_url": "https://media.w3.org/2010/05/bunny/trailer.mp4",
    },
)
OPEN_BY_ID = {item["vod_id"]: item for item in OPEN_ITEMS}
TRUSTED_PLAY_HOSTS = {"archive.org", "download.blender.org", "media.w3.org"}


class UpstreamError(RuntimeError):
    pass


class ArchiveClient(Protocol):
    def search(self, query: str, page: int, rows: int) -> Mapping[str, Any]: ...

    def metadata(self, identifier: str) -> Mapping[str, Any]: ...


class InternetArchiveClient:
    def _get_json(self, url: str, params: Mapping[str, object] | None = None) -> Mapping[str, Any]:
        if params:
            url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
        except (OSError, urllib.error.URLError, TimeoutError) as error:
            raise UpstreamError("公共档案服务暂时不可用") from error
        if len(body) > MAX_RESPONSE_BYTES:
            raise UpstreamError("公共档案响应过大")
        try:
            value = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise UpstreamError("公共档案返回了无效数据") from error
        if not isinstance(value, dict):
            raise UpstreamError("公共档案返回格式错误")
        return value

    def search(self, query: str, page: int, rows: int) -> Mapping[str, Any]:
        return self._get_json(
            SEARCH_URL,
            {
                "q": query,
                "fl[]": [
                    "identifier",
                    "title",
                    "description",
                    "date",
                    "creator",
                    "licenseurl",
                ],
                "rows": rows,
                "page": page,
                "sort[]": "downloads desc",
                "output": "json",
            },
        )

    def metadata(self, identifier: str) -> Mapping[str, Any]:
        encoded = urllib.parse.quote(identifier, safe="")
        return self._get_json(f"{METADATA_URL}/{encoded}")


def _text(value: object) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    if value is None:
        return ""
    return str(value).strip()


def _plain_text(value: object, limit: int = 2000) -> str:
    text = _text(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _year(value: object) -> str:
    match = re.search(r"(?:18|19|20)\d{2}", _text(value))
    return match.group(0) if match else ""


def _safe_page(value: object) -> int:
    try:
        page = int(str(value or "1"))
    except ValueError:
        return 1
    return max(1, min(MAX_PAGE, page))


def _query_term(keyword: str) -> str:
    escaped = keyword.replace("\\", "\\\\").replace('"', '\\"')
    return f'title:("{escaped}") AND mediatype:movies AND format:MPEG4 AND {SEARCH_SCOPE}'


def _poster(identifier: str) -> str:
    return f"{ARCHIVE_BASE}/services/img/{urllib.parse.quote(identifier, safe='')}"


def _vod_from_doc(document: Mapping[str, Any]) -> dict[str, str]:
    identifier = _text(document.get("identifier"))
    return {
        "vod_id": identifier,
        "vod_name": _plain_text(document.get("title"), 200) or identifier,
        "vod_pic": _poster(identifier),
        "vod_remarks": _year(document.get("date")) or "公共档案",
        "vod_year": _year(document.get("date")),
        "vod_actor": _plain_text(document.get("creator"), 300),
        "vod_content": _plain_text(document.get("description")),
    }


def _is_playable(file: Mapping[str, Any]) -> bool:
    name = _text(file.get("name"))
    if not name.lower().endswith(".mp4"):
        return False
    if _text(file.get("private")).lower() == "true":
        return False
    if any(marker in name.lower() for marker in ("_thumb", "trailer", "sample")):
        return False
    return True


def _playable_files(metadata: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw_files = metadata.get("files")
    if not isinstance(raw_files, list):
        return []
    files = [item for item in raw_files if isinstance(item, dict) and _is_playable(item)]
    files.sort(
        key=lambda item: (
            _text(item.get("source")).lower() != "original",
            _text(item.get("format")).lower() not in {"h.264", "mpeg4"},
            _text(item.get("name")).lower(),
        )
    )
    return files[:MAX_PLAYABLE_FILES]


def _episode_label(file: Mapping[str, Any], index: int) -> str:
    title = _plain_text(file.get("title"), 80)
    if not title:
        title = _text(file.get("name")).rsplit(".", 1)[0]
    title = title.replace("$", " ").replace("#", " ").strip()
    return title or f"视频 {index}"


def _download_url(identifier: str, name: str) -> str:
    encoded_identifier = urllib.parse.quote(identifier, safe="")
    encoded_name = urllib.parse.quote(name, safe="/()[],-_.~")
    return f"{ARCHIVE_BASE}/download/{encoded_identifier}/{encoded_name}"


class SourceService:
    def __init__(
        self,
        archive: ArchiveClient | None = None,
        archive_enabled: bool | None = None,
    ) -> None:
        self._archive = archive or InternetArchiveClient()
        if archive_enabled is None:
            archive_enabled = os.environ.get("SOURCE_ENABLE_ARCHIVE", "1").strip() != "0"
        self._archive_enabled = archive_enabled

    def handle(self, params: Mapping[str, Sequence[str]]) -> dict[str, object]:
        play = self._first(params, "play")
        if play:
            return self._player(play)
        keyword = self._first(params, "wd").strip()
        if keyword:
            return self._search(keyword, _safe_page(self._first(params, "pg")))
        identifier = self._first(params, "ids").strip()
        if identifier:
            return self._detail(identifier)
        category_id = self._first(params, "t").strip()
        if category_id:
            return self._category(category_id, _safe_page(self._first(params, "pg")))
        return self._home()

    @staticmethod
    def _first(params: Mapping[str, Sequence[str]], key: str) -> str:
        values = params.get(key, ())
        return str(values[0]) if values else ""

    def _catalog(self, query: str, page: int) -> dict[str, object]:
        payload = self._archive.search(query, page, PAGE_SIZE)
        response = payload.get("response")
        if not isinstance(response, dict):
            raise UpstreamError("公共档案搜索格式错误")
        raw_docs = response.get("docs")
        docs = raw_docs if isinstance(raw_docs, list) else []
        items = [
            _vod_from_doc(item)
            for item in docs
            if isinstance(item, dict)
            and IDENTIFIER_PATTERN.fullmatch(_text(item.get("identifier")))
        ]
        try:
            total = max(0, int(response.get("numFound", len(items))))
        except (TypeError, ValueError):
            total = len(items)
        return {
            "page": page,
            "pagecount": max(1, math.ceil(total / PAGE_SIZE)) if total else 1,
            "limit": PAGE_SIZE,
            "total": total,
            "list": items,
        }

    def _home(self) -> dict[str, object]:
        result = self._static_result(OPEN_ITEMS)
        result["class"] = [
            {"type_id": item.type_id, "type_name": item.name}
            for item in self._visible_categories()
        ]
        return result

    def _category(self, category_id: str, page: int) -> dict[str, object]:
        if category_id == OPEN_CATEGORY.type_id:
            return self._static_result(OPEN_ITEMS, page)
        if not self._archive_enabled:
            return {"page": page, "pagecount": 1, "limit": PAGE_SIZE, "total": 0, "list": []}
        category = CATEGORY_BY_ID.get(category_id)
        if category is None:
            return {"page": page, "pagecount": 1, "limit": PAGE_SIZE, "total": 0, "list": []}
        return self._catalog(category.query, page)

    def _search(self, keyword: str, page: int) -> dict[str, object]:
        keyword = keyword[:MAX_SEARCH_LENGTH].strip()
        if not keyword:
            return {"page": page, "pagecount": 1, "limit": PAGE_SIZE, "total": 0, "list": []}
        if not self._archive_enabled:
            lowered = keyword.casefold()
            matches = [
                item
                for item in OPEN_ITEMS
                if lowered in f"{item['vod_name']} {item['vod_content']}".casefold()
            ]
            return self._static_result(matches, page)
        return self._catalog(_query_term(keyword), page)

    def _detail(self, identifier: str) -> dict[str, object]:
        static_item = OPEN_BY_ID.get(identifier)
        if static_item is not None:
            vod = self._public_static_item(static_item)
            vod.update(
                {
                    "vod_play_from": "开放影片",
                    "vod_play_url": f"正片${static_item['play_url']}",
                }
            )
            return {"list": [vod]}
        if not IDENTIFIER_PATTERN.fullmatch(identifier):
            return {"list": [], "msg": "条目标识无效"}
        payload = self._archive.metadata(identifier)
        raw_metadata = payload.get("metadata")
        metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
        metadata = dict(metadata)
        metadata.setdefault("identifier", identifier)
        files = _playable_files(payload)
        if not files:
            return {"list": [], "msg": "该条目没有可直接播放的 MP4 文件"}
        episodes = []
        for index, file in enumerate(files, start=1):
            name = _text(file.get("name"))
            episodes.append(f"{_episode_label(file, index)}${_download_url(identifier, name)}")
        vod = _vod_from_doc(metadata)
        vod.update(
            {
                "vod_play_from": "Internet Archive",
                "vod_play_url": "#".join(episodes),
                "vod_area": "Internet Archive",
            }
        )
        return {"list": [vod]}

    @staticmethod
    def _player(play: str) -> dict[str, object]:
        if len(play) > 4096:
            return {"parse": 0, "url": "", "msg": "播放地址过长"}
        parsed = urllib.parse.urlparse(play)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in TRUSTED_PLAY_HOSTS
            or not parsed.path.lower().endswith(".mp4")
        ):
            return {"parse": 0, "url": "", "msg": "播放地址不受信任"}
        return {
            "parse": 0,
            "url": play,
            "header": {
                "User-Agent": USER_AGENT,
                "Referer": f"{parsed.scheme}://{parsed.netloc}/",
            },
        }

    def _visible_categories(self) -> tuple[Category, ...]:
        return (OPEN_CATEGORY, *CATEGORIES) if self._archive_enabled else (OPEN_CATEGORY,)

    @staticmethod
    def _public_static_item(item: Mapping[str, str]) -> dict[str, str]:
        return {key: value for key, value in item.items() if key != "play_url"}

    @classmethod
    def _static_result(
        cls,
        items: Sequence[Mapping[str, str]],
        page: int = 1,
    ) -> dict[str, object]:
        visible = [cls._public_static_item(item) for item in items] if page == 1 else []
        return {
            "page": page,
            "pagecount": 1,
            "limit": PAGE_SIZE,
            "total": len(items),
            "list": visible,
        }


class SourceRequestHandler(BaseHTTPRequestHandler):
    service = SourceService()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            self._write_json(200, {"status": "ok", "service": "visoncube-source-prototype"})
            return
        if parsed.path == "/config.json":
            self._write_json(200, self._config())
            return
        if parsed.path != "/api/source":
            self._write_json(404, {"msg": "not found"})
            return
        try:
            result = self.service.handle(urllib.parse.parse_qs(parsed.query, keep_blank_values=True))
        except UpstreamError as error:
            result = {"list": [], "msg": str(error)}
        except Exception:
            result = {"list": [], "msg": "测试线路处理失败"}
        self._write_json(200, result)

    def _config(self) -> dict[str, object]:
        configured = os.environ.get("SOURCE_PUBLIC_API_URL", "").strip()
        if configured:
            parsed = urllib.parse.urlparse(configured)
            api_url = configured if parsed.scheme in {"http", "https"} and parsed.netloc else ""
        else:
            api_url = ""
        if not api_url:
            host = self.headers.get("Host", "127.0.0.1:8765").strip()
            if not HOST_PATTERN.fullmatch(host):
                host = "127.0.0.1:8765"
            api_url = f"http://{host}/api/source"
        return {
            "sites": [
                {
                    "key": "visoncube_public_archive",
                    "name": "VisonCube · 公共影像（测试）",
                    "type": 4,
                    "api": api_url,
                    "danmaku": 0,
                    "searchable": 1,
                    "quickSearch": 0,
                    "changeable": 0,
                }
            ],
            "parses": [],
        }

    def _write_json(self, status: int, payload: Mapping[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="VisonCube type-4 source prototype")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), SourceRequestHandler)
    print(f"VisonCube source prototype: http://{args.host}:{args.port}/api/source")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
