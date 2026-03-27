/**
 * CREDA API Service v2.0
 * All requests route through the Gateway (port 8080).
 * Voice audio goes directly to the Multilingual service (port 8000).
 */
import axios from 'axios';

// ─── Base URLs ────────────────────────────────────────────────────────────────
export const GATEWAY_URL =
  import.meta.env.VITE_API_GATEWAY_URL || 'http://localhost:8080';

export const MULTILINGUAL_URL =
  import.meta.env.VITE_MULTILINGUAL_URL || 'http://localhost:8000';

// ─── Axios Instances ──────────────────────────────────────────────────────────
const gatewayClient = axios.create({
  baseURL: GATEWAY_URL,
  timeout: 30000,   
  headers: { 'Content-Type': 'application/json' },
});

const multilingualClient = axios.create({
  baseURL: MULTILINGUAL_URL,
  timeout: 60000,
});

// ─── Types ────────────────────────────────────────────────────────────────────
export interface UserProfile {
  user_id?: string;
  name?: string;
  age?: number;
  income?: number;
  expenses?: number;
  savings?: number;
  dependents?: number;
  risk_tolerance?: number;
  goal_type?: string;
  time_horizon?: number;
  language?: string;
  monthly_emi?: number;
  emergency_fund?: number;
  life_insurance_cover?: number;
  has_health_insurance?: boolean;
  investments_80c?: number;
  nps_contribution?: number;
  health_insurance_premium?: number;
  hra?: number;
  home_loan_interest?: number;
  target_retirement_age?: number;
}

export interface ChatRequest {
  message: string;
  user_id: string;
  session_id?: string;
  language?: string;
  user_profile?: Partial<UserProfile>;
  portfolio_data?: Record<string, any>;
}

export interface ChatResponse {
  session_id: string;
  response: string;
  intent: string;
  data: Record<string, any>;
  user_id: string;
}

export interface VoiceProcessResponse {
  transcript: string;
  response_text: string;
  language: string;
  processing_time_ms: number;
  audio?: Blob;
}

export interface SIPCalcRequest {
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

export interface TaxWizardRequest {
  user_id: string;
  annual_income: number;
  investments_80c?: number;
  nps_contribution?: number;
  health_insurance_premium?: number;
  hra?: number;
  home_loan_interest?: number;
}

export interface StressTestRequest {
  user_id: string;
  event_type: 'market_crash' | 'job_loss' | 'medical_emergency' | 'baby' | 'home_purchase' | 'marriage';
  severity?: number;
}

export interface CouplePlannerRequest {
  partner1_user_id: string;
  partner2_user_id: string;
  combined_goal?: string;
}

// ─── Fallback Dummy Data ──────────────────────────────────────────────────────
export const DUMMY_DATA = {
  chat: {
    response: 'CREDA is in offline mode. Please start the backend at http://localhost:8080.',
    intent: 'general_chat',
    data: {},
    session_id: 'offline',
    user_id: 'guest',
  },
  healthScore: {
    score: 72,
    grade: 'B',
    breakdown: {
      emergency_fund: 65,
      insurance: 70,
      diversification: 80,
      debt_ratio: 75,
      tax_efficiency: 68,
      retirement_readiness: 72,
    },
    recommendations: [
      'Build emergency fund to 6 months of expenses',
      'Consider term life insurance with Rs.50L+ cover',
      'Increase SIP by 10% annually (step-up SIP)',
    ],
    user_id: 'guest',
  },
  sip: {
    monthly_amount: 10000,
    years: 15,
    expected_return: 12,
    total_invested: 1800000,
    expected_value: 4999300,
    wealth_gain: 3199300,
  },
  fire: {
    fire_number: 25000000,
    years_to_fire: 18,
    monthly_required: 42000,
    current_gap: 15000,
  },
  taxWizard: {
    old_regime_tax: 112500,
    new_regime_tax: 95000,
    recommended: 'new',
    savings: 17500,
    missed_deductions: [],
  },
  portfolio: {
    persona: 'Balanced Investor',
    allocation: {
      large_cap_equity: 0.4,
      mid_cap_equity: 0.15,
      government_bonds: 0.25,
      corporate_bonds: 0.1,
      gold: 0.1,
    },
    expected_return: 0.12,
    risk_score: 6.5,
  },
  rebalance: {
    needs_rebalancing: true,
    drift_percentage: 8.4,
    last_rebalanced: '2024-02-15',
  },
  budget: {
    adaptive_allocation: {
      needs: 0.50,
      wants: 0.25,
      savings: 0.25,
    },
    confidence_score: 0.92,
  },
};

// ─── Helper ───────────────────────────────────────────────────────────────────
function unwrap(data: any): any {
  if (data && typeof data === 'object' && 'data' in data) return data.data;
  return data;
}

// ─── API Service ──────────────────────────────────────────────────────────────
export class ApiService {
  static async healthCheck(): Promise<any> {
    try {
      const res = await gatewayClient.get('/health');
      return res.data;
    } catch {
      return { status: 'offline' };
    }
  }

