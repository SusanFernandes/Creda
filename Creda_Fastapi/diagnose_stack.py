"""
Quick diagnosis: packages vs processes vs URLs.

Run in the SAME conda env you use for CREDA:
    python diagnose_stack.py

Interpreting:
- ImportError / ModuleNotFoundError → package install issue (pip/uv).
- Ports CLOSED + only gateway expected if you never started multilingual/finance → NOT a corrupt library.
- Ports OPEN but /health not 200 → service crashed after bind or wrong app on port (code/config).
"""
from __future__ import annotations

import importlib
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def try_import(name: str) -> str:
    try:
        importlib.import_module(name)
        return "OK"
    except Exception as e:
        return f"FAIL: {type(e).__name__}: {e}"


def port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        return s.connect_ex((host, port)) == 0
    finally:
        s.close()


def main() -> None:
    print("Python:", sys.executable)
    print()

    print("=== Package imports (failure = install / env issue, not 'corrupt random library') ===")
    for pkg in (
        "fastapi",
        "uvicorn",
        "httpx",
        "pydantic",
        "torch",
        "transformers",
        "chromadb",
        "sqlmodel",
    ):
        print(f"  {pkg:16} {try_import(pkg)}")
    print()

    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    ml = os.getenv("FASTAPI1_URL", "http://localhost:8010")
    fin = os.getenv("FASTAPI2_URL", "http://localhost:8001")
    gw_port = int(os.getenv("GATEWAY_PORT", "8080"))

    print("=== From .env (gateway talks to these) ===")
    print(f"  FASTAPI1_URL (multilingual): {ml}")
    print(f"  FASTAPI2_URL (finance):      {fin}")
    print(f"  GATEWAY_PORT:                {gw_port}")
    print()

    def host_port(url: str) -> tuple[str, int]:
        from urllib.parse import urlparse

        u = urlparse(url)
        return u.hostname or "127.0.0.1", u.port or (443 if u.scheme == "https" else 80)

    h1, p1 = host_port(ml)
    h2, p2 = host_port(fin)

    print("=== TCP ports (OPEN = something is listening; CLOSED = process not running / wrong port) ===")
    print(f"  multilingual {h1}:{p1}  -> {'OPEN' if port_open(h1, p1) else 'CLOSED'}")
    print(f"  finance      {h2}:{p2}  -> {'OPEN' if port_open(h2, p2) else 'CLOSED'}")
    print(f"  gateway      127.0.0.1:{gw_port} -> {'OPEN' if port_open('127.0.0.1', gw_port) else 'CLOSED'}")
    print()

    print("=== HTTP /health (only if port is open) ===")
    try:
        import httpx
    except ImportError:
        print("  httpx not installed; skip HTTP checks")
        return

    for label, base in [("multilingual", ml), ("finance", fin)]:
        if not port_open(host_port(base)[0], host_port(base)[1]):
            print(f"  {label}: skip (port closed)")
            continue
        try:
            r = httpx.get(f"{base.rstrip('/')}/health", timeout=5.0)
            print(f"  {label}: GET /health -> {r.status_code}")
        except Exception as e:
            print(f"  {label}: GET /health -> ERROR {e}")
    print()
    print("=== Summary ===")
    print("  'All connection attempts failed' in gateway logs = cannot reach FASTAPI1/2 URLs.")
    print("  That almost always means multilingual/finance were never started (or wrong port in .env).")
    print("  Fix: run  python run_stack.py  OR start fastapi1_multilingual.py + fastapi2_finance.py separately.")


if __name__ == "__main__":
    main()
