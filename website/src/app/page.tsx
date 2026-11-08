'use client';

import React from 'react';
import Link from 'next/link';
import { researchData, ModelConfig } from '@/data/researchData';
import LeaderboardTable from '@/components/LeaderboardTable';
import ScatterFrontier from '@/components/ScatterFrontier';
import VRAMBudgetChart from '@/components/VRAMBudgetChart';
import EvidenceBadge from '@/components/EvidenceBadge';
import HardwareBadge from '@/components/HardwareBadge';
import {
  ArrowRight,
  Cpu,
  Database,
  Activity,
  Layers,
  ShieldCheck,
  TrendingUp,
  BarChart2,
  GitCompare,
  BookOpen,
  Trophy
} from 'lucide-react';

export default function HomePage() {
  const models = researchData.models;

  // Key empirical findings strictly on GTX 1050 Ti
  const keyFindings = [
    {
      title: 'Speculative Decoding Throughput Jump',
      stat: '+25.6%',
      statLabel: 'Decode Speed Gain on GTX 1050 Ti',
      description:
        'Dual-head speculative decoding (MTP) accelerates Qwen2.5-1.5B from 24.2 to 30.4 tok/s with zero memory allocation penalty or loss in greedily generated outputs.',
      badge: 'measured' as const,
      link: '/experiments'
    },
    {
      title: 'GDDR5 Bus Saturation Bottleneck',
      stat: '112 GB/s',
      statLabel: 'Rigid Memory Bandwidth Ceiling',
      description:
        'Single-batch autoregressive generation is purely memory-bandwidth bound. Token latency scales linearly with parameter tensor footprint regardless of context depth.',
      badge: 'measured' as const,
      link: '/experiments'
    },
    {
      title: 'Context Length vs KV Cache Collapse',
      stat: '3,800 tok',
      statLabel: '3B Model Safe Horizon Under 4 GiB',
      description:
        '3B models in Q4_K_M consume ~2.5 GiB for weights alone. Unquantized FP16 KV cache consumes remaining headroom by 3,800 tokens, triggering OOM without Q8_0 KV quantization.',
      badge: 'measured' as const,
      link: '/experiments'
    },
    {
      title: 'Defensive Cyber Triage Viability',
      stat: '76.8%',
      statLabel: 'CVE Severity Extraction Accuracy',
      description:
        'Fine-tuned and few-shot SLMs (1.5B–3B) successfully triage CVEs and extract CVSS vectors under strict deterministic extraction protocols.',
      badge: 'measured' as const,
      link: '/experiments'
    }
  ];

  return (
    <div className="space-y-12">
      {/* Hero Section (Epoch AI Editorial Authority) */}
      <section className="relative pt-2 pb-6 space-y-6 border-b border-[#E2E5E5] dark:border-[#242F32]">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#E6F3F4] dark:bg-[#0D2C28] border border-[#006D77]/25 dark:border-[#2DD4BF]/30 text-xs font-mono text-[#006D77] dark:text-[#2DD4BF]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#006D77] dark:bg-[#2DD4BF]" aria-hidden="true" />
          <span>REPRODUCIBLE RESEARCH · CONSTRAINED SILICON TESTBED</span>
        </div>

        <div className="max-w-4xl space-y-3">
          <h1 className="text-3xl sm:text-5xl font-serif font-medium tracking-tight text-[#0E1415] dark:text-[#F2F5F5] leading-tight">
            Small Language Model Benchmarks &{' '}
            <span className="text-[#006D77] dark:text-[#2DD4BF]">
              Physical Limits
            </span>
          </h1>
          <p className="text-sm sm:text-base text-[#475456] dark:text-[#98A8AA] leading-relaxed max-w-3xl">
            Independent empirical benchmarks evaluating Small Language Models (0.5B to 3B parameters) under an unforgiving
            4096 MiB physical VRAM ceiling. We measure real decode throughput, prefill latency, memory allocation envelopes,
            and needle retrieval fidelity under single-host hardware controls.
          </p>
        </div>

        {/* Testbed Physical Instrumentation Parameters */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2">
          <div className="p-3.5 rounded-lg bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] space-y-1 shadow-sm">
            <span className="text-[11px] font-mono uppercase tracking-wider text-[#526063] dark:text-[#98A8AA]">Hardware Station</span>
            <div className="text-sm font-bold text-[#0E1415] dark:text-[#F2F5F5] flex items-center gap-1.5">
              <Cpu className="w-4 h-4 text-[#006D77] dark:text-[#2DD4BF]" aria-hidden="true" />
              <span>GTX 1050 Ti (4 GiB)</span>
            </div>
            <span className="text-[11px] text-[#526063] dark:text-[#98A8AA] font-mono">PVE CT 108 · Debian 12</span>
          </div>

          <div className="p-3.5 rounded-lg bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] space-y-1 shadow-sm">
            <span className="text-[11px] font-mono uppercase tracking-wider text-[#526063] dark:text-[#98A8AA]">Memory Ceiling</span>
            <div className="text-sm font-bold text-[#0E1415] dark:text-[#F2F5F5] flex items-center gap-1.5">
              <Database className="w-4 h-4 text-[#0E7A5A] dark:text-[#34D399]" aria-hidden="true" />
              <span>4096 MiB GDDR5</span>
            </div>
            <span className="text-[11px] text-[#526063] dark:text-[#98A8AA] font-mono">112 GB/s Bandwidth</span>
          </div>

          <div className="p-3.5 rounded-lg bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] space-y-1 shadow-sm">
            <span className="text-[11px] font-mono uppercase tracking-wider text-[#526063] dark:text-[#98A8AA]">Runtime Engine</span>
            <div className="text-sm font-bold text-[#0E1415] dark:text-[#F2F5F5] flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-[#0284C7] dark:text-[#38BDF8]" aria-hidden="true" />
              <span>llama.cpp b12024</span>
            </div>
            <span className="text-[11px] text-[#526063] dark:text-[#98A8AA] font-mono">CUDA 12 · T=0.0 Greedy</span>
          </div>

          <div className="p-3.5 rounded-lg bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] space-y-1 shadow-sm">
            <span className="text-[11px] font-mono uppercase tracking-wider text-[#526063] dark:text-[#98A8AA]">Integrity Standard</span>
            <div className="text-sm font-bold text-[#0E1415] dark:text-[#F2F5F5] flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-[#B45309] dark:text-[#FBBF24]" aria-hidden="true" />
              <span>Fail-Closed Bounds</span>
            </div>
            <span className="text-[11px] text-[#526063] dark:text-[#98A8AA] font-mono">22 Research Questions</span>
          </div>
        </div>
      </section>

      {/* Flagship Section 1: Artificial Analysis Style Model Leaderboard */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <Trophy className="w-5 h-5 text-[#006D77] dark:text-[#2DD4BF]" aria-hidden="true" />
              <h2 className="text-xl sm:text-2xl font-serif font-semibold text-[#0E1415] dark:text-[#F2F5F5] tracking-tight">
                Model Leaderboard
              </h2>
            </div>
            <p className="text-xs sm:text-sm text-[#475456] dark:text-[#98A8AA]">
              Ranked on composite quality index (ARC, HellaSwag, GSM8K, IFEval), generation throughput, and physical VRAM footprint on GTX 1050 Ti.
            </p>
          </div>
          <Link
            href="/models"
            className="inline-flex items-center gap-1 text-xs font-semibold text-[#006D77] dark:text-[#2DD4BF] hover:underline self-start sm:self-auto"
          >
            <span>Explore All Telemetry</span>
            <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
          </Link>
        </div>

        {/* Live Leaderboard Table Component */}
        <LeaderboardTable models={models} />
      </section>

      {/* Flagship Section 2: Interactive Scatter Plot & Pareto Frontier */}
      <section className="space-y-4">
        <ScatterFrontier models={models} />
      </section>

      {/* Flagship Section 3: VRAM Allocation Breakdown */}
      <section className="space-y-4">
        <VRAMBudgetChart models={models} />
      </section>

      {/* Flagship Section 4: Key Empirical Findings */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-xl sm:text-2xl font-serif font-semibold text-[#0E1415] dark:text-[#F2F5F5] tracking-tight">
              Verified Scientific Findings
            </h2>
            <p className="text-xs sm:text-sm text-[#475456] dark:text-[#98A8AA]">
              Key conclusions backed by repeatable hardware campaigns and fail-closed statistical controls.
            </p>
          </div>
          <Link
            href="/experiments"
            className="inline-flex items-center gap-1 text-xs font-semibold text-[#006D77] dark:text-[#2DD4BF] hover:underline"
          >
            <span>View All 7 Experiments</span>
            <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {keyFindings.map((finding) => (
            <Link
              key={finding.title}
              href={finding.link}
              className="p-5 rounded-xl bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] hover:border-[#006D77] dark:hover:border-[#2DD4BF]/60 transition-colors flex flex-col justify-between group shadow-sm"
            >
              <div className="space-y-2.5">
                <div className="flex items-start justify-between gap-3">
                  <h3 className="font-serif font-bold text-[#0E1415] dark:text-[#F2F5F5] group-hover:text-[#006D77] dark:group-hover:text-[#2DD4BF] transition-colors text-sm sm:text-base">
                    {finding.title}
                  </h3>
                  <EvidenceBadge status={finding.badge} className="shrink-0" />
                </div>

                <div className="space-y-1">
                  <div className="text-2xl sm:text-3xl font-extrabold text-[#006D77] dark:text-[#2DD4BF] font-mono tracking-tight">
                    {finding.stat}
                  </div>
                  <div className="text-xs font-semibold text-[#475456] dark:text-[#98A8AA]">
                    {finding.statLabel}
                  </div>
                </div>

                <p className="text-xs text-[#475456] dark:text-[#98A8AA] leading-relaxed font-sans pt-1">
                  {finding.description}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-[#ECEEED] dark:border-[#1C2426] flex items-center justify-between text-xs text-[#006D77] dark:text-[#2DD4BF] font-medium">
                <span>Inspect campaign telemetry & sweep table</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" aria-hidden="true" />
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Section 5: Scientific Integrity Standards */}
      <section className="p-6 rounded-xl bg-[#F5F5F3] dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] space-y-4">
        <div className="flex items-center gap-2 text-[#006D77] dark:text-[#2DD4BF]">
          <ShieldCheck className="w-5 h-5" aria-hidden="true" />
          <h2 className="text-lg font-serif font-bold text-[#0E1415] dark:text-[#F2F5F5]">Scientific Integrity & Methodology Guardrails</h2>
        </div>

        <p className="text-xs sm:text-sm text-[#475456] dark:text-[#98A8AA] leading-relaxed">
          The SLM-Limits research program strictly separates measured observations from analytical models and exploratory
          probes. To prevent misleading claims, this platform enforces four core scientific standards:
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2 text-xs">
          <div className="p-3 rounded-lg bg-white dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32] space-y-1 shadow-sm">
            <span className="font-bold text-[#0E1415] dark:text-[#F2F5F5]">1. Hardware Control</span>
            <p className="text-[#475456] dark:text-[#98A8AA]">
              Evaluations run strictly on the designated constrained target: NVIDIA GeForce GTX 1050 Ti (4 GiB GDDR5, PVE CT 108).
            </p>
          </div>

          <div className="p-3 rounded-lg bg-white dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32] space-y-1 shadow-sm">
            <span className="font-bold text-[#0E1415] dark:text-[#F2F5F5]">2. Non-Independent Queries</span>
            <p className="text-[#475456] dark:text-[#98A8AA]">
              Repeated deterministic queries on one machine are consistency checks, not statistical hardware replicates.
            </p>
          </div>

          <div className="p-3 rounded-lg bg-white dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32] space-y-1 shadow-sm">
            <span className="font-bold text-[#0E1415] dark:text-[#F2F5F5]">3. Fail-Closed Machinery</span>
            <p className="text-[#475456] dark:text-[#98A8AA]">
              Hypothesis testing algorithms fail-closed unless independent randomized hardware replicates exist.
            </p>
          </div>

          <div className="p-3 rounded-lg bg-white dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32] space-y-1 shadow-sm">
            <span className="font-bold text-[#0E1415] dark:text-[#F2F5F5]">4. Provenance Links</span>
            <p className="text-[#475456] dark:text-[#98A8AA]">
              Every score traces directly to committed git logs, raw token outputs, and reproduction scripts.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
