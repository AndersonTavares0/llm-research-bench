'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { ModelConfig } from '@/data/researchData';
import HardwareBadge from '@/components/HardwareBadge';
import {
  Trophy,
  Zap,
  Database,
  ArrowUpDown,
  Search,
  ExternalLink,
  GitCompare,
  SlidersHorizontal,
  ChevronRight,
  Info,
  HelpCircle,
  Clock,
  Sparkles
} from 'lucide-react';

interface LeaderboardTableProps {
  models: ModelConfig[];
  onSelectModel?: (model: ModelConfig) => void;
  selectedModelId?: string;
}

type SortField = 'rank' | 'quality' | 'speed' | 'vram' | 'ttft';

export const LeaderboardTable: React.FC<LeaderboardTableProps> = ({
  models,
  onSelectModel,
  selectedModelId
}) => {
  const [sortField, setSortField] = useState<SortField>('quality');
  const [sortAsc, setSortAsc] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sizeFilter, setSizeFilter] = useState<'all' | 'sub2b' | '3b' | 'dense' | 'mtp'>('all');
  const [showExplanation, setShowExplanation] = useState<boolean>(false);

  // Compute composite zero-shot quality score (average of ARC, HellaSwag, GSM8K, IFEval)
  const rankedModels = useMemo(() => {
    const list = models.map((m) => {
      const q = m.quality_scores;
      const compositeQuality = (q.arc_challenge + q.hellaswag + q.gsm8k_flex + q.ifeval_strict) / 4;
      return {
        ...m,
        compositeQuality: Number((compositeQuality * 100).toFixed(1))
      };
    });

    // Default sort by quality descending
    list.sort((a, b) => b.compositeQuality - a.compositeQuality);
    return list.map((m, idx) => ({ ...m, rank: idx + 1 }));
  }, [models]);

  const filteredModels = useMemo(() => {
    return rankedModels.filter((m) => {
      const matchesSearch =
        m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.family.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.quantization.toLowerCase().includes(searchQuery.toLowerCase());

      let matchesFilter = true;
      if (sizeFilter === 'sub2b') matchesFilter = m.parameters_b <= 2.0;
      else if (sizeFilter === '3b') matchesFilter = m.parameters_b > 2.0;
      else if (sizeFilter === 'mtp') matchesFilter = m.speculative_decoding;
      else if (sizeFilter === 'dense') matchesFilter = !m.speculative_decoding;

      return matchesSearch && matchesFilter;
    });
  }, [rankedModels, searchQuery, sizeFilter]);

  const sortedModels = useMemo(() => {
    const list = [...filteredModels];
    list.sort((a, b) => {
      let valA = 0;
      let valB = 0;
      switch (sortField) {
        case 'rank':
          valA = a.rank;
          valB = b.rank;
          break;
        case 'quality':
          valA = a.compositeQuality;
          valB = b.compositeQuality;
          break;
        case 'speed':
          valA = a.generation_tok_s;
          valB = b.generation_tok_s;
          break;
        case 'vram':
          valA = a.vram_peak_mib;
          valB = b.vram_peak_mib;
          break;
        case 'ttft':
          valA = a.ttft_ms;
          valB = b.ttft_ms;
          break;
      }
      return sortAsc ? valA - valB : valB - valA;
    });
    return list;
  }, [filteredModels, sortField, sortAsc]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const maxQuality = useMemo(() => Math.max(...rankedModels.map((m) => m.compositeQuality), 100), [rankedModels]);
  const maxSpeed = useMemo(() => Math.max(...rankedModels.map((m) => m.generation_tok_s), 1), [rankedModels]);

  return (
    <div className="space-y-4">
      {/* Control Bar: Filters, Search, and Methodology Drawer Toggle */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        {/* Segmented Filter Pills (Artificial Analysis Style) */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none text-xs" role="group" aria-label="Filter models by size or architecture">
          {[
            { label: 'All Evaluated Models', value: 'all' },
            { label: 'Dense Autoregressive', value: 'dense' },
            { label: 'Speculative (MTP)', value: 'mtp' },
            { label: '≤ 2.0B Parameters', value: 'sub2b' },
            { label: '3.0B+ Parameters', value: '3b' }
          ].map((pill) => {
            const isActive = sizeFilter === pill.value;
            return (
              <button
                key={pill.value}
                onClick={() => setSizeFilter(pill.value as any)}
                aria-pressed={isActive}
                className={`px-3 py-1.5 rounded-md font-medium whitespace-nowrap transition-colors shrink-0 text-xs ${
                  isActive
                    ? 'bg-[#006D77] dark:bg-[#2DD4BF] text-white dark:text-[#0A0E0F] font-semibold shadow-sm'
                    : 'bg-white dark:bg-[#121719] text-[#475456] dark:text-[#98A8AA] border border-[#E2E5E5] dark:border-[#242F32] hover:bg-[#F5F5F3] dark:hover:bg-[#182022]'
                }`}
              >
                {pill.label}
              </button>
            );
          })}
        </div>

        {/* Right Search Input and Metric Guide Button */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowExplanation(!showExplanation)}
            aria-expanded={showExplanation}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-white dark:bg-[#121719] text-[#475456] dark:text-[#98A8AA] border border-[#E2E5E5] dark:border-[#242F32] hover:bg-[#F5F5F3] dark:hover:bg-[#182022] transition-colors shrink-0"
          >
            <HelpCircle className="w-3.5 h-3.5 text-[#006D77] dark:text-[#2DD4BF]" aria-hidden="true" />
            <span>Metric Definitions</span>
          </button>

          <div className="relative flex-1 md:w-56">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[#526063] dark:text-[#98A8AA]" aria-hidden="true" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search model name..."
              aria-label="Filter models by name or family"
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] rounded-md text-[#0E1415] dark:text-[#F2F5F5] placeholder-[#526063] dark:placeholder-[#98A8AA] focus:outline-none focus:border-[#006D77] focus:ring-1 focus:ring-[#006D77] dark:focus:border-[#2DD4BF] dark:focus:ring-[#2DD4BF]"
            />
          </div>
        </div>
      </div>

      {/* Explanatory Metric Context (Artificial Analysis Standard) */}
      {showExplanation && (
        <div className="p-4 rounded-xl bg-[#E6F3F4] dark:bg-[#0D2C28] border border-[#006D77]/25 dark:border-[#2DD4BF]/30 text-xs text-[#0E1415] dark:text-[#F2F5F5] space-y-2">
          <div className="font-bold text-[#006D77] dark:text-[#2DD4BF] flex items-center gap-1.5 text-xs">
            <Info className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>How Metrics are Measured Under Constrained Hardware Controls</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 leading-relaxed">
            <div className="p-2.5 rounded-lg bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] shadow-sm">
              <span className="font-semibold text-[#006D77] dark:text-[#2DD4BF] block mb-1">Composite Quality Index</span>
              Arithmetic mean across 4 standardized zero-shot benchmarks: ARC-Challenge (reasoning), HellaSwag (sentence completion), GSM8K flex (grade school math), and IFEval strict (instruction adherence). All executed under greedy decoding (T=0.0).
            </div>
            <div className="p-2.5 rounded-lg bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] shadow-sm">
              <span className="font-semibold text-[#006D77] dark:text-[#2DD4BF] block mb-1">Decode Speed (tok/s)</span>
              Pure generation throughput measured on single-token autoregressive decoding (b=1) under pinned llama.cpp. Strictly bounded by 112 GB/s GDDR5 bus transfer speeds.
            </div>
            <div className="p-2.5 rounded-lg bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] shadow-sm">
              <span className="font-semibold text-[#006D77] dark:text-[#2DD4BF] block mb-1">Peak VRAM & Physical Ceiling</span>
              Hardware memory sampled at 250ms intervals during 8,192-token context runs. The percentage shows consumption relative to the rigid 4096 MiB physical boundary of the GTX 1050 Ti.
            </div>
          </div>
        </div>
      )}

      {/* Speculative Decoding & MTP Architecture Clarification Banner */}
      <div className="p-3.5 rounded-lg bg-[#F5F5F3] dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] text-xs text-[#526063] dark:text-[#98A8AA] flex items-start gap-2.5">
        <Info className="w-4 h-4 text-[#006D77] dark:text-[#2DD4BF] shrink-0 mt-0.5" aria-hidden="true" />
        <div className="space-y-1">
          <p className="font-semibold text-[#0E1415] dark:text-[#F2F5F5]">
            Architectural Scope of Speculative Decoding (MTP vs Dense Autoregressive)
          </p>
          <p className="leading-relaxed">
            Multi-Token Prediction (MTP) draft acceleration relies on auxiliary prediction heads embedded natively into the model weights (such as <strong className="text-[#0E1415] dark:text-[#F2F5F5]">Gemma-4:E2B</strong>). Architectures without native MTP heads (<strong className="text-[#0E1415] dark:text-[#F2F5F5]">Qwen2.5, SmolLM2, Llama-3.2, Qwen3.5</strong>) execute in standard single-token autoregressive mode under <code className="font-mono text-[11px] px-1 py-0.5 rounded bg-[#E2E5E5] dark:bg-[#1D2629]">llama.cpp</code>. Both the baseline (non-MTP) and MTP-accelerated Gemma variants are evaluated in the benchmark for direct controlled comparison.
          </p>
        </div>
      </div>

      {/* Main Leaderboard Table Container */}
      <div className="rounded-xl border border-[#E2E5E5] dark:border-[#242F32] bg-white dark:bg-[#121719] overflow-x-auto shadow-sm">
        <table className="w-full text-left border-collapse text-xs" aria-label="Model performance leaderboard table">
          <caption className="sr-only">
            Ranked Small Language Model leaderboard showing quality index, decode speed, peak VRAM, and latency on GTX 1050 Ti.
          </caption>
          <thead>
            <tr className="border-b border-[#E2E5E5] dark:border-[#242F32] bg-[#F5F5F3] dark:bg-[#182022] text-[#475456] dark:text-[#98A8AA] font-semibold uppercase tracking-wider text-[11px]">
              <th scope="col" className="py-3 px-3 text-center w-12 cursor-pointer hover:text-[#006D77] dark:hover:text-[#2DD4BF]" onClick={() => handleSort('rank')}>
                <div className="flex items-center justify-center gap-1">
                  <span>#</span>
                  <ArrowUpDown className="w-3 h-3 opacity-50" aria-hidden="true" />
                </div>
              </th>
              <th scope="col" className="py-3 px-4 min-w-[220px]">
                Model Name
              </th>
              <th scope="col" className="py-3 px-4 cursor-pointer hover:text-[#006D77] dark:hover:text-[#2DD4BF] min-w-[180px]" onClick={() => handleSort('quality')}>
                <div className="flex items-center gap-1.5">
                  <Trophy className="w-3.5 h-3.5 text-[#006D77] dark:text-[#2DD4BF]" aria-hidden="true" />
                  <span>Quality Index</span>
                  <ArrowUpDown className="w-3 h-3 opacity-60" aria-hidden="true" />
                </div>
              </th>
              <th scope="col" className="py-3 px-4 cursor-pointer hover:text-[#0284C7] dark:hover:text-[#38BDF8] min-w-[180px]" onClick={() => handleSort('speed')}>
                <div className="flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 text-[#0284C7] dark:text-[#38BDF8]" aria-hidden="true" />
                  <span>Decode Speed</span>
                  <ArrowUpDown className="w-3 h-3 opacity-60" aria-hidden="true" />
                </div>
              </th>
              <th scope="col" className="py-3 px-4 cursor-pointer hover:text-[#0E7A5A] dark:hover:text-[#34D399] min-w-[170px]" onClick={() => handleSort('vram')}>
                <div className="flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-[#0E7A5A] dark:text-[#34D399]" aria-hidden="true" />
                  <span>Peak VRAM (4 GiB)</span>
                  <ArrowUpDown className="w-3 h-3 opacity-60" aria-hidden="true" />
                </div>
              </th>
              <th scope="col" className="py-3 px-3 cursor-pointer hover:text-[#006D77] dark:hover:text-[#2DD4BF] min-w-[90px]" onClick={() => handleSort('ttft')}>
                <div className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5 opacity-60" aria-hidden="true" />
                  <span>TTFT</span>
                  <ArrowUpDown className="w-3 h-3 opacity-50" aria-hidden="true" />
                </div>
              </th>
              <th scope="col" className="py-3 px-3 text-right min-w-[80px]">
                Compare
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#ECEEED] dark:divide-[#1C2426]">
            {sortedModels.map((m) => {
              const isSelected = selectedModelId === m.id;
              const qualityPct = Math.min(100, (m.compositeQuality / maxQuality) * 100);
              const speedPct = Math.min(100, (m.generation_tok_s / maxSpeed) * 100);

              // Distinctive Artificial Analysis Rank Badges (#1, #2, #3)
              let rankBadge = (
                <span className="font-mono text-xs font-bold text-[#526063] dark:text-[#98A8AA]">
                  {m.rank}
                </span>
              );
              if (m.rank === 1) {
                rankBadge = (
                  <span className="w-6 h-6 rounded-full bg-[#E6F3F4] text-[#006D77] dark:bg-[#0D2C28] dark:text-[#2DD4BF] border border-[#006D77]/30 dark:border-[#2DD4BF]/40 flex items-center justify-center font-mono text-xs font-bold mx-auto">
                    1
                  </span>
                );
              } else if (m.rank === 2) {
                rankBadge = (
                  <span className="w-6 h-6 rounded-full bg-[#F5F5F3] text-[#475456] dark:bg-[#182022] dark:text-[#98A8AA] border border-[#E2E5E5] dark:border-[#242F32] flex items-center justify-center font-mono text-xs font-semibold mx-auto">
                    2
                  </span>
                );
              } else if (m.rank === 3) {
                rankBadge = (
                  <span className="w-6 h-6 rounded-full bg-[#F5F5F3] text-[#526063] dark:bg-[#182022] dark:text-[#98A8AA] border border-[#E2E5E5] dark:border-[#242F32] flex items-center justify-center font-mono text-xs font-medium mx-auto">
                    3
                  </span>
                );
              }

              return (
                <tr
                  key={m.id}
                  onClick={() => onSelectModel && onSelectModel(m)}
                  className={`group transition-colors cursor-pointer ${
                    isSelected
                      ? 'bg-[#E6F3F4]/50 dark:bg-[#0D2C28]/40 border-l-2 border-l-[#006D77] dark:border-l-[#2DD4BF]'
                      : 'hover:bg-[#F5F5F3] dark:hover:bg-[#182022]'
                  }`}
                >
                  {/* Rank */}
                  <td className="py-3 px-3 text-center">{rankBadge}</td>

                  {/* Model & Quantization */}
                  <td className="py-3 px-4">
                    <div className="flex flex-col">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-[#0E1415] dark:text-[#F2F5F5] group-hover:text-[#006D77] dark:group-hover:text-[#2DD4BF] transition-colors">
                          {m.name}
                        </span>
                        {m.speculative_decoding ? (
                          <span
                            className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#E6F3F4] dark:bg-[#0D2C28] text-[#006D77] dark:text-[#2DD4BF] border border-[#006D77]/25 dark:border-[#2DD4BF]/30 font-semibold"
                            title="Speculative decoding enabled via auxiliary multi-token prediction heads"
                          >
                            Speculative (MTP +25.6%)
                          </span>
                        ) : (
                          <span
                            className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#F5F5F3] dark:bg-[#182022] text-[#526063] dark:text-[#98A8AA] border border-[#E2E5E5] dark:border-[#242F32]"
                            title="Standard single-token autoregressive decoding"
                          >
                            Autoregressive (Dense)
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5 text-[11px] font-mono text-[#526063] dark:text-[#98A8AA]">
                        <span>{m.parameters_b}B Params</span>
                        <span>•</span>
                        <span>{m.quantization}</span>
                        <span>•</span>
                        <span>{m.family}</span>
                      </div>
                    </div>
                  </td>

                  {/* Quality Index with Proportional Bar */}
                  <td className="py-3 px-4 font-mono">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-[#006D77] dark:text-[#2DD4BF] text-sm">{m.compositeQuality}%</span>
                        <span className="text-[10px] text-[#526063] dark:text-[#98A8AA] font-sans">Avg 4 tasks</span>
                      </div>
                      <div className="w-full h-1.5 rounded-full bg-[#E2E5E5] dark:bg-[#242F32] overflow-hidden">
                        <div
                          className="h-full rounded-full bg-[#006D77] dark:bg-[#2DD4BF] transition-all duration-500"
                          style={{ width: `${qualityPct}%` }}
                        />
                      </div>
                    </div>
                  </td>

                  {/* Decode Speed with Cyan Speed Bar */}
                  <td className="py-3 px-4 font-mono">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-[#0369A1] dark:text-[#38BDF8] text-sm">
                          {m.generation_tok_s} <span className="text-[10px] font-normal text-[#526063] dark:text-[#98A8AA]">tok/s</span>
                        </span>
                        <span className="text-[10px] text-[#526063] dark:text-[#98A8AA] font-sans">{speedPct.toFixed(0)}% max</span>
                      </div>
                      <div className="w-full h-1.5 rounded-full bg-[#E2E5E5] dark:bg-[#242F32] overflow-hidden">
                        <div
                          className="h-full rounded-full bg-[#0284C7] dark:bg-[#38BDF8] transition-all duration-500"
                          style={{ width: `${speedPct}%` }}
                        />
                      </div>
                    </div>
                  </td>

                  {/* Peak VRAM with Gauge Bar */}
                  <td className="py-3 px-4 font-mono">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-[#0E1415] dark:text-[#F2F5F5] text-sm">
                          {m.vram_peak_mib} <span className="text-[10px] font-normal text-[#526063] dark:text-[#98A8AA]">MiB</span>
                        </span>
                        <span className={`text-[10px] font-semibold ${m.vram_budget_pct > 80 ? 'text-[#B45309] dark:text-[#FBBF24]' : 'text-[#0E7A5A] dark:text-[#34D399]'}`}>
                          {m.vram_budget_pct}%
                        </span>
                      </div>
                      <div className="w-full h-1.5 rounded-full bg-[#E2E5E5] dark:bg-[#242F32] overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            m.vram_budget_pct > 80 ? 'bg-[#B45309] dark:bg-[#FBBF24]' : 'bg-[#0E7A5A] dark:bg-[#34D399]'
                          }`}
                          style={{ width: `${m.vram_budget_pct}%` }}
                        />
                      </div>
                    </div>
                  </td>

                  {/* TTFT Latency */}
                  <td className="py-3 px-3 font-mono text-[#475456] dark:text-[#98A8AA] text-xs">
                    {m.ttft_ms} ms
                  </td>

                  {/* Actions */}
                  <td className="py-3 px-3 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <Link
                        href={`/compare?m1=${m.id}`}
                        onClick={(e) => e.stopPropagation()}
                        aria-label={`Compare ${m.name} against baseline`}
                        className="p-1.5 rounded-md hover:bg-[#F5F5F3] dark:hover:bg-[#182022] text-[#526063] dark:text-[#98A8AA] hover:text-[#006D77] dark:hover:text-[#2DD4BF] transition-colors"
                      >
                        <GitCompare className="w-3.5 h-3.5" aria-hidden="true" />
                      </Link>
                      <ChevronRight className="w-4 h-4 text-[#BAC2C2] dark:text-[#3B4C50] group-hover:text-[#006D77] dark:group-hover:text-[#2DD4BF] group-hover:translate-x-0.5 transition-all" aria-hidden="true" />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default LeaderboardTable;
