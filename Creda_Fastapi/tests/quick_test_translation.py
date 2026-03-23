#!/usr/bin/env python3
"""
Quick test: Verify IndicTrans2 models load correctly and translate correctly.

CRITICAL: IndicTrans2 has two separate models and this test verifies:
1. Both models (indic-en and en-indic) load correctly
2. Each model is used in the correct direction
3. IndicProcessor is properly initialized
4. Translations work in both directions

Usage:
    python quick_test_translation.py
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("QUICK TEST: IndicTrans2 Translation")
print("=" * 70)

# Import checks
try:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    print("✓ Transformers imported")
except ImportError as e:
    print(f"❌ Failed to import transformers: {e}")
    sys.exit(1)

try:
    from IndicTransToolkit.processor import IndicProcessor
    print("✓ IndicTransToolkit imported")
except ImportError as e:
    print(f"❌ Failed to import IndicTransToolkit: {e}")
    print("  Install with: pip install IndicTransToolkit")
    sys.exit(1)

import torch

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"✓ Device: {device}")

# CRITICAL: IndicProcessor must be initialized
print("\n[Step 1] Initializing IndicProcessor...")
try:
    ip = IndicProcessor(inference=True)
    print("✓ IndicProcessor initialized")
except Exception as e:
    print(f"❌ Failed to initialize IndicProcessor: {e}")
    sys.exit(1)

# Load FIRST model: Indic → English
print("\n[Step 2] Loading indic-en model (Indic → English)...")
try:
    indic_en_model = AutoModelForSeq2SeqLM.from_pretrained(
        "ai4bharat/indictrans2-indic-en-dist-200M",
        trust_remote_code=True,
    ).to(device)
    indic_en_tokenizer = AutoTokenizer.from_pretrained(
        "ai4bharat/indictrans2-indic-en-dist-200M",
        trust_remote_code=True,
    )
    print("✓ Indic→En model loaded")
except Exception as e:
    print(f"❌ Failed to load indic-en model: {e}")
    sys.exit(1)

# Load SECOND model: English → Indic
print("[Step 3] Loading en-indic model (English → Indic)...")
try:
    en_indic_model = AutoModelForSeq2SeqLM.from_pretrained(
        "ai4bharat/indictrans2-en-indic-dist-200M",
        trust_remote_code=True,
    ).to(device)
    en_indic_tokenizer = AutoTokenizer.from_pretrained(
        "ai4bharat/indictrans2-en-indic-dist-200M",
        trust_remote_code=True,
    )
    print("✓ En→Indic model loaded")
except Exception as e:
    print(f"❌ Failed to load en-indic model: {e}")
    sys.exit(1)

# FLORES code mapping (needed for IndicTrans2)
FLORES_CODES = {
    "hi": "hin_Deva",  "ta": "tam_Taml",  "te": "tel_Telu",
    "bn": "ben_Beng",  "mr": "mar_Deva",  "gu": "guj_Gujr",
    "kn": "kan_Knda",  "ml": "mal_Mlym",  "pa": "pan_Guru",
    "ur": "urd_Arab",  "as": "asm_Beng",  "or": "ory_Orya",
    "en": "eng_Latn",
}

# Test cases
test_cases = [
    {
        "name": "Hindi → English",
        "text": "मैं आपके लिए वित्तीय सलाह दे सकता हूं।",
        "src_lang": "hi",
        "model": indic_en_model,
        "tokenizer": indic_en_tokenizer,
        "tgt_flores": "eng_Latn",
        "direction": "Indic→En",
    },
    {
        "name": "Tamil → English",
        "text": "நான் உங்களுக்கு நிதி ஆலோசனை வழங்க முடியும்.",
        "src_lang": "ta",
        "model": indic_en_model,
        "tokenizer": indic_en_tokenizer,
        "tgt_flores": "eng_Latn",
        "direction": "Indic→En",
    },
    {
        "name": "English → Hindi",
        "text": "I can provide you with financial advice.",
        "src_lang": "en",
        "model": en_indic_model,
        "tokenizer": en_indic_tokenizer,
        "tgt_flores": "hin_Deva",
        "direction": "En→Indic",
    },
    {
        "name": "English → Tamil",
        "text": "SIP is a systematic investment plan.",
        "src_lang": "en",
        "model": en_indic_model,
        "tokenizer": en_indic_tokenizer,
        "tgt_flores": "tam_Taml",
        "direction": "En→Indic",
    },
]

print("\n[Step 4] Testing translations...")
print("=" * 70)

all_passed = True
for i, test in enumerate(test_cases, 1):
    print(f"\nTest {i}: {test['name']}")
    print(f"  Direction: {test['direction']}")
    print(f"  Input: {test['text'][:60]}...")

    try:
        src_flores = FLORES_CODES[test["src_lang"]]

        # CRITICAL: Must use preprocess_batch
        batch = ip.preprocess_batch(
            [test["text"]],
            src_lang=src_flores,
            tgt_lang=test["tgt_flores"],
        )

        # Tokenize
        inputs = test["tokenizer"](
            batch,
            return_tensors="pt",
            padding=True,
            truncation=True,
        ).to(device)

        # Generate
        with torch.no_grad():
            generated = test["model"].generate(**inputs, max_length=256, num_beams=4)

        # Decode
        decoded = test["tokenizer"].batch_decode(generated, skip_special_tokens=True)

        # CRITICAL: Must use postprocess_batch
        result = ip.postprocess_batch(decoded, lang=test["tgt_flores"])[0]

        print(f"  ✓ Output: {result[:80]}")

    except Exception as e:
        print(f"  ❌ Failed: {e}")
        all_passed = False

print("\n" + "=" * 70)
if all_passed:
    print("✅ TRANSLATION TEST PASSED")
    print("=" * 70)
    print("\nTranslation service is ready. You can now:")
    print("  1. Run quick_test_parler_tts.py to test text-to-speech")
    print("  2. Start the full service: uvicorn fastapi1_multilingual:app --reload")
else:
    print("⚠️  SOME TRANSLATION TESTS FAILED")
    print("=" * 70)
    print("\nTroubleshooting:")
    print("  - Check IndicTransToolkit installation: pip install IndicTransToolkit")
    print("  - Verify HuggingFace token is set if models don't download")
    print("  - Check internet connection")
    sys.exit(1)
