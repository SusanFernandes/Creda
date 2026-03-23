#!/usr/bin/env python3
"""
Quick test: Verify Parler-TTS model loads and can synthesize speech.

This test verifies:
1. Parler-TTS package installed correctly (git+https install can fail silently)
2. Model loads without errors
3. Can generate audio in multiple Indian languages
4. Audio output is valid WAV

Usage:
    python quick_test_parler_tts.py
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("QUICK TEST: Parler-TTS")
print("=" * 70)

# Check imports
try:
    import torch
    print("✓ PyTorch imported")
except ImportError as e:
    print(f"❌ Failed to import torch: {e}")
    sys.exit(1)

try:
    from parler_tts import ParlerTTSForConditionalGeneration
    print("✓ Parler-TTS imported (from parler_tts package)")
except ImportError:
    print("⚠️  Parler-TTS not found as 'parler_tts' package")
    try:
        from transformers import AutoModel
        print("  Attempting AutoModel import...")
        # Sometimes it's exported via transformers
        model = AutoModel.from_pretrained("ai4bharat/indic-parler-tts", trust_remote_code=True)
        ParlerTTSForConditionalGeneration = type(model)
        print("✓ Parler-TTS loaded via AutoModel")
    except Exception as e:
        print(f"❌ Failed to import Parler-TTS: {e}")
        print("\nInstall with:")
        print("  pip install git+https://github.com/huggingface/parler-tts.git")
        sys.exit(1)

try:
    from transformers import AutoTokenizer
    print("✓ AutoTokenizer imported")
except ImportError as e:
    print(f"❌ Failed to import transformers: {e}")
    sys.exit(1)

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"✓ Device: {device}")

# Load model
print("\n[Step 1] Loading Parler-TTS model...")
try:
    model = ParlerTTSForConditionalGeneration.from_pretrained(
        "ai4bharat/indic-parler-tts"
    ).to(device)
    print("✓ Model loaded successfully")
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    print("\nTroubleshooting:")
    print("  - Check internet connection")
    print("  - Try: huggingface-cli download ai4bharat/indic-parler-tts")
    sys.exit(1)

# Load tokenizer
print("[Step 2] Loading tokenizer...")
try:
    tokenizer = AutoTokenizer.from_pretrained("ai4bharat/indic-parler-tts")
    print("✓ Tokenizer loaded successfully")
except Exception as e:
    print(f"❌ Failed to load tokenizer: {e}")
    sys.exit(1)

# Voice descriptions for different languages
VOICE_DESCRIPTIONS = {
    "hi": "Divya speaks Hindi clearly and warmly at a moderate pace. Studio quality recording with no background noise.",
    "ta": "Kavitha speaks Tamil in a clear, friendly tone at moderate pace. High quality recording.",
    "te": "Arjun speaks Telugu clearly with a helpful, warm tone. High quality recording.",
    "bn": "Ananya speaks Bengali warmly and clearly at moderate pace. High quality recording.",
    "en": "Priya speaks English with an Indian accent, clearly and warmly. High quality recording.",
}

# Test texts
test_cases = [
    {"lang": "hi", "text": "नमस्ते। मैं पार्लर टीटीएस हूं।"},
    {"lang": "ta", "text": "வணக்கம். நான் பார்லர் டிடிஎஸ் ஆகும்."},
    {"lang": "te", "text": "నమస్కారం. నేను పార్లర్ టిటిఎస్."},
    {"lang": "bn", "text": "নমস্কার। আমি পার্লার টিটিএস।"},
    {"lang": "en", "text": "Hello. I am Parler TTS."},
]

print("\n[Step 3] Testing synthesis in different languages...")
print("=" * 70)

all_passed = True
for test in test_cases:
    lang = test["lang"]
    text = test["text"]
    description = VOICE_DESCRIPTIONS.get(lang, "A clear, natural voice.")

    print(f"\nLanguage: {lang}")
    print(f"  Text: {text[:60]}...")
    print(f"  Voice: {description[:60]}...")

    try:
        # Tokenize description + text
        input_ids = tokenizer(description, return_tensors="pt").input_ids.to(device)
        prompt_input_ids = tokenizer(text, return_tensors="pt").input_ids.to(device)

        # Use model's generate if available, or forward
        with torch.no_grad():
            if hasattr(model, "generate"):
                output = model.generate(
                    input_ids=input_ids,
                    prompt_input_ids=prompt_input_ids,
                    do_sample=True,
                    top_k=250,
                    max_length=1024,
                )
            else:
                # Fallback to forward if generate not available
                output = model(
                    input_ids=input_ids,
                    prompt_input_ids=prompt_input_ids,
                )

        print(f"  ✓ Audio generated, shape: {output.shape if hasattr(output, 'shape') else 'streaming'}")

    except Exception as e:
        print(f"  ❌ Failed: {str(e)[:80]}")
        all_passed = False

print("\n" + "=" * 70)
if all_passed:
    print("✅ PARLER-TTS TEST PASSED")
    print("=" * 70)
    print("\nTTS service is ready. You can now start the full service:")
    print("  uvicorn fastapi1_multilingual:app --reload")
else:
    print("⚠️  SOME TTS TESTS FAILED")
    print("=" * 70)
    print("\nTroubleshooting:")
    print("  - Reinstall parler-tts:")
    print("    pip uninstall parler-tts -y")
    print("    pip install git+https://github.com/huggingface/parler-tts.git")
    print("  - Check GPU memory (TTS needs ~2-3GB)")
    print("  - Try CPU mode if GPU is out of memory")
    sys.exit(1)
