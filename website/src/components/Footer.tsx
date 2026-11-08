'use client';

import React from 'react';
import Link from 'next/link';
import { ExternalLink } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer role="contentinfo" className="w-full border-t border-[#E2E5E5] dark:border-[#242F32] bg-[#FFFFFF] dark:bg-[#121719] py-6 sm:py-7 text-[#475456] dark:text-[#98A8AA] text-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-4">
        {/* Main Row: Brand & Horizontal Nav */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-serif font-bold text-sm tracking-tight text-[#0E1415] dark:text-[#F2F5F5]">
              SLM-Limits Research
            </span>
            <span className="text-[11px] font-mono text-[#526063] dark:text-[#98A8AA] border-l border-[#E2E5E5] dark:border-[#242F32] pl-2">
              GTX 1050 Ti Testbed
            </span>
          </div>

          {/* Inline Navigation Links */}
          <nav aria-label="Footer Navigation" className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
            <Link href="/models" className="hover:text-[#006D77] dark:hover:text-[#2DD4BF] transition-colors">
              Models
            </Link>
            <Link href="/benchmarks" className="hover:text-[#006D77] dark:hover:text-[#2DD4BF] transition-colors">
              Benchmarks
            </Link>
            <Link href="/compare" className="hover:text-[#006D77] dark:hover:text-[#2DD4BF] transition-colors">
              Compare
            </Link>
            <Link href="/experiments" className="hover:text-[#006D77] dark:hover:text-[#2DD4BF] transition-colors">
              Experiments
            </Link>
            <Link href="/methodology" className="hover:text-[#006D77] dark:hover:text-[#2DD4BF] transition-colors">
              Methodology
            </Link>
            <a
              href="https://github.com/AndersonTavares0/llm-research-bench/blob/main/reports/en-US/report_en-US.pdf"
              target="_blank"
              rel="noreferrer"
              className="hover:text-[#006D77] dark:hover:text-[#2DD4BF] transition-colors inline-flex items-center gap-1"
            >
              <span>Report (PDF)</span>
              <ExternalLink className="w-3 h-3 opacity-60" />
            </a>
            <a
              href="https://github.com/AndersonTavares0/llm-research-bench"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-[#006D77] dark:hover:text-[#2DD4BF] transition-colors inline-flex items-center gap-1"
            >
              <span>GitHub</span>
              <ExternalLink className="w-3 h-3 opacity-60" />
            </a>
          </nav>
        </div>

        {/* Bottom Hardware & Attribution Note */}
        <div className="pt-3 border-t border-[#ECEEED] dark:border-[#1C2426] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-[11px] text-[#526063] dark:text-[#98A8AA]">
          <p>
            &copy; 2026 SLM-Limits Research Program. Open science benchmark for resource-constrained edge computing.
          </p>
          <p className="font-mono">
            NVIDIA GTX 1050 Ti · 4096 MiB GDDR5 (112 GB/s) · PVE CT 108 · llama.cpp
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
