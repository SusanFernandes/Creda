/**
 * Creda App — FastAPI Service Layer
 * All calls route through the Gateway at GATEWAY_URL.
 */

const GATEWAY_URL = process.env.EXPO_PUBLIC_GATEWAY_URL ?? 'http://localhost:8080';
const MULTILINGUAL_URL = process.env.EXPO_PUBLIC_MULTILINGUAL_URL ?? 'http://localhost:8000';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ChatRequest {
  message: string;
  user_id: string;
  session_id?: string;
  language?: string;
  user_profile?: Record<string, any>;
  portfolio_data?: Record<string, any>;
}

export interface ChatResponse {
  session_id: string;
  response: string;
  intent: string;
  data: Record<string, any>;
  user_id: string;
}

export interface SIPRequest {
  monthly_amount: number;
  expected_return: number;
  years: number;
  step_up_percent?: number;
}

export interface FIRERequest {
  user_id: string;
  monthly_expenses?: number;
  current_savings?: number;
  monthly_investment?: number;
  expected_return?: number;
  inflation_rate?: number;
}

export interface TaxRequest {
  user_id: string;
  annual_income: number;
  investments_80c?: number;
  nps_contribution?: number;
  health_insurance_premium?: number;
  hra?: number;
  home_loan_interest?: number;
}

export interface UserProfile {
  user_id?: string;
  name?: string;
  age?: number;
  income?: number;
  expenses?: number;
  savings?: number;
  language?: string;
  [key: string]: any;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

async function post<T>(url: string, body: any): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  const json = await res.json();
  return (json?.data ?? json) as T;
}

async function get<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  const json = await res.json();
  return (json?.data ?? json) as T;
}

// ─── Offline fallbacks ────────────────────────────────────────────────────────

const OFFLINE_CHAT: ChatResponse = {
  session_id: 'offline',
  user_id: 'guest',
  intent: 'general_chat',
  data: {},
  response:
    'Creda is in offline mode. Please start the backend at http://localhost:8080 to enable AI features.',
};

// ─── API Service ──────────────────────────────────────────────────────────────

