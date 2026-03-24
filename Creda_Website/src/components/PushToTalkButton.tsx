/**
 * PushToTalkButton — floating voice command button for CREDA website.
 *
 * - Press once → starts listening (VAD auto-stops on silence)
 * - Can also press again to stop manually
 * - Shows live transcript + status above the button
 * - Pulsing red ring while listening, spinner while processing
 */

import { useEffect, useRef } from 'react';
import { Mic, MicOff, Loader2, Volume2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useVoiceController, VoiceStatus } from '@/hooks/useVoiceController';

// ── Status styling ────────────────────────────────────────────────────────────
const STATUS_CONFIG: Record<VoiceStatus, {
  bg: string; ring: string; icon: React.ComponentType<any>; pulse: boolean; label: string;
}> = {
  idle:       { bg: 'bg-primary',     ring: 'ring-primary/30',     icon: Mic,     pulse: false, label: 'Tap to speak' },
  listening:  { bg: 'bg-destructive', ring: 'ring-destructive/50', icon: MicOff,  pulse: true,  label: 'Listening…' },
  processing: { bg: 'bg-amber-500',   ring: 'ring-amber-400/50',   icon: Loader2, pulse: false, label: 'Thinking…' },
  speaking:   { bg: 'bg-emerald-500', ring: 'ring-emerald-400/50', icon: Volume2, pulse: true,  label: 'Speaking…' },
};

export function PushToTalkButton() {
  const { status, isListening, transcript, startListening, stopListening } = useVoiceController();
  const transcriptRef = useRef<HTMLDivElement>(null);
  const cfg = STATUS_CONFIG[status];
  const Icon = cfg.icon;

  // Auto-scroll transcript
  useEffect(() => {
    if (transcriptRef.current && transcript) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [transcript]);

  const handlePress = () => {
    if (status === 'idle') {
      startListening();
    } else if (status === 'listening') {
      stopListening();
    }
    // processing / speaking: ignore presses
  };

  return (
    <div className="fixed bottom-6 right-6 flex flex-col items-end gap-3 z-50">
      {/* Transcript / status bubble */}
      {(status !== 'idle' || transcript) && (
        <div
          ref={transcriptRef}
          className={cn(
            'bg-background/95 backdrop-blur-sm border border-border rounded-2xl',
            'px-4 py-3 shadow-lg max-w-[260px] text-sm transition-all duration-200',
            'animate-in slide-in-from-bottom-2',
          )}
        >
          <p className="text-xs font-medium text-muted-foreground mb-1">{cfg.label}</p>
          {transcript && (
            <p className="text-foreground leading-snug line-clamp-3">{transcript}</p>
          )}
        </div>
      )}

      {/* Main mic button */}
      <button
        onClick={handlePress}
        disabled={status === 'processing' || status === 'speaking'}
        aria-label={cfg.label}
        className={cn(
          // Base
          'relative w-14 h-14 rounded-full flex items-center justify-center',
          'shadow-lg transition-all duration-200 focus:outline-none',
          'ring-4',
          cfg.bg,
          cfg.ring,
          // Pulse ring on listening / speaking
          cfg.pulse && 'before:absolute before:inset-0 before:rounded-full before:animate-ping',
          cfg.pulse && `before:${cfg.bg} before:opacity-30`,
          // Disabled  
          (status === 'processing' || status === 'speaking')
            ? 'cursor-not-allowed opacity-90'
            : 'hover:scale-105 active:scale-95 cursor-pointer',
        )}
      >
        {/* Wider pulse ring (CSS animation via Tailwind) */}
        {cfg.pulse && (
          <span
            className={cn(
              'absolute inset-0 rounded-full animate-ping opacity-25',
              cfg.bg,
            )}
          />
        )}

        <Icon
          className={cn(
            'relative z-10 text-white',
            status === 'processing' && 'animate-spin',
          )}
          size={24}
          strokeWidth={2}
        />
      </button>
    </div>
  );
}

export default PushToTalkButton;
