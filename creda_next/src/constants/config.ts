export const APP_CONFIG = {
  name: 'CREDA',
  tagline: 'AI-Powered Financial Intelligence for India',
  description:
    'AI-powered portfolio analysis, tax optimization, and multilingual voice assistance — designed for the Indian investor.',
  url: process.env.NEXT_PUBLIC_APP_URL ?? 'https://creda.finance',
  supportedLanguages: [
    'English',
    'Hindi',
    'Tamil',
    'Telugu',
    'Bengali',
    'Marathi',
    'Gujarati',
    'Kannada',
    'Malayalam',
    'Punjabi',
    'Urdu',
  ],
  stats: {
    aiAgents: 22,
    languages: 11,
    knowledgeDocs: 26,
  },
} as const;

export const API_CONFIG = {
  baseUrl: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8001',
  timeout: 30_000,
} as const;
