#!/usr/bin/env python3
"""Start/reuse this project's loopback server independently of the launcher terminal."""
from __future__ import annotations

import argparse
import errno
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

from serve import APPLICATION, INFO_PATH, PROTOCOL, project_id

READY_TIMEOUT = 10.0


class LaunchError(RuntimeError):
    pass


def inspect_server(web_root: Path, port: int, bundle: str,
                   timeout: float = 0.75) -> dict | None:
    """None means connection refused; unverified occupied ports are never replaced."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://127.0.0.1:{port}{INFO_PATH}", timeout=timeout) as response:
            if response.status != 200:
                raise LaunchError(f"ポート{port}のサーバーを識別できません。既存プロセスは変更しません。")
            payload = response.read(4097)
    except urllib.error.HTTPError as error:
        raise LaunchError(f"ポート{port}は別のサーバーが使用しています（HTTP {error.code}）。停止しません。") from error
    except urllib.error.URLError as error:
        if getattr(error.reason, "errno", None) == errno.ECONNREFUSED:
            return None
        raise LaunchError(f"ポート{port}の応答を確認できません: {error.reason}。既存プロセスは変更しません。") from error
    except (TimeoutError, OSError) as error:
        raise LaunchError(f"ポート{port}の応答を確認できません: {error}。既存プロセスは変更しません。") from error
    try:
        info = json.loads(payload) if len(payload) <= 4096 else None
    except (ValueError, UnicodeDecodeError):
        info = None
    expected = {"application": APPLICATION, "protocol": PROTOCOL,
                "project_id": project_id(web_root), "port": port, "bundle": bundle}
    if not isinstance(info, dict) or any(info.get(key) != value for key, value in expected.items()):
        raise LaunchError(f"ポート{port}は別の作品・配布版・プロセスが使用しています。停止せず終了します。")
    return info


def stop_own_child(child: subprocess.Popen) -> None:
    """Only the Popen handle created by this invocation is eligible for cleanup."""
    if child.poll() is not None:
        return
    child.terminate()
    try:
        child.wait(timeout=1.0)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=1.0)


def ensure_server(web_root: Path, port: int, bundle: str) -> dict:
    web_root = web_root.resolve()
    if not (web_root / bundle / "index.html").is_file():
        raise LaunchError(f"配布ファイルがありません: {web_root / bundle / 'index.html'}")
    existing = inspect_server(web_root, port, bundle)
    url = f"http://127.0.0.1:{port}/"
    if existing is not None:
        return {"url": url, "reused": True, "bundle": bundle}

    log_dir = web_root / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"detached_server_{port}.log"
    try:
        with log_path.open("ab", buffering=0) as log:
            child = subprocess.Popen(
                [sys.executable, str(web_root / "serve.py"), "--bundle", bundle,
                 "--port", str(port), "--no-browser"],
                cwd=str(web_root), stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT,
                close_fds=True, start_new_session=True,
            )
    except OSError as error:
        raise LaunchError(f"ローカルサーバーを起動できません: {error}") from error

    deadline = time.monotonic() + READY_TIMEOUT
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise LaunchError(f"サーバーが10秒以内に準備できませんでした。ログ: {log_path}")
            # Check identity before exit status: another simultaneous launcher
            # may have won the bind race and started the same requested server.
            ready = inspect_server(web_root, port, bundle, timeout=min(0.4, remaining))
            if ready is not None:
                return {"url": url, "reused": child.poll() is not None,
                        "bundle": bundle, "spawned_pid": child.pid, "log": str(log_path)}
            status = child.poll()
            if status is not None:
                raise LaunchError(f"ローカルサーバーが終了しました（終了コード{status}）。ログ: {log_path}")
            time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))
    except (LaunchError, OSError, KeyboardInterrupt):
        stop_own_child(child)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", choices=["site_bundle", "dist"], default="site_bundle")
    parser.add_argument("--port", type=int, default=8777)
    parser.add_argument("--no-browser", action="store_true", help="サーバーだけ準備し、ブラウザを開きません")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535")
    try:
        result = ensure_server(Path(__file__).resolve().parent, args.port, args.bundle)
    except (LaunchError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    print(("起動済みの見学サーバーを再利用します: " if result["reused"] else "見学サーバーを起動しました: ") + result["url"])
    print("この起動用端末は閉じて構いません。リンクはこのPC上のブラウザで開いてください。")
    if result["reused"]:
        print("既存サーバーをSTART_WEB.shで起動した場合、その元の端末は開いたままにしてください。")
    if not args.no_browser:
        try:
            opened = webbrowser.open(result["url"])
        except (webbrowser.Error, OSError):
            opened = False
        if not opened:
            print("ブラウザを自動で開けませんでした。上記URLをブラウザで開いてください。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
