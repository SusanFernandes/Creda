'use client';

import React from 'react';
import Link from 'next/link';
import { Github, Twitter, Linkedin } from 'lucide-react';

const footerLinks = [
  {
    title: 'Product',
    links: [
      { label: 'Features', href: '#features' },
      { label: 'Voice Assistant', href: '/voice' },
      { label: 'Portfolio X-Ray', href: '/portfolio' },
      { label: 'Tax Wizard', href: '/tax-wizard' },
      { label: 'FIRE Planner', href: '/fire-planner' },
    ],
  },
  {
    title: 'Platform',
    links: [
      { label: 'Dashboard', href: '/dashboard' },
      { label: 'Knowledge Hub', href: '/knowledge' },
      { label: 'Market Pulse', href: '/market-pulse' },
      { label: 'Compliance', href: '/compliance' },
      { label: 'Help Center', href: '/help' },
    ],
  },
  {
    title: 'Legal',
    links: [
      { label: 'Privacy Policy', href: '/privacy' },
      { label: 'Terms of Service', href: '/terms' },
      { label: 'SEBI Disclaimer', href: '/compliance' },
      { label: 'Security', href: '/security' },
    ],
  },
];

export default function LandingFooter() {
  return (
    <footer className="bg-white dark:bg-slate-950 border-t border-slate-100 dark:border-slate-800">
      <div className="max-w-7xl mx-auto px-6 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-12 mb-12">
          {/* Brand */}
          <div className="lg:col-span-2 space-y-5">
            <Link href="/" className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center">
                <span className="text-white font-black text-lg">C</span>
              </div>
              <span className="text-2xl font-black italic tracking-tight text-slate-900 dark:text-slate-50">CREDA</span>
            </Link>
            <p className="text-slate-500 text-sm leading-relaxed max-w-xs">
              AI-powered financial intelligence for the Indian investor. Multilingual, SEBI-compliant, and fully self-hosted.
            </p>
            <div className="flex items-center gap-3">
              {[
                { icon: Twitter, href: '#', label: 'Twitter' },
                { icon: Linkedin, href: '#', label: 'LinkedIn' },
                { icon: Github, href: '#', label: 'GitHub' },
              ].map(({ icon: Icon, href, label }) => (
                <a
                  key={label}
                  href={href}
                  aria-label={label}
                  className="w-9 h-9 rounded-xl border border-slate-200 dark:border-slate-800 flex items-center justify-center text-slate-400 hover:text-slate-900 dark:hover:text-slate-50 hover:border-slate-300 dark:hover:border-slate-700 transition"
                >
                  <Icon className="w-4 h-4" />
                </a>
              ))}
            </div>
          </div>

          {/* Links */}
          {footerLinks.map((section) => (
            <div key={section.title} className="space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">{section.title}</h3>
              <ul className="space-y-3">
                {section.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-slate-500 hover:text-slate-900 dark:hover:text-slate-50 transition"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="pt-8 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-slate-400">
            &copy; {new Date().getFullYear()} CREDA. All rights reserved.
          </p>
          <p className="text-xs text-slate-400 text-center sm:text-right max-w-sm">
            CREDA is an AI financial coaching tool, not a SEBI-registered advisor. All recommendations are educational only.
          </p>
        </div>
      </div>
    </footer>
  );
}
