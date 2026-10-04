#!/usr/bin/env python3
"""Loopback-only static server for the Sagrada Família Web walkthrough."""
from __future__ import annotations

import argparse
import errno
import hashlib
import http.server
import ipaddress
import json
import logging
import mimetypes
import os
from pathlib import Path
import re
import socket
import struct
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import zlib

APPLICATION = "sagrada-familia-web"
PROTOCOL = 2
INFO_PATH = "/__sagrada_familia_server_info"
REPORT_LIMIT = 256 * 1024
CAPTURE_LIMIT = 12 * 1024 * 1024
LOGGER = logging.getLogger(APPLICATION)


def project_id(web_root: Path) -> str:
    return hashlib.sha256(str(web_root.resolve()).encode()).hexdigest()


def accepts_gzip(header: str) -> bool:
    values: dict[str, float] = {}
    for item in header.split(","):
        pieces = [part.strip() for part in item.split(";")]
        encoding, quality = pieces[0].lower(), 1.0
        for parameter in pieces[1:]:
            if parameter.lower().startswith("q="):
                try:
                    quality = float(parameter[2:])
                except ValueError:
                    quality = 0.0
        if encoding:
            values[encoding] = quality if 0.0 <= quality <= 1.0 else 0.0
    return values.get("gzip", values.get("*", 0.0)) > 0.0


def valid_png(data: bytes) -> bool:
    """Validate PNG framing/CRC/dimensions without decompressing image data."""
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return False
    offset, first, saw_idat = 8, True, False
    while offset + 12 <= len(data):
        size = struct.unpack_from(">I", data, offset)[0]
        end = offset + 12 + size
        if end > len(data):
            return False
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + size]
        crc = struct.unpack_from(">I", data, offset + 8 + size)[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != crc:
            return False
        if first:
            if kind != b"IHDR" or size != 13:
                return False
            width, height = struct.unpack_from(">II", payload)
            if not (0 < width <= 16384 and 0 < height <= 16384
                    and width * height <= 67_108_864):
                return False
            first = False
        elif kind == b"IHDR":
            return False
        if kind == b"IDAT":
            saw_idat = True
        if kind == b"IEND":
            return size == 0 and saw_idat and end == len(data)
        offset = end
    return False


def atomic_write(target: Path, payload: bytes, web_root: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.parent.resolve().is_relative_to(web_root.resolve()):
        raise ValueError("Output directory escapes the Web project")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".qa-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class WebServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], web_root: Path, qa_enabled: bool = False,
                 bundle: str = "dist"):
        if address[0] != "127.0.0.1":
            raise ValueError("Only the IPv4 loopback address is permitted")
        if bundle not in {"dist", "site_bundle"}:
            raise ValueError("Bundle must be dist or site_bundle")
        self.web_root = web_root.resolve()
        self.bundle = bundle
        self.static_root = (self.web_root / bundle).resolve()
        if not self.static_root.is_relative_to(self.web_root):
            raise ValueError("Static root escapes the Web project")
        self.qa_enabled = qa_enabled
        self.qa_lock = threading.Lock()
        super().__init__(address, Handler)

    def info(self) -> dict:
        return {"application": APPLICATION, "protocol": PROTOCOL,
                "project_id": project_id(self.web_root),
                "port": self.server_address[1], "qa_enabled": self.qa_enabled,
                "bundle": self.bundle}


class Handler(http.server.SimpleHTTPRequestHandler):
    server: WebServer
    server_version = "SagradaFamiliaLocal/1"

    def __init__(self, *args, **kwargs):
        server = args[2]
        super().__init__(*args, directory=str(server.static_root), **kwargs)

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, fmt: str, *args):
        LOGGER.info("%s %s", self.client_address[0], fmt % args)

    def json_response(self, status: int, content: dict):
        payload = json.dumps(content, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def do_GET(self):
        if urllib.parse.urlsplit(self.path).path == INFO_PATH:
            self.json_response(200, self.server.info())
            return
        super().do_GET()

    def do_HEAD(self):
        if urllib.parse.urlsplit(self.path).path == INFO_PATH:
            self.json_response(200, self.server.info())
            return
        super().do_HEAD()

    def list_directory(self, path):
        self.send_error(404, "Directory listing is disabled")
        return None

    def send_head(self):
        target = Path(self.translate_path(self.path)).resolve()
        if not target.is_relative_to(self.server.static_root):
            self.send_error(403, "Path outside static root")
            return None
        if target.is_dir():
            target = (target / "index.html").resolve()
        if not target.is_relative_to(self.server.static_root) or not target.is_file():
            self.send_error(404, "File not found")
            return None
        source = target
        encoded = False
        compressed = Path(str(target) + ".gz")
        if accepts_gzip(self.headers.get("Accept-Encoding", "")) and compressed.is_file():
            compressed = compressed.resolve()
            if compressed.is_relative_to(self.server.static_root):
                source, encoded = compressed, True
        content_type = {".wasm": "application/wasm", ".pck": "application/octet-stream",
                        ".js": "text/javascript", ".json": "application/json"}.get(target.suffix)
        content_type = content_type or mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        try:
            stream = source.open("rb")
        except OSError:
            self.send_error(404, "File not found")
            return None
        stat = os.fstat(stream.fileno())
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(stat.st_size))
        self.send_header("Last-Modified", self.date_time_string(stat.st_mtime))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Vary", "Accept-Encoding")
        self.send_header("X-Content-Type-Options", "nosniff")
        if encoded:
            self.send_header("Content-Encoding", "gzip")
        self.end_headers()
        return stream

    def qa_origin_allowed(self) -> bool:
        port = self.server.server_address[1]
        host = self.headers.get("Host", "")
        return (ipaddress.ip_address(self.client_address[0]).is_loopback
                and host in {f"127.0.0.1:{port}", f"localhost:{port}"}
                and self.headers.get("Origin", "") == f"http://{host}")

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        if not self.server.qa_enabled or parsed.path not in {"/__qa/report", "/__qa/capture"}:
            self.json_response(404, {"error": "Endpoint unavailable"})
            return
        if not self.qa_origin_allowed():
            self.json_response(403, {"error": "Same-origin loopback requests only"})
            return
        is_report = parsed.path == "/__qa/report"
        expected_type = "application/json" if is_report else "image/png"
        if self.headers.get_content_type() != expected_type:
            self.json_response(415, {"error": f"Expected {expected_type}"})
            return
        if self.headers.get("Transfer-Encoding"):
            self.json_response(400, {"error": "Chunked uploads are not accepted"})
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self.json_response(411, {"error": "Content-Length required"})
            return
        limit = REPORT_LIMIT if is_report else CAPTURE_LIMIT
        if length <= 0 or length > limit:
            self.json_response(413, {"error": "Upload size outside allowed range"})
            return
        try:
            payload = self.rfile.read(length)
        except (TimeoutError, socket.timeout):
            self.json_response(408, {"error": "Upload timed out"})
            return
        if len(payload) != length:
            self.json_response(400, {"error": "Incomplete upload"})
            return
        try:
            if is_report:
                def reject_nonfinite(value):
                    raise ValueError(f"Invalid JSON constant: {value}")
                report = json.loads(payload.decode("utf-8"), parse_constant=reject_nonfinite)
                if not isinstance(report, dict):
                    raise ValueError("Report must be a JSON object")
                payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
                relative = Path("qa/browser_report_latest.json")
            else:
                query = urllib.parse.parse_qs(parsed.query)
                filenames = query.get("filename", [])
                if len(filenames) != 1 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\.png", filenames[0]) or ".." in filenames[0]:
                    raise ValueError("Use one safe filename query parameter ending in .png")
                if not valid_png(payload):
                    raise ValueError("Invalid PNG structure, checksum, or dimensions")
                relative = Path("screenshots") / filenames[0]
            with self.server.qa_lock:
                atomic_write(self.server.web_root / relative, payload, self.server.web_root)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            self.json_response(400, {"error": str(error)})
            return
        except OSError:
            LOGGER.exception("QA artifact write failed")
            self.json_response(500, {"error": "Could not save QA artifact"})
            return
        self.json_response(200, {"ok": True, "path": str(relative), "bytes": len(payload)})


