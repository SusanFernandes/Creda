/**
 * useVoiceController — Push-to-talk voice command hook for CREDA Expo app.
 *
 * Architecture
 * ════════════
 * 1. expo-av Audio.Recording captures audio with metering enabled.
 * 2. Every 200 ms we poll getStatusAsync() for dB metering level.
 * 3. When level < SILENCE_DB_THRESHOLD for ≥ SILENCE_DURATION_MS,
 *    recording auto-stops — voice activity detection without extra libs.
 * 4. Recorded file is POSTed to /voice/command (Gateway → Multilingual).
 * 5. Groq function-calling returns structured intent JSON.
 * 6. Hook executes navigation (expo-router) or emits an event for the page.
 *
 * Replaces NAVIGATION_MAP + startSpeechToText in voiceagent.tsx.
 */

import { useState, useRef, useCallback } from 'react';
import { Alert } from 'react-native';
import { Audio } from 'expo-av';
import * as Speech from 'expo-speech';
import { router } from 'expo-router';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL ?? 'http://localhost:8001';

// ── Voice Activity Detection config ─────────────────────────────────────────
const SILENCE_DB_THRESHOLD  = -35;   // dB — below this = silence (typical background ≈ -60)
const SILENCE_DURATION_MS   = 1500;  // ms of consecutive silence before auto-stop
const VAD_POLL_INTERVAL_MS  = 200;   // how often to check metering
const MAX_RECORDING_MS      = 10000; // hard ceiling

// ── Route map (LLM screen name → Expo Router path) ──────────────────────────
// The LLM decides WHICH screen; this table just maps the name to a path.
const EXPO_ROUTES: Record<string, string> = {
  dashboard:        '/(protected)/(drawer)/(tabs)',
  home:             '/(protected)/(drawer)/(tabs)',
  portfolio:        '/(protected)/(drawer)/(tabs)/investments',
  investments:      '/(protected)/(drawer)/(tabs)/investments',
  expenses:         '/(protected)/(drawer)/(tabs)/expenses',
  expense_analytics:'/(protected)/(drawer)/(tabs)/expenses',
  bills:            '/(protected)/(drawer)/(tabs)/bills',
  budget:           '/(protected)/(drawer)/budgets',
  goals:            '/(protected)/(drawer)/goals',
  knowledge:        '/(protected)/(drawer)/knowledge',
  financial_health: '/(protected)/voiceagent',   // stays in agent for now
  advisory:         '/(protected)/voiceagent',
  voice:            '/(protected)/voiceagent',
  sip_calculator:   '/(protected)/voiceagent',
  fire_planner:     '/(protected)/voiceagent',
  tax_wizard:       '/(protected)/voiceagent',
  couples_planner:  '/(protected)/voiceagent',
  insurance:        '/(protected)/(drawer)/insurance',
  fraud_detection:  '/(protected)/(drawer)/fraud',
  security:         '/(protected)/(drawer)/fraud',
};

export type VoiceStatus = 'idle' | 'listening' | 'processing' | 'speaking';

export interface VoiceIntentResult {
  transcript: string;
  type: 'function_call' | 'conversation';
  function?: string;
  args?: Record<string, any>;
  response?: string;
}

/** Simple event emitter for cross-component voice actions. */
type VoiceActionListener = (action: string, params: Record<string, any>) => void;
const _listeners: VoiceActionListener[] = [];
export const voiceActionBus = {
  on: (fn: VoiceActionListener) => { _listeners.push(fn); },
  off: (fn: VoiceActionListener) => { const i = _listeners.indexOf(fn); if (i !== -1) _listeners.splice(i, 1); },
  emit: (action: string, params: Record<string, any>) => { _listeners.forEach((fn) => fn(action, params)); },
};

