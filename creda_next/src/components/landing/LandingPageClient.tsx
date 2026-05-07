'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import {
  ArrowRight,
  CheckCircle,
  BarChart4,
  Shield,
  Mic,
  Receipt,
  Target,
  Users,
  ChevronDown,
  Star,
  Lock,
  Server,
  TrendingUp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import LandingNavbar from '@/components/layout/LandingNavbar';
import LandingFooter from '@/components/layout/LandingFooter';

const features = [
  {
    icon: BarChart4,
    title: 'Portfolio X-Ray',
    description:
      'Upload your CAS statement and get a complete breakdown — asset allocation, overlap analysis, fund ratings, and rebalancing suggestions.',
    tag: 'MF + Stocks + FDs',
  },
  {
    icon: Mic,
    title: 'Voice in Your Language',
    description:
      'Ask about your investments in Hindi, Tamil, Bengali, or any of 11 Indian languages. CREDA understands context, not just words.',
    tag: '11 Languages',
  },
  {
    icon: Shield,
    title: 'SEBI-Compliant Advice',
    description:
      'Every recommendation is logged and cross-referenced with SEBI/RBI guidelines. Full audit trail for regulatory compliance.',
    tag: '100% Auditable',
  },
  {
    icon: Receipt,
    title: 'Tax Copilot',
    description:
      'Old vs. new regime comparison, advance tax reminders, salary restructuring — maximize your post-tax returns.',
    tag: 'Section 80C to 80U',
  },
  {
    icon: Target,
    title: 'Goal Planning',
    description:
      'Retirement, education, first home — set goals, track progress, get drift alerts and course corrections.',
    tag: 'FIRE + Goals',
  },
  {
    icon: Users,
    title: 'Family Wealth',
    description:
      'Consolidated family dashboard — track your spouse, parents, and children portfolios in one place.',
    tag: 'Multi-Member',
  },
];

const stats = [
  { value: '22', label: 'AI Agents' },
  { value: '11', label: 'Indian Languages' },
  { value: '26', label: 'Knowledge Documents' },
  { value: '100%', label: 'Self-Hosted & Private', accent: true },
];

const testimonials = [
  {
    quote:
      '"I asked about my SIP overlap in Hindi and got a clear, actionable breakdown. No other tool does this. The portfolio X-ray alone saved me from paying high expense ratios."',
    name: 'Rahul S.',
    role: 'Software Engineer, Bengaluru',
    initials: 'RS',
    color: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600',
  },
  {
    quote:
      '"The tax copilot showed me I would save Rs 48,000 by switching to the new regime. I love the proactive SIP reminders — never missed one since I started using CREDA."',
    name: 'Priya P.',
    role: 'Business Owner, Mumbai',
    initials: 'PP',
    color: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600',
  },
  {
    quote:
      '"My parents do not speak English. CREDA lets them ask about their PPF and SCSS in Tamil. The family wealth dashboard shows everything in one place. Truly built for India."',
    name: 'Arjun K.',
    role: 'Product Manager, Chennai',
    initials: 'AK',
    color: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600',
  },
];

const faqs = [
  {
    q: 'Is my financial data safe?',
    a: 'CREDA is fully self-hosted — your data never leaves your infrastructure. All data is encrypted with AES-256 at rest and in transit. We do not sell, share, or access your financial information.',
  },
  {
    q: 'Which languages are supported?',
    a: 'CREDA supports 11 Indian languages: English, Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, and Urdu. Both text and voice interfaces work in all supported languages.',
  },
  {
    q: 'How do I upload my portfolio?',
    a: 'Download your Consolidated Account Statement (CAS) from CAMS or KFintech, then upload the PDF in the Portfolio section. CREDA parses it automatically and gives you a complete fund-by-fund breakdown.',
  },
  {
    q: 'Is CREDA SEBI-registered?',
    a: 'CREDA is an AI-powered financial coaching tool, not a registered investment advisor. All recommendations are educational and informational. Every AI output is tagged with a compliance disclaimer and logged for audit purposes per SEBI guidelines.',
  },
  {
    q: 'Can I use it on mobile?',
    a: 'Yes. The web dashboard is fully responsive and works on any device. There is also a React Native mobile app and WhatsApp integration via Twilio for on-the-go access.',
  },
];

function FaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-100 dark:border-slate-800 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-6 py-5 text-left"
        aria-expanded={open}
      >
        <span className="text-sm font-semibold text-slate-900 dark:text-slate-50 pr-4">{q}</span>
        <ChevronDown className={`w-5 h-5 text-slate-400 flex-shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <p className="px-6 pb-5 text-sm text-slate-500 dark:text-slate-400 leading-relaxed">{a}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Stars() {
  return (
    <div className="flex items-center gap-0.5" aria-label="5 out of 5 stars">
      {Array.from({ length: 5 }).map((_, i) => (
        <Star key={i} className="w-4 h-4 text-amber-400 fill-amber-400" />
      ))}
    </div>
  );
}

export default function LandingPageClient() {
  return (
    <div className="min-h-screen bg-white dark:bg-slate-950 font-sans transition-colors duration-300">
      <LandingNavbar />

      {/* Hero */}
      <section className="relative min-h-[90vh] flex items-center justify-center pt-24 pb-20 px-6 overflow-hidden">
        <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
          <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-blue-100/50 dark:bg-blue-900/10 rounded-full blur-[140px]" />
          <div className="absolute bottom-1/4 right-1/3 w-[400px] h-[400px] bg-slate-100 dark:bg-slate-800/10 rounded-full blur-[120px]" />
        </div>
        <div className="relative z-10 max-w-5xl mx-auto text-center">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <Badge variant="outline" className="mb-10 px-5 py-2.5 rounded-full border-slate-200 dark:border-slate-800 font-bold uppercase tracking-[0.2em] text-[10px] bg-white/50 dark:bg-slate-900/50 backdrop-blur-xl">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse mr-2 inline-block" />
              Trusted by investors across India
            </Badge>
            <h1 className="text-5xl md:text-8xl font-bold tracking-tight text-slate-900 dark:text-slate-50 mb-8 leading-[0.95]">
              Smarter Money<br /><span className="text-blue-600">Decisions.</span>
            </h1>
            <p className="text-lg md:text-xl text-slate-500 dark:text-slate-400 max-w-2xl mx-auto leading-relaxed mb-14 font-medium">
              AI-powered portfolio analysis, tax optimization, and multilingual voice assistance designed for the Indian investor.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Button size="lg" className="h-14 px-10 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm shadow-lg shadow-blue-600/20 hover:scale-[1.02] transition-all" asChild>
                <Link href="/auth/sign-up" className="flex items-center gap-3">Start Free<ArrowRight className="w-4 h-4" /></Link>
              </Button>
              <Button size="lg" variant="outline" className="h-14 px-10 rounded-2xl border-slate-200 dark:border-slate-800 font-bold text-sm" asChild>
                <Link href="#features">See How It Works</Link>
              </Button>
            </div>
            <div className="mt-16 flex flex-wrap items-center justify-center gap-8 md:gap-12 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400">
              {['SEBI Compliant', 'Bank-Grade Encryption', '11+ Indian Languages'].map((item) => (
                <span key={item} className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-500" />{item}
                </span>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-24 md:py-32 bg-slate-50/50 dark:bg-slate-900/30 px-6 border-y border-slate-100 dark:border-slate-800/50">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 lg:gap-24 items-center">
            <motion.div initial={{ opacity: 0, x: -30 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ duration: 0.6 }}>
              <div className="inline-block mb-6 px-4 py-1.5 rounded-full bg-blue-600 text-white text-[10px] font-bold uppercase tracking-widest">How It Works</div>
              <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-slate-50 mb-12 leading-tight">Your wealth,<br />managed intelligently.</h2>
              <div className="space-y-12">
                {[
                  { label: 'Portfolio Analysis', value: '22+ Agents', desc: 'AI agents analyze your mutual funds, stocks, and fixed deposits using research-grade models.' },
                  { label: 'Voice Assistant', value: '11 Languages', desc: 'Talk to CREDA in Hindi, Tamil, Bengali, Kannada, or any of 11 Indian languages.' },
                  { label: 'Tax Optimization', value: 'Regime-Smart', desc: 'Old vs. new regime comparison, advance tax reminders, and salary restructuring suggestions.' },
                ].map((item) => (
                  <div key={item.label} className="group border-l-2 border-slate-200 dark:border-slate-800 pl-8 hover:border-blue-600 transition-colors">
                    <div className="flex justify-between items-baseline mb-2">
                      <span className="text-sm font-bold uppercase tracking-widest text-slate-400">{item.label}</span>
                      <span className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">{item.value}</span>
                    </div>
                    <p className="text-slate-500 text-sm">{item.desc}</p>
                  </div>
                ))}
              </div>
            </motion.div>
            <motion.div initial={{ opacity: 0, scale: 0.98 }} whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true }} transition={{ duration: 0.6 }} className="relative">
              <div className="bg-white dark:bg-slate-900 shadow-2xl rounded-3xl overflow-hidden border border-slate-100 dark:border-slate-800">
                <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-slate-900 dark:bg-slate-50 flex items-center justify-center">
                      <TrendingUp className="w-5 h-5 text-white dark:text-slate-900" />
                    </div>
                    <span className="text-xs font-bold uppercase tracking-widest text-slate-500">Portfolio Dashboard</span>
                  </div>
                  <span className="inline-flex items-center gap-1.5 text-[10px] font-bold text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20 px-3 py-1 rounded-full border border-emerald-200 dark:border-emerald-800">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />Live
                  </span>
                </div>
                <div className="p-6 space-y-5">
                  <div className="space-y-2">
                    <div className="flex justify-between text-[11px] font-bold uppercase tracking-widest text-slate-400">
                      <span>Portfolio Health Score</span><span>82%</span>
                    </div>
                    <Progress value={82} className="h-2" />
                  </div>
                  <div className="space-y-3 pt-2">
                    {[
                      { color: 'bg-emerald-500', text: 'Equity allocation optimized' },
                      { color: 'bg-blue-500', text: 'Tax-loss harvesting opportunity' },
                      { color: 'bg-amber-500', text: 'SIP review recommended' },
                    ].map((item) => (
                      <div key={item.text} className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800/50 rounded-2xl border border-slate-100 dark:border-slate-800">
                        <div className="flex items-center gap-3">
                          <div className={`w-2 h-2 rounded-full ${item.color}`} />
                          <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">{item.text}</span>
                        </div>
                        <ArrowRight className="w-4 h-4 text-slate-300" />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 md:py-32 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
              <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-slate-50 mb-4">
                Everything you need to<br /><span className="text-blue-600">grow your wealth.</span>
              </h2>
              <p className="text-slate-500 text-lg max-w-2xl mx-auto">22 specialized AI agents working together to give you institutional-grade financial insights.</p>
            </motion.div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, i) => (
              <motion.div key={feature.title} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.08 }}
                className="group bg-white dark:bg-slate-900 p-8 rounded-3xl border border-slate-100 dark:border-slate-800 hover:shadow-xl hover:border-blue-100 dark:hover:border-blue-900/30 transition-all duration-300">
                <div className="w-12 h-12 rounded-2xl bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center text-blue-600 mb-6 group-hover:bg-blue-600 group-hover:text-white transition-all duration-300">
                  <feature.icon className="w-5 h-5" />
                </div>
                <h3 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-50 mb-3">{feature.title}</h3>
                <p className="text-slate-500 leading-relaxed mb-6 text-sm">{feature.description}</p>
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 border border-slate-200 dark:border-slate-700 px-3 py-1 rounded-full">{feature.tag}</span>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Security */}
      <section id="security" className="py-24 md:py-32 px-6 bg-slate-900 dark:bg-slate-950 text-white relative overflow-hidden">
        <div className="absolute inset-0 bg-blue-500/5 blur-[150px]" aria-hidden="true" />
        <div className="max-w-4xl mx-auto relative z-10 text-center">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
            <div className="inline-block mb-6 px-4 py-1.5 rounded-full bg-white/10 text-white border border-white/20 text-[10px] font-bold uppercase tracking-widest backdrop-blur-xl">Security &amp; Compliance</div>
            <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-6">Your data stays<br /><span className="text-blue-400">yours.</span></h2>
            <p className="text-slate-400 text-lg max-w-2xl mx-auto mb-16">We do not sell your data. We do not share it. Everything runs locally on your infrastructure.</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                { icon: Lock, title: 'AES-256 Encrypted', desc: 'All data encrypted at rest and in transit with bank-grade encryption.' },
                { icon: Shield, title: 'SEBI / RBI Aligned', desc: 'Complete audit trail. Every recommendation logged with regulatory references.' },
                { icon: Server, title: 'Self-Hosted', desc: 'Run on your own servers. Your financial data never leaves your infrastructure.' },
              ].map((item) => (
                <div key={item.title} className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-xl text-center">
                  <div className="w-10 h-10 rounded-xl bg-blue-600/20 flex items-center justify-center text-blue-400 mb-4 mx-auto">
                    <item.icon className="w-5 h-5" />
                  </div>
                  <h3 className="font-bold mb-2">{item.title}</h3>
                  <p className="text-slate-400 text-sm">{item.desc}</p>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-20 px-6 bg-white dark:bg-slate-950 border-y border-slate-100 dark:border-slate-800/50">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12">
            {stats.map((s, i) => (
              <motion.div key={s.label} initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }} className="text-center">
                <div className={`text-4xl md:text-5xl font-bold tracking-tight mb-2 ${s.accent ? 'text-blue-600' : 'text-slate-900 dark:text-slate-50'}`}>{s.value}</div>
                <p className="text-sm font-medium text-slate-500">{s.label}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-24 md:py-32 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
              <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-slate-50 mb-4">What users <span className="text-blue-600">are saying.</span></h2>
              <p className="text-slate-500 text-lg max-w-2xl mx-auto">Built for Indian investors, loved by people who want clarity on their money.</p>
            </motion.div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {testimonials.map((t, i) => (
              <motion.div key={t.name} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }}
                className="bg-white dark:bg-slate-900 p-8 rounded-3xl border border-slate-100 dark:border-slate-800">
                <Stars />
                <p className="text-slate-600 dark:text-slate-300 text-sm leading-relaxed my-5">{t.quote}</p>
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm ${t.color}`}>{t.initials}</div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-50">{t.name}</p>
                    <p className="text-xs text-slate-400">{t.role}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-24 md:py-32 px-6 bg-slate-50/50 dark:bg-slate-900/30 border-y border-slate-100 dark:border-slate-800/50">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-slate-50 mb-4">Frequently asked <span className="text-blue-600">questions.</span></h2>
          </div>
          <div className="space-y-3">
            {faqs.map((faq) => (<FaqItem key={faq.q} q={faq.q} a={faq.a} />))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 md:py-32 px-6 text-center">
        <div className="max-w-3xl mx-auto">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
            <h2 className="text-4xl md:text-6xl font-bold tracking-tight text-slate-900 dark:text-slate-50 mb-6">
              Start making smarter<br /><span className="text-blue-600">money decisions today.</span>
            </h2>
            <p className="text-slate-500 text-lg mb-10 max-w-xl mx-auto">Join thousands of Indian investors using CREDA to manage, protect, and grow their wealth.</p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Button size="lg" className="h-14 px-10 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm shadow-lg shadow-blue-600/20 hover:scale-[1.02] transition-all" asChild>
                <Link href="/auth/sign-up" className="flex items-center gap-3">Start Free Today<ArrowRight className="w-4 h-4" /></Link>
              </Button>
              <Button size="lg" variant="ghost" className="h-14 px-10 font-bold text-sm" asChild>
                <Link href="/auth/sign-in">Already have an account? Sign in</Link>
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      <LandingFooter />
    </div>
  );
}
