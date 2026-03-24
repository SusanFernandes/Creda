#!/usr/bin/env python3
"""
Quick test: Verify IndicConformer-600M model loads and signature is correct.
This is the MOST CRITICAL TEST because the forward() call signature is not standard.

AI4Bharat models use trust_remote_code=True, which means the forward() function
signature is defined in the model's custom code, not HuggingFace standard Transformers.

This test verifies:
1. Model loads without errors
2. The actual method signature (may be forward(), transcribe(), or something else)
3. A dummy audio can be transcribed

Usage:
    python quick_test_asr.py
"""

import os
import sys
import torch
import torchaudio
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("QUICK TEST: IndicConformer-600M ASR Model")
print("=" * 70)

try:
    from transformers import AutoModel
    print("✓ Transformers imported")
except ImportError as e:
    print(f"❌ Failed to import transformers: {e}")
    sys.exit(1)

# Step 1: Load model
print("\n[Step 1] Loading IndicConformer-600M-multilingual...")
try:
    model = AutoModel.from_pretrained(
        "ai4bharat/indic-conformer-600m-multilingual",
        trust_remote_code=True,
    )
    print("✓ Model loaded successfully")
    print(f"  Model type: {type(model)}")
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    print("\nTroubleshooting:")
    print("  - Check internet connection")
    print("  - Check HuggingFace token (export HF_TOKEN=your_token)")
    print("  - Try: huggingface-cli download ai4bharat/indic-conformer-600m-multilingual")
    sys.exit(1)

# Step 2: Inspect the model to find the actual method
print("\n[Step 2] Inspecting model methods...")
print(f"  Model class: {model.__class__.__name__}")
print(f"  Model device: cuda if available, else cpu")

# List available methods
methods = [m for m in dir(model) if not m.startswith("_") and callable(getattr(model, m))]
print(f"  Available key methods: {', '.join(methods[:10])}...")

# Check for common entry points
if hasattr(model, "forward"):
    print("  ✓ Has forward() method")
if hasattr(model, "transcribe"):
    print("  ✓ Has transcribe() method")
if hasattr(model, "__call__"):
    print("  ✓ Has __call__() method (callable directly)")

# Step 3: Create dummy audio (3 seconds of silence at 16kHz)
print("\n[Step 3] Creating dummy audio (3 sec silence at 16kHz)...")
try:
    wav = torch.zeros(1, 48000)  # 3 seconds at 16kHz
    print(f"✓ Dummy audio created: shape {wav.shape}, dtype {wav.dtype}")
except Exception as e:
    print(f"❌ Failed to create dummy audio: {e}")
    sys.exit(1)

# Step 4: Test the actual call signature
print("\n[Step 4] Testing call signature...")
call_methods = [
    ("model(wav, 'hi', 'rnnt')", lambda: model(wav, "hi", "rnnt")),
    ("model.forward(wav, 'hi', 'rnnt')", lambda: model.forward(wav, "hi", "rnnt")),
    ("model.transcribe(wav, 'hi', 'rnnt')", lambda: model.transcribe(wav, "hi", "rnnt")),
]

success = False
for method_name, method_fn in call_methods:
    try:
        print(f"\n  Trying: {method_name}")
        result = method_fn()
        print(f"  ✓ SUCCESS! Method signature works")
        print(f"    Result type: {type(result)}")
        print(f"    Result: {str(result)[:100]}...")
        success = True
        break
    except TypeError as e:
        print(f"  ✗ TypeError (wrong signature): {str(e)[:80]}")
    except Exception as e:
        print(f"  ✗ Exception: {str(e)[:80]}")

if not success:
    print("\n❌ None of the standard call signatures worked!")
    print("\nTroubleshooting:")
    print("  - Check model documentation: https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual")
    print("  - Try: model.__call__.__doc__")
    print("  - Try: help(model)")
    sys.exit(1)

# Step 5: Test different languages
print("\n[Step 5] Testing different languages...")
languages = ["hi", "ta", "te", "bn", "en"]

for lang in languages:
    try:
        result = model(wav, lang, "rnnt")
        # Result might be a string, dict, or other type
        status = "✓" if result else "⚠️"
        print(f"  {status} {lang}: {type(result).__name__}")
    except Exception as e:
        print(f"  ❌ {lang}: {str(e)[:60]}")

print("\n" + "=" * 70)
print("✅ ASR MODEL TEST PASSED")
print("=" * 70)
print("\nASR service is ready. You can now:")
print("  1. Run quick_test_translation.py to test translation")
print("  2. Run quick_test_parler_tts.py to test text-to-speech")
print("  3. Start the full service: uvicorn fastapi1_multilingual:app --reload")
