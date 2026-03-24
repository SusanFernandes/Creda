/**
 * useVoiceController — Push-to-talk voice command hook for CREDA website.
 *
 * Architecture
 * ════════════
 * 1. MediaRecorder captures raw PCM/webm audio from the mic.
 * 2. Web Audio API AnalyserNode monitors amplitude every 200 ms.
 * 3. When silence (RMS < threshold) persists for ≥ SILENCE_DURATION_MS,
 *    recording auto-stops — no button release required.
 * 4. Recorded blob is POSTed to /voice/command (Gateway → Multilingual).
 * 5. Backend returns structured intent via Groq function calling.
 * 6. Hook executes navigation or dispatches a custom event for the page.
 *
 * Replaces the entire NAVIGATION_MAP + regex logic in useReliableVoice.ts.
 */

import { useState, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useToast } from '@/hooks/use-toast';
import { useLanguage } from '@/contexts/LanguageContext';

// ── Route map (screen name returned by LLM → path) ───────────────────────────
// This is NOT a keyword map — the LLM decides which screen; this just maps it.
const SCREEN_ROUTES: Record<string, string> = {
  dashboard:        '/dashboard',
  portfolio:        '/portfolio',
  budget:           '/budget',
  advisory:         '/advisory',
  goals:            '/goals',
  expense_analytics:'/expense-analytics',
  financial_health: '/health',
  knowledge:        '/knowledge',
  voice:            '/voice',
  settings:         '/settings',
  security:         '/security',
  help:             '/help',
  sip_calculator:   '/sip-calculator',
  fire_planner:     '/fire-planner',
  tax_wizard:       '/tax-wizard',
  couples_planner:  '/couples-planner',
  // aliases
  insurance:        '/knowledge',
  bills:            '/budget',
  investments:      '/portfolio',
  fraud_detection:  '/security',
};

// ── Voice activity detection config ─────────────────────────────────────────
const VAD_CHECK_INTERVAL_MS = 200;   // how often we poll RMS
const SILENCE_THRESHOLD_RMS  = 0.01; // below this = silence
const SILENCE_DURATION_MS    = 1500; // silence for this long → auto-stop
const MAX_RECORDING_MS       = 10000; // hard ceiling

// ── Gateway URL ──────────────────────────────────────────────────────────────
const GATEWAY_URL = import.meta.env.VITE_API_GATEWAY_URL ?? 'http://localhost:8080';
const MULTILINGUAL_URL = import.meta.env.VITE_MULTILINGUAL_URL ?? 'http://localhost:8000';

export type VoiceStatus = 'idle' | 'listening' | 'processing' | 'speaking';

export interface VoiceCommandResult {
  transcript: string;
  type: 'function_call' | 'conversation';
  function?: string;
  args?: Record<string, any>;
  response?: string;
}

