# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CREDA Multilingual Service v2.0
# Voice-first AI financial coaching in 22 Indian languages
# Port 8000
#
# Pipeline: Voice → IndicConformer ASR → Groq LLM → Indic Parler-TTS
# Translation (IndicTrans2) only used for backend English→Indic
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import asyncio
import os
import io
import json
import time
import logging
from contextlib import asynccontextmanager
from typing import Optional
from urllib.parse import quote as url_quote

import torch
import soundfile as sf
import numpy as np
from scipy import signal as scipy_signal
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOGGING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("creda.multilingual")


def _resample_waveform(wav: torch.Tensor, orig_sr: int, target_sr: int) -> torch.Tensor:
    """Resample (1, T) waveform; prefers torchaudio if compatible, else scipy (avoids broken torchaudio DLLs on Windows)."""
    if orig_sr == target_sr:
        return wav
    try:
        import torchaudio

        return torchaudio.transforms.Resample(orig_freq=orig_sr, new_freq=target_sr)(wav)
    except Exception as e:
        logger.debug("torchaudio resample unavailable (%s), using scipy", e)
        w = wav.squeeze(0).detach().cpu().numpy().astype(np.float64)
        num = int(round(w.shape[-1] * target_sr / float(orig_sr)))
        out = scipy_signal.resample(w, num)
        return torch.from_numpy(out.astype(np.float32)).unsqueeze(0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LANG_NAMES = {
    "hi": "Hindi",    "ta": "Tamil",      "te": "Telugu",
    "bn": "Bengali",  "mr": "Marathi",    "gu": "Gujarati",
    "kn": "Kannada",  "ml": "Malayalam",   "pa": "Punjabi",
    "ur": "Urdu",     "en": "English",     "as": "Assamese",
    "or": "Odia",     "mai": "Maithili",   "kok": "Konkani",
    "sa": "Sanskrit", "sd": "Sindhi",      "ne": "Nepali",
    "doi": "Dogri",   "brx": "Bodo",       "mni": "Manipuri",
    "sat": "Santali",
}

FLORES_CODES = {
    "hi": "hin_Deva",  "ta": "tam_Taml",  "te": "tel_Telu",
    "bn": "ben_Beng",  "mr": "mar_Deva",  "gu": "guj_Gujr",
    "kn": "kan_Knda",  "ml": "mal_Mlym",  "pa": "pan_Guru",
    "ur": "urd_Arab",  "as": "asm_Beng",  "or": "ory_Orya",
    "en": "eng_Latn",
}

VOICE_DESCRIPTIONS = {
    "hi": "Divya speaks Hindi clearly and warmly at a moderate pace. Studio quality recording with no background noise.",
    "ta": "Kavitha speaks Tamil in a clear, friendly tone at moderate pace. High quality recording.",
    "te": "Arjun speaks Telugu clearly with a helpful, warm tone. High quality recording.",
    "bn": "Ananya speaks Bengali warmly and clearly at moderate pace. High quality recording.",
    "mr": "Priya speaks Marathi clearly and confidently. High quality recording.",
    "gu": "Hitesh speaks Gujarati in a clear, friendly tone. High quality recording.",
    "kn": "Kaveri speaks Kannada warmly and clearly. High quality recording.",
    "ml": "Vidya speaks Malayalam in a clear, calm tone. High quality recording.",
    "pa": "Gurpreet speaks Punjabi clearly and warmly. High quality recording.",
    "ur": "Zara speaks Urdu in a clear, calm, and warm tone. High quality recording.",
    "en": "Priya speaks English with an Indian accent, clearly and warmly. High quality recording.",
}

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
FASTAPI2_URL = os.getenv("FASTAPI2_URL", "http://localhost:8001")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENGINE 1 — ASR  (Speech → Text)
# Model: ai4bharat/indic-conformer-600m-multilingual
# Single model covers all 22 scheduled Indian languages.
# Language is passed as a hint — NOT auto-detected from audio.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ASREngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.fallback_pipeline = None

        # Primary: IndicConformer multilingual
        try:
            from transformers import AutoModel

            logger.info("Loading ASR primary: ai4bharat/indic-conformer-600m-multilingual ...")
            self.model = AutoModel.from_pretrained(
                "ai4bharat/indic-conformer-600m-multilingual",
                trust_remote_code=True,
            ).to(self.device)
            logger.info("ASR primary (IndicConformer) loaded on %s", self.device)
        except Exception as e:
            logger.warning("ASR primary failed to load: %s", e)
            self._load_fallback()

    def _load_fallback(self):
        """Load Whisper as fallback ASR."""
        try:
            from transformers import pipeline as hf_pipeline

            logger.info("Loading ASR fallback: openai/whisper-large-v3 ...")
            self.fallback_pipeline = hf_pipeline(
                "automatic-speech-recognition",
                model="openai/whisper-large-v3",
                device=0 if self.device == "cuda" else -1,
                chunk_length_s=30,
            )
            logger.info("ASR fallback (Whisper) loaded")
        except Exception as e:
            logger.error("ASR fallback also failed: %s", e)

    def preprocess_audio(self, audio_bytes: bytes) -> torch.Tensor:
        """Raw bytes → 16 kHz mono float tensor of shape (1, num_samples)."""
        buf = io.BytesIO(audio_bytes)
        wav: torch.Tensor | None = None
        sr: int | None = None

        # Prefer soundfile first (avoids importing torchaudio when its Windows DLLs mismatch torch).
        try:
            buf.seek(0)
            audio_np, sr = sf.read(buf, dtype="float32")
            wav = torch.from_numpy(audio_np).float()
            if wav.dim() == 1:
                wav = wav.unsqueeze(0)
            elif wav.dim() == 2 and wav.shape[1] <= 2:
                wav = wav.T
        except Exception:
            wav = None

        if wav is None:
            try:
                import torchaudio

                buf.seek(0)
                wav, sr = torchaudio.load(buf)
            except Exception as e:
                logger.debug("torchaudio.load skipped: %s", e)
                wav = None

        if wav is None:
            # pydub fallback — handles M4A/AAC from Expo (requires ffmpeg in PATH)
            buf.seek(0)
            try:
                from pydub import AudioSegment

                seg = AudioSegment.from_file(buf)
                seg = seg.set_channels(1).set_frame_rate(16000)
                samples = np.array(seg.get_array_of_samples(), dtype=np.float32)
                samples /= np.iinfo(seg.array_type).max
                wav = torch.from_numpy(samples).unsqueeze(0)
                sr = 16000
            except Exception as pydub_err:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported audio format — tried soundfile, torchaudio, pydub: {pydub_err}. "
                    "Ensure ffmpeg is installed on the server.",
                )

        # mono
        if wav.shape[0] > 1:
            wav = torch.mean(wav, dim=0, keepdim=True)

        # resample to 16 kHz
        if sr is not None and sr != 16000:
            wav = _resample_waveform(wav, sr, 16000)

        # peak-normalize
        wav = wav / (wav.abs().max() + 1e-8)
        return wav

    def transcribe(self, audio_bytes: bytes, language_code: str) -> str:
        """
        Transcribe audio bytes in the given language.
        language_code is 2-letter ISO ("hi", "ta", "te") or extended ("mai", "kok").
        """
        wav = self.preprocess_audio(audio_bytes)

        # Primary: IndicConformer
        if self.model is not None:
            try:
                wav_dev = wav.to(self.device)
                with torch.no_grad():
                    transcript = self.model(wav_dev, language_code, "rnnt")
                return transcript if isinstance(transcript, str) else str(transcript)
            except Exception as e:
                logger.warning("ASR primary inference failed, falling back to Whisper: %s", e)
                if self.fallback_pipeline is None:
                    self._load_fallback()

        # Fallback: Whisper
        if self.fallback_pipeline is not None:
            try:
                wav_np = wav.squeeze(0).numpy()
                result = self.fallback_pipeline(
                    {"raw": wav_np, "sampling_rate": 16000},
                    generate_kwargs={"language": language_code},
                )
                return result["text"]
            except Exception as e:
                logger.error("ASR fallback inference failed: %s", e)
                raise HTTPException(status_code=500, detail=f"All ASR engines failed: {e}")

        raise HTTPException(status_code=503, detail="No ASR engine available")

    @property
    def is_ready(self) -> bool:
        return self.model is not None or self.fallback_pipeline is not None

    @property
    def engine_type(self) -> str:
        if self.model is not None:
            return "IndicConformer-600M (primary)"
        if self.fallback_pipeline is not None:
            return "Whisper-large-v3 (fallback)"
        return "unavailable"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENGINE 2 — LLM  (Financial response in native language)
