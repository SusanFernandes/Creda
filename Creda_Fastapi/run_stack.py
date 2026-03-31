"""
Start CREDA backends in one terminal: finance (:8001) + multilingual (:8010), then gateway (:8080).

Usage (from Creda_Fastapi, with conda env activated):
    python run_stack.py

Env:
    STACK_WAIT_SECONDS — max seconds to wait for each service /health (default 600).
    FASTAPI1_URL, FASTAPI2_URL, MULTILINGUAL_PORT — same as .env (loaded automatically).

Ctrl+C stops all child processes.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent
CHILDREN: list[subprocess.Popen] = []


def load_env_file() -> None:
    try:
        from dotenv import load_dotenv as _load

        _load(ROOT / ".env")
    except ImportError:
        pass


def kill_children() -> None:
    for p in CHILDREN:
        if p.poll() is None:
            p.terminate()
    deadline = time.time() + 8
    for p in CHILDREN:
        while p.poll() is None and time.time() < deadline:
            time.sleep(0.1)
    for p in CHILDREN:
        if p.poll() is None:
            p.kill()


def wait_for_health(url: str, label: str, max_seconds: float) -> bool:
    deadline = time.time() + max_seconds
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            r = httpx.get(f"{url.rstrip('/')}/health", timeout=5.0)
            if r.status_code == 200:
                print(f"[stack] OK {label}  {url}/health")
                return True
        except Exception as e:
            if attempt == 1 or attempt % 15 == 0:
                print(f"[stack] waiting for {label}… ({e!s:.80})")
        time.sleep(2.0)
    print(f"[stack] TIMEOUT: {label} did not become healthy in {max_seconds:.0f}s", file=sys.stderr)
    return False


def main() -> int:
    os.chdir(ROOT)
    load_env_file()

    env = os.environ.copy()
    multilingual_port = env.get("MULTILINGUAL_PORT", "8010")
    ml_url = env.get("FASTAPI1_URL", f"http://localhost:{multilingual_port}")
    fin_url = env.get("FASTAPI2_URL", "http://localhost:8001")
    max_wait = float(env.get("STACK_WAIT_SECONDS", "600"))

    py = sys.executable

    print("[stack] Starting finance service…")
    p_fin = subprocess.Popen(
        [py, str(ROOT / "fastapi2_finance.py")],
        cwd=str(ROOT),
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    CHILDREN.append(p_fin)

    print("[stack] Starting multilingual service…")
    p_ml = subprocess.Popen(
        [py, str(ROOT / "fastapi1_multilingual.py")],
        cwd=str(ROOT),
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    CHILDREN.append(p_ml)

    if not wait_for_health(fin_url, "finance", max_wait):
        kill_children()
        return 1
    if not wait_for_health(ml_url, "multilingual", max_wait):
        kill_children()
        return 1

    print("[stack] Starting API gateway…")
    p_gw = subprocess.Popen(
        [py, str(ROOT / "app.py")],
        cwd=str(ROOT),
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    CHILDREN.append(p_gw)

    def _handle(sig: int, frame) -> None:  # noqa: ARG001
        print("\n[stack] shutting down…")
        kill_children()
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle)

    # Block until gateway exits (main process to watch)
    code = p_gw.wait()
    kill_children()
    return int(code or 0)


if __name__ == "__main__":
    sys.exit(main())