export const ApiService = {
  /** Health check – returns true when gateway is reachable */
  async healthCheck(): Promise<boolean> {
    try {
      await fetch(`${GATEWAY_URL}/health`);
      return true;
    } catch {
      return false;
    }
  },

  /** Send a message to the LangGraph AI agent */
  async chat(req: ChatRequest): Promise<ChatResponse> {
    try {
      return await post<ChatResponse>(`${GATEWAY_URL}/chat`, req);
    } catch (err) {
      console.error('[ApiService.chat]', err);
      return { ...OFFLINE_CHAT, user_id: req.user_id };
    }
  },

  /** Upsert user profile in the backend */
  async upsertProfile(profile: UserProfile): Promise<any> {
    try {
      return await post(`${GATEWAY_URL}/profile/upsert`, profile);
    } catch (err) {
      console.error('[ApiService.upsertProfile]', err);
      return null;
    }
  },

  /** Get user profile */
  async getProfile(userId: string): Promise<UserProfile | null> {
    try {
      return await get<UserProfile>(`${GATEWAY_URL}/profile/${userId}`);
    } catch (err) {
      console.error('[ApiService.getProfile]', err);
      return null;
    }
  },

  /** Money Health Score */
  async getHealthScore(profile: UserProfile): Promise<any> {
    try {
      return await post(`${GATEWAY_URL}/money-health-score`, profile);
    } catch (err) {
      console.error('[ApiService.getHealthScore]', err);
      return null;
    }
  },

  /** SIP Calculator */
  async calculateSIP(req: SIPRequest): Promise<any> {
    try {
      return await post(`${GATEWAY_URL}/sip-calculator`, req);
    } catch (err) {
      console.error('[ApiService.calculateSIP]', err);
      return null;
    }
  },

  /** FIRE Planner */
  async firePlanner(req: FIRERequest): Promise<any> {
    try {
      return await post(`${GATEWAY_URL}/fire-planner`, req);
    } catch (err) {
      console.error('[ApiService.firePlanner]', err);
      return null;
    }
  },

  /** Tax Wizard */
  async taxWizard(req: TaxRequest): Promise<any> {
    try {
      return await post(`${GATEWAY_URL}/tax-wizard`, req);
    } catch (err) {
      console.error('[ApiService.taxWizard]', err);
      return null;
    }
  },

  /** Portfolio X-Ray (attach as FormData from caller) */
  async portfolioXray(formData: FormData): Promise<any> {
    try {
      const res = await fetch(`${GATEWAY_URL}/portfolio/xray`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      return json?.data ?? json;
    } catch (err) {
      console.error('[ApiService.portfolioXray]', err);
      return null;
    }
  },

  /** Couples Planner */
  async couplesPlanner(partner1Id: string, partner2Id: string, goal?: string): Promise<any> {
    try {
      return await post(`${GATEWAY_URL}/couples-planner`, {
        partner1_user_id: partner1Id,
        partner2_user_id: partner2Id,
        combined_goal: goal,
      });
    } catch (err) {
      console.error('[ApiService.couplesPlanner]', err);
      return null;
    }
  },

  /** RAG knowledge query */
  async ragQuery(query: string, userId = 'app_user'): Promise<any> {
    try {
      return await post(`${GATEWAY_URL}/rag_query`, { query, user_id: userId });
    } catch (err) {
      console.error('[ApiService.ragQuery]', err);
      return { answer: OFFLINE_CHAT.response, sources: [], confidence: 0 };
    }
  },

  /**
   * Portfolio allocation based on user profile.
   * Mirrors the /get_portfolio_allocation gateway route.
   */
  async getPortfolioAllocation(profile: UserProfile): Promise<any> {
    try {
      const params = new URLSearchParams();
      if (profile.user_id) params.append('user_id', profile.user_id);
      const res = await fetch(`${GATEWAY_URL}/get_portfolio_allocation?${params}`, {
        method: 'GET',
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      return json?.data ?? json;
    } catch (err) {
      console.error('[ApiService.getPortfolioAllocation]', err);
      // Fallback: use /chat with a portfolio question
      try {
        const chatRes = await this.chat({
          message: `Suggest portfolio allocation for a ${profile.age}-year-old with income ₹${profile.income}, savings ₹${profile.savings}, risk_tolerance ${profile.risk_tolerance}/10, goal: ${profile.goal_type}, horizon: ${profile.time_horizon} years.`,
          user_id: profile.user_id ?? 'app_user',
          user_profile: profile,
        });
        return chatRes.data?.allocation ?? null;
      } catch {
        return null;
      }
    }
  },

  async processVoice(
    audioUri: string,
    languageCode = 'hi',
    userId = 'app_user',
  ): Promise<{ transcript: string; response_text: string; language: string } | null> {
    try {
      const formData = new FormData();
      // React Native fetch can attach local file URIs directly
      formData.append('audio', { uri: audioUri, name: 'recording.wav', type: 'audio/wav' } as any);
      formData.append('language_code', languageCode);
      formData.append('session_id', userId);

      const res = await fetch(`${MULTILINGUAL_URL}/process_voice`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const transcript = decodeURIComponent(res.headers.get('x-transcript') ?? '');
      const responseText = decodeURIComponent(res.headers.get('x-response-text') ?? '');
      const language = res.headers.get('x-language') ?? languageCode;
      return { transcript, response_text: responseText, language };
    } catch (err) {
      console.error('[ApiService.processVoice]', err);
      return null;
    }
  },

  /**
   * Push-to-talk: send audio → ASR + Groq function-calling → structured intent.
   * Returns { transcript, type, function?, args?, response? }
   */
  async voiceCommand(
    audioUri: string,
    languageCode = 'en',
    currentScreen = 'dashboard',
    userId = 'app_user',
  ): Promise<{
    transcript: string;
    type: 'function_call' | 'conversation';
    function?: string;
    args?: Record<string, any>;
    response?: string;
  } | null> {
    try {
      const formData = new FormData();
      formData.append('audio', { uri: audioUri, name: 'command.m4a', type: 'audio/m4a' } as any);
      formData.append('language_code', languageCode);
      formData.append('current_screen', currentScreen);
      formData.append('user_id', userId);

      const res = await fetch(`${GATEWAY_URL}/voice/command`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error('[ApiService.voiceCommand]', err);
      return null;
    }
  },
};
