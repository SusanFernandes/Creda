import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Providers from './providers';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export const metadata: Metadata = {
  title: {
    default: 'CREDA — AI-Powered Financial Intelligence',
    template: '%s | CREDA',
  },
  description:
    'AI-powered portfolio analysis, tax optimization, and multilingual voice assistance — designed for the Indian investor. SEBI-compliant. Bank-grade security.',
  keywords: [
    'financial planning India',
    'AI financial advisor',
    'portfolio analysis',
    'tax optimization India',
    'SEBI compliant',
    'multilingual voice assistant',
    'mutual fund analysis',
    'FIRE planner India',
  ],
  authors: [{ name: 'CREDA' }],
  openGraph: {
    title: 'CREDA — AI-Powered Financial Intelligence',
    description:
      'Smarter money decisions for the Indian investor. 22 AI agents, 11 languages, SEBI-compliant.',
    type: 'website',
    locale: 'en_IN',
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.variable}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
