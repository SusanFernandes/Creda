# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CREDA Pipecat Bot — Real-Time Streaming Voice Pipeline
#
# Architecture:
#   Browser WebRTC audio in
#     → SmallWebRTCTransport + SileroVAD
#     → IndicConformerSTTService (buffers segment, batch-transcribes)
#     → CREDAIntentProcessor (Groq function-calling, nav commands)
#     → ParlerTTSService (Parler-TTS / gTTS fallback)
#     → SmallWebRTCTransport audio out
#
# Each WebRTC peer connection runs its own isolated pipeline.
# Navigation commands are sent back to the browser via the WebRTC
# data channel as JSON messages.
#
# Install:  pip install "pipecat-ai[webrtc,silero]"
#           apt install ffmpeg libavcodec-extra   (or via Dockerfile)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from __future__ import annotations

import asyncio
import io
import wave
from typing import AsyncGenerator, Dict, Optional

from loguru import logger

# ── Pipecat ──────────────────────────────────────────────────────────────────
try:
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.frames.frames import (
        EndFrame,
        Frame,
        OutputTransportMessageFrame,
        TranscriptionFrame,
        TTSAudioRawFrame,
        TTSSpeakFrame,
        TTSStartedFrame,
        TTSStoppedFrame,
    )
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineTask
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
    from pipecat.services.stt_service import SegmentedSTTService
    from pipecat.services.tts_service import TTSService
    from pipecat.transports.base_transport import TransportParams
    from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
    from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

    PIPECAT_AVAILABLE = True
except ImportError as _pipecat_err:
    PIPECAT_AVAILABLE = False
    logger.warning(
        "pipecat-ai[webrtc,silero] not installed — real-time voice disabled. "
        "Install with: pip install 'pipecat-ai[webrtc,silero]'  (%s)",
        _pipecat_err,
    )

# ── Active sessions ───────────────────────────────────────────────────────────
_sessions: Dict[str, "PipelineTask"] = {}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Screen label map (LLM canonical name → display label)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_SCREEN_LABELS: Dict[str, str] = {
    "dashboard": "Dashboard",
    "portfolio": "Portfolio",
    "budget": "Budget",
    "advisory": "AI Advisory",
    "goals": "Goals",
    "expense_analytics": "Expense Analytics",
    "financial_health": "Financial Health",
    "knowledge": "Knowledge Base",
    "voice": "Voice Assistant",
    "settings": "Settings",
    "sip_calculator": "SIP Calculator",
    "fire_planner": "Retirement Planner",
    "tax_wizard": "Tax Wizard",
    "insurance": "Insurance",
    "bills": "Bills",
    "investments": "Investments",
    "fraud_detection": "Fraud Detection",
    "couples_planner": "Couples Planner",
    "security": "Security",
    "help": "Help",
}

# Multilingual spoken confirmations — 11 languages (same set as PTT hooks)
_CONFIRM: Dict[str, callable] = {
    "en": lambda s: f"Opening {s}",
    "hi": lambda s: f"{s} खोल रहा हूँ",
    "ta": lambda s: f"{s} திறக்கிறேன்",
    "te": lambda s: f"{s} తెరుస్తున్నాను",
    "bn": lambda s: f"{s} খুলছি",
    "mr": lambda s: f"{s} उघडत आहे",
    "gu": lambda s: f"{s} ખોલી રહ્યો છું",
    "kn": lambda s: f"{s} ತೆರೆಯುತ್ತಿದ್ದೇನೆ",
    "ml": lambda s: f"{s} തുറക്കുന്നു",
    "pa": lambda s: f"{s} ਖੋਲ੍ਹ ਰਿਹਾ ਹਾਂ",
    "ur": lambda s: f"{s} کھول رہا ہوں",
}

