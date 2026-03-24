
import { useRouter } from "expo-router";
import { useEffect } from "react";

/**
 * voice.tsx — Immediately redirect to the full AI Voice Agent screen.
 */
export default function VoiceScreen() {
  const router = useRouter();

  useEffect(() => {
    // Replace so back-button doesn't loop
    router.replace("/voiceagent" as any);
  }, []);

  return null;
}
