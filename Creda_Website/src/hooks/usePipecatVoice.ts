/**
 * usePipecatVoice — Real-time WebRTC voice hook for CREDA website.
 *
 * Architecture
 * ════════════
 * 1. Browser creates RTCPeerConnection + microphone audio track.
 * 2. SDP offer is POSTed to /pipecat/offer (Gateway → Multilingual service).
 * 3. Backend starts a real-time Pipecat pipeline:
 *    Mic audio → SileroVAD → IndicConformer STT → Groq intent → Parler-TTS
 * 4. Bot audio arrives back over the WebRTC audio track.
 * 5. Navigation commands arrive over the WebRTC data channel as JSON.
 *
 * This is NOT push-to-talk — conversation is always open once connected.
 * The PTT hook (useVoiceController) remains the fallback when unavailable.
 *
 * Data-channel message shapes from the bot:
 *   { type: "creda_navigate", screen: string, transcript: string }
 *   { type: "creda_action",   action: string, params: {}, transcript: string }
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useToast } from '@/hooks/use-toast';

// ── Route map ─────────────────────────────────────────────────────────────────
// Matches the mapping in useVoiceController.ts — keep them in sync.
const SCREEN_ROUTES: Record<string, string> = {
  dashboard:         '/dashboard',
  portfolio:         '/portfolio',
  budget:            '/budget',
  advisory:          '/advisory',
  goals:             '/goals',
  expense_analytics: '/expense-analytics',
  financial_health:  '/health',
  knowledge:         '/knowledge',
  voice:             '/voice',
  settings:          '/settings',
  security:          '/security',
  help:              '/help',
  sip_calculator:    '/sip-calculator',
  fire_planner:      '/fire-planner',
  tax_wizard:        '/tax-wizard',
  couples_planner:   '/couples-planner',
  insurance:         '/knowledge',
  bills:             '/budget',
  investments:       '/portfolio',
  fraud_detection:   '/security',
};

// ── Config ───────────────────────────────────────────────────────────────────
const GATEWAY_URL =
  import.meta.env.VITE_API_GATEWAY_URL ?? 'http://localhost:8080';

// ICE servers — add TURN credentials here for production deployment.
// For local (same-machine) testing, an empty array works.
const ICE_SERVERS: RTCIceServer[] = [
  { urls: 'stun:stun.l.google.com:19302' },
  { urls: 'stun:stun1.l.google.com:19302' },
];

// ── Types ────────────────────────────────────────────────────────────────────
export type PipecatStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'bot-speaking'
  | 'error';

export interface UsePipecatVoiceOptions {
  /** IETF language tag / CREDA language code, e.g. "en", "hi", "ta" */
  languageCode?: string;
  /** Initial screen name so the bot knows context */
  initialScreen?: string;
  /** Called when the bot sends a creda_navigate message */
  onNavigate?: (screen: string, transcript: string) => void;
  /** Called when the bot sends a creda_action message */
  onAction?: (
    action: string,
    params: Record<string, unknown>,
    transcript: string,
  ) => void;
}

export interface UsePipecatVoiceReturn {
  status: PipecatStatus;
  isBotSpeaking: boolean;
  connect: () => Promise<void>;
  disconnect: () => void;
  /** Tell the bot which screen the user is currently on */
  updateScreen: (screen: string) => void;
  /** Whether the browser / server supports real-time mode */
  isSupported: boolean;
}