_GREETINGS: Dict[str, str] = {
    "en": "Hello! I'm CREDA, your AI financial coach. How can I help you today?",
    "hi": "नमस्ते! मैं CREDA हूँ, आपका AI वित्तीय सहायक। आज मैं आपकी कैसे मदद कर सकता हूँ?",
    "ta": "வணக்கம்! நான் CREDA, உங்கள் AI நிதி ஆலோசகர். இன்று எப்படி உதவலாம்?",
    "te": "నమస్కారం! నేను CREDA, మీ AI ఆర్థిక సహాయకుడు. ఈరోజు ఎలా సహాయం చేయగలను?",
    "bn": "নমস্কার! আমি CREDA, আপনার AI আর্থিক পরামর্শদাতা। আজ কীভাবে সাহায্য করতে পারি?",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STT Service — IndicConformer wrapper
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if PIPECAT_AVAILABLE:

    class IndicConformerSTTService(SegmentedSTTService):
        """Pipecat STT service backed by the CREDA IndicConformer ASR engine.

        ``SegmentedSTTService`` handles the VAD-aware audio buffering:
        - it accumulates raw PCM while the user is speaking,
        - constructs a complete WAV segment when VAD stop fires,
        - calls ``run_stt(wav_bytes)`` exactly once per utterance.
        """

        def __init__(self, language_code: str = "en", **kwargs):
            super().__init__(**kwargs)
            self._language_code = language_code

        async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame, None]:  # type: ignore[override]
            from fastapi1_multilingual import asr_engine  # imported here to avoid circular

            if asr_engine is None or not asr_engine.is_ready:
                logger.warning("Pipecat STT: ASR engine not ready — skipping utterance")
                return

            loop = asyncio.get_event_loop()
            try:
                transcript: str = await loop.run_in_executor(
                    None, asr_engine.transcribe, audio, self._language_code
                )
                transcript = (transcript or "").strip()
                logger.info("Pipecat STT [%s]: %r", self._language_code, transcript[:120])
                if transcript:
                    yield TranscriptionFrame(text=transcript, user_id="", timestamp=0)
            except Exception as exc:
                logger.error("Pipecat STT error: %s", exc)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TTS Service — Parler-TTS wrapper
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    class ParlerTTSService(TTSService):
        """Pipecat TTS service backed by the CREDA Parler-TTS / gTTS engine.

        ``run_tts`` receives aggregated sentence text, synthesises WAV bytes
        with the engine (blocking, run in executor), resamples to 16 kHz mono,
        and yields 20 ms ``TTSAudioRawFrame`` chunks.
        """

        _OUT_SAMPLE_RATE = 16000

        def __init__(self, language_code: str = "en", **kwargs):
            super().__init__(
                sample_rate=self._OUT_SAMPLE_RATE,
                push_stop_frames=True,
                push_start_frame=True,
                **kwargs,
            )
            self._language_code = language_code

        async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame, None]:  # type: ignore[override]
            from fastapi1_multilingual import tts_engine

            if tts_engine is None:
                logger.warning("Pipecat TTS: engine not loaded")
                return

            import numpy as np

            loop = asyncio.get_event_loop()
            try:
                wav_bytes: bytes = await loop.run_in_executor(
                    None, tts_engine.synthesize, text, self._language_code
                )
            except Exception as exc:
                logger.error("Pipecat TTS synthesis error: %s", exc)
                return

            # ── Parse WAV ────────────────────────────────────────────────────
            try:
                with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                    src_rate = wf.getframerate()
                    n_channels = wf.getnchannels()
                    n_frames = wf.getnframes()
                    raw_pcm = wf.readframes(n_frames)
            except Exception:
                # gTTS returns MP3, not WAV — handle gracefully
                try:
                    from pydub import AudioSegment

                    seg = AudioSegment.from_file(io.BytesIO(wav_bytes))
                    seg = seg.set_channels(1).set_frame_rate(self._OUT_SAMPLE_RATE).set_sample_width(2)
                    raw_pcm = seg.raw_data
                    src_rate = self._OUT_SAMPLE_RATE
                    n_channels = 1
                except Exception as exc2:
                    logger.error("Pipecat TTS: cannot decode audio: %s", exc2)
                    return

            # ── float32 conversion ───────────────────────────────────────────
            samples = np.frombuffer(raw_pcm, dtype=np.int16).astype(np.float32) / 32768.0
            if n_channels == 2:
                samples = samples.reshape(-1, 2).mean(axis=1)

            # ── Resample to 16 kHz if needed ─────────────────────────────────
            if src_rate != self._OUT_SAMPLE_RATE:
                try:
                    import torch
                    import torchaudio

                    t = torch.from_numpy(samples).unsqueeze(0)
                    t = torchaudio.transforms.Resample(src_rate, self._OUT_SAMPLE_RATE)(t)
                    samples = t.squeeze(0).numpy()
                except Exception:
                    from scipy import signal as _sig

                    num = int(round(len(samples) * self._OUT_SAMPLE_RATE / float(src_rate)))
                    samples = _sig.resample(samples.astype(np.float64), num).astype(np.float32)

            # ── Yield in 20 ms chunks (320 samples × 2 bytes at 16 kHz) ─────
            pcm_out: bytes = (samples * 32767).astype(np.int16).tobytes()
            CHUNK = 320 * 2  # 20 ms at 16 kHz, mono, 16-bit

            for i in range(0, len(pcm_out), CHUNK):
                chunk = pcm_out[i : i + CHUNK]
                if not chunk:
                    continue
                # Pad last chunk to full 20 ms if necessary
                if len(chunk) < CHUNK:
                    chunk = chunk + b"\x00" * (CHUNK - len(chunk))
                yield TTSAudioRawFrame(
                    audio=chunk,
                    sample_rate=self._OUT_SAMPLE_RATE,
                    num_channels=1,
                    context_id=context_id,
                )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Intent Processor — TranscriptionFrame → spoken reply + data-channel cmd
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    class CREDAIntentProcessor(FrameProcessor):
        """Converts transcriptions into CREDA actions.

        Calls ``_resolve_intent()`` from ``fastapi1_multilingual`` (Groq
        function-calling) and either:
          - speaks a confirmation + sends a WebRTC data-channel navigation cmd, or
          - generates a conversational LLM response and speaks it.
        """

        def __init__(
            self,
            language_code: str = "en",
            current_screen: str = "dashboard",
            **kwargs,
        ):
            super().__init__(**kwargs)
            self._language_code = language_code
            self._current_screen = current_screen

        async def process_frame(self, frame: Frame, direction: FrameDirection):
            await super().process_frame(frame, direction)

            if not isinstance(frame, TranscriptionFrame):
                await self.push_frame(frame, direction)
                return

            transcript = frame.text
            logger.info("Pipecat intent: %r", transcript[:80])

            # ── Resolve intent via Groq function-calling ─────────────────────
            try:
                from fastapi1_multilingual import _resolve_intent

                intent = await _resolve_intent(
                    transcript, self._language_code, self._current_screen
                )
            except Exception as exc:
                logger.error("Intent resolution error: %s", exc)
                await self.push_frame(
                    TTSSpeakFrame("Sorry, I had trouble understanding that. Please try again.")
                )
                return

            intent_type = intent.get("type")
            fn = intent.get("function", "")
            args = intent.get("args", {})

            # ── navigate_to_screen ───────────────────────────────────────────
            if intent_type == "function_call" and fn == "navigate_to_screen":
                screen = args.get("screen", "dashboard")
                label = _SCREEN_LABELS.get(screen, screen.replace("_", " ").title())
                confirm_fn = _CONFIRM.get(self._language_code, _CONFIRM["en"])
                await self.push_frame(TTSSpeakFrame(confirm_fn(label)))
                await self.push_frame(
                    OutputTransportMessageFrame(
                        message={
                            "type": "creda_navigate",
                            "screen": screen,
                            "transcript": transcript,
                        }
                    )
                )
                self._current_screen = screen

            # ── execute_financial_action ─────────────────────────────────────
            elif intent_type == "function_call" and fn == "execute_financial_action":
                action = args.get("action", "")
                readable = action.replace("_", " ")
                await self.push_frame(TTSSpeakFrame(f"Running {readable}…"))
                await self.push_frame(
                    OutputTransportMessageFrame(
                        message={
                            "type": "creda_action",
                            "action": action,
                            "params": args.get("params", {}),
                            "transcript": transcript,
                        }
                    )
                )

            # ── answer_financial_question / conversation ─────────────────────
            else:
                response: str = intent.get("response", "")
                if not response:
                    # Fall back to the conversational LLM
                    try:
                        from fastapi1_multilingual import llm_engine

                        if llm_engine and llm_engine.is_ready:
                            loop = asyncio.get_event_loop()
                            response = await loop.run_in_executor(
                                None,
                                llm_engine.get_financial_response,
                                transcript,
                                self._language_code,
                                {},
                                "pipecat_session",
                            )
                    except Exception as exc:
                        logger.error("LLM fallback error: %s", exc)
                        response = "Sorry, I couldn't generate a response right now."

                if response:
                    await self.push_frame(TTSSpeakFrame(response))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Pipeline runner — one per WebRTC connection
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def run_pipecat_bot(
        connection: SmallWebRTCConnection,
        language_code: str = "en",
        user_id: str = "anonymous",
        current_screen: str = "dashboard",
    ) -> None:
        """Run a complete real-time voice pipeline for one WebRTC peer."""

        transport = SmallWebRTCTransport(
            webrtc_connection=connection,
            params=TransportParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                audio_in_sample_rate=16000,
                audio_out_sample_rate=16000,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
                vad_audio_passthrough=True,
            ),
        )

        stt = IndicConformerSTTService(language_code=language_code)
        intent_proc = CREDAIntentProcessor(
            language_code=language_code,
            current_screen=current_screen,
        )
        tts = ParlerTTSService(language_code=language_code)

        pipeline = Pipeline(
            [
                transport.input(),
                stt,
                intent_proc,
                tts,
                transport.output(),
            ]
        )

        task = PipelineTask(pipeline)
        pc_id = connection.pc_id
        _sessions[pc_id] = task

        greeting = _GREETINGS.get(language_code, _GREETINGS["en"])

        @transport.event_handler("on_client_connected")
        async def on_connected(transport, conn):
            await task.queue_frames([TTSSpeakFrame(greeting)])

        @transport.event_handler("on_client_disconnected")
        async def on_disconnected(transport, conn):
            logger.info("Pipecat: client disconnected %s", pc_id)
            _sessions.pop(pc_id, None)
            await task.queue_frames([EndFrame()])

        runner = PipelineRunner(handle_sigint=False)
        try:
            await runner.run(task)
        finally:
            _sessions.pop(pc_id, None)
            logger.info("Pipecat: pipeline ended for %s", pc_id)

