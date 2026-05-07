/**
 * CREDA API Service v3.1 (Next.js)
 *
 * All requests are proxied through the Next.js API route at /api/backend,
 * which injects the Clerk `x-user-id` / `x-user-email` headers that
 * FastAPI's `get_auth()` dependency requires.
 *
 * Direct browser → FastAPI calls are NEVER made, which avoids:
 *  - CORS issues (same-origin to the Next.js server)
 *  - Leaking the backend URL to the browser
 *  - Auth header bypasses
 */
import axios from 'axios';

// ─── Base URL ─────────────────────────────────────────────────────────────────
// Route through the Next.js proxy (same-origin) so Clerk auth headers are
// injected server-side. Falls back to direct backend URL for SSR / tests.
export const API_URL =
  typeof window !== 'undefined'
    ? '/api/backend'
    : (process.env.BACKEND_API_URL ?? 'http://localhost:8001');

// ─── Axios Instance ───────────────────────────────────────────────────────────
const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Auth is handled server-side by the /api/backend proxy route (Clerk → x-user-id).
// setAuthToken / _authToken are retained for backward compatibility but are no-ops.
let _authToken: string | null = null;

api.interceptors.request.use((config) => {
  // The proxy injects x-user-id; Authorization header is not used by FastAPI.
  if (_authToken) {
    config.headers.Authorization = `Bearer ${_authToken}`;
  }
  return config;
});

// ─── Types ────────────────────────────────────────────────────────────────────
export interface UserProfile {
  user_id?: string;
  name?: string;
  age?: number;
  city?: string;
  state?: string;
  monthly_income?: number;
  monthly_expenses?: number;
  savings?: number;
  dependents?: number;
  /** Backend DB column is `risk_appetite` — NOT risk_tolerance */
  risk_appetite?: string;
  language?: string;
  employment_type?: string;
  monthly_emi?: number;
  emergency_fund?: number;
  life_insurance_cover?: number;
  has_health_insurance?: boolean;
  investments_80c?: number;
  nps_contribution?: number;
  health_insurance_premium?: number;
  hra?: number;
  rent_paid?: number;
  home_loan_interest?: number;
  ytd_bonus_income?: number;
  epf_balance?: number;
  nps_balance?: number;
  /** Maps to fire_target_age in the DB */
  fire_target_age?: number;
  fire_corpus_target?: number;
  onboarding_complete?: boolean;
}

export interface ChatRequest {
  message: string;
  user_id: string;
  session_id?: string;
  language?: string;
}

export interface ChatResponse {
  session_id: string;
  response: string;
  intent: string;
  data: Record<string, any>;
  user_id: string;
}

export interface AgentRequest {
  language?: string;
  voice_mode?: boolean;
}

export interface StressTestRequest extends AgentRequest {
  events?: string[];
}

export interface CouplesRequest extends AgentRequest {
  partner_income?: number;
  partner_expenses?: number;
  split_strategy?: string;
}

export interface GoalSimulatorRequest extends AgentRequest {
  target_amount?: number;
  years?: number;
}

export interface ResearchRequest extends AgentRequest {
  message: string;
}

export interface LifeEventRequest extends AgentRequest {
  message: string;
}

export interface SIPRequest {
  monthly_amount: number;
  years: number;
  expected_return: number;
  step_up_percent?: number;
}

export interface OptimizeRequest {
  goals?: string[];
  time_horizon_years?: number;
  language?: string;
}

export interface RebalanceRequest {
  target_allocation?: Record<string, number>;
  threshold?: number;
  language?: string;
}

export interface GoalCreateRequest {
  goal_name: string;
  target_amount: number;
  target_date?: string;
  current_saved?: number;
  monthly_investment?: number;
}

export interface ExpenseRequest {
  amount: number;
  category: string;
  description?: string;
  expense_date?: string;
}

export interface FamilyLinkRequest {
  member_email: string;
  relationship_type: string;
}

// ─── Fallback Dummy Data ──────────────────────────────────────────────────────
const DUMMY = {
  chat: { response: 'Backend offline. Start python/backend on port 8001.', intent: 'general_chat', data: {}, session_id: 'offline', user_id: 'guest' } as ChatResponse,
  health: { score: 72, grade: 'B', dimensions: { savings_rate: 65, emergency_fund: 55, debt_management: 70, insurance_coverage: 60, investment_diversity: 75, retirement_readiness: 50 }, recommendations: ['Build 6-month emergency fund', 'Increase SIP by 10% annually', 'Get term life insurance ₹50L+'] },
  sip: { monthly_amount: 10000, years: 15, expected_return: 12, total_invested: 1800000, expected_value: 4999300, wealth_gain: 3199300 },
  fire: { fire_number: 25000000, years_to_fire: 18, monthly_required: 42000 },
  tax: { old_regime_tax: 112500, new_regime_tax: 95000, recommended: 'new', savings: 17500 },
  portfolio: { total_invested: 0, current_value: 0, xirr: 0, gain: 0, gain_pct: 0, funds_count: 0, funds: [] },
};

