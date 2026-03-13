"""Subprocess wrapper that captures stdout/stderr in real-time."""

import asyncio
import os
import signal
import sys
import time
import uuid
import logging
from pathlib import Path

from rdb.storage import get_db, insert_log, insert_http
from rdb.proxy import start_proxy, find_free_port

logger = logging.getLogger(__name__)


async def wrap_and_capture(command: list[str], db_path: Path | None = None) -> int:
    """Wrap a subprocess, capture its stdout/stderr, and proxy HTTP traffic.

    Returns the subprocess exit code.
    """
    session_id = uuid.uuid4().hex[:12]
    conn = get_db(db_path)

    # Start HTTP proxy (cross_thread=True since proxy runs in a separate thread)
    proxy_port = find_free_port()
    proxy_conn = get_db(db_path, cross_thread=True)

    def store_http(**kwargs):
        insert_http(proxy_conn, session_id, proc.pid if proc else 0, **kwargs)

    proxy_server, proxy_thread = start_proxy(proxy_port, store_http)

    # Prepare environment with proxy settings
    env = os.environ.copy()
    proxy_url = f"http://127.0.0.1:{proxy_port}"
    env["HTTP_PROXY"] = proxy_url
    env["http_proxy"] = proxy_url
    env["RDB_SESSION_ID"] = session_id
    env["RDB_PROXY_PORT"] = str(proxy_port)

    print(f"[rdb] Session: {session_id}")
    print(f"[rdb] HTTP proxy: {proxy_url}")
    print(f"[rdb] Running: {' '.join(command)}")
    print(f"[rdb] ---")

    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    async def read_stream(stream, stream_name: str):
        while True:
            line = await stream.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip("\n")
            insert_log(conn, session_id, proc.pid, stream_name, text)
            dest = sys.stdout if stream_name == "stdout" else sys.stderr
            dest.write(text + "\n")
            dest.flush()

    # Read both streams concurrently
    await asyncio.gather(
        read_stream(proc.stdout, "stdout"),
        read_stream(proc.stderr, "stderr"),
    )

    exit_code = await proc.wait()

    # Shutdown proxy
    proxy_server.shutdown()

    print(f"[rdb] ---")
    print(f"[rdb] Process exited with code {exit_code}")
    print(f"[rdb] Session {session_id} saved to {conn.execute('PRAGMA database_list').fetchone()[2]}")

    proxy_conn.close()
    conn.close()
    return exit_code
