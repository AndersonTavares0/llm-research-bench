'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu, X, ExternalLink } from 'lucide-react';
import ThemeToggle from '@/components/ThemeToggle';

const GithubIcon: React.FC<{ className?: string }> = ({ className = 'w-3.5 h-3.5' }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path
      fillRule="evenodd"
      d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
      clipRule="evenodd"
    />
  </svg>
);

export const Navbar: React.FC = () => {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && mobileMenuOpen) {
        setMobileMenuOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [mobileMenuOpen]);

  const navLinks = [
    { href: '/', label: 'Overview' },
    { href: '/models', label: 'Models' },
    { href: '/benchmarks', label: 'Benchmarks' },
    { href: '/compare', label: 'Compare' },
    { href: '/experiments', label: 'Experiments' },
    { href: '/methodology', label: 'Methodology' },
  ];

  return (
    <header role="banner" className="sticky top-0 z-50 w-full border-b border-[#E2E5E5] dark:border-[#242F32] bg-[#FBFBFA]/95 dark:bg-[#0A0E0F]/95 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-12 sm:h-13">
          {/* Logo Brandmark */}
          <div className="flex items-center gap-2.5">
            <Link
              href="/"
              className="flex items-center gap-2 group focus:outline-none"
            >
              <span className="font-serif font-semibold text-base tracking-tight text-[#0E1415] dark:text-[#F2F5F5] group-hover:text-[#006D77] dark:group-hover:text-[#2DD4BF] transition-colors">
                SLM-Limits
              </span>
              <span className="hidden sm:inline-flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#F5F5F3] dark:bg-[#182022] text-[#526063] dark:text-[#98A8AA] border border-[#E2E5E5] dark:border-[#242F32]">
                <span className="w-1.5 h-1.5 rounded-full bg-[#006D77] dark:bg-[#2DD4BF]" aria-hidden="true" />
                GTX 1050 Ti · 4GB
              </span>
            </Link>
          </div>

          {/* Desktop Nav Links (Clean, unbloated, low-profile) */}
          <nav aria-label="Main Navigation" className="hidden md:flex items-center space-x-0.5 lg:space-x-1">
            {navLinks.map((link) => {
              const isActive = pathname === link.href || (link.href !== '/' && pathname.startsWith(link.href));
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  aria-current={isActive ? 'page' : undefined}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-[#E6F3F4] dark:bg-[#0D2C28] text-[#006D77] dark:text-[#2DD4BF] font-semibold'
                      : 'text-[#475456] dark:text-[#98A8AA] hover:text-[#0E1415] dark:hover:text-[#F2F5F5] hover:bg-[#F5F5F3] dark:hover:bg-[#182022]'
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>

          {/* Right Controls */}
          <div className="flex items-center gap-1.5 sm:gap-2">
            <ThemeToggle />

            <a
              href="https://github.com/AndersonTavares0/llm-research-bench"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="GitHub Repository (opens in a new tab)"
              className="p-1 rounded text-[#475456] dark:text-[#98A8AA] hover:text-[#0E1415] dark:hover:text-[#F2F5F5] hover:bg-[#F5F5F3] dark:hover:bg-[#182022] transition-colors"
            >
              <GithubIcon />
            </a>

            {/* Mobile Hamburger Button */}
            <div className="flex md:hidden">
              <button
                type="button"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                aria-expanded={mobileMenuOpen}
                aria-controls="mobile-navigation"
                aria-label={mobileMenuOpen ? 'Close main menu' : 'Open main menu'}
                className="p-1 rounded text-[#475456] dark:text-[#98A8AA] hover:text-[#0E1415] dark:hover:text-[#F2F5F5]"
              >
                {mobileMenuOpen ? (
                  <X className="w-4 h-4" aria-hidden="true" />
                ) : (
                  <Menu className="w-4 h-4" aria-hidden="true" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div
          id="mobile-navigation"
          className="md:hidden border-b border-[#E2E5E5] dark:border-[#242F32] bg-[#FBFBFA] dark:bg-[#0A0E0F] px-4 pt-1.5 pb-3 space-y-0.5"
        >
          {navLinks.map((link) => {
            const isActive = pathname === link.href || (link.href !== '/' && pathname.startsWith(link.href));
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                aria-current={isActive ? 'page' : undefined}
                className={`block px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  isActive
                    ? 'bg-[#E6F3F4] dark:bg-[#0D2C28] text-[#006D77] dark:text-[#2DD4BF] font-semibold'
                    : 'text-[#475456] dark:text-[#98A8AA] hover:text-[#0E1415] dark:hover:text-[#F2F5F5] hover:bg-[#F5F5F3] dark:hover:bg-[#182022]'
                }`}
              >
                {link.label}
              </Link>
            );
          })}
          <div className="pt-2 border-t border-[#E2E5E5] dark:border-[#242F32] flex items-center justify-between text-[11px] text-[#526063] dark:text-[#98A8AA]">
            <span>NVIDIA GTX 1050 Ti · 4096 MiB</span>
            <a
              href="https://github.com/AndersonTavares0/llm-research-bench"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-[#006D77] dark:text-[#2DD4BF]"
            >
              <span>GitHub</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      )}
    </header>
  );
};

export default Navbar;