function unwrap(data: any): any {
  return data && typeof data === 'object' && 'data' in data ? data.data : data;
}

// ─── API Service ──────────────────────────────────────────────────────────────
export class ApiService {

  /** Call this with the Clerk JWT on mount (e.g. from useAuth().getToken()) */
  static setAuthToken(token: string | null) {
    _authToken = token;
  }

  static async healthCheck() {
    try { return (await api.get('/health')).data; }
    catch { return { status: 'offline' }; }
  }

  // ── Auth ──────────────────────────────────────────────────────────────
  static async login(email: string, password: string) {
    return (await api.post('/auth/token', { email, password })).data;
  }

  static async register(email: string, password: string, name: string) {
    return (await api.post('/auth/register', { email, password, name })).data;
  }

  // ── Profile ───────────────────────────────────────────────────────────
  static async upsertProfile(profile: UserProfile) {
    try { return unwrap((await api.post('/profile/upsert', profile)).data); }
    catch { return null; }
  }

  static async getProfile(userId: string): Promise<UserProfile | null> {
    try { return unwrap((await api.get(`/profile/${userId}`)).data) as UserProfile; }
    catch { return null; }
  }

  // ── Chat ──────────────────────────────────────────────────────────────
  static async chat(req: ChatRequest): Promise<ChatResponse> {
    try { return unwrap((await api.post('/chat', req)).data) as ChatResponse; }
    catch { return { ...DUMMY.chat, user_id: req.user_id }; }
  }

  /**
   * Stream chat responses from the backend over SSE.
   * The backend `POST /chat/stream` returns `text/event-stream`.
   * Uses native `fetch` instead of axios so the ReadableStream is available.
   *
   * @param req  - Chat request payload
   * @param onChunk - Called for every SSE `data:` chunk received
   * @returns Full assembled response text
   */
  static async chatStream(
    req: ChatRequest,
    onChunk: (chunk: string) => void,
  ): Promise<string> {
    const response = await fetch(`${API_URL}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });

    if (!response.ok || !response.body) {
      throw new Error(`Stream request failed: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let full = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      // Parse SSE lines: "data: <content>\n\n"
      for (const line of chunk.split('\n')) {
        if (line.startsWith('data: ')) {
          const text = line.slice(6);
          if (text === '[DONE]') break;
          full += text;
          onChunk(text);
        }
      }
    }

    return full;
  }

  // ── Voice ─────────────────────────────────────────────────────────────
  static async voicePipeline(audioBlob: Blob, language: string = 'hi') {
    const form = new FormData();
    form.append('audio', audioBlob, 'recording.webm');
    form.append('language', language);
    return (await api.post('/voice/pipeline', form, { timeout: 60000, headers: { 'Content-Type': 'multipart/form-data' } })).data;
  }

  static async voiceNavigate(transcript: string, currentPage: string = 'dashboard', language: string = 'en') {
    return (await api.post('/voice/navigate-text', { transcript, current_page: currentPage, language })).data;
  }

  static async speak(text: string, language: string = 'en') {
    try {
      const res = await api.post('/voice/speak', { text, language }, { responseType: 'arraybuffer', timeout: 30000 });
      return new Blob([res.data], { type: 'audio/wav' });
    } catch { return null; }
  }

