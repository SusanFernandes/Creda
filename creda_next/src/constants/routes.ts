export const ROUTES = {
  // Public
  HOME: '/',
  SIGN_IN: '/auth/sign-in',
  SIGN_UP: '/auth/sign-up',
  FORGOT_PASSWORD: '/auth/forgot-password',
  RESET_PASSWORD: '/auth/reset-password',
  ONBOARDING: '/onboarding',

  // Dashboard
  DASHBOARD: '/dashboard',
  CHAT: '/chat',
  PORTFOLIO: '/portfolio',
  BUDGET: '/budget',
  EXPENSES: '/expense-analytics',
  GOALS: '/goals',
  HEALTH: '/health',

  // Planning
  FIRE_PLANNER: '/fire-planner',
  SIP_CALCULATOR: '/sip-calculator',
  TAX_WIZARD: '/tax-wizard',
  COUPLES_PLANNER: '/couples-planner',
  STRESS_TEST: '/stress-test',
  MARKET_PULSE: '/market-pulse',
  PERSONALITY: '/personality',
  SOCIAL_PROOF: '/social-proof',
  LIFE_EVENTS: '/life-events',

  // Tools
  VOICE: '/voice',
  RESEARCH: '/research',
  ADVISORY: '/advisory',
  KNOWLEDGE: '/knowledge',
  REPORT_CARD: '/report-card',
  FAMILY: '/family',
  COMPLIANCE: '/compliance',
  NOTIFICATIONS: '/notifications',

  // Settings
  SETTINGS: '/settings',
  SECURITY: '/security',
  ADMIN: '/admin',
  HELP: '/help',
} as const;

export type Route = (typeof ROUTES)[keyof typeof ROUTES];