# Provider: Groq Cloud — free tier, no credit-card required
# CRITICAL: The LLM responds DIRECTLY in the user's language.
# There is NO translation step before or after this.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class LLMEngine:
    def __init__(self):
        from groq import Groq

        if not GROQ_API_KEY:
            logger.error("GROQ_API_KEY not set — LLM engine will not work")
        self.client = Groq(api_key=GROQ_API_KEY)
        self.primary_model = "llama-3.3-70b-versatile"
        self.fallback_model = "llama-3.1-8b-instant"
        logger.info(
            "LLM engine (Groq) initialized  primary=%s  fallback=%s",
            self.primary_model,
            self.fallback_model,
        )

    def _build_system_prompt(self, language_code: str, user_profile: dict) -> str:
        lang_name = LANG_NAMES.get(language_code, "Hindi")
        return f"""You are CREDA, a friendly AI financial coach for Indian users.

LANGUAGE RULE: The user is speaking {lang_name}. You MUST respond ONLY in {lang_name}.
If the user mixes Hindi and English (Hinglish), respond in the same mix naturally.
Never respond in English if the user spoke in a regional language.

RESPONSE FORMAT: Keep responses under 80 words. This will be spoken aloud via
text-to-speech, so write naturally as you would speak — no bullet points, no
markdown, no headers.

INDIAN FINANCIAL CONTEXT you must understand:
- SIP (Systematic Investment Plan), ELSS (tax-saving mutual funds), PPF (Public
  Provident Fund), NPS (National Pension System), demat account, CAMS statement,
  XIRR, expense ratio, Section 80C, LTCG, chit funds, gold loans, Sukanya Samriddhi
  Yojana — these are all standard Indian financial terms.
- Currency is always Indian Rupees (₹), not dollars.
- Regulatory bodies are RBI, SEBI, IRDAI, PFRDA.

USER PROFILE:
- Monthly income: ₹{user_profile.get('income', 'not provided')}
- Savings rate: {user_profile.get('savings_rate', 'not provided')}%
- Risk profile: {user_profile.get('risk_profile', 'moderate')}
- Age: {user_profile.get('age', 'not provided')}
- Goals: {user_profile.get('goals', 'not provided')}

Speak like a trusted friend who happens to be a CA — warm, clear, and practical."""

    def get_financial_response(
        self,
        transcript: str,
        language_code: str,
        user_profile: dict,
        session_id: str = "default",
    ) -> str:
        system_prompt = self._build_system_prompt(language_code, user_profile)
        
        # Get conversation history for this session (last 6 messages = 3 exchanges)
        history = _conversation_store.get(session_id, [])[-6:]
        
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        messages.extend(history)
        messages.append({"role": "user", "content": transcript})

        # Primary model
        try:
            resp = self.client.chat.completions.create(
                model=self.primary_model,
                messages=messages,
                max_tokens=200,
                temperature=0.7,
            )
            reply = resp.choices[0].message.content
            # Store conversation for next turn
            _conversation_store[session_id].append({"role": "user", "content": transcript})
            _conversation_store[session_id].append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            logger.warning("LLM primary (%s) failed, falling back: %s", self.primary_model, e)

        # Fallback model
        try:
            resp = self.client.chat.completions.create(
                model=self.fallback_model,
                messages=messages,
                max_tokens=200,
                temperature=0.7,
            )
            reply = resp.choices[0].message.content
        except Exception as e:
            logger.error("LLM fallback (%s) also failed: %s", self.fallback_model, e)
            raise HTTPException(status_code=503, detail=f"All LLM engines failed: {e}")
        
        # Store conversation for next turn
        _conversation_store[session_id].append({"role": "user", "content": transcript})
        _conversation_store[session_id].append({"role": "assistant", "content": reply})
        
        return reply

    @property
    def is_ready(self) -> bool:
        return self.client is not None and GROQ_API_KEY is not None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENGINE 3 — TTS  (Text → Speech)
