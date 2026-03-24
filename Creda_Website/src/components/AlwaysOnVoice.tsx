/**
 * AlwaysOnVoice — smart voice layer for CREDA website.
 *
 * Strategy
 * ────────
 * 1. Try Pipecat real-time WebRTC mode first (always-on, hands-free).
 * 2. If the browser doesn't support WebRTC, pipecat is not installed on the
 *    backend, or the WebRTC session enters a persistent error state →
 *    transparently swap in the Push-to-Talk fallback.
 *
 * This lets us upgrade to real-time voice without removing the robust PTT
 * system that already works correctly.
 */

import { useState } from 'react';
import { PipecatVoiceButton } from './PipecatVoiceButton';
import { PushToTalkButton } from './PushToTalkButton';

export function AlwaysOnVoice() {
  // Start optimistically with Pipecat; fall back on fatal error
  const [useFallback, setUseFallback] = useState(false);

  if (useFallback) {
    return <PushToTalkButton />;
  }

  return (
    <PipecatVoiceButton
      onFatalError={() => {
        console.info('[AlwaysOnVoice] Pipecat failed — switching to push-to-talk mode');
        setUseFallback(true);
      }}
    />
  );
}
