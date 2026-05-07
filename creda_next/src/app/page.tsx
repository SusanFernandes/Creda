import type { Metadata } from 'next';
import LandingPageClient from '@/components/landing/LandingPageClient';

export const metadata: Metadata = {
  title: 'CREDA — AI-Powered Financial Intelligence for India',
  description:
    'AI-powered portfolio analysis, tax optimization, and multilingual voice assistance — designed for the Indian investor. 22 AI agents, 11 languages, SEBI-compliant.',
  openGraph: {
    title: 'CREDA — Smarter Money Decisions',
    description:
      'AI-powered financial intelligence for the Indian investor. Portfolio X-Ray, Tax Copilot, FIRE Planner, and multilingual voice assistance.',
    images: ['/og-landing.png'],
  },
};

export default function LandingPage() {
  return <LandingPageClient />;
}