# Model: ai4bharat/indic-parler-tts
# Auto-detects language from the text script.
# Voice character controlled via description string.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TTSEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None
        self.desc_tokenizer = None
        self.sample_rate = 44100

        try:
            from parler_tts import ParlerTTSForConditionalGeneration
            from transformers import AutoTokenizer

            logger.info("Loading TTS primary: ai4bharat/indic-parler-tts ...")
            self.model = ParlerTTSForConditionalGeneration.from_pretrained(
                "ai4bharat/indic-parler-tts",
            ).to(self.device)
            self.tokenizer = AutoTokenizer.from_pretrained("ai4bharat/indic-parler-tts")
            self.desc_tokenizer = AutoTokenizer.from_pretrained(
                self.model.config.text_encoder._name_or_path,
            )

            # Use model's native sample rate when available
            if hasattr(self.model.config, "sampling_rate"):
                self.sample_rate = self.model.config.sampling_rate

            logger.info("TTS primary (Indic Parler-TTS) loaded  sr=%d", self.sample_rate)
        except Exception as e:
            logger.warning("TTS primary failed to load: %s", e)

    def synthesize(self, text: str, language_code: str) -> bytes:
        """Generate WAV audio bytes for the given text and language."""
        if self.model is not None:
            try:
                return self._synthesize_parler(text, language_code)
            except Exception as e:
                logger.warning("TTS primary inference failed, falling back to gTTS: %s", e)

        return self._synthesize_gtts(text, language_code)

    def _synthesize_parler(self, text: str, language_code: str) -> bytes:
        description = VOICE_DESCRIPTIONS.get(language_code, VOICE_DESCRIPTIONS["hi"])

        desc_ids = self.desc_tokenizer(description, return_tensors="pt").to(self.device)
        prompt_ids = self.tokenizer(text, return_tensors="pt").to(self.device)

        with torch.no_grad():
            generation = self.model.generate(
                input_ids=desc_ids.input_ids,
                attention_mask=desc_ids.attention_mask,
                prompt_input_ids=prompt_ids.input_ids,
                prompt_attention_mask=prompt_ids.attention_mask,
            )

        audio_arr = generation.cpu().numpy().squeeze()
        buf = io.BytesIO()
        sf.write(buf, audio_arr, samplerate=self.sample_rate, format="WAV")
        buf.seek(0)
        return buf.read()

    def _synthesize_gtts(self, text: str, language_code: str) -> bytes:
        """gTTS fallback — free, online, lower quality."""
        try:
            from gtts import gTTS

            tts = gTTS(text=text, lang=language_code)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            buf.seek(0)
            return buf.read()
        except Exception as e:
            logger.error("TTS fallback (gTTS) also failed: %s", e)
            raise HTTPException(status_code=503, detail=f"All TTS engines failed: {e}")

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    @property
    def engine_type(self) -> str:
        if self.model is not None:
            return "Indic Parler-TTS (primary)"
        return "gTTS (fallback-only)"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENGINE 4 — TRANSLATION  (IndicTrans2)
