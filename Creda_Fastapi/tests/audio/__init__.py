# Audio-dependent tests
# These tests require audio files to be placed in this directory.
# Run separately: pytest tests/audio/ -v
#
# Required audio files:
#   - sample_en.wav    (short English speech, e.g. "show my portfolio")
#   - sample_hi.wav    (short Hindi speech)
#   - silence.wav      (2 seconds of silence — for edge case testing)
#
# Generate test audio:
#   python -c "
#   import numpy as np; import soundfile as sf
#   sr=16000; silence=np.zeros(sr*2, dtype=np.float32)
#   sf.write('tests/audio/silence.wav', silence, sr)
#   print('Created silence.wav')
#   "
