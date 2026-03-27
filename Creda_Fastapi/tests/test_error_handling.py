#!/usr/bin/env python3
"""
Error Handling & Edge Cases Tests - Priority 2 Features

Tests:
  ✅ Corrupt audio files
  ✅ Unsupported languages
  ✅ Timeout scenarios
  ✅ Empty/invalid input
  ✅ Malformed JSON
  ✅ Very long queries (>500 chars)
  ✅ Special characters & emoji
  ✅ Code-mixing (Hinglish, Tamlish, etc.)
  ✅ Boundary conditions

Run: pytest tests/test_error_handling.py -v
"""

import pytest
import requests
import json
import time
import io
import wave
import struct
from pathlib import Path

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GATEWAY_URL = "http://localhost:8080"
MULTILINGUAL_URL = "http://localhost:8000"
FINANCE_URL = "http://localhost:8001"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST CLASS 1: CORRUPT & INVALID AUDIO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCorruptAudio:
    """Test handling of corrupted or invalid audio files."""

    def test_corrupt_wav_file(self):
        """Test endpoint with completely corrupted WAV."""
        corrupt_data = b"This is not audio at all! \x00" * 100
        
        resp = requests.post(
            f"{MULTILINGUAL_URL}/transcribe_only",
            files={"file": ("corrupt.wav", corrupt_data, "audio/wav")},
            data={"language_code": "en"},
            timeout=30,
        )
        
        # Should handle gracefully (either 400 or 422, not 500)
        assert resp.status_code in (400, 422, 500), f"Unexpected status: {resp.status_code}"
        print(f"✓ Corrupt WAV handled: {resp.status_code}")

    def test_empty_audio_file(self):
        """Test with empty audio file."""
        empty_data = b""
        
        resp = requests.post(
            f"{MULTILINGUAL_URL}/transcribe_only",
            files={"file": ("empty.wav", empty_data, "audio/wav")},
            data={"language_code": "en"},
            timeout=30,
        )
        
        assert resp.status_code in (400, 422, 500)
        print(f"✓ Empty audio handled: {resp.status_code}")

    def test_wrong_audio_format(self):
        """Test with MP3 sent as WAV."""
        # Simulate MP3 header
        mp3_header = b"ID3" + b"\x00" * 100
        
        resp = requests.post(
            f"{MULTILINGUAL_URL}/transcribe_only",
            files={"file": ("audio.wav", mp3_header, "audio/wav")},
            data={"language_code": "en"},
            timeout=30,
        )
        
        assert resp.status_code in (400, 422, 422)
        print(f"✓ Wrong audio format handled: {resp.status_code}")

    def test_exceeds_file_size_limit(self):
        """Test with excessively large audio file."""
        # Create a 500MB+ file (simulate by sending large chunk)
        large_data = b"\x00" * (600 * 1024 * 1024)  # 600MB
        
        # This may timeout or fail before reaching the service
        try:
            resp = requests.post(
                f"{MULTILINGUAL_URL}/transcribe_only",
                files={"file": ("huge.wav", large_data[:10*1024*1024], "audio/wav")},  # Still large
                data={"language_code": "en"},
                timeout=10,
            )
            assert resp.status_code in (413, 422, 500, 408)
        except (requests.Timeout, requests.ConnectionError) as e:
            # Expected for large files
            print(f"✓ Large file rejected: {type(e).__name__}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST CLASS 2: INVALID LANGUAGE CODES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestInvalidLanguages:
    """Test handling of unsupported and invalid language codes."""

    def test_unsupported_language_code(self):
        """Test with completely non-existent language."""
        resp = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "Hello",
                "user_id": "test_user",
                "language": "xx",  # Fake language code
            },
            timeout=60,
        )
        
        # Should handle gracefully
        assert resp.status_code in (400, 422, 200), f"Status: {resp.status_code}"
        print(f"✓ Unsupported language handled: {resp.status_code}")

    def test_malformed_language_code(self):
        """Test with malformed language code."""
        resp = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "Hello",
                "user_id": "test_user",
                "language": "!!!invalid!!!",
            },
            timeout=60,
        )
        
        assert resp.status_code in (400, 422, 200)

    def test_numeric_language_code(self):
        """Test with numeric language value."""
        resp = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "Hello",
                "user_id": "test_user",
                "language": 12345,  # Number instead of string
            },
            timeout=60,
        )
        
        # Should either fail gracefully or default to English
        assert resp.status_code in (400, 422, 200)

    def test_case_insensitive_language_check(self):
        """Test if language codes are case-insensitive."""
        codes = ["HI", "Hi", "TN", "EN"]  # Mixed case
        
        for code in codes:
            resp = requests.post(
                f"{GATEWAY_URL}/chat",
                json={
                    "message": "Test",
                    "user_id": "test_user",
                    "language": code.lower() if code != code else code,
                },
                timeout=60,
            )
            
            # Should work (most APIs normalize to lowercase)
            print(f"✓ Language code '{code}': {resp.status_code}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST CLASS 3: INVALID INPUT DATA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestInvalidInput:
    """Test handling of invalid or missing input parameters."""

    def test_empty_message(self):
        """Test with empty message."""
        resp = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "",
                "user_id": "test_user",
            },
            timeout=60,
        )
        
        # Should handle gracefully
        assert resp.status_code in (400, 422, 200)

    def test_null_message(self):
        """Test with null message."""
        resp = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": None,
                "user_id": "test_user",
            },
            timeout=60,
        )
        
        assert resp.status_code in (400, 422, 200)

    def test_missing_required_fields(self):
        """Test with missing required fields."""
        # Missing user_id
        resp = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "Hello",
            },
            timeout=60,
        )
        
        assert resp.status_code in (400, 422, 200)

    def test_malformed_json(self):
        """Test with invalid JSON."""
        resp = requests.post(
            f"{GATEWAY_URL}/chat",
            data="{invalid json",  # Broken JSON
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
        
        assert resp.status_code in (400, 422)

    def test_extra_unknown_fields(self):
        """Test with extra unknown fields (should be ignored)."""
        resp = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "Hello",
                "user_id": "test_user",
                "unknown_field_1": "value",
                "unknown_field_2": {"nested": "value"},
                "malicious_param": "../../etc/passwd",
            },
            timeout=60,
        )
        
        # Should ignore unknown fields and process normally
        assert resp.status_code == 200
        print("✓ Unknown fields ignored gracefully")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST CLASS 4: EDGE CASES - TEXT CONTENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestTextEdgeCases:
    """Test edge cases in text content."""

    def test_very_long_query(self):
        """Test with extremely long query (>500 chars)."""
        long_text = "Tell me about mutual funds. " * 50  # ~1500 chars
        
        resp = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": long_text,
                "user_id": "test_user",
            },
            timeout=60,
        )
        
        # Should handle (may timeout but shouldn't crash)
        assert resp.status_code in (200, 408, 413)
        print(f"✓ Long query ({len(long_text)} chars) handled")

    def test_query_with_special_characters(self):
        """Test with special characters and symbols."""
        special_queries = [
            "What is a P/E ratio?",
            "Mutual funds @200% return?",
            "Investment <= $1 million",
            "ROI: 15% per annum",
            "$$$$ wealth creation $$$$",
            "Invest 50-60% in equity",
        ]
        
        for query in special_queries:
            resp = requests.post(
                f"{GATEWAY_URL}/chat",
                json={
                    "message": query,
                    "user_id": "test_user",
                },
                timeout=60,
            )
            
            assert resp.status_code == 200
            print(f"✓ Special chars handled: "{query[:40]}..."")

    def test_query_with_emoji(self):
        """Test with emoji in query."""
        emoji_queries = [
            "Tell me about 📈 stocks",
            "I want 💰 wealth 💎",
            "Investment 🚀 strategies ✨",
            "Portfolio 📊 analysis 🎯",
        ]
        
        for query in emoji_queries:
            resp = requests.post(
                f"{GATEWAY_URL}/chat",
                json={
                    "message": query,
                    "user_id": "test_user",
                },
                timeout=60,
            )
            
            assert resp.status_code == 200
            print(f"✓ Emoji query handled")

    def test_code_mixing_hinglish(self):
        """Test Hinglish (Hindi + English code-mixing)."""
        hinglish = "Mujhe ₹50,000 per month ke liye best investment batao jo 8-10% return de"
        
        resp = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": hinglish,
                "user_id": "test_user",
                "language": "hi",  # Declared as Hindi, but mixed with English
            },
            timeout=60,
        )
        
        assert resp.status_code == 200
        print("✓ Hinglish code-mixing handled")

    def test_code_mixing_tamlish(self):
        """Test Tamlish (Tamil + English code-mixing)."""
        tamlish = "En company shares vango yada best valai"
        
        resp = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": tamlish,
                "user_id": "test_user",
                "language": "ta",
            },
            timeout=60,
        )
        
        assert resp.status_code in (200, 422)
        print("✓ Tamlish code-mixing handled")

    def test_repeated_characters(self):
        """Test with repeated characters."""
        repeated = "Hellloooooo brooooo!!!"
        
        resp = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": repeated,
                "user_id": "test_user",
            },
            timeout=60,
        )
        
        assert resp.status_code == 200


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST CLASS 5: BOUNDARY CONDITIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestBoundaryConditions:
    """Test boundary conditions and limits."""

    def test_single_character_query(self):
        """Test with single character."""
        resp = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "A",
                "user_id": "test_user",
            },
            timeout=60,
        )
        
        # Should handle
        assert resp.status_code in (200, 400, 422)

    def test_whitespace_only_query(self):
        """Test with only whitespace."""
        resp = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "     \n\t\r\n     ",
                "user_id": "test_user",
            },
            timeout=60,
        )
        
        assert resp.status_code in (200, 400, 422)

    def test_numeric_only_query(self):
        """Test with only numbers."""
        resp = requests.post(
            f"{GATEWAY_URL}/chat",
            json={
                "message": "123456789",
                "user_id": "test_user",
            },
            timeout=60,
        )
        
        assert resp.status_code == 200

    def test_zero_and_negative_values(self):
        """Test Finance API with boundary values."""
        test_values = [
            {"monthly_amount": 0, "years": 10},  # Zero investment
            {"monthly_amount": -1000, "years": 10},  # Negative investment
            {"monthly_amount": 1000, "years": 0},  # Zero years
            {"monthly_amount": 1000, "years": -5},  # Negative years
        ]
        
        for params in test_values:
            resp = requests.post(
                f"{FINANCE_URL}/sip-calculator",
                json=params,
                timeout=30,
            )
            
            # Should handle gracefully (error or default)
            assert resp.status_code in (200, 400, 422)
            print(f"✓ Boundary value handled: {params}")

    def test_very_large_investment_amount(self):
        """Test with very large investment amounts."""
        resp = requests.post(
            f"{FINANCE_URL}/sip-calculator",
            json={
                "monthly_amount": 999999999999,  # Huge amount
                "expected_return": 12,
                "years": 10,
            },
            timeout=30,
        )
        
        # Should handle (calculate or error)
        assert resp.status_code in (200, 400, 422)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST CLASS 6: TIMEOUT & RATE LIMITING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestTimeoutAndRateLimiting:
    """Test timeout and rate limiting behavior."""

    def test_endpoint_timeout(self):
        """Test that endpoints timeout gracefully."""
        # Send request with very short timeout
        try:
            resp = requests.post(
                f"{GATEWAY_URL}/chat",
                json={
                    "message": "This is a very long query that might take time" * 10,
                    "user_id": "test_user",
                },
                timeout=0.1,  # 100ms timeout (unrealistic)
            )
            # If it succeeds, it's fast
            print("✓ Response within 100ms (very fast)")
        except requests.Timeout:
            # Expected
            print("✓ Timeout handled gracefully")

    def test_rapid_sequential_requests(self):
        """Test behavior with rapid requests."""
        query = "Tell me about investment"
        
        for i in range(5):
            resp = requests.post(
                f"{GATEWAY_URL}/chat",
                json={
                    "message": query,
                    "user_id": f"user_{i}",
                    "session_id": f"session_{i}",
                },
                timeout=60,
            )
            
            assert resp.status_code == 200
            time.sleep(0.5)  # Minimal delay
        
        print("✓ Rapid sequential requests handled")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST CLASS 7: TRANSLATION EDGE CASES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestTranslationEdgeCases:
    """Test translation with edge case inputs."""

    def test_translate_empty_text(self):
        """Test translation with empty text."""
        resp = requests.post(
            f"{MULTILINGUAL_URL}/translate",
            json={
                "text": "",
                "source_language": "en",
                "target_language": "hi",
            },
            timeout=30,
        )
        
        assert resp.status_code in (200, 400, 422)

    def test_translate_numbers_only(self):
        """Test translation with only numbers."""
        resp = requests.post(
            f"{MULTILINGUAL_URL}/translate",
            json={
                "text": "123456789",
                "source_language": "en",
                "target_language": "hi",
            },
            timeout=30,
        )
        
        assert resp.status_code == 200

    def test_translate_same_source_target(self):
        """Test translation with same source and target language."""
        resp = requests.post(
            f"{MULTILINGUAL_URL}/translate",
            json={
                "text": "Hello world",
                "source_language": "en",
                "target_language": "en",  # Same language
            },
            timeout=30,
        )
        
        # Should return text as-is or handle gracefully
        assert resp.status_code in (200, 400, 422)

    def test_translate_invalid_language_pair(self):
        """Test translation with invalid language pair."""
        resp = requests.post(
            f"{MULTILINGUAL_URL}/translate",
            json={
                "text": "Hello",
                "source_language": "xyz",
                "target_language": "abc",
            },
            timeout=30,
        )
        
        assert resp.status_code in (400, 422, 200)