else:
    # Stub when pipecat is not installed — used by tests / import-time checks

    async def run_pipecat_bot(connection, language_code="en", user_id="anonymous", current_screen="dashboard"):  # type: ignore[misc]
        raise RuntimeError("pipecat-ai[webrtc,silero] is not installed")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Signaling helper — used by FastAPI endpoint
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def create_connection_from_offer(sdp: str, sdp_type: str) -> "SmallWebRTCConnection":
    """Initialise an aiortc peer connection from the browser's SDP offer.

    Waits up to 10 s for ICE gathering to complete before returning so the
    full SDP answer (with ICE candidates) can be sent back to the browser.
    """
    if not PIPECAT_AVAILABLE:
        raise RuntimeError("pipecat-ai[webrtc,silero] is not installed")

    connection = SmallWebRTCConnection()
    await connection.initialize(sdp=sdp, type=sdp_type)

    # aiortc gathers ICE candidates asynchronously — wait for completion
    timeout = 10.0
    elapsed = 0.0
    while connection.pc.iceGatheringState != "complete" and elapsed < timeout:
        await asyncio.sleep(0.1)
        elapsed += 0.1

    if connection.pc.iceGatheringState != "complete":
        logger.warning("ICE gathering did not complete within %.1fs", timeout)

    return connection