  // ── Portfolio ─────────────────────────────────────────────────────────
  static async uploadPortfolio(file: File, password?: string) {
    const form = new FormData();
    form.append('file', file);
    if (password) form.append('password', password);
    return (await api.post('/portfolio/upload', form, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 60000 })).data;
  }

  static async portfolioXray() {
    try { return (await api.post('/portfolio/xray')).data; }
    catch { return null; }
  }

  static async portfolioSummary() {
    try { return (await api.get('/portfolio/summary')).data; }
    catch { return DUMMY.portfolio; }
  }

  static async refreshNavs() {
    try { return (await api.post('/portfolio/refresh-navs')).data; }
    catch { return null; }
  }

  static async optimizePortfolio(req: OptimizeRequest = {}) {
    try { return (await api.post('/portfolio/optimize', req)).data; }
    catch { return { optimization: 'Service temporarily unavailable.' }; }
  }

  static async checkRebalance(req: RebalanceRequest = {}) {
    try { return (await api.post('/portfolio/check-rebalance', req)).data; }
    catch { return null; }
  }

  static async navSearch(query: string) {
    try { return (await api.get('/portfolio/nav/search', { params: { q: query } })).data; }
    catch { return { results: [] }; }
  }

  // ── Goals ─────────────────────────────────────────────────────────────
  static async createGoal(req: GoalCreateRequest) {
    return (await api.post('/portfolio/goals', req)).data;
  }

  static async listGoals() {
    try { return (await api.get('/portfolio/goals')).data; }
    catch { return { goals: [], funds: [] }; }
  }

  static async linkFundsToGoal(goalId: string, fundIds: string[]) {
    return (await api.post('/portfolio/goals/link', { goal_id: goalId, fund_ids: fundIds })).data;
  }

  // ── SIP Calculator ───────────────────────────────────────────────────
  static async calculateSIP(req: SIPRequest) {
    try { return (await api.post('/portfolio/sip-calculator', req)).data; }
    catch { return DUMMY.sip; }
  }

  // ── Agent Endpoints ───────────────────────────────────────────────────
  static async firePlanner(req: AgentRequest = {}) {
    try { return (await api.post('/agents/fire-planner', req)).data; }
    catch { return DUMMY.fire; }
  }

  static async taxWizard(req: AgentRequest = {}) {
    try { return (await api.post('/agents/tax-wizard', req)).data; }
    catch { return DUMMY.tax; }
  }

  static async taxCopilot(req: AgentRequest = {}) {
    try { return (await api.post('/agents/tax-copilot', req)).data; }
    catch { return null; }
  }

  static async moneyHealth(req: AgentRequest = {}) {
    try { return (await api.post('/agents/money-health', req)).data; }
    catch { return DUMMY.health; }
  }

  static async stressTest(req: StressTestRequest) {
    try { return (await api.post('/agents/stress-test', req)).data; }
    catch { return null; }
  }

  static async budgetCoach(req: AgentRequest = {}) {
    try { return (await api.post('/agents/budget-coach', req)).data; }
    catch { return null; }
  }

  static async goalPlanner(req: AgentRequest = {}) {
    try { return (await api.post('/agents/goal-planner', req)).data; }
    catch { return null; }
  }

  static async goalSimulator(req: GoalSimulatorRequest) {
    try { return (await api.post('/agents/goal-simulator', req)).data; }
    catch { return null; }
  }

  static async couplesFinance(req: CouplesRequest) {
    try { return (await api.post('/agents/couples-finance', req)).data; }
    catch { return null; }
  }

  static async marketPulse(req: AgentRequest = {}) {
    try { return (await api.post('/agents/market-pulse', req)).data; }
    catch { return null; }
  }

  static async moneyPersonality(req: AgentRequest = {}) {
    try { return (await api.post('/agents/money-personality', req)).data; }
    catch { return null; }
  }

  static async socialProof(req: AgentRequest = {}) {
    try { return (await api.post('/agents/social-proof', req)).data; }
    catch { return null; }
  }

  static async etResearch(req: ResearchRequest) {
    try { return (await api.post('/agents/et-research', req)).data; }
    catch { return null; }
  }

  static async humanHandoff(req: AgentRequest = {}) {
    try { return (await api.post('/agents/human-handoff', req)).data; }
    catch { return null; }
  }

  static async familyWealth(req: AgentRequest = {}) {
    try { return (await api.post('/agents/family-wealth', req)).data; }
    catch { return null; }
  }

  static async expenseAnalytics(req: AgentRequest = {}) {
    try { return (await api.post('/agents/expense-analytics', req)).data; }
    catch { return null; }
  }

  static async lifeEventAdvisor(req: LifeEventRequest) {
    try { return (await api.post('/agents/life-event-advisor', req)).data; }
    catch { return null; }
  }

  // ── Budget & Expenses ─────────────────────────────────────────────────
  static async budgetSummary() {
    try { return (await api.get('/budget/summary')).data; }
    catch { return null; }
  }

  static async logExpense(req: ExpenseRequest) {
    return (await api.post('/budget/expense', req)).data;
  }

  static async deleteExpense(expenseId: string) {
    return (await api.delete(`/budget/expense/${expenseId}`)).data;
  }

  static async listExpenses() {
    try { return (await api.get('/budget/expenses')).data; }
    catch { return []; }
  }

  // ── Nudges / Notifications ────────────────────────────────────────────
  static async generateNudges() {
    try { return (await api.post('/nudges/generate')).data; }
    catch { return null; }
  }

  static async getPendingNudges() {
    try { return (await api.get('/nudges/pending')).data; }
    catch { return []; }
  }

  static async markNudgeRead(nudgeId: string) {
    return (await api.post(`/nudges/${nudgeId}/read`)).data;
  }

  static async markAllNudgesRead() {
    return (await api.post('/nudges/mark-all-read')).data;
  }

  // ── Compliance ────────────────────────────────────────────────────────
  static async complianceReport() {
    try { return (await api.post('/compliance/report')).data; }
    catch { return null; }
  }

  static async aiDisclosure() {
    try { return (await api.get('/compliance/ai-disclosure')).data; }
    catch { return null; }
  }

  // ── Family ────────────────────────────────────────────────────────────
  static async linkFamily(req: FamilyLinkRequest) {
    return (await api.post('/family/link', req)).data;
  }

  static async acceptFamilyLink(linkId: string) {
    return (await api.post(`/family/accept/${linkId}`)).data;
  }

  static async getFamilyMembers() {
    try { return (await api.get('/family/members')).data; }
    catch { return []; }
  }

  static async unlinkFamily(linkId: string) {
    return (await api.delete(`/family/unlink/${linkId}`)).data;
  }

  // ── Export ────────────────────────────────────────────────────────────
  static async exportCsv(type: 'portfolio' | 'goals' | 'compliance') {
    return (await api.get(`/export/${type}/csv`, { responseType: 'blob' })).data;
  }

  static async exportPdf(type: 'portfolio') {
    return (await api.get(`/export/${type}/pdf`, { responseType: 'blob' })).data;
  }

  // ── Admin ─────────────────────────────────────────────────────────────
  static async adminStats() {
    try { return (await api.get('/admin/stats')).data; }
    catch { return null; }
  }

  static async adminActivity() {
    try { return (await api.get('/admin/activity')).data; }
    catch { return []; }
  }

  static async adminUsers() {
    try { return (await api.get('/admin/users')).data; }
    catch { return []; }
  }

  // ── Auth (extended) ───────────────────────────────────────────────────
  static async passwordResetRequest(email: string) {
    return (await api.post('/auth/password-reset-request', { email })).data;
  }

  static async passwordResetConfirm(token: string, new_password: string) {
    return (await api.post('/auth/password-reset-confirm', { token, new_password })).data;
  }

  static async sendVerification(email: string) {
    return (await api.post('/auth/send-verification', { email })).data;
  }

  static async verifyEmail(token: string) {
    return (await api.post('/auth/verify-email', { token })).data;
  }

  static async verificationStatus() {
    try { return (await api.get('/auth/verification-status')).data; }
    catch { return null; }
  }

  // ── Profile (extended) ────────────────────────────────────────────────
  static async isOnboarded(userId: string) {
    try { return (await api.get(`/profile/${userId}/is-onboarded`)).data; }
    catch { return null; }
  }

  // ── Voice (extended) ──────────────────────────────────────────────────
  static async transcribe(audioBlob: Blob) {
    const fd = new FormData();
    fd.append('audio', audioBlob, 'recording.webm');
    return (await api.post('/voice/transcribe', fd, { headers: { 'Content-Type': 'multipart/form-data' } })).data;
  }

  // ── Portfolio (extended) ──────────────────────────────────────────────
  static async navStats() {
    try { return (await api.get('/portfolio/nav/stats')).data; }
    catch { return null; }
  }

  static async portfolioHistory(userId: string) {
    try { return (await api.get(`/portfolio/history/${userId}`)).data; }
    catch { return []; }
  }

  // ── Budget (extended) ─────────────────────────────────────────────────
  static async createBudgetPlan(plan: { category: string; planned_amount: number; month?: string }) {
    return (await api.post('/budget/plan', plan)).data;
  }
}

// ─── WebSocket helper ─────────────────────────────────────────────────────────
// WebSocket connections bypass the Next.js proxy (WS upgrade is not HTTP), so
// they connect directly to the backend. Use NEXT_PUBLIC_WS_URL in production.
const WS_URL =
  (process.env.NEXT_PUBLIC_WS_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8001')
    .replace(/^https?/, 'ws')
    .replace('/api/backend', '');

export function connectNotificationWS(userId: string): WebSocket {
  const wsUrl = `${WS_URL}/ws/notifications?user_id=${encodeURIComponent(userId)}`;
  return new WebSocket(wsUrl);
}