def find_existing(port: int, web_root: Path, bundle: str = "dist") -> dict | None:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://127.0.0.1:{port}{INFO_PATH}", timeout=2) as response:
            data = response.read(4097)
        if len(data) > 4096:
            return None
        info = json.loads(data)
        if (info.get("application") == APPLICATION and info.get("protocol") == PROTOCOL
                and info.get("project_id") == project_id(web_root) and info.get("port") == port
                and info.get("bundle") == bundle):
            return info
    except (OSError, ValueError, urllib.error.URLError):
        pass
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8776)
    parser.add_argument("--bundle", choices=["dist", "site_bundle"], default="dist",
                        help="Static directory to serve (default: dist)")
    parser.add_argument("--qa", action="store_true", help="Enable same-origin QA reports and PNG captures")
    parser.add_argument("--open-browser", action="store_true", dest="open_browser")
    parser.add_argument("--no-browser", action="store_false", dest="open_browser")
    parser.set_defaults(open_browser=False)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("Port must be between 0 and 65535")
    web_root = Path(__file__).resolve().parent
    if not (web_root / args.bundle / "index.html").is_file():
        action = "./build_web.sh" if args.bundle == "dist" else "python3 tools/package_static.py"
        parser.error(f"{args.bundle}/index.html is missing. Run {action} first.")
    log_dir = web_root / "logs"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(log_dir / "server.log")])
    try:
        server = WebServer(("127.0.0.1", args.port), web_root, args.qa, args.bundle)
    except OSError as error:
        existing = find_existing(args.port, web_root, args.bundle) if error.errno == errno.EADDRINUSE else None
        if existing is None:
            LOGGER.error("Port %s cannot serve %s: %s. Existing process identity/bundle could not be matched; no process was changed.", args.port, args.bundle, error)
            return 1
        if args.qa and not existing.get("qa_enabled"):
            LOGGER.error("This project's server already runs without QA. Stop it in its terminal before restarting with --qa.")
            return 1
        url = f"http://127.0.0.1:{args.port}/"
        LOGGER.info("Reusing this project's server: %s (bundle=%s, QA=%s). Its original terminal controls shutdown.", url, args.bundle, existing.get("qa_enabled"))
        if args.open_browser:
            webbrowser.open(url)
        return 0
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    LOGGER.info("Sagrada Família local walkthrough: %s (bundle=%s, QA=%s)", url, args.bundle, args.qa)
    LOGGER.info("Keep this terminal open. Ctrl+C stops this server. Only 127.0.0.1 is listening.")
    if args.open_browser:
        opener = threading.Timer(0.3, webbrowser.open, args=(url,))
        opener.daemon = True
        opener.start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        LOGGER.info("Stopping local server.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
