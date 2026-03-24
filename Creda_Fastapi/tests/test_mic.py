#!/usr/bin/env python3
"""
test_mic.py — Local microphone test for CREDA Multilingual Service.

Records audio from your mic and sends it to the /process_voice endpoint.
NOT part of the main service — only for local development testing.

Install:  pip install pyaudio requests
Usage:    python test_mic.py --lang hi --duration 5
"""

import argparse
import io
import os
import sys
import wave
import requests

CREDA_URL = os.getenv("CREDA_MULTILINGUAL_URL", "http://localhost:8000")


def record_audio(duration: int = 5, sample_rate: int = 16000) -> bytes:
    """Record from the default mic and return WAV bytes."""
    try:
        import pyaudio
    except ImportError:
        print("pyaudio not installed. Run:  pip install pyaudio")
        sys.exit(1)

    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=sample_rate,
        input=True,
        frames_per_buffer=1024,
    )

    print(f"Recording for {duration} seconds …")
    frames = []
    for _ in range(0, int(sample_rate / 1024 * duration)):
        frames.append(stream.read(1024))

    stream.stop_stream()
    stream.close()
    p.terminate()
    print("Recording done.")

    # Convert to WAV bytes in-memory
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(frames))
    buf.seek(0)
    return buf.read()


def send_to_creda(audio_bytes: bytes, language_code: str):
    """Send audio to /process_voice and play the response."""
    url = f"{CREDA_URL}/process_voice"
    print(f"Sending {len(audio_bytes)} bytes to {url}  lang={language_code}")

    resp = requests.post(
        url,
        files={"file": ("test_audio.wav", audio_bytes, "audio/wav")},
        data={"language_code": language_code, "user_profile": "{}"},
        stream=True,
    )

    if resp.status_code != 200:
        print(f"Error {resp.status_code}: {resp.text}")
        return

    # Print metadata from headers
    from urllib.parse import unquote

    transcript = unquote(resp.headers.get("X-Transcript", ""))
    response_text = unquote(resp.headers.get("X-Response-Text", ""))
    processing_time = resp.headers.get("X-Processing-Time", "")

    print(f"\n{'='*50}")
    print(f"  Transcript : {transcript}")
    print(f"  Response   : {response_text}")
    print(f"  Time       : {processing_time}")
    print(f"{'='*50}")

    # Save response audio
    out_path = "creda_response.wav"
    with open(out_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Audio saved to {out_path}")

    # Try to play it
    try:
        if sys.platform == "win32":
            os.system(f'start "" "{out_path}"')
        elif sys.platform == "darwin":
            os.system(f"afplay {out_path}")
        else:
            os.system(f"aplay {out_path} 2>/dev/null || paplay {out_path} 2>/dev/null")
    except Exception:
        pass


def test_health():
    """Quick health check."""
    try:
        resp = requests.get(f"{CREDA_URL}/health", timeout=5)
        print(f"Health: {resp.json()}")
    except Exception as e:
        print(f"Service unreachable: {e}")


def test_text(text: str, language_code: str):
    """Send a text query and get audio response."""
    url = f"{CREDA_URL}/process_text"
    print(f"Sending text query: '{text}'  lang={language_code}")

    resp = requests.post(
        url,
        json={"text": text, "language_code": language_code, "user_profile": {}},
        stream=True,
    )

    if resp.status_code != 200:
        print(f"Error {resp.status_code}: {resp.text}")
        return

    from urllib.parse import unquote

    response_text = unquote(resp.headers.get("X-Response-Text", ""))
    print(f"\n  Response: {response_text}")

    out_path = "creda_text_response.wav"
    with open(out_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"  Audio saved to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test CREDA Multilingual Service")
    parser.add_argument("--lang", default="hi", help="Language code (hi, ta, te, bn, en, ...)")
    parser.add_argument("--duration", type=int, default=5, help="Recording duration in seconds")
    parser.add_argument("--text", type=str, default=None, help="Send text instead of recording mic")
    parser.add_argument("--health", action="store_true", help="Just check service health")
    args = parser.parse_args()

    if args.health:
        test_health()
    elif args.text:
        test_text(args.text, args.lang)
    else:
        audio = record_audio(duration=args.duration)
        send_to_creda(audio, args.lang)