# ONLY used when the finance backend (Port 8001) returns English
# text that needs converting to the user's language.
# NOT in the main voice path.
#
# Critical fix from v1: IndicProcessor is properly initialized.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TranslationEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if self.device == "cuda" else torch.float32

        self.indic_en_model = None
        self.indic_en_tokenizer = None
        self.en_indic_model = None
        self.en_indic_tokenizer = None
        self.ip = None  # IndicProcessor — was MISSING in v1

        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            from IndicTransToolkit.processor import IndicProcessor

            # IndicProcessor — THIS was the critical missing piece in v1
            self.ip = IndicProcessor(inference=True)

            # Indic → English
            indic_en = "ai4bharat/indictrans2-indic-en-dist-200M"
            logger.info("Loading Translation (Indic->En): %s ...", indic_en)
            self.indic_en_tokenizer = AutoTokenizer.from_pretrained(
                indic_en, trust_remote_code=True,
            )
            self.indic_en_model = AutoModelForSeq2SeqLM.from_pretrained(
                indic_en, trust_remote_code=True, torch_dtype=dtype,
            ).to(self.device)
            logger.info("Translation (Indic->En) loaded")

            # English → Indic
            en_indic = "ai4bharat/indictrans2-en-indic-dist-200M"
            logger.info("Loading Translation (En->Indic): %s ...", en_indic)
            self.en_indic_tokenizer = AutoTokenizer.from_pretrained(
                en_indic, trust_remote_code=True,
            )
            self.en_indic_model = AutoModelForSeq2SeqLM.from_pretrained(
                en_indic, trust_remote_code=True, torch_dtype=dtype,
            ).to(self.device)
            logger.info("Translation (En->Indic) loaded")

        except Exception as e:
            logger.warning("Translation engine failed to load: %s", e)

    def translate_to_english(self, text: str, src_lang: str) -> str:
        """Translate from an Indian language to English."""
        if src_lang == "en":
            return text
        if self.indic_en_model is None or self.ip is None:
            raise HTTPException(
                status_code=503,
                detail="Translation engine (Indic->En) not available",
            )

        src_flores = FLORES_CODES.get(src_lang, "hin_Deva")
        batch = self.ip.preprocess_batch([text], src_lang=src_flores, tgt_lang="eng_Latn")
        inputs = self.indic_en_tokenizer(
            batch, return_tensors="pt", padding=True, truncation=True,
        ).to(self.device)

        with torch.no_grad():
            generated = self.indic_en_model.generate(**inputs, max_length=256, num_beams=4)

        decoded = self.indic_en_tokenizer.batch_decode(generated, skip_special_tokens=True)
        return self.ip.postprocess_batch(decoded, lang="eng_Latn")[0]

    def translate_from_english(self, text: str, tgt_lang: str) -> str:
        """Translate from English to an Indian language."""
        if tgt_lang == "en":
            return text
        if self.en_indic_model is None or self.ip is None:
            raise HTTPException(
                status_code=503,
                detail="Translation engine (En->Indic) not available",
            )

        tgt_flores = FLORES_CODES.get(tgt_lang, "hin_Deva")
        batch = self.ip.preprocess_batch([text], src_lang="eng_Latn", tgt_lang=tgt_flores)
        inputs = self.en_indic_tokenizer(
            batch, return_tensors="pt", padding=True, truncation=True,
        ).to(self.device)

        with torch.no_grad():
            generated = self.en_indic_model.generate(**inputs, max_length=256, num_beams=4)

        decoded = self.en_indic_tokenizer.batch_decode(generated, skip_special_tokens=True)
        return self.ip.postprocess_batch(decoded, lang=tgt_flores)[0]

    @property
    def is_ready(self) -> bool:
        return self.ip is not None and (
            self.indic_en_model is not None or self.en_indic_model is not None
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FASTAPI APPLICATION
# Models load ONCE at startup via lifespan, not per-request.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONVERSATION HISTORY STORE
# In-memory storage for multi-turn conversations per session.
# Resets on service restart (acceptable for MVP).
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from collections import defaultdict
from typing import Dict, List as ListType

_conversation_store: Dict[str, ListType[dict]] = defaultdict(list)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENGINE INSTANCES
# ASR and LLM loaded at startup (needed on every request).
# TTS and Translation loaded on first use (lazy loading to save RAM).
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

asr_engine: Optional[ASREngine] = None
llm_engine: Optional[LLMEngine] = None
tts_engine: Optional[TTSEngine] = None
translation_engine: Optional[TranslationEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global asr_engine, llm_engine, tts_engine, translation_engine

    print("\n" + "═" * 70)
    print("  CREDA Multilingual Service v2.0")
    print("  Initializing all engines...")
    print("═" * 70)
    logger.info("\n" + "=" * 60)
    logger.info("  CREDA Multilingual Service v2.0 — Starting up")
    logger.info("  Loading all engines (this may take 30-60 seconds)...")
    logger.info("=" * 60)

    t0 = time.time()

    try:
        print("  [1/4] Loading ASR (Speech Recognition)...")
        asr_engine = ASREngine()
        print(f"        ✓ {asr_engine.engine_type}")
        logger.info("  ✓ ASR loaded: %s", asr_engine.engine_type)

        print("  [2/4] Loading LLM (Financial Advisor)...")
        llm_engine = LLMEngine()
        print(f"        ✓ Groq ({llm_engine.primary_model})")
        logger.info("  ✓ LLM loaded: Groq (%s / %s)", llm_engine.primary_model, llm_engine.fallback_model)

        print("  [3/4] Loading TTS (Text-to-Speech)...")
        tts_engine = TTSEngine()
        print(f"        ✓ {tts_engine.engine_type}")
        logger.info("  ✓ TTS loaded: %s", tts_engine.engine_type)

        print("  [4/4] Loading Translation (IndicTrans2)...")
        translation_engine = TranslationEngine()
        status = "✓ Ready" if translation_engine.is_ready else "⚠ Fallback only"
        print(f"        {status}")
        logger.info("  ✓ Translation loaded: %s", "ready" if translation_engine.is_ready else "unavailable")

    except Exception as e:
        print(f"\n  ✗ STARTUP FAILED: {e}")
        logger.error("Startup failed: %s", e, exc_info=True)
        raise

    elapsed = time.time() - t0

    print("\n  Performing health checks...")
    health_status = {
        "ASR": asr_engine.is_ready if asr_engine else False,
        "LLM": llm_engine.is_ready if llm_engine else False,
        "TTS": tts_engine.is_ready if tts_engine else False,
        "Translation": translation_engine.is_ready if translation_engine else False,
    }

    all_ready = all(health_status.values())
    if all_ready:
        print("  ✓ All health checks passed")
    else:
        print("  ⚠️  Some engines degraded (fallbacks available)")

    print("\n" + "═" * 70)
    print(f"  ✅ SERVICE READY in {elapsed:.1f} seconds")
    print("  Listening on http://0.0.0.0:8000")
    print("  Documentation: http://0.0.0.0:8000/docs")
    print("  Endpoints: /health, /supported_languages, /process_voice, /process_text, /translate")
    print("═" * 70 + "\n")

    logger.info("=" * 60)
    logger.info("  ✅ All engines loaded in %.1fs", elapsed)
    logger.info("  Service ready")
    logger.info("=" * 60)

    yield

    logger.info("CREDA Multilingual Service — Shutting down")





app = FastAPI(
    title="CREDA Multilingual Service",
    description="Voice-first AI financial coaching in 22 Indian languages",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REQUEST / RESPONSE MODELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TextRequest(BaseModel):
    text: str
    language_code: str = "hi"
    user_profile: dict = {}


class TranslateRequest(BaseModel):
    text: str
    source_language: str
    target_language: str


class TTSRequest(BaseModel):
    text: str
    language_code: str = "hi"


def _safe_header(value: str, max_len: int = 500) -> str:
    """URL-encode a string so it is safe for HTTP headers (ASCII-only)."""
    return url_quote(value[:max_len], safe="")


# Helper: map old full language name → ISO code
_NAME_TO_CODE = {v.lower(): k for k, v in LANG_NAMES.items()}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINT 1 — POST /process_voice
# Main pipeline: Audio → ASR → LLM → TTS → Audio
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.post("/process_voice")
async def process_voice(
    file: UploadFile = File(None),
    audio: UploadFile = File(None),
    language_code: str = Form("hi"),
    language: str = Form(None),
    session_id: str = Form("default"),
    user_profile: str = Form("{}"),
):
    """
    Voice pipeline: audio bytes -> ASR -> LLM (native language) -> TTS -> WAV stream.

    Accepts the audio as either ``file`` or ``audio`` form field for backward
    compatibility with the API gateway.
    """
    start_time = time.time()

    # Accept either field name for backward compat with gateway
    upload = file or audio
    if upload is None:
        raise HTTPException(
            status_code=400,
            detail="No audio file provided (use 'file' or 'audio' form field)",
        )

    # Gateway may send `language` (old full-name) instead of `language_code` (new ISO)
    lang = language_code
    if language and language.lower() != "hindi":
        lang = _NAME_TO_CODE.get(language.lower(), language_code)

    # Parse user profile JSON
    try:
        profile = json.loads(user_profile) if isinstance(user_profile, str) else user_profile
    except (json.JSONDecodeError, TypeError):
        profile = {}

    if lang not in LANG_NAMES:
        raise HTTPException(status_code=400, detail=f"Unsupported language code: {lang}")

    # Step 1: ASR
    audio_bytes = await upload.read()
    transcript = asr_engine.transcribe(audio_bytes, lang)
    logger.info("ASR [%s]: %s", lang, transcript[:120])

    # Step 2: LLM — responds in native language directly, no translation
    response_text = llm_engine.get_financial_response(transcript, lang, profile, session_id)
    logger.info("LLM [%s]: %s", lang, response_text[:120])

    # Step 3: TTS
    audio_out = tts_engine.synthesize(response_text, lang)

    elapsed = time.time() - start_time
    logger.info("Voice pipeline done in %.2fs", elapsed)

    return StreamingResponse(
        io.BytesIO(audio_out),
        media_type="audio/wav",
        headers={
            "X-Transcript": _safe_header(transcript),
            "X-Response-Text": _safe_header(response_text),
            "X-Language": lang,
            "X-Processing-Time": f"{elapsed:.2f}s",
        },
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINT 2 — POST /process_text
# Text input → LLM → TTS → Audio
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.post("/process_text")
async def process_text(
    text: str = Form(...),
    language_code: str = Form("hi"),
    session_id: str = Form("default"),
    user_profile: str = Form("{}"),
):
    """For users who type instead of speak — returns voice audio reply."""
    start_time = time.time()

    lang = language_code
    if lang not in LANG_NAMES:
        raise HTTPException(status_code=400, detail=f"Unsupported language code: {lang}")

    # Parse user profile JSON
    try:
        profile = json.loads(user_profile) if isinstance(user_profile, str) else user_profile
    except (json.JSONDecodeError, TypeError):
        profile = {}

    response_text = llm_engine.get_financial_response(
        text, lang, profile, session_id
    )
    
    # TTS
    audio_out = tts_engine.synthesize(response_text, lang)

    elapsed = time.time() - start_time
    return StreamingResponse(
        io.BytesIO(audio_out),
        media_type="audio/wav",
        headers={
            "X-Response-Text": _safe_header(response_text),
            "X-Language": lang,
            "X-Processing-Time": f"{elapsed:.2f}s",
        },
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINT 3 — POST /translate
# Backend translation — NOT in main voice path
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.post("/translate")
async def translate(request: TranslateRequest):
    """
    Translate between English and Indian languages using IndicTrans2.
    Used when the finance backend (Port 8001) returns English text.
    """
    src = request.source_language
    tgt = request.target_language

    if src == tgt:
        return {"translated_text": request.text, "source": src, "target": tgt}

    if src == "en":
        translated = translation_engine.translate_from_english(request.text, tgt)
    elif tgt == "en":
        translated = translation_engine.translate_to_english(request.text, src)
    else:
        # Indic A → English → Indic B
        english = translation_engine.translate_to_english(request.text, src)
        translated = translation_engine.translate_from_english(english, tgt)

    return {"translated_text": translated, "source": src, "target": tgt}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINT 4 — POST /tts_only
# Generate audio for given text — used by finance backend
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.post("/tts_only")
async def tts_only(request: TTSRequest):
    """TTS-only endpoint — used by the finance backend to speak a response."""
    lang = request.language_code
    if lang not in LANG_NAMES:
        raise HTTPException(status_code=400, detail=f"Unsupported language code: {lang}")

    audio = tts_engine.synthesize(request.text, lang)
    return StreamingResponse(io.BytesIO(audio), media_type="audio/wav")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINT 5 — POST /transcribe_only
# Returns text transcript without LLM or TTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.post("/transcribe_only")
async def transcribe_only(
    file: UploadFile = File(...),
    language_code: str = Form("hi"),
):
    """ASR-only — returns a transcript for text-based query paths."""
    if language_code not in LANG_NAMES:
        raise HTTPException(status_code=400, detail=f"Unsupported language code: {language_code}")

    audio_bytes = await file.read()
    transcript = asr_engine.transcribe(audio_bytes, language_code)
    return {"transcript": transcript, "language": language_code}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINT 6 — GET /health
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/health")
async def health():
    """Status of all engines."""
    return {
        "status": "healthy",
        "engines": {
            "asr": {
                "ready": asr_engine.is_ready if asr_engine else False,
                "type": asr_engine.engine_type if asr_engine else "not loaded",
            },
            "llm": {
                "ready": llm_engine.is_ready if llm_engine else False,
                "provider": "Groq",
                "primary_model": llm_engine.primary_model if llm_engine else None,
                "fallback_model": llm_engine.fallback_model if llm_engine else None,
            },
            "tts": {
                "ready": tts_engine.is_ready if tts_engine else False,
                "type": tts_engine.engine_type if tts_engine else "not loaded",
            },
            "translation": {
                "ready": translation_engine.is_ready if translation_engine else False,
                "indic_to_en": (
                    translation_engine.indic_en_model is not None
                    if translation_engine
                    else False
                ),
                "en_to_indic": (
                    translation_engine.en_indic_model is not None
                    if translation_engine
                    else False
                ),
            },
        },
        "languages_supported": len(LANG_NAMES),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINT 7 — GET /supported_languages
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/supported_languages")
async def supported_languages():
    """Full list of supported languages — useful for the frontend dropdown."""
    languages = []
    for code, name in LANG_NAMES.items():
        languages.append(
            {
                "code": code,
                "name": name,
                "asr": True,  # IndicConformer covers all 22
                "tts": code in VOICE_DESCRIPTIONS,
                "translation": code in FLORES_CODES,
                "llm": True,  # Groq handles all via system prompt
            }
        )
    return {"languages": languages, "total": len(languages)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BACKWARD-COMPAT ENDPOINTS
# The API gateway (app.py) still routes to these old endpoint names.
# We provide thin wrappers so the gateway keeps working without changes.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/")
async def root():
    """Root info endpoint."""
    return {"message": "CREDA Multilingual Service v2.0", "status": "running"}


@app.post("/get_audio_response")
async def get_audio_response(request: TTSRequest):
    """Legacy endpoint — equivalent to /tts_only."""
    return await tts_only(request)


@app.post("/process_multilingual_query")
async def process_multilingual_query(request_data: dict):
    """
    Legacy endpoint used by the gateway for text-based multilingual queries.
    Maps to the new LLM-direct flow.
    """
    text = request_data.get("text", request_data.get("query", ""))
    language = request_data.get("language", "hi")

    lang_code = _NAME_TO_CODE.get(language.lower(), language)

    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    response_text = llm_engine.get_financial_response(text, lang_code, {})

    return {
        "success": True,
        "original_text": text,
        "detected_language": lang_code,
        "response": response_text,
    }


@app.post("/understand_intent")
async def understand_intent(request_data: dict):
    """
    Legacy intent-analysis endpoint. Now handled by LLM intent classification.
    Returns structured intent for backward compatibility with the gateway.
    """
    text = request_data.get("text", "")
    language = request_data.get("language", "en")
    lang_code = _NAME_TO_CODE.get(language.lower(), language)

    try:
        from groq import Groq

        client = Groq(api_key=GROQ_API_KEY)
        prompt = f"""Classify this financial query into exactly one intent.
Return ONLY a JSON object with no extra text:
{{"intent": "<one of: expense_logging, budget_query, portfolio_query, goal_setting, insurance_query, bill_payment, fraud_alert, general_query>", "entities": {{"amount": null, "category": null, "time_period": null}}, "confidence": 0.9}}

Query: "{text}"
"""
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        # Handle markdown-wrapped JSON
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception:
        return {
            "intent": "general_query",
            "entities": {"amount": None, "category": None, "time_period": None},
            "confidence": 0.5,
        }


@app.post("/test_asr")
async def test_asr():
    """Legacy ASR diagnostic endpoint."""
    return {
        "model_loaded": asr_engine.is_ready if asr_engine else False,
        "model_type": asr_engine.engine_type if asr_engine else "not loaded",
        "device": asr_engine.device if asr_engine else "unknown",
        "test_status": "ready" if (asr_engine and asr_engine.is_ready) else "unavailable",
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINT — POST /voice/command
# Push-to-talk: audio → ASR → Groq function-calling → structured intent
# Replaces ALL keyword/regex navigation maps in frontend.
# Returns JSON the client executes directly (navigate / action / answer).
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# All navigable screens — the LLM picks from this enum
_NAVIGATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "navigate_to_screen",
            "description": "Navigate the user to a specific screen in the CREDA app",
            "parameters": {
                "type": "object",
                "properties": {
                    "screen": {
                        "type": "string",
                        "enum": [
                            "dashboard", "portfolio", "budget", "advisory",
                            "goals", "expense_analytics", "financial_health",
                            "knowledge", "voice", "settings", "sip_calculator",
                            "fire_planner", "tax_wizard", "insurance", "bills",
                            "investments", "fraud_detection", "couples_planner",
                            "security", "help",
                        ],
                        "description": "The screen to navigate to",
                    }
                },
                "required": ["screen"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_financial_action",
            "description": "Execute a financial action such as calculating SIP, showing health score, or running a stress test",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "calculate_sip", "show_portfolio_xray", "run_stress_test",
                            "get_health_score", "compare_tax_regime", "show_budget_analysis",
                            "list_goals", "check_insurance_gap", "show_expense_breakdown",
                        ],
                    },
                    "params": {
                        "type": "object",
                        "description": "Optional parameters for the action",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "answer_financial_question",
            "description": "Answer a conversational financial question without navigating anywhere",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "language": {"type": "string"},
                },
                "required": ["question"],
            },
        },
    },
]

_INTENT_SYSTEM_PROMPT = """\
You are the voice controller for CREDA, an Indian personal-finance app.
The user spoke in {lang_name}. They are currently on the '{current_screen}' screen.

Interpret their voice command and call exactly ONE of the provided functions.
Commands can be in Hindi, Tamil, Telugu, Bengali, Hinglish, or any Indian language/English.

Examples:
- "mera portfolio dikhao" → navigate_to_screen(portfolio)
- "SIP calculator kholna hai" → navigate_to_screen(sip_calculator)
- "mera paisa kahan ja raha hai" → execute_financial_action(show_expense_breakdown)
- "retirement plan banao" → navigate_to_screen(fire_planner)
- "tax bachao" → execute_financial_action(compare_tax_regime)
- "health score batao" → execute_financial_action(get_health_score)
- "SIP kya hota hai" → answer_financial_question(...)
- "show my bills" → navigate_to_screen(bills)
- "budget dekhna hai" → navigate_to_screen(budget)
"""


async def _resolve_intent(transcript: str, language_code: str, current_screen: str) -> dict:
    """ASR transcript → structured intent via Groq function calling."""
    if not llm_engine or not llm_engine.is_ready:
        return {"type": "conversation", "response": transcript, "raw_transcript": transcript}

    lang_name = LANG_NAMES.get(language_code, "Hindi")
    system = _INTENT_SYSTEM_PROMPT.format(lang_name=lang_name, current_screen=current_screen)

    try:
        resp = llm_engine.client.chat.completions.create(
            model=llm_engine.primary_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": transcript},
            ],
            tools=_NAVIGATION_TOOLS,
            tool_choice="auto",
            max_tokens=200,
            temperature=0,
        )
        msg = resp.choices[0].message

        if msg.tool_calls:
            tc = msg.tool_calls[0]
            return {
                "type": "function_call",
                "function": tc.function.name,
                "args": json.loads(tc.function.arguments),
                "raw_transcript": transcript,
            }
        else:
            return {
                "type": "conversation",
                "response": msg.content or transcript,
                "raw_transcript": transcript,
            }
    except Exception as e:
        logger.warning("Intent resolution failed: %s", e)
        return {"type": "conversation", "response": transcript, "raw_transcript": transcript}


@app.post("/voice/command")
async def voice_command(
    audio: UploadFile = File(...),
    language_code: str = Form(default="en"),
    current_screen: str = Form(default="dashboard"),
    user_id: str = Form(default="anonymous"),
):
    """
    Push-to-talk voice command endpoint.

    Pipeline: audio → ASR → Groq function-calling → structured JSON intent.
    Replaces ALL NAVIGATION_MAP / keyword regex logic in the frontend.

    Response shape:
      {transcript, type: "function_call"|"conversation", function?, args?, response?}
    """
    start = time.time()

    if not asr_engine or not asr_engine.is_ready:
        raise HTTPException(status_code=503, detail="ASR engine not ready")

    lang = language_code
    if lang not in LANG_NAMES:
        lang = "en"

    audio_bytes = await audio.read()
    transcript = asr_engine.transcribe(audio_bytes, lang)
    logger.info("PTT ASR [%s] → %s", lang, transcript[:120])

    intent = await _resolve_intent(transcript, lang, current_screen)
    logger.info("PTT intent: %s in %.2fs", intent.get("type"), time.time() - start)

    return JSONResponse(content={"transcript": transcript, **intent})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINT — POST /pipecat/offer
# WebRTC signaling: browser SDP offer → bot SDP answer.
# Starts an isolated Pipecat real-time voice pipeline per connection.
# Requires: pip install "pipecat-ai[webrtc,silero]"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PipecatOfferRequest(BaseModel):
    sdp: str
    type: str = "offer"
    language_code: str = "en"
    user_id: str = "anonymous"
    current_screen: str = "dashboard"


@app.post("/pipecat/offer")
async def pipecat_offer(request: PipecatOfferRequest):
    """
    WebRTC signaling endpoint for the Pipecat real-time voice bot.

    Flow:
      1. Browser creates RTCPeerConnection + mic track + data channel.
      2. Browser POSTs SDP offer here.
      3. This endpoint creates a SmallWebRTCConnection, returns SDP answer.
      4. Pipecat pipeline runs in a background task for the lifetime of the call.
      5. Bot audio arrives via WebRTC audio track; navigation commands via data channel.
    """
    try:
        from pipecat_bot import create_connection_from_offer, run_pipecat_bot, PIPECAT_AVAILABLE
    except ImportError as exc:
        raise HTTPException(
            status_code=501,
            detail=f"Pipecat is not installed on this server: {exc}",
        )

    if not PIPECAT_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="pipecat-ai[webrtc,silero] is not installed. "
                   "Run: pip install 'pipecat-ai[webrtc,silero]'",
        )

    try:
        connection = await create_connection_from_offer(request.sdp, request.type)
    except Exception as exc:
        logger.error("Pipecat offer failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to initialise WebRTC connection: {exc}")

    answer = connection.get_answer()
    if not answer:
        raise HTTPException(status_code=500, detail="aiortc failed to produce SDP answer")

    # Launch bot pipeline as a fire-and-forget background task
    asyncio.create_task(
        run_pipecat_bot(
            connection=connection,
            language_code=request.language_code,
            user_id=request.user_id,
            current_screen=request.current_screen,
        ),
        name=f"pipecat-{answer['pc_id']}",
    )

    logger.info(
        "Pipecat session started  pc_id=%s  lang=%s  user=%s",
        answer["pc_id"],
        request.language_code,
        request.user_id,
    )

    return JSONResponse(content={
        "sdp": answer["sdp"],
        "type": answer["type"],
        "pc_id": answer["pc_id"],
    })


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "fastapi1_multilingual:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
