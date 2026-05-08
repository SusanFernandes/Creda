'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { KeyRound, Eye, EyeOff, CheckCircle, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useTheme } from '@/contexts/ThemeContext';

export default function ResetPasswordPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const { currentTheme, setTheme } = useTheme();

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setErrorMsg('Passwords do not match.');
      return;
    }
    if (password.length < 8) {
      setErrorMsg('Password must be at least 8 characters.');
      return;
    }
    setStatus('loading');
    setErrorMsg('');
    try {
      // In production: await ApiService.resetPassword({ token, password })
      await new Promise((r) => setTimeout(r, 1200));
      setStatus('success');
      setTimeout(() => router.push('/auth/sign-in'), 2500);
    } catch {
      setStatus('error');
      setErrorMsg('Could not reset password. The link may be expired. Please request a new one.');
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
          <button
            onClick={() => setTheme(currentTheme === 'dark' ? 'light' : 'dark')}
            aria-label="Toggle theme"
            className="w-9 h-9 rounded-xl border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-500 hover:text-slate-900 dark:hover:text-white transition"
          >
            {currentTheme === 'dark' ? '☀️' : '🌙'}
          </button>
        </div>
      </nav>

      <div className="absolute top-1/3 left-1/4 w-[300px] h-[300px] bg-blue-50/60 dark:bg-blue-900/10 rounded-full blur-[100px] pointer-events-none" aria-hidden />

      <div className="min-h-screen pt-16 flex items-center justify-center px-6 py-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="relative z-10 w-full max-w-sm"
        >
          {status === 'success' ? (
            <div className="text-center">
              <div className="w-14 h-14 rounded-2xl bg-emerald-50 dark:bg-emerald-900/20 flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-7 h-7 text-emerald-500" />
              </div>
              <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50 mb-2">Password reset!</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
                Your password has been updated successfully. Redirecting you to sign in…
              </p>
              <Button asChild className="w-full">
                <Link href="/auth/sign-in">Go to Sign In</Link>
              </Button>
            </div>
          ) : (
            <>
              <div className="text-center mb-8">
                <div className="w-14 h-14 rounded-2xl bg-blue-600 flex items-center justify-center mx-auto mb-4">
                  <KeyRound className="w-7 h-7 text-white" />
                </div>
                <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-50">Set new password</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Choose a strong password for your account</p>
              </div>

              {errorMsg && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/50 text-red-600 dark:text-red-400 px-4 py-3 rounded-xl mb-5 text-sm flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {errorMsg}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <Label htmlFor="password" className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2 block">
                    New password
                  </Label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      required
                      autoFocus
                      placeholder="Min. 8 characters"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="h-12 rounded-xl border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div>
                  <Label htmlFor="confirm" className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2 block">
                    Confirm password
                  </Label>
                  <div className="relative">
                    <Input
                      id="confirm"
                      type={showConfirm ? 'text' : 'password'}
                      required
                      placeholder="Repeat your password"
                      value={confirm}
                      onChange={(e) => setConfirm(e.target.value)}
                      className="h-12 rounded-xl border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirm(!showConfirm)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                      aria-label={showConfirm ? 'Hide password' : 'Show password'}
                    >
                      {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={status === 'loading'}
                  className="w-full h-12 rounded-xl bg-blue-600 hover:bg-blue-700 font-bold text-sm"
                >
                  {status === 'loading' ? 'Resetting…' : 'Reset Password'}
                </Button>
              </form>

              <div className="mt-6 text-center">
                <Link href="/auth/forgot-password" className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 font-semibold">
                  Request a new link
                </Link>
              </div>
            </>
          )}
        </motion.div>
      </div>
    </div>
  );
}