export function useVoiceController(
  userId = 'app_user',
  language = 'en',
  /** Optional: if provided, conversation answers are forwarded here instead of TTS */
  onConversationTranscript?: (transcript: string) => void,
) {
  const [status, setStatus]           = useState<VoiceStatus>('idle');
  const [transcript, setTranscript]   = useState('');
  const [isListening, setIsListening] = useState(false);

  const recordingRef      = useRef<Audio.Recording | null>(null);
  const vadIntervalRef    = useRef<ReturnType<typeof setInterval> | null>(null);
  const maxTimeoutRef     = useRef<ReturnType<typeof setTimeout> | null>(null);
  const silenceCounterRef = useRef(0);

  // ── VAD: poll metering, stop on sustained silence ────────────────────────
  // Fix: directly stops recordingRef inside interval — avoids stale useCallback closure.
  const startVAD = useCallback(() => {
    silenceCounterRef.current = 0;

    vadIntervalRef.current = setInterval(async () => {
      const rec = recordingRef.current;
      if (!rec) { stopVAD(); return; }

      try {
        const status = await rec.getStatusAsync();
        const db = status.metering ?? -160;

        if (db < SILENCE_DB_THRESHOLD) {
          silenceCounterRef.current += VAD_POLL_INTERVAL_MS;
          if (silenceCounterRef.current >= SILENCE_DURATION_MS) {
            // Stop via refs directly — avoids stale closure on stopAndProcess
            if (vadIntervalRef.current) { clearInterval(vadIntervalRef.current); vadIntervalRef.current = null; }
            if (maxTimeoutRef.current)  { clearTimeout(maxTimeoutRef.current);   maxTimeoutRef.current  = null; }
            try { await rec.stopAndUnloadAsync(); } catch { /* already stopped */ }
            recordingRef.current = null;
            setIsListening(false);
            const uri = rec.getURI();
            if (uri) { sendAudioToBackend(uri); } else { setStatus('idle'); }
          }
        } else {
          silenceCounterRef.current = 0;
        }
      } catch {
        // Recording may have already stopped — ignore
      }
    }, VAD_POLL_INTERVAL_MS);
  }, [sendAudioToBackend]);  // sendAudioToBackend is stable; added to deps for correctness

  const stopVAD = useCallback(() => {
    if (vadIntervalRef.current) { clearInterval(vadIntervalRef.current); vadIntervalRef.current = null; }
    if (maxTimeoutRef.current)  { clearTimeout(maxTimeoutRef.current);   maxTimeoutRef.current  = null; }
  }, []);

  // ── Send audio to backend and handle intent ───────────────────────────────
  const sendAudioToBackend = useCallback(async (uri: string) => {
    setStatus('processing');

    const formData = new FormData();
    // React Native FormData accepts {uri, type, name} for file uploads
    formData.append('audio', { uri, type: 'audio/m4a', name: 'command.m4a' } as any);
    formData.append('language_code', language);
    formData.append('current_screen', 'voiceagent');
    formData.append('user_id', userId);

    try {
      const res = await fetch(`${BACKEND_URL}/voice/pipeline`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const result: VoiceIntentResult = await res.json();
      setTranscript(result.transcript ?? '');

      if (result.type === 'function_call') {
        if (result.function === 'navigate_to_screen') {
          const screen = result.args?.screen as string;
          const route  = EXPO_ROUTES[screen];
          if (route) {
            const label = screen.replace(/_/g, ' ');
            // Multilingual confirmation template — TTS will render in native voice
            const CONFIRM: Record<string, (l: string) => string> = {
              en: (l) => `Opening ${l}`,
              hi: (l) => `${l} खोल रहा हूँ`,
              ta: (l) => `${l} திறக்கிறேன்`,
              te: (l) => `${l} తెరుస్తున్నాను`,
              bn: (l) => `${l} খুলছি`,
              mr: (l) => `${l} उघडत आहे`,
              gu: (l) => `${l} ખોলી રહ્યો છું`,
              kn: (l) => `${l} ತೆರೆಯುತ್ತಿದ್ದேನೆ`,
              ml: (l) => `${l} തുറക്കുന്നു`,
              pa: (l) => `${l} ਖੋਲ੍ਹ ਰਿਹਾ ਹਾਂ`,
              ur: (l) => `${l} کھول رہا ہوں`,
            };
            const confirmText = (CONFIRM[language] ?? CONFIRM.en)(label);
            Speech.speak(confirmText, { language: language === 'en' ? 'en-IN' : language, rate: 0.9 });
            setTimeout(() => router.push(route as any), 600);
          } else {
            // LLM returned an unmapped screen — surface gracefully
            Speech.speak(`Sorry, that screen is not available yet.`, { language: 'en-IN' });
          }
          return result;
        } else if (result.function === 'execute_financial_action') {
          const action = result.args?.action as string ?? '';
          const params = result.args?.params ?? {};
          voiceActionBus.emit(action, params);
          return result;
        } else if (result.function === 'answer_financial_question') {
          const text = result.args?.question ?? result.transcript ?? '';
          if (onConversationTranscript) {
            onConversationTranscript(result.transcript ?? text);
          } else if (text) {
            await speakResponse(text);
          }
          return result;
        }
      } else if (result.type === 'conversation') {
        // Conversational answer — either forward to parent or speak directly
        if (onConversationTranscript) {
          onConversationTranscript(result.transcript ?? '');
        } else if (result.response) {
          await speakResponse(result.response);
        }
      }

      return result;
    } catch (err) {
      console.error('[AppVoice] voice command failed:', err);
      Speech.speak('Sorry, could not reach server. Check your connection.', { language: 'en-IN' });
      return null;
    } finally {
      setStatus('idle');
    }
  }, [language, userId, onConversationTranscript]);

  // ── TTS: speak via CREDA Parler-TTS or fallback to expo-speech ───────────
  const speakResponse = useCallback(async (text: string): Promise<void> => {
    setStatus('speaking');
    // Try CREDA TTS (better Indian voices)
    try {
      const res = await fetch(`${BACKEND_URL}/voice/speak`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, language_code: language }),
      });
      if (!res.ok) throw new Error('TTS failed');
      // expo can play a URL directly — download blob and play via Expo AV
      const blob = await res.blob();
      const { sound } = await Audio.Sound.createAsync({ uri: URL.createObjectURL(blob) });
      await new Promise<void>((resolve) => {
        sound.setOnPlaybackStatusUpdate((s) => {
          if (s.isLoaded && s.didJustFinish) { sound.unloadAsync(); resolve(); }
        });
        sound.playAsync().catch(() => resolve());
      });
    } catch {
      // Fallback to expo-speech (always available)
      await new Promise<void>((resolve) => {
        Speech.speak(text, {
          language: language === 'en' ? 'en-IN' : language,
          rate: 0.88,
          onDone: resolve,
          onError: () => resolve(),
        });
      });
    } finally {
      setStatus('idle');
    }
  }, [language]);

  // ── Public: stop + process recording ─────────────────────────────────────
  const stopAndProcess = useCallback(async () => {
    stopVAD();
    const rec = recordingRef.current;
    if (!rec) return;

    try {
      await rec.stopAndUnloadAsync();
    } catch { /* already stopped */ }

    const uri = rec.getURI();
    recordingRef.current = null;
    setIsListening(false);

    if (uri) {
      await sendAudioToBackend(uri);
    } else {
      setStatus('idle');
    }
  }, [stopVAD, sendAudioToBackend]);

  // ── Public: start recording ───────────────────────────────────────────────
  const startListening = useCallback(async () => {
    if (status !== 'idle') return;

    const { granted } = await Audio.requestPermissionsAsync();
    if (!granted) {
      Alert.alert('Microphone access denied', 'Allow mic access in settings to use voice commands.');
      return;
    }

    await Audio.setAudioModeAsync({
      allowsRecordingIOS: true,
      playsInSilentModeIOS: true,
    });

    try {
      const { recording } = await Audio.Recording.createAsync({
        // Custom options to enable metering
        android: {
          extension: '.m4a',
          outputFormat: Audio.AndroidOutputFormat.MPEG_4,
          audioEncoder: Audio.AndroidAudioEncoder.AAC,
          sampleRate: 16000,
          numberOfChannels: 1,
          bitRate: 64000,
        },
        ios: {
          extension: '.m4a',
          outputFormat: Audio.IOSOutputFormat.MPEG4AAC,
          audioQuality: Audio.IOSAudioQuality.MEDIUM,
          sampleRate: 16000,
          numberOfChannels: 1,
          bitRate: 64000,
          linearPCMBitDepth: 16,
          linearPCMIsBigEndian: false,
          linearPCMIsFloat: false,
        },
        web: {
          mimeType: 'audio/webm',
          bitsPerSecond: 64000,
        },
        isMeteringEnabled: true,
      });

      recordingRef.current = recording;
      setIsListening(true);
      setStatus('listening');
      setTranscript('');

      startVAD();
      maxTimeoutRef.current = setTimeout(() => stopAndProcess(), MAX_RECORDING_MS);
    } catch (err) {
      console.error('[AppVoice] recording start failed:', err);
      Alert.alert('Recording error', 'Could not start recording. Please try again.');
      setStatus('idle');
    }
  }, [status, startVAD, stopAndProcess]);

  // ── Public: manual stop ───────────────────────────────────────────────────
  const stopListening = useCallback(async () => {
    await stopAndProcess();
  }, [stopAndProcess]);

  return {
    status,
    isListening,
    transcript,
    startListening,
    stopListening,
    speakResponse,
  };
}
