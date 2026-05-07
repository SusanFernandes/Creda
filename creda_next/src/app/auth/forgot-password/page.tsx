'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { Mail, ArrowLeft, CheckCircle, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useTheme } from '@/contexts/ThemeContext';

export default function ForgotPasswordPage() {
  const { currentTheme, setTheme } = useTheme();
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email) return;
    setStatus('loading');
    setErrorMsg('');
    try {
      // In production, call your API: await ApiService.forgotPassword(email)
      await new Promise((r) => setTimeout(r, 1200)); // simulate
      setStatus('success');
    } catch {
      setStatus('error');
      setErrorMsg('Failed to send reset link. Please try again.');
    }
  }

  return (
    <div className="min-h-screen bg-white dark:bg-slate-950 transition-colors duration-300">
      {/* Navbar */}
      <nav className="fixed top-0 inset-x-0 z-50 border-b border-slate-200/50 dark:border-slate-800/50 bg-white/80 dark:bg-slate-950/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center">
              <span className="text-white font-black text-lg">C</span>
            </div>
            <span className="text-xl font-black italic tracking-tight text-slate-900 dark:text-slate-50">CREDA</span>
          </Link>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setTheme(currentTheme === 'dark' ? 'light' : 'dark')}
              aria-label="Toggle theme"
              className="w-9 h-9 rounded-xl border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-500 hover:text-slate-900 dark:hover:text-white transition"
            >
              {currentTheme === 'dark' ? '☀️' : '🌙'}
            </button>
            <Button size="sm" asChild>
              <Link href="/auth/sign-in">Sign In</Link>
            </Button>
          </div>
        </div>
      </nav>

      {/* Background glow */}
      <div className="absolute top-1/3 right-1/4 w-[300px] h-[300px] bg-blue-50/60 dark:bg-blue-900/10 rounded-full blur-[100px] pointer-events-none" aria-hidden />

      {/* Main content */}
      <div className="min-h-screen pt-16 flex items-center justify-center px-6 py-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="relative z-10 w-full max-w-sm"
        >
          {status === 'success' ? (
            /* Success state */
            <div className="text-center">
              <div className="w-14 h-14 rounded-2xl bg-emerald-50 dark:bg-emerald-900/20 flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-7 h-7 text-emerald-500" />
              </div>
              <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50 mb-2">Check your email</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-8">
                We sent a password reset link to <strong className="text-slate-700 dark:text-slate-300">{email}</strong>.
                Check your inbox and follow the instructions.
              </p>
              <p className="text-xs text-slate-400 mb-6">
                {"Didn't receive the email? Check your spam folder or "}
                <button
                  onClick={() => setStatus('idle')}
                  className="text-blue-600 hover:text-blue-700 font-semibold underline"
                >
                  try again
                </button>
                .
              </p>
              <Button variant="outline" asChild className="w-full">
                <Link href="/auth/sign-in" className="flex items-center justify-center gap-2">
                  <ArrowLeft className="w-4 h-4" />
                  Back to Sign In
                </Link>
              </Button>
            </div>
          ) : (
            /* Form state */
            <>
              <div className="text-center mb-8">
                <div className="w-14 h-14 rounded-2xl bg-blue-600 flex items-center justify-center mx-auto mb-4">
                  <Mail className="w-7 h-7 text-white" />
                </div>
                <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50">Reset your password</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Enter your email to receive a reset link</p>
              </div>

              {errorMsg && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/50 text-red-600 dark:text-red-400 px-4 py-3 rounded-xl mb-5 text-sm flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {errorMsg}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <Label htmlFor="email" className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2 block">
                    Email address
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    required
                    autoFocus
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="h-12 rounded-xl border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900"
                  />
                </div>
                <Button
                  type="submit"
                  disabled={status === 'loading'}
                  className="w-full h-12 rounded-xl bg-blue-600 hover:bg-blue-700 font-bold text-sm"
                >
                  {status === 'loading' ? 'Sending…' : 'Send Reset Link'}
                </Button>
              </form>

              <div className="mt-8 pt-6 border-t border-slate-100 dark:border-slate-800">
                <p className="text-center text-sm text-slate-500 dark:text-slate-400">
                  {"Remember your password? "}
                  <Link href="/auth/sign-in" className="text-blue-600 hover:text-blue-700 dark:text-blue-400 font-semibold">
                    Sign in
                  </Link>
                </p>
              </div>
            </>
          )}
        </motion.div>
      </div>
    </div>
  );
}

