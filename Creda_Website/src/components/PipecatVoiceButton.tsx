/**
 * PipecatVoiceButton — always-on real-time voice button for CREDA website.
 *
 * Unlike the PTT button, this connects to a live Pipecat streaming pipeline
 * (SmallWebRTCTransport) so conversation is fully hands-free.
 *
 * Visual states
 * ─────────────
 *  disconnected  — grey mic icon,  "Live off"
 *  connecting    — amber spinner,  "Connecting…"
 *  connected     — green pulsing,  "Listening…"
 *  bot-speaking  — blue pulsing,   "Bot speaking…"
 *  error         — red with ×,     "Unavailable"
 *
 * If the WebRTC session fails, it gracefully renders null so the parent
 * (AlwaysOnVoice) can swap in the PTT fallback.
 */

import { useEffect, useRef } from 'react';
import { Mic, Loader2, Volume2, WifiOff } from 'lucide-react';
import { cn } from '@/lib/utils';
import { usePipecatVoice, PipecatStatus } from '@/hooks/usePipecatVoice';
import { useLanguage } from '@/contexts/LanguageContext';
import { useLocation } from 'react-router-dom';

// Language name (from LanguageContext) → ISO code for the backend
const LANG_MAP: Record<string, string> = {
  english: 'en', hindi: 'hi', tamil: 'ta', telugu: 'te',
  bengali: 'bn', marathi: 'mr', gujarati: 'gu', kannada: 'kn',
  malayalam: 'ml', punjabi: 'pa', urdu: 'ur',
};

// ── Status config ─────────────────────────────────────────────────────────────
const STATUS_CONFIG: Record<
  PipecatStatus,
  {
    bg: string;
    ring: string;
    icon: React.ComponentType<{ className?: string }>;
    pulse: boolean;
    label: string;
  }
> = {
  disconnected: {
    bg:    'bg-muted text-muted-foreground',
    ring:  'ring-muted/30',
    icon:  WifiOff,
    pulse: false,
    label: 'Live off',
  },
  connecting: {
    bg:    'bg-amber-500 text-white',
    ring:  'ring-amber-400/40',
    icon:  Loader2,
    pulse: false,
    label: 'Connecting…',
  },
  connected: {
    bg:    'bg-emerald-500 text-white',
    ring:  'ring-emerald-400/40',
    icon:  Mic,
    pulse: true,
    label: 'Listening…',
  },
  'bot-speaking': {
    bg:    'bg-primary text-primary-foreground',
    ring:  'ring-primary/40',
    icon:  Volume2,
    pulse: true,
    label: 'Bot speaking…',
  },
  error: {
    bg:    'bg-destructive/80 text-white',
    ring:  'ring-destructive/30',
    icon:  WifiOff,
    pulse: false,
    label: 'Unavailable',
  },
};

// Props that AlwaysOnVoice passes so it knows when to fall back
interface PipecatVoiceButtonProps {
  /** Called if the underlying WebRTC session enters permanent error state */
  onFatalError?: () => void;
}

export function PipecatVoiceButton({ onFatalError }: PipecatVoiceButtonProps) {
  const { currentLanguage } = useLanguage();
  const languageCode = LANG_MAP[currentLanguage] ?? 'en';
  const location = useLocation();

  // Derive current screen slug from pathname
  const currentScreen = location.pathname.replace(/^\//, '') || 'dashboard';

  const {
    status,
    isBotSpeaking,
    connect,
    disconnect,
    updateScreen,
    isSupported,
  } = usePipecatVoice({
    languageCode,
    initialScreen: currentScreen,
  });

  // Sync current screen whenever route changes
  useEffect(() => {
    updateScreen(currentScreen);
  }, [currentScreen, updateScreen]);

  // Auto-connect on mount if supported
  const didAutoConnect = useRef(false);
  useEffect(() => {
    if (!isSupported || didAutoConnect.current) return;
    didAutoConnect.current = true;
    connect().catch(() => {/* handled inside hook */});
  }, [isSupported, connect]);

  // If persistent error — notify parent after a brief delay
  const errorCountRef = useRef(0);
  useEffect(() => {
    if (status === 'error') {
      errorCountRef.current += 1;
      if (errorCountRef.current >= 2) {
        onFatalError?.();
      } else {
        // Retry once after 3 s
        const t = setTimeout(() => connect().catch(() => {}), 3000);
        return () => clearTimeout(t);
      }
    } else {
      errorCountRef.current = 0;
    }
    return undefined;
  }, [status, connect, onFatalError]);

  if (!isSupported) return null;

  const cfg  = STATUS_CONFIG[status];
  const Icon = cfg.icon;

  const handleClick = () => {
    if (status === 'disconnected' || status === 'error') {
      connect().catch(() => {});
    } else if (status === 'connected' || status === 'bot-speaking') {
      disconnect();
    }
    // connecting — ignore
  };

  return (
    <div className="fixed bottom-6 right-6 flex flex-col items-end gap-2 z-50">
      {/* Status chip */}
      <div
        className={cn(
          'text-xs font-medium px-2.5 py-1 rounded-full',
          'bg-background/90 backdrop-blur-sm border border-border',
          'shadow-sm transition-all duration-200',
          status === 'connected' && 'text-emerald-600 border-emerald-300 dark:text-emerald-400',
          status === 'bot-speaking' && 'text-primary border-primary/40',
          status === 'connecting' && 'text-amber-600 border-amber-300 dark:text-amber-400',
          (status === 'error' || status === 'disconnected') && 'text-muted-foreground',
        )}
      >
        {status === 'connected' && (
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5 animate-pulse" />
        )}
        {cfg.label}
      </div>

      {/* Main button */}
      <button
        onClick={handleClick}
        aria-label={cfg.label}
        title={cfg.label}
        className={cn(
          // Base layout
          'relative w-14 h-14 rounded-full',
          'flex items-center justify-center',
          'shadow-lg ring-4 transition-all duration-200',
          'focus:outline-none focus-visible:ring-offset-2',
          cfg.bg,
          cfg.ring,
          // Pulsing halo while listening / bot speaking
          cfg.pulse &&
            'after:absolute after:inset-0 after:rounded-full after:animate-ping',
          cfg.pulse && `after:opacity-20 after:${cfg.bg.split(' ')[0]}`,
          // Disabled cursor while connecting
          status === 'connecting' && 'cursor-wait',
        )}
      >
        {/* "LIVE" badge on connected */}
        {(status === 'connected' || status === 'bot-speaking') && (
          <span className="absolute -top-1 -right-1 text-[9px] font-bold bg-emerald-500 text-white rounded px-1 leading-4">
            LIVE
          </span>
        )}

        <Icon
          className={cn(
            'w-6 h-6',
            status === 'connecting' && 'animate-spin',
          )}
        />
      </button>
    </div>
  );
}