export function useVoiceController() {
  const [status, setStatus]           = useState<VoiceStatus>('idle');
  const [transcript, setTranscript]   = useState('');
  const [isListening, setIsListening] = useState(false);

  const navigate  = useNavigate();
  const location  = useLocation();
  const { toast } = useToast();
  const { currentLanguage } = useLanguage();

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef        = useRef<Blob[]>([]);
  const streamRef        = useRef<MediaStream | null>(null);
  const audioCtxRef      = useRef<AudioContext | null>(null);
  const analyserRef      = useRef<AnalyserNode | null>(null);
  const vadIntervalRef   = useRef<ReturnType<typeof setInterval> | null>(null);
  const maxTimeoutRef    = useRef<ReturnType<typeof setTimeout> | null>(null);
  const silenceCounterRef = useRef(0);

  // Map LanguageContext language names (lowercase) → ISO codes for the backend
  const getLangCode = useCallback((): string => {
    const map: Record<string, string> = {
      english: 'en', hindi: 'hi', tamil: 'ta', telugu: 'te',
      bengali: 'bn', marathi: 'mr', gujarati: 'gu', kannada: 'kn',
      malayalam: 'ml', punjabi: 'pa', urdu: 'ur',
    };
    return map[currentLanguage] ?? 'en';
  }, [currentLanguage]);

  const getCurrentScreen = useCallback((): string => {
    const path = location.pathname.replace(/^\//, '') || 'dashboard';
    // Normalise path to screen name
    return path.replace('-', '_');
  }, [location.pathname]);

  // ── VAD: monitor mic volume, auto-stop on silence ─────────────────────────
  // Fix: accesses refs directly inside the interval — no stale closure issue.
  const startVAD = useCallback(() => {
    if (!analyserRef.current) return;
    const analyser = analyserRef.current;
    const buf = new Uint8Array(analyser.fftSize);
    silenceCounterRef.current = 0;

    vadIntervalRef.current = setInterval(() => {
      analyser.getByteTimeDomainData(buf);
      let sum = 0;
      for (let i = 0; i < buf.length; i++) {
        const v = (buf[i] - 128) / 128;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / buf.length);

      if (rms < SILENCE_THRESHOLD_RMS) {
        silenceCounterRef.current += VAD_CHECK_INTERVAL_MS;
        if (silenceCounterRef.current >= SILENCE_DURATION_MS) {
          // Stop via refs directly — avoids stale useCallback closure
          if (vadIntervalRef.current) { clearInterval(vadIntervalRef.current); vadIntervalRef.current = null; }
          if (maxTimeoutRef.current)  { clearTimeout(maxTimeoutRef.current);   maxTimeoutRef.current  = null; }
          if (mediaRecorderRef.current?.state === 'recording') {
            mediaRecorderRef.current.stop(); // triggers onstop → processAudio
          }
          setIsListening(false);
        }
      } else {
        silenceCounterRef.current = 0; // voice detected — reset counter
      }
    }, VAD_CHECK_INTERVAL_MS);
  }, []); // empty deps OK — only uses refs

  const stopVAD = useCallback(() => {
    if (vadIntervalRef.current) { clearInterval(vadIntervalRef.current); vadIntervalRef.current = null; }
    if (maxTimeoutRef.current)  { clearTimeout(maxTimeoutRef.current);   maxTimeoutRef.current  = null; }
  }, []);

  // ── TTS: speak text via Indic Parler-TTS or browser fallback ─────────────
  const speakResponse = useCallback(async (text: string): Promise<void> => {
    setStatus('speaking');
    const langCode = getLangCode();

    try {
      const res = await fetch(`${MULTILINGUAL_URL}/tts_only`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, language_code: langCode }),
      });
      if (!res.ok) throw new Error('TTS failed');
      const audioBlob = await res.blob();
      const url = URL.createObjectURL(audioBlob);
      await new Promise<void>((resolve) => {
        const audio = new Audio(url);
        audio.onended = () => { URL.revokeObjectURL(url); resolve(); };
        audio.onerror = () => { URL.revokeObjectURL(url); resolve(); };
        audio.play().catch(() => resolve());
      });
    } catch {
      // Browser speech synthesis fallback
      if ('speechSynthesis' in window) {
        await new Promise<void>((resolve) => {
          const utt = new SpeechSynthesisUtterance(text);
          utt.lang = langCode === 'en' ? 'en-IN' : langCode;
          utt.rate = 0.95;
          utt.onend  = () => resolve();
          utt.onerror = () => resolve();
          window.speechSynthesis.speak(utt);
        });
      }
    } finally {
      setStatus('idle');
    }
  }, [getLangCode]);

  // ── Multilingual navigation confirmations ─────────────────────────────────
  // Templates are pre-baked per language — no round-trip LLM call needed.
  // TTS will render the native-language text in the correct voice.
  const CONFIRM_TEMPLATE: Record<string, (label: string) => string> = {
    en:  (l) => `Opening ${l}`,
    hi:  (l) => `${l} खोल रहा हूँ`,
    ta:  (l) => `${l} திறக்கிறேன்`,
    te:  (l) => `${l} తెరుస్తున్నాను`,
    bn:  (l) => `${l} খুলছি`,
    mr:  (l) => `${l} उघडत आहे`,
    gu:  (l) => `${l} ખોલી રહ્યો છું`,
    kn:  (l) => `${l} ತೆರೆಯುತ್ತಿದ್ದேನೆ`,
    ml:  (l) => `${l} തുറക്കുന്നു`,
    pa:  (l) => `${l} ਖੋਲ੍ਹ ਰਿਹਾ ਹਾਂ`,
    ur:  (l) => `${l} کھول رہا ہوں`,
  };

  const SCREEN_LABELS: Record<string, string> = {
    dashboard: 'Dashboard', portfolio: 'Portfolio', budget: 'Budget',
    advisory: 'Advisory', goals: 'Goals', expense_analytics: 'Expense Analytics',
    financial_health: 'Financial Health', knowledge: 'Knowledge',
    sip_calculator: 'SIP Calculator', fire_planner: 'FIRE Planner',
    tax_wizard: 'Tax Wizard', couples_planner: 'Couples Planner',
    settings: 'Settings', security: 'Security', help: 'Help',
    bills: 'Bills', investments: 'Investments',
  };

  const speakConfirmation = useCallback(async (screen: string): Promise<void> => {
    const label   = SCREEN_LABELS[screen] ?? screen.replace(/_/g, ' ');
    const langCode = getLangCode();
    const template = CONFIRM_TEMPLATE[langCode] ?? CONFIRM_TEMPLATE.en;
    await speakResponse(template(label));
  }, [getLangCode, speakResponse]);

  // ── Process and send audio to backend ────────────────────────────────────
  const processAudio = useCallback(async (blob: Blob) => {
    setStatus('processing');

    const formData = new FormData();
    formData.append('audio', blob, 'command.webm');
    formData.append('language_code', getLangCode());
    formData.append('current_screen', getCurrentScreen());
    formData.append('user_id', 'web_user');

    try {
      const res = await fetch(`${GATEWAY_URL}/voice/command`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status} — ${await res.text()}`);
      const result: VoiceCommandResult = await res.json();
      setTranscript(result.transcript ?? '');

      if (result.type === 'function_call') {
        if (result.function === 'navigate_to_screen') {
          const screen = result.args?.screen as string;
          const route  = SCREEN_ROUTES[screen];
          if (route) {
            await speakConfirmation(screen);
            if (location.pathname !== route) navigate(route);
          } else {
            // LLM returned a screen name we don't know — surface it gracefully
            toast({
              title: 'Navigation unavailable',
              description: `Screen "${screen}" is not available yet.`,
            });
          }
        } else if (result.function === 'execute_financial_action') {
          window.dispatchEvent(new CustomEvent('creda:voice-action', {
            detail: { action: result.args?.action, params: result.args?.params ?? {} },
          }));
          toast({
            title: '✅ Action triggered',
            description: (result.args?.action as string)?.replace(/_/g, ' '),
          });
        } else if (result.function === 'answer_financial_question') {
          // Conversational answer pre-filled by the LLM
          const text = result.response ?? result.args?.question ?? '';
          if (text) await speakResponse(text);
        }
      } else if (result.type === 'conversation') {
        // LLM chose to answer without function call — speak it
        if (result.response) await speakResponse(result.response);
      }
    } catch (err) {
      console.error('[PushToTalk] voice command failed:', err);
      toast({
        title: 'Voice command failed',
        description: 'Could not reach backend. Is the server running?',
        variant: 'destructive',
      });
    } finally {
      setStatus('idle');
    }
  }, [getLangCode, getCurrentScreen, navigate, location.pathname, toast, speakConfirmation, speakResponse]);

  // ── Public: start recording ───────────────────────────────────────────────
  const startListening = useCallback(async () => {
    if (status !== 'idle') return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Wire up Web Audio API for VAD
      const audioCtx  = new window.AudioContext();
      const source    = audioCtx.createMediaStreamSource(stream);
      const analyser  = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      audioCtxRef.current = audioCtx;
      analyserRef.current = analyser;

      // MediaRecorder
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';
      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        // Tear down audio pipeline — runs whether stopped by VAD OR button
        try { audioCtxRef.current?.close(); } catch {}
        streamRef.current?.getTracks().forEach((t) => t.stop());
        audioCtxRef.current = null;
        analyserRef.current = null;
        chunksRef.current   = [];
        processAudio(blob);
      };

      recorder.start(100); // collect a chunk every 100 ms for reliable blob assembly
      setIsListening(true);
      setStatus('listening');
      setTranscript('');

      startVAD();
      // Hard ceiling: stop after MAX_RECORDING_MS even without silence
      maxTimeoutRef.current = setTimeout(() => {
        stopVAD();
        if (mediaRecorderRef.current?.state === 'recording') mediaRecorderRef.current.stop();
        setIsListening(false);
      }, MAX_RECORDING_MS);
    } catch (err) {
      console.error('[PushToTalk] mic access failed:', err);
      toast({
        title: 'Microphone access denied',
        description: 'Allow microphone access in your browser to use voice commands.',
        variant: 'destructive',
      });
    }
  }, [status, processAudio, startVAD, stopVAD, toast]);

  // ── Public: manual stop (button press while listening) ───────────────────
  const stopListening = useCallback(() => {
    stopVAD();
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop(); // triggers onstop → cleanup → processAudio
    }
    setIsListening(false);
  }, [stopVAD]);

  return {
    status,
    isListening,
    transcript,
    startListening,
    stopListening,
    speakResponse,
  };
}
