# Audio Tests README
#
# These tests require audio files to be placed in this directory.
#
# Required files:
#   sample_en.wav  — Short English speech (e.g. "show my portfolio", 2-5 seconds)
#   sample_hi.wav  — Short Hindi speech (e.g. "मेरा पोर्टफोलियो दिखाओ", 2-5 seconds)
#   silence.wav    — 2 seconds of silence (for edge case testing)
#
# Generate silence.wav automatically:
#   python -c "
#   import numpy as np; import soundfile as sf
#   sr=16000; silence=np.zeros(sr*2, dtype=np.float32)
#   sf.write('tests/audio/silence.wav', silence, sr)
#   print('Created silence.wav')
#   "
#
# Run audio tests:
#   cd Creda_Fastapi
#   pytest tests/audio/ -v
#
# Tests auto-skip if audio files are missing.