// ── Hook ──────────────────────────────────────────────────────────────────────
export function usePipecatVoice({
  languageCode = 'en',
  initialScreen,
  onNavigate,
  onAction,
}: UsePipecatVoiceOptions = {}): UsePipecatVoiceReturn {
  const navigate   = useNavigate();
  const location   = useLocation();
  const { toast }  = useToast();

  const [status, setStatus]           = useState<PipecatStatus>('disconnected');
  const [isBotSpeaking, setIsBotSpeaking] = useState(false);

  // Current screen synced from router location
  const currentScreenRef = useRef<string>(
    initialScreen ?? (location.pathname.replace(/^\//, '') || 'dashboard'),
  );

  // WebRTC refs
  const pcRef      = useRef<RTCPeerConnection | null>(null);
  const dcRef      = useRef<RTCDataChannel | null>(null);
  const audioElRef = useRef<HTMLAudioElement | null>(null);
  const streamRef  = useRef<MediaStream | null>(null);

  // Keep route screen in sync
  useEffect(() => {
    const slug = location.pathname.replace(/^\//, '') || 'dashboard';
    currentScreenRef.current = slug;
  }, [location.pathname]);

  // ── Cleanup helper ──────────────────────────────────────────────────────────
  const cleanup = useCallback(() => {
    if (dcRef.current) {
      dcRef.current.close();
      dcRef.current = null;
    }
    if (pcRef.current) {
      pcRef.current.close();
      pcRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (audioElRef.current) {
      audioElRef.current.srcObject = null;
    }
    setStatus('disconnected');
    setIsBotSpeaking(false);
  }, []);

  // ── Data-channel message handler ───────────────────────────────────────────
  const handleDataChannelMessage = useCallback(
    (event: MessageEvent) => {
      let msg: Record<string, unknown>;
      try {
        msg = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
      } catch {
        return;
      }

      const msgType = msg.type as string;

      if (msgType === 'creda_navigate') {
        const screen     = msg.screen as string;
        const transcript = (msg.transcript as string) ?? '';
        const path       = SCREEN_ROUTES[screen];

        if (path) {
          navigate(path);
          onNavigate?.(screen, transcript);
          toast({
            title: 'CREDA',
            description: `Navigated to ${screen.replace(/_/g, ' ')}`,
            duration: 2000,
          });
        }
        return;
      }

      if (msgType === 'creda_action') {
        const action     = msg.action as string;
        const params     = (msg.params as Record<string, unknown>) ?? {};
        const transcript = (msg.transcript as string) ?? '';
        onAction?.(action, params, transcript);
        return;
      }
    },
    [navigate, onNavigate, onAction, toast],
  );

  // ── Connect ────────────────────────────────────────────────────────────────
  const connect = useCallback(async () => {
    if (status !== 'disconnected' && status !== 'error') return;

    setStatus('connecting');
    cleanup();

    // 1. Get microphone
    let micStream: MediaStream;
    try {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    } catch (err) {
      console.error('[Pipecat] Microphone access denied:', err);
      toast({ title: 'Microphone blocked', description: 'Please allow microphone access.', variant: 'destructive' });
      setStatus('error');
      return;
    }
    streamRef.current = micStream;

    // 2. Create peer connection
    const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
    pcRef.current = pc;

    // 3. Add microphone track so the server can receive audio
    micStream.getAudioTracks().forEach((track) => pc.addTrack(track, micStream));

    // 4. Create data channel — server will "see" it via aiortc `ondatachannel`
    const dc = pc.createDataChannel('creda', { ordered: true });
    dcRef.current = dc;

    dc.onopen    = () => console.debug('[Pipecat] Data channel open');
    dc.onmessage = handleDataChannelMessage;
    dc.onclose   = () => console.debug('[Pipecat] Data channel closed');

    // 5. Receive bot audio via ontrack
    pc.ontrack = (event) => {
      const [remoteStream] = event.streams;
      if (!audioElRef.current) {
        const audio       = new Audio();
        audio.autoplay    = true;
        audioElRef.current = audio;
      }
      audioElRef.current.srcObject = remoteStream;
    };

    // 6. Track ICE + connection state changes
    pc.oniceconnectionstatechange = () => {
      const s = pc.iceConnectionState;
      console.debug('[Pipecat] ICE:', s);
      if (s === 'connected' || s === 'completed') {
        setStatus('connected');
      } else if (s === 'failed' || s === 'closed') {
        cleanup();
        setStatus('error');
      }
    };

    pc.onconnectionstatechange = () => {
      if (pc.connectionState === 'failed' || pc.connectionState === 'closed') {
        cleanup();
      }
    };

    // 7. Create SDP offer
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    // 8. POST offer to backend — backend returns full SDP answer (ICE included)
    let answerData: { sdp: string; type: RTCSdpType; pc_id: string };
    try {
      const resp = await fetch(`${GATEWAY_URL}/pipecat/offer`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sdp:            offer.sdp,
          type:           offer.type,
          language_code:  languageCode,
          user_id:        'web_user',
          current_screen: currentScreenRef.current,
        }),
      });

      if (!resp.ok) {
        const detail = await resp.text();
        throw new Error(`${resp.status}: ${detail}`);
      }
      answerData = await resp.json();
    } catch (err) {
      console.error('[Pipecat] Offer exchange failed:', err);
      toast({
        title: 'Real-time voice unavailable',
        description: 'Falling back to push-to-talk mode.',
        duration: 3000,
      });
      cleanup();
      setStatus('error');
      return;
    }

    // 9. Set remote description (SDP answer from aiortc)
    await pc.setRemoteDescription({
      sdp:  answerData.sdp,
      type: answerData.type,
    });

    console.info('[Pipecat] Session started  pc_id=%s', answerData.pc_id);
    // status will update to 'connected' once ICE completes
  }, [status, languageCode, cleanup, handleDataChannelMessage, toast]);

  // ── Disconnect ─────────────────────────────────────────────────────────────
  const disconnect = useCallback(() => {
    cleanup();
  }, [cleanup]);

  // ── updateScreen — inform the running session of current screen ────────────
  const updateScreen = useCallback((screen: string) => {
    currentScreenRef.current = screen;
    // If data channel is open, send the update to the bot so it has context
    if (dcRef.current?.readyState === 'open') {
      try {
        dcRef.current.send(JSON.stringify({ type: 'screen_update', screen }));
      } catch {}
    }
  }, []);

  // ── Auto-disconnect on unmount ─────────────────────────────────────────────
  useEffect(() => () => cleanup(), [cleanup]);

  // ── Detect browser support ─────────────────────────────────────────────────
  const isSupported: boolean =
    typeof RTCPeerConnection !== 'undefined' &&
    typeof navigator?.mediaDevices?.getUserMedia === 'function';

  return {
    status,
    isBotSpeaking,
    connect,
    disconnect,
    updateScreen,
    isSupported,
  };
}