  static async chat(req: ChatRequest): Promise<ChatResponse> {
    try {
      const res = await gatewayClient.post('/chat', req);
      return (res.data?.data ?? res.data) as ChatResponse;
    } catch {
      return { ...DUMMY_DATA.chat, user_id: req.user_id };
    }
  }

  static async processVoiceAudio(
    audioBlob: Blob,
    languageCode: string = 'hi',
    userId: string = 'web_user',
    userProfile: Partial<UserProfile> = {},
  ): Promise<VoiceProcessResponse> {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');
    formData.append('language_code', languageCode);
    formData.append('session_id', userId);
    formData.append('user_profile', JSON.stringify(userProfile));

    const res = await multilingualClient.post('/process_voice', formData, {
      responseType: 'arraybuffer',
    });

    const transcript = decodeURIComponent(res.headers['x-transcript'] || '');
    const responseText = decodeURIComponent(res.headers['x-response-text'] || '');
    const language = res.headers['x-language'] || languageCode;
    const processingTime = parseFloat(res.headers['x-processing-time'] || '0') * 1000;
    const audio = new Blob([res.data], { type: 'audio/wav' });

    return { transcript, response_text: responseText, language, processing_time_ms: processingTime, audio };
  }

  static async ttsOnly(text: string, languageCode: string = 'hi'): Promise<Blob | null> {
    try {
      const formData = new FormData();
      formData.append('text', text);
      formData.append('language_code', languageCode);
      const res = await multilingualClient.post('/tts_only', formData, { responseType: 'arraybuffer' });
      return new Blob([res.data], { type: 'audio/wav' });
    } catch {
      return null;
    }
  }

  static async upsertProfile(profile: UserProfile): Promise<any> {
    try {
      const res = await gatewayClient.post('/profile/upsert', profile);
      return unwrap(res.data);
    } catch {
      return null;
    }
  }

  static async getProfile(userId: string): Promise<UserProfile | null> {
    try {
      const res = await gatewayClient.get(`/profile/${userId}`);
      return unwrap(res.data) as UserProfile;
    } catch {
      return null;
    }
  }

  static async getHealthScore(profile: UserProfile): Promise<any> {
    try {
      const res = await gatewayClient.post('/money-health-score', {
        user_id: profile.user_id || 'anonymous',
        language: profile.language || 'en',
        ...profile,
      });
      return unwrap(res.data);
    } catch {
      return DUMMY_DATA.healthScore;
    }
  }

  static async calculateSIP(req: SIPCalcRequest): Promise<any> {
    try {
      const res = await gatewayClient.post('/sip-calculator', req);
      return unwrap(res.data);
    } catch {
      return DUMMY_DATA.sip;
    }
  }

  static async firePlanner(req: FIRERequest): Promise<any> {
    try {
      const res = await gatewayClient.post('/fire-planner', req);
      return unwrap(res.data);
    } catch {
      return DUMMY_DATA.fire;
    }
  }

  static async taxWizard(req: TaxWizardRequest): Promise<any> {
    try {
      const res = await gatewayClient.post('/tax-wizard', req);
      return unwrap(res.data);
    } catch {
      return DUMMY_DATA.taxWizard;
    }
  }

  static async couplesPlanner(req: CouplePlannerRequest): Promise<any> {
    try {
      const res = await gatewayClient.post('/couples-planner', req);
      return unwrap(res.data);
    } catch {
      return null;
    }
  }

  static async portfolioXray(pdfFile: File, userId: string): Promise<any> {
    try {
      const form = new FormData();
      form.append('file', pdfFile);
      form.append('user_id', userId);
      const res = await gatewayClient.post('/portfolio/xray', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000,
      });
      return unwrap(res.data);
    } catch {
      return null;
    }
  }

