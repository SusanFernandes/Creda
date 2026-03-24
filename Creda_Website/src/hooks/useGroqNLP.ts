/**
 * useGroqNLP — NLP / Intent processing for voice commands.
 * Routes through the CREDA backend (/chat) instead of calling Groq directly
 * from the browser (which would expose API keys).
 */
import { useState } from 'react';
import { ApiService, VOICE_COMMANDS } from '@/services/api';

export interface NLPResponse {
  intent: string;
  action: string;
  parameters: Record<string, any>;
  confidence: number;
  response_text?: string;
  translation?: string;
  session_id?: string;
}

// Map an action string to the React Router path
export const ACTION_TO_PATH: Record<string, string> = {
  dashboard: '/dashboard',
  portfolio: '/portfolio',
  budget: '/budget',
  health: '/health',
  fire: '/fire-planner',
  sip: '/sip-calculator',
  tax: '/tax-wizard',
  advisory: '/advisory',
  goals: '/goals',
  knowledge: '/knowledge',
  voice: '/voice',
  couples: '/couples-planner',
  settings: '/settings',
  help: '/help',
};

export const useGroqNLP = () => {
  const [isProcessing, setIsProcessing] = useState(false);

  /**
   * Process a natural-language command.
   * 1. Try keyword matching (fast, offline).
   * 2. If no keyword match OR text is a financial question, send to /chat.
   */
  const processCommand = async (
    text: string,
    language: string = 'english',
    userId: string = 'web_user',
    sessionId?: string,
  ): Promise<NLPResponse> => {
    setIsProcessing(true);

    try {
      const lowerText = text.toLowerCase().trim();

      // ── Step 1: keyword match (navigation intent) ─────────────────────────
      for (const [action, keywords] of Object.entries(VOICE_COMMANDS)) {
        const matched = keywords.some(
          (kw) =>
            lowerText.includes(kw.toLowerCase()) ||
            fuzzyMatch(lowerText, kw.toLowerCase(), 0.85),
        );

        if (matched) {
          // Pure navigation — no need to call the backend
          return {
            intent: 'navigation',
            action,
            parameters: { path: ACTION_TO_PATH[action] ?? '/dashboard' },
            confidence: 0.9,
          };
        }
      }

      // ── Step 2: send to CREDA backend for financial questions ──────────────
      const langCode = languageNameToCode(language);
      const chatRes = await ApiService.chat({
        message: text,
        user_id: userId,
        session_id: sessionId,
        language: langCode,
      });

      return {
        intent: chatRes.intent || 'general_chat',
        action: 'answer',
        parameters: chatRes.data || {},
        confidence: 0.95,
        response_text: chatRes.response,
        session_id: chatRes.session_id,
      };
    } catch (err) {
      console.warn('useGroqNLP: backend failed, using fallback pattern matching', err);
      return patternFallback(text);
    } finally {
      setIsProcessing(false);
    }
  };

  return { processCommand, isProcessing };
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
function languageNameToCode(name: string): string {
  const map: Record<string, string> = {
    hindi: 'hi', tamil: 'ta', telugu: 'te', bengali: 'bn',
    marathi: 'mr', gujarati: 'gu', kannada: 'kn', malayalam: 'ml',
    punjabi: 'pa', urdu: 'ur', english: 'en',
  };
  return map[name.toLowerCase()] ?? 'en';
}

function fuzzyMatch(text: string, keyword: string, threshold = 0.85): boolean {
  if (text.length === 0) return keyword.length === 0;
  if (keyword.length === 0) return false;
  const matrix: number[][] = Array.from({ length: keyword.length + 1 }, (_, i) =>
    Array.from({ length: text.length + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0)),
  );
  for (let i = 1; i <= keyword.length; i++) {
    for (let j = 1; j <= text.length; j++) {
      matrix[i][j] =
        keyword[i - 1] === text[j - 1]
          ? matrix[i - 1][j - 1]
          : Math.min(matrix[i - 1][j - 1] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j] + 1);
    }
  }
  const maxLen = Math.max(text.length, keyword.length);
  return (maxLen - matrix[keyword.length][text.length]) / maxLen >= threshold;
}

function patternFallback(text: string): NLPResponse {
  const lower = text.toLowerCase();
  const rules: Array<{ patterns: string[]; intent: string; action: string }> = [
    { patterns: ['portfolio', 'investment', 'fund', 'sip', 'निवेश', 'పెట్టుబడి'], intent: 'portfolio', action: 'portfolio' },
    { patterns: ['budget', 'expense', 'spend', 'खर्च', 'ఖర్చు'], intent: 'budget', action: 'budget' },
    { patterns: ['health', 'score', 'स्वास्थ्य', 'ఆరోగ్యం'], intent: 'health', action: 'health' },
    { patterns: ['retire', 'fire', 'रिटायर', 'పదవీ'], intent: 'fire', action: 'fire' },
    { patterns: ['tax', 'टैक्स', 'పన్ను', 'কর'], intent: 'tax', action: 'tax' },
    { patterns: ['goal', 'target', 'लक्ष्य', 'లక్ష్యం'], intent: 'goals', action: 'goals' },
    { patterns: ['dashboard', 'home', 'डैशबोर्ड'], intent: 'navigation', action: 'dashboard' },
  ];

  for (const rule of rules) {
    if (rule.patterns.some((p) => lower.includes(p))) {
      return { intent: rule.intent, action: rule.action, parameters: {}, confidence: 0.6 };
    }
  }

  return { intent: 'general_chat', action: 'answer', parameters: {}, confidence: 0.4 };
}
