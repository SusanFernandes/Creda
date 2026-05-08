'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { SignIn, SignUp } from '@clerk/nextjs';
import Link from 'next/link';
import { Shield, Zap, Globe, TrendingUp, CheckCircle } from 'lucide-react';

interface AuthProps {
  mode: 'sign-in' | 'sign-up';
}

const features = [
  { icon: Shield, title: 'Bank-Grade Security', desc: 'AES-256 encryption, fully self-hosted' },
  { icon: Zap, title: 'AI-Powered Insights', desc: '22 specialized financial AI agents' },
  { icon: Globe, title: '11 Indian Languages', desc: 'Voice and text in your native language' },
  { icon: TrendingUp, title: 'Smart Optimization', desc: 'Portfolio, tax, and budget automation' },
];

const AuthPage: React.FC<AuthProps> = ({ mode }) => {
  return (
    <div className="min-h-screen bg-white dark:bg-slate-950 flex">
      {/* Left panel */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 bg-slate-900 dark:bg-slate-950 relative overflow-hidden">
        {/* Glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] bg-blue-600/10 rounded-full blur-[120px]" aria-hidden />

        {/* Logo */}
        <Link href="/" className="flex items-center gap-3 relative z-10">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center">
            <span className="text-white font-black text-xl">C</span>
          </div>
          <span className="text-2xl font-black italic tracking-tight text-white">CREDA</span>
        </Link>

        {/* Content */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
          className="relative z-10 space-y-8"
        >
          <div>
            <h2 className="text-4xl font-bold text-white tracking-tight mb-4 leading-tight">
              Smarter Money<br /><span className="text-blue-400">Decisions.</span>
            </h2>
            <p className="text-slate-400 text-lg">
              AI-powered financial intelligence built for the Indian investor.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {features.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + i * 0.1 }}
                className="bg-white/5 border border-white/10 rounded-2xl p-4 backdrop-blur-sm"
              >
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-xl bg-blue-600/20 flex items-center justify-center text-blue-400 flex-shrink-0">
                    <f.icon className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white mb-0.5">{f.title}</p>
                    <p className="text-xs text-slate-400">{f.desc}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          <div className="flex flex-wrap gap-4 text-[11px] font-bold uppercase tracking-widest text-slate-500">
            {['SEBI Compliant', 'AES-256 Encrypted', 'Self-Hosted'].map((tag) => (
              <span key={tag} className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                {tag}
              </span>
            ))}
          </div>
        </motion.div>

        {/* Footer quote */}
        <div className="relative z-10">
          <p className="text-slate-500 text-xs italic">
            "I asked about my SIP overlap in Hindi and got a clear, actionable breakdown." — Rahul S., Bengaluru
          </p>
        </div>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 bg-white dark:bg-slate-950">
        {/* Mobile logo */}
        <Link href="/" className="flex items-center gap-2 mb-8 lg:hidden">
          <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center">
            <span className="text-white font-black text-lg">C</span>
          </div>
          <span className="text-xl font-black italic tracking-tight text-slate-900 dark:text-slate-50">CREDA</span>
        </Link>

        <motion.div
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="w-full max-w-md"
        >
          <div className="mb-6 text-center">
            <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50 mb-1">
              {mode === 'sign-in' ? 'Welcome back' : 'Create your account'}
            </h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {mode === 'sign-in'
                ? 'Sign in to access your financial dashboard'
                : 'Start your financial journey with CREDA for free'}
            </p>
          </div>

          {mode === 'sign-in' ? (
            <SignIn
              appearance={{
                elements: {
                  rootBox: 'w-full',
                  card: 'bg-transparent shadow-none border-none p-0',
                  headerTitle: 'hidden',
                  headerSubtitle: 'hidden',
                  socialButtonsBlockButton:
                    'border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-xl h-11',
                  formButtonPrimary:
                    'bg-blue-600 hover:bg-blue-700 rounded-xl h-12 font-bold text-sm',
                  footerActionLink: 'text-blue-600 hover:text-blue-700',
                  formFieldInput:
                    'rounded-xl border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 h-11',
                },
              }}
              signUpUrl="/auth/sign-up"
              fallbackRedirectUrl="/dashboard"
            />
          ) : (
            <SignUp
              appearance={{
                elements: {
                  rootBox: 'w-full',
                  card: 'bg-transparent shadow-none border-none p-0',
                  headerTitle: 'hidden',
                  headerSubtitle: 'hidden',
                  socialButtonsBlockButton:
                    'border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-xl h-11',
                  formButtonPrimary:
                    'bg-blue-600 hover:bg-blue-700 rounded-xl h-12 font-bold text-sm',
                  footerActionLink: 'text-blue-600 hover:text-blue-700',
                  formFieldInput:
                    'rounded-xl border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 h-11',
                },
              }}
              signInUrl="/auth/sign-in"
              fallbackRedirectUrl="/dashboard"
            />
          )}

          <div className="mt-6 text-center">
            <Link
              href="/auth/forgot-password"
              className="text-sm text-slate-500 hover:text-blue-600 dark:hover:text-blue-400 transition"
            >
              Forgot your password?
            </Link>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default AuthPage;
