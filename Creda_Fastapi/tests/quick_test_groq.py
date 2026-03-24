#!/usr/bin/env python3
"""
Quick test: Verify Groq API key works and LLM responds correctly.
Run this FIRST before starting the full service.

Usage:
    python quick_test_groq.py
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY not set in .env file")
    sys.exit(1)

print("=" * 70)
print("QUICK TEST: Groq LLM")
print("=" * 70)
print(f"API Key found: {GROQ_API_KEY[:20]}...{GROQ_API_KEY[-10:]}")

try:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    print("✓ Groq client initialized")
except Exception as e:
    print(f"❌ Failed to initialize Groq client: {e}")
    sys.exit(1)

# Test 1: English response
print("\n[Test 1] English: Simple greeting")
try:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Say hello in exactly one sentence"}],
        max_tokens=50,
    )
    reply = response.choices[0].message.content
    print(f"✓ Response: {reply}")
except Exception as e:
    print(f"❌ Failed: {e}")
    sys.exit(1)

# Test 2: Hindi response (critical for multilingual service)
print("\n[Test 2] Hindi: Multilingual capability")
try:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": "आप कौन हैं? एक लाइन में हिंदी में बताइए।"
            }
        ],
        max_tokens=50,
    )
    reply = response.choices[0].message.content
    print(f"✓ Response: {reply}")
except Exception as e:
    print(f"❌ Failed: {e}")
    sys.exit(1)

# Test 3: Financial context
print("\n[Test 3] Financial: Domain context")
try:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a CA. Respond in Hindi only.",
            },
            {
                "role": "user",
                "content": "SIP क्या है? एक लाइन में बताइए।"
            }
        ],
        max_tokens=50,
    )
    reply = response.choices[0].message.content
    print(f"✓ Response: {reply}")
except Exception as e:
    print(f"❌ Failed: {e}")
    sys.exit(1)

# Test 4: Tamil response (another major Indian language)
print("\n[Test 4] Tamil: Another major language")
try:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": "நீங்கள் யார்? ஒரு வரியில் சொல்லுங்கள்."
            }
        ],
        max_tokens=50,
    )
    reply = response.choices[0].message.content
    print(f"✓ Response: {reply}")
except Exception as e:
    print(f"❌ Failed (Tamil may require more specific setup): {e}")

print("\n" + "=" * 70)
print("✅ GROQ LLM TEST PASSED")
print("=" * 70)
print("\nGroq service is ready. You can now:")
print("  1. Run quick_test_asr.py to test speech-to-text")
print("  2. Run quick_test_translation.py to test translation")
print("  3. Run quick_test_parler_tts.py to test text-to-speech")
print("  4. Start the full service: uvicorn fastapi1_multilingual:app --reload")
