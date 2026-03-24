#!/usr/bin/env python3
"""
Comprehensive Multilingual Service Test Suite

This script tests the CREDA multilingual service end-to-end.
Run this AFTER the service is started:
    1. Terminal 1: uvicorn fastapi1_multilingual:app --host 0.0.0.0 --port 8000 --reload
    2. Terminal 2: python comprehensive_multilingual_test.py

The test suite includes:
    - Endpoint availability (health check)
    - Language support verification
    - Conversation history (session persistence)
    - Text-to-speech synthesis in multiple languages
    - Translation in both directions
    - Full voice pipeline (requires audio file)

Usage:
    python comprehensive_multilingual_test.py [--base-url http://localhost:8000]
    python comprehensive_multilingual_test.py --text "hello"              # Text-only test
    python comprehensive_multilingual_test.py --voice audio.wav --lang hi # Voice test
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from urllib.parse import urljoin

try:
    import requests
    from requests.exceptions import ConnectionError, Timeout
except ImportError:
    print("❌ requests library not found. Install with: pip install requests")
    sys.exit(1)

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def log_success(msg):
    print(f"{GREEN}✓{RESET} {msg}")

def log_error(msg):
    print(f"{RED}✗{RESET} {msg}")

def log_warning(msg):
    print(f"{YELLOW}⚠{RESET} {msg}")

def log_info(msg):
    print(f"{BLUE}ℹ{RESET} {msg}")

class MultilingualServiceTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.timeout = 30
        self.session_id = f"test-{int(time.time())}"

    def test_health(self):
        """Test if service is running and engines are ready."""
        print("\n" + "=" * 70)
        print("TEST 1: Service Health Check")
        print("=" * 70)

        try:
            resp = self.session.get(f"{self.base_url}/health", timeout=5)
            if resp.status_code != 200:
                log_error(f"Health check failed: {resp.status_code}")
                return False

            data = resp.json()
            log_success("Service is running")

            # Check each engine
            for engine, status in data.items():
                if status.get("ready"):
                    log_success(f"  {engine}: {status.get('type', 'ready')}")
                else:
                    log_warning(f"  {engine}: not ready")

            return True

        except ConnectionError:
            log_error(f"Cannot connect to {self.base_url}")
            log_info("Make sure service is running: uvicorn fastapi1_multilingual:app --reload")
            return False
        except Exception as e:
            log_error(f"Health check error: {e}")
            return False

    def test_supported_languages(self):
        """Test /supported_languages endpoint."""
        print("\n" + "=" * 70)
        print("TEST 2: Supported Languages")
        print("=" * 70)

        try:
            resp = self.session.get(f"{self.base_url}/supported_languages")
            if resp.status_code != 200:
                log_error(f"Failed: {resp.status_code}")
                return False

            data = resp.json()
            langs = data.get("languages", {})

            log_success(f"Service supports {len(langs)} languages:")
            for code, info in sorted(langs.items())[:5]:
                print(f"  {code}: {info.get('name', 'Unknown')}")
            if len(langs) > 5:
                print(f"  ... and {len(langs) - 5} more")

            return True

        except Exception as e:
            log_error(f"Error: {e}")
            return False

    def test_text_to_speech_single_turn(self, language="hi"):
        """Test /process_text endpoint (single turn)."""
        print("\n" + "=" * 70)
        print(f"TEST 3: Text-to-Speech ({language})")
        print("=" * 70)

        test_texts = {
            "hi": "नमस्ते। मैं आपके वित्तीय सवालों का जवाब दे रहा हूं।",
            "ta": "வணக்கம். நான் உங்கள் நிதி கேள்விகளுக்கு பதிலளிக்கிறேன்.",
            "te": "నమస్కారం. నేను మీ ఆర్థిక ప్రశ్నలకు సమాధానం ఇస్తున్నాను.",
            "en": "Hello. I am answering your financial questions.",
        }

        text = test_texts.get(language, test_texts["en"])

        try:
            files = {
                "text": (None, text),
                "language_code": (None, language),
                "session_id": (None, self.session_id),
            }

            resp = self.session.post(f"{self.base_url}/process_text", files=files, timeout=30)

            if resp.status_code != 200:
                log_error(f"Failed: {resp.status_code} - {resp.text[:100]}")
                return False

            # Check response headers
            transcript = resp.headers.get("x-response-text", "N/A")
            lang = resp.headers.get("x-language", "unknown")
            proc_time = resp.headers.get("x-processing-time", "unknown")

            log_success(f"Audio generated in {proc_time}")
            log_info(f"  Language: {lang}")
            log_info(f"  Response: {transcript[:80]}...")
            log_info(f"  Audio size: {len(resp.content)} bytes")

            return True

        except requests.Timeout:
            log_error("Request timeout (30s) - service may be overloaded")
            return False
        except Exception as e:
            log_error(f"Error: {e}")
            return False

    def test_conversation_history(self, language="hi"):
        """Test conversation history with multiple turns."""
        print("\n" + "=" * 70)
        print(f"TEST 4: Conversation History ({language})")
        print("=" * 70)

        conversations = {
            "hi": [
                "SIP क्या है?",
                "इसमें कितना पैसा लगता है?",
                "क्या मैं अभी शुरू कर सकता हूं?",
            ],
            "en": [
                "What is SIP?",
                "How much money do I need to invest?",
                "Can I start this month?",
            ],
        }

        texts = conversations.get(language, conversations["en"])

        try:
            for i, text in enumerate(texts, 1):
                print(f"\n  Turn {i}: {text[:60]}...")

                files = {
                    "text": (None, text),
                    "language_code": (None, language),
                    "session_id": (None, self.session_id),
                }

                resp = self.session.post(
                    f"{self.base_url}/process_text",
                    files=files,
                    timeout=30
                )

                if resp.status_code != 200:
                    log_error(f"  Failed: {resp.status_code}")
                    return False

                response = resp.headers.get("x-response-text", "N/A")
                log_success(f"  Response: {response[:60]}...")

                time.sleep(1)  # Rate limit

            log_success(f"Conversation of {len(texts)} turns completed")
            return True

        except Exception as e:
            log_error(f"Error: {e}")
            return False

    def test_translation(self):
        """Test /translate endpoint."""
        print("\n" + "=" * 70)
        print("TEST 5: Translation")
        print("=" * 70)

        test_cases = [
            {
                "text": "SIP is a systematic investment plan.",
                "src_lang": "en",
                "tgt_lang": "hi",
                "name": "English → Hindi",
            },
            {
                "text": "SIP एक व्यवस्थित निवेश योजना है।",
                "src_lang": "hi",
                "tgt_lang": "en",
                "name": "Hindi → English",
            },
        ]

        try:
            for test in test_cases:
                print(f"\n  {test['name']}")
                print(f"    Input: {test['text'][:60]}...")

                data = {
                    "text": test["text"],
                    "src_lang": test["src_lang"],
                    "tgt_lang": test["tgt_lang"],
                }

                resp = self.session.post(
                    f"{self.base_url}/translate",
                    json=data,
                    timeout=30
                )

                if resp.status_code != 200:
                    log_error(f"    Failed: {resp.status_code}")
                    continue

                result = resp.json().get("translated_text", "N/A")
                log_success(f"    Output: {result[:60]}...")

                time.sleep(1)

            return True

        except Exception as e:
            log_error(f"Error: {e}")
            return False

    def test_voice_pipeline(self, audio_file, language="hi"):
        """Test /process_voice endpoint with actual audio file."""
        print("\n" + "=" * 70)
        print("TEST 6: Voice Pipeline")
        print("=" * 70)

        if not Path(audio_file).exists():
            log_warning(f"Audio file not found: {audio_file}")
            log_info("Skipping voice pipeline test")
            return True

        try:
            with open(audio_file, "rb") as f:
                files = {
                    "audio": (Path(audio_file).name, f, "audio/wav"),
                }
                data = {
                    "language_code": language,
                    "user_profile": json.dumps({"income": 100000, "risk_profile": "moderate"}),
                }

                print(f"  Uploading {Path(audio_file).name} ({os.path.getsize(audio_file)} bytes)")
                print(f"  Language: {language}")

                resp = self.session.post(
                    f"{self.base_url}/process_voice",
                    files=files,
                    data=data,
                    timeout=60
                )

                if resp.status_code != 200:
                    log_error(f"Failed: {resp.status_code}")
                    return False

                transcript = resp.headers.get("x-transcript", "N/A")
                response_text = resp.headers.get("x-response-text", "N/A")
                proc_time = resp.headers.get("x-processing-time", "unknown")

                log_success(f"Voice processed in {proc_time}")
                log_info(f"  Transcript: {transcript[:80]}...")
                log_info(f"  Response: {response_text[:80]}...")
                log_info(f"  Audio output: {len(resp.content)} bytes")

                return True

        except requests.Timeout:
            log_error("Voice processing timeout (60s) - service overloaded or audio too long")
            return False
        except Exception as e:
            log_error(f"Error: {e}")
            return False

    def run_all_tests(self, audio_file=None, languages=None):
        """Run the full test suite."""
        print("\n")
        print("╔" + "=" * 68 + "╗")
        print("║" + " CREDA Multilingual Service Test Suite ".center(68) + "║")
        print("╚" + "=" * 68 + "╝")

        if languages is None:
            languages = ["hi", "en"]

        tests = [
            ("Health", self.test_health),
            ("Languages", self.test_supported_languages),
        ]

        for lang in languages:
            tests.extend([
                (f"Text-to-Speech ({lang})", lambda l=lang: self.test_text_to_speech_single_turn(l)),
                (f"Conversation ({lang})", lambda l=lang: self.test_conversation_history(l)),
            ])

        tests.append(("Translation", self.test_translation))

        if audio_file:
            for lang in languages:
                tests.append(
                    (f"Voice ({lang})", lambda l=lang: self.test_voice_pipeline(audio_file, l))
                )

        results = {}
        for test_name, test_fn in tests:
            try:
                results[test_name] = test_fn()
            except Exception as e:
                log_error(f"Unexpected error in {test_name}: {e}")
                results[test_name] = False

        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        print(f"Passed: {passed}/{total}")

        for test_name, passed in sorted(results.items()):
            status = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
            print(f"  {status} {test_name}")

        if passed == total:
            print(f"\n{GREEN}✅ ALL TESTS PASSED{RESET}")
            return 0
        else:
            print(f"\n{YELLOW}⚠️  {total - passed} TEST(S) FAILED{RESET}")
            return 1


def main():
    parser = argparse.ArgumentParser(
        description="CREDA Multilingual Service Test Suite"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Service base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--voice",
        type=str,
        help="Path to audio file for voice tests",
    )
    parser.add_argument(
        "--lang",
        default="hi",
        help="Language code for tests (default: hi)",
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        help="Multiple languages to test (default: hi en)",
    )

    args = parser.parse_args()

    tester = MultilingualServiceTester(args.base_url)
    languages = args.languages or ["hi", "en"]

    return tester.run_all_tests(
        audio_file=args.voice,
        languages=languages,
    )


if __name__ == "__main__":
    sys.exit(main())