  static async stressTest(req: StressTestRequest): Promise<any> {
    try {
      const res = await gatewayClient.post('/portfolio/stress-test', req);
      return unwrap(res.data);
    } catch {
      return null;
    }
  }

  static async ragQuery(query: string, userId: string = 'web_user'): Promise<any> {
    try {
      const res = await gatewayClient.post('/rag_query', { query, user_id: userId });
      return unwrap(res.data);
    } catch {
      return { answer: DUMMY_DATA.chat.response, sources: [], confidence: 0 };
    }
  }

  static async getPortfolioAllocation(profile: UserProfile): Promise<any> {
    try {
      const res = await gatewayClient.get('/get_portfolio_allocation', { params: { user_id: profile.user_id } });
      return unwrap(res.data);
    } catch {
      return DUMMY_DATA.portfolio;
    }
  }

  static async portfolioOptimization(req: any): Promise<any> {
    try {
      const res = await gatewayClient.post('/portfolio/optimize', req);
      return unwrap(res.data);
    } catch {
      return DUMMY_DATA.portfolio;
    }
  }

  static async checkRebalancing(req: any): Promise<any> {
    try {
      const res = await gatewayClient.post('/portfolio/check-rebalance', req);
      return unwrap(res.data);
    } catch {
      return DUMMY_DATA.rebalance;
    }
  }

  static async optimizeBudget(profile: UserProfile, expenses: any[]): Promise<any> {
    try {
      const res = await gatewayClient.post('/budget/optimize', { profile, expenses });
      return unwrap(res.data);
    } catch {
      return DUMMY_DATA.budget;
    }
  }
}

// ─── Voice Command Keywords (multilingual) ────────────────────────────────────
export const VOICE_COMMANDS: Record<string, string[]> = {
  dashboard: ['dashboard', 'home', 'main', 'overview', 'डैशबोर्ड', 'होम', 'முதன்மை', 'ড্যাশবোর্ড', 'డ్యాష్‌బోర్డ్', 'ਡੈਸ਼ਬੋਰਡ'],
  portfolio: ['portfolio', 'investments', 'assets', 'holdings', 'mutual funds', 'पोर्टफोलियो', 'निवेश', 'முதலீடுகள்', 'পোর্টফোলিও', 'పోర్ట్‌ఫోలియో', 'ਪੋਰਟਫੋਲੀਓ'],
  budget: ['budget', 'expenses', 'spending', 'बजट', 'खर्च', 'பட்ஜெட்', 'বাজেট', 'బడ్జెట్', 'ਬਜਟ'],
  health: ['financial health', 'health score', 'money health', 'वित्तीय स्वास्थ्य', 'நிதி ஆரோக்கியம்', 'আর্থিক স্বাস্থ্য'],
  fire: ['fire planner', 'retirement', 'retire early', 'रिटायरमेंट', 'ஓய்வுக்காலம்', 'অবসর', 'పదవీ విరమణ'],
  sip: ['sip', 'sip calculator', 'systematic investment', 'एसआईपी', 'SIP கால்குலேட்டர்', 'SIP ক্যালকুলেটর'],
  tax: ['tax', 'tax wizard', 'income tax', 'टैक्स', 'कर', 'வரி', 'কর', 'పన్ను', 'ਟੈਕਸ'],
  advisory: ['advisory', 'advice', 'financial advice', 'सलाह', 'ஆலோசனை', 'পরামর্শ', 'సలహా', 'ਸਲਾਹ'],
  goals: ['goals', 'financial goals', 'लक्ष्य', 'இலக்குகள்', 'লক্ষ্য', 'లక్ష్యాలు', 'ਟੀਚੇ'],
  knowledge: ['knowledge', 'learn', 'education', 'ज्ञान', 'அறிவு', 'জ্ঞান', 'జ్ఞానం', 'ਗਿਆਨ'],
  voice: ['voice', 'voice assistant', 'speak', 'वॉयस', 'குரல்', 'ভয়েস', 'వాయిస్', 'ਅਵਾਜ਼'],
  couples: ['couples', 'joint planning', 'partner', 'spouse', 'पार्टनर', 'साथी', 'கூட்டு திட்டமிடல்'],
};
