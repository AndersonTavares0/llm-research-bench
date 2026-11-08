'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import researchData, { ModelConfig } from '@/data/researchData';
import ScatterFrontier from '@/components/ScatterFrontier';
import LeaderboardTable from '@/components/LeaderboardTable';
import EvidenceBadge from '@/components/EvidenceBadge';
import HardwareBadge from '@/components/HardwareBadge';
import {
  Cpu,
  Search,
  Zap,
  Gauge,
  Thermometer,
  Layers,
  ArrowRight,
  GitCompare,
  Globe,
  Activity,
  CheckCircle2,
  X,
  Trophy,
  Info,
  Flame
} from 'lucide-react';

export default function ModelExplorerPage() {
  const { models } = researchData;
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFamily, setSelectedFamily] = useState<string>('all');
  const [selectedModel, setSelectedModel] = useState<ModelConfig | null>(models[0]);
  const [activeTab, setActiveTab] = useState<'leaderboard' | 'frontier'>('leaderboard');

  const families = useMemo(() => {
    const set = new Set(models.map((m) => m.family));
    return Array.from(set);
  }, [models]);

  const filteredModels = useMemo(() => {
    return models.filter((m) => {
      const matchSearch =
        m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.quantization.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.notes.toLowerCase().includes(searchQuery.toLowerCase());
      const matchFamily = selectedFamily === 'all' || m.family === selectedFamily;
      return matchSearch && matchFamily;
    });
  }, [models, searchQuery, selectedFamily]);

  return (
    <div className="space-y-8">
      {/* Page Header (Epoch AI Editorial Authority) */}
      <div className="space-y-2 border-b border-[#E2E5E5] dark:border-[#242F32] pb-6">
        <div className="flex items-center gap-2 text-xs font-mono text-[#006D77] dark:text-[#2DD4BF]">
          <Cpu className="w-4 h-4" aria-hidden="true" />
          <span>INFERENCE PROFILES & BENCHMARK LEADERBOARD</span>
        </div>
        <h1 className="text-2xl sm:text-4xl font-serif font-medium tracking-tight text-[#0E1415] dark:text-[#F2F5F5]">
          Small Language Model Explorer
        </h1>
        <p className="text-xs sm:text-sm text-[#475456] dark:text-[#98A8AA] max-w-3xl leading-relaxed">
          Detailed telemetry, VRAM consumption, generation throughput, and tokenization fertility across 6 evaluated
          quantized models. Single physical testbed: NVIDIA GTX 1050 Ti 4GB (PVE CT 108).
        </p>
      </div>

      {/* View Switcher: Leaderboard Table vs Interactive Scatter Frontier */}
      <div className="flex items-center gap-2 border-b border-[#E2E5E5] dark:border-[#242F32] pb-2">
        <button
          onClick={() => setActiveTab('leaderboard')}
          aria-pressed={activeTab === 'leaderboard'}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-md text-xs font-semibold transition-all ${
            activeTab === 'leaderboard'
              ? 'bg-[#006D77] dark:bg-[#2DD4BF] text-white dark:text-[#0A0E0F] shadow-sm'
              : 'bg-[#F5F5F3] dark:bg-[#182022] text-[#475456] dark:text-[#98A8AA] border border-[#E2E5E5] dark:border-[#242F32] hover:bg-[#ECEEED] dark:hover:bg-[#1D2629]'
          }`}
        >
          <Trophy className="w-4 h-4" aria-hidden="true" />
          <span>Model Leaderboard Table</span>
        </button>

        <button
          onClick={() => setActiveTab('frontier')}
          aria-pressed={activeTab === 'frontier'}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-md text-xs font-semibold transition-all ${
            activeTab === 'frontier'
              ? 'bg-[#006D77] dark:bg-[#2DD4BF] text-white dark:text-[#0A0E0F] shadow-sm'
              : 'bg-[#F5F5F3] dark:bg-[#182022] text-[#475456] dark:text-[#98A8AA] border border-[#E2E5E5] dark:border-[#242F32] hover:bg-[#ECEEED] dark:hover:bg-[#1D2629]'
          }`}
        >
          <Zap className="w-4 h-4" aria-hidden="true" />
          <span>Interactive 2D Scatter Frontier</span>
        </button>
      </div>

      {/* Active Tab View */}
      {activeTab === 'leaderboard' ? (
        <LeaderboardTable
          models={filteredModels}
          onSelectModel={(model) => setSelectedModel(model)}
          selectedModelId={selectedModel?.id}
        />
      ) : (
        <ScatterFrontier
          models={filteredModels}
          onSelectModel={(model) => setSelectedModel(model)}
          initialX="vram_peak_mib"
          initialY="generation_tok_s"
        />
      )}

      {/* Selected Model Detail Drawer */}
      {selectedModel && (
        <section aria-label="Detailed model telemetry drawer" className="p-4 sm:p-6 rounded-xl bg-white dark:bg-[#121719] border border-[#006D77]/30 dark:border-[#2DD4BF]/30 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E2E5E5] dark:border-[#242F32] pb-4">
            <div>
              <span className="text-[10px] uppercase font-mono tracking-wider text-[#006D77] dark:text-[#2DD4BF] font-semibold">
                Detailed Telemetry Profile
              </span>
              <h2 className="text-xl sm:text-2xl font-serif font-bold text-[#0E1415] dark:text-[#F2F5F5]">
                {selectedModel.name}
              </h2>
              <div className="text-xs font-mono text-[#475456] dark:text-[#98A8AA] mt-0.5">
                {selectedModel.quantization} • {selectedModel.parameters_b}B Parameters • {selectedModel.family} Family
              </div>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <EvidenceBadge status={selectedModel.evidence_status} />
              <HardwareBadge />
            </div>
          </div>

          {/* Primary Telemetry Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3.5 rounded-lg bg-[#F5F5F3] dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32] space-y-1">
              <div className="text-[10px] uppercase font-mono text-[#526063] dark:text-[#98A8AA]">Decode Throughput</div>
              <div className="text-lg font-bold text-[#0E1415] dark:text-[#F2F5F5] font-mono">
                {selectedModel.generation_tok_s} <span className="text-xs font-normal text-[#526063] dark:text-[#98A8AA]">tok/s</span>
              </div>
              <div className="text-[10px] text-[#475456] dark:text-[#98A8AA] font-sans">Single token generation (b=1)</div>
            </div>

            <div className="p-3.5 rounded-lg bg-[#F5F5F3] dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32] space-y-1">
              <div className="text-[10px] uppercase font-mono text-[#526063] dark:text-[#98A8AA]">Prefill Speed</div>
              <div className="text-lg font-bold text-[#0E1415] dark:text-[#F2F5F5] font-mono">
                {selectedModel.prompt_eval_tok_s} <span className="text-xs font-normal text-[#526063] dark:text-[#98A8AA]">tok/s</span>
              </div>
              <div className="text-[10px] text-[#475456] dark:text-[#98A8AA] font-sans">Prompt evaluation throughput</div>
            </div>

            <div className="p-3.5 rounded-lg bg-[#F5F5F3] dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32] space-y-1">
              <div className="text-[10px] uppercase font-mono text-[#526063] dark:text-[#98A8AA]">Peak VRAM (8k ctx)</div>
              <div className="text-lg font-bold text-[#006D77] dark:text-[#2DD4BF] font-mono">
                {selectedModel.vram_peak_mib} <span className="text-xs font-normal text-[#526063] dark:text-[#98A8AA]">MiB</span>
              </div>
              <div className="text-[10px] text-[#475456] dark:text-[#98A8AA] font-sans">{selectedModel.vram_budget_pct}% of 4096 MiB ceiling</div>
            </div>

            <div className="p-3.5 rounded-lg bg-[#F5F5F3] dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32] space-y-1">
              <div className="text-[10px] uppercase font-mono text-[#526063] dark:text-[#98A8AA]">Time to First Token</div>
              <div className="text-lg font-bold text-[#0E1415] dark:text-[#F2F5F5] font-mono">
                {selectedModel.ttft_ms} <span className="text-xs font-normal text-[#526063] dark:text-[#98A8AA]">ms</span>
              </div>
              <div className="text-[10px] text-[#475456] dark:text-[#98A8AA] font-sans">End-to-end prompt response latency</div>
            </div>
          </div>

          {/* Language Fertility & Zero-shot Quality */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
            {/* Zero Shot Quality */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-[#0E1415] dark:text-[#F2F5F5] flex items-center gap-1.5">
                <Trophy className="w-3.5 h-3.5 text-[#006D77] dark:text-[#2DD4BF]" aria-hidden="true" />
                <span>Zero-Shot Quality Observations</span>
              </h3>
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="p-2.5 rounded-lg bg-[#F5F5F3] dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32] flex justify-between items-center">
                  <span className="text-[#475456] dark:text-[#98A8AA]">ARC-Challenge:</span>
                  <span className="font-bold text-[#006D77] dark:text-[#2DD4BF]">{(selectedModel.quality_scores.arc_challenge * 100).toFixed(1)}%</span>
                </div>
                <div className="p-2.5 rounded-lg bg-[#F5F5F3] dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32] flex justify-between items-center">
                  <span className="text-[#475456] dark:text-[#98A8AA]">HellaSwag:</span>
                  <span className="font-bold text-[#006D77] dark:text-[#2DD4BF]">{(selectedModel.quality_scores.hellaswag * 100).toFixed(1)}%</span>
                </div>
                <div className="p-2.5 rounded-lg bg-[#F5F5F3] dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32] flex justify-between items-center">
                  <span className="text-[#475456] dark:text-[#98A8AA]">GSM8K Flex:</span>
                  <span className="font-bold text-[#006D77] dark:text-[#2DD4BF]">{(selectedModel.quality_scores.gsm8k_flex * 100).toFixed(1)}%</span>
                </div>
                <div className="p-2.5 rounded-lg bg-[#F5F5F3] dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32] flex justify-between items-center">
                  <span className="text-[#475456] dark:text-[#98A8AA]">IFEval Strict:</span>
                  <span className="font-bold text-[#006D77] dark:text-[#2DD4BF]">{(selectedModel.quality_scores.ifeval_strict * 100).toFixed(1)}%</span>
                </div>
              </div>
              <div className="text-[11px] text-[#475456] dark:text-[#98A8AA] leading-relaxed">
                Evaluated under greedy decoding (T=0.0) against standardized first-100 subsets to verify baseline zero-shot reasoning fidelity under quantization.
              </div>
            </div>

            {/* Language Fertility */}
            {selectedModel.fertility && selectedModel.fertility.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#0E1415] dark:text-[#F2F5F5] flex items-center gap-1.5">
                  <Globe className="w-3.5 h-3.5 text-[#0284C7] dark:text-[#38BDF8]" aria-hidden="true" />
                  <span>Tokenizer Sub-Word Fertility (pt-BR vs en-US)</span>
                </h3>
                <div className="rounded-lg border border-[#E2E5E5] dark:border-[#242F32] overflow-hidden text-xs">
                  <table className="w-full text-left font-mono" aria-label="Language fertility table">
                    <thead className="bg-[#F5F5F3] dark:bg-[#182022] text-[#475456] dark:text-[#98A8AA] text-[11px]">
                      <tr>
                        <th scope="col" className="p-2">Lang</th>
                        <th scope="col" className="p-2">Words</th>
                        <th scope="col" className="p-2">Tokens</th>
                        <th scope="col" className="p-2">Fertility Ratio</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#ECEEED] dark:divide-[#1C2426] text-[#0E1415] dark:text-[#F2F5F5]">
                      {selectedModel.fertility.map((item) => (
                        <tr key={item.language} className="hover:bg-[#F5F5F3] dark:hover:bg-[#182022]">
                          <td className="p-2 font-bold text-[#006D77] dark:text-[#2DD4BF]">{item.language}</td>
                          <td className="p-2">{item.word_count}</td>
                          <td className="p-2">{item.token_count}</td>
                          <td className="p-2 font-bold text-[#B45309] dark:text-[#FBBF24]">{item.fertility_ratio}x</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="text-[11px] text-[#475456] dark:text-[#98A8AA] leading-relaxed">
                  <strong>Practical Consequence:</strong> Portuguese content requires ~33% more sub-word tokens than English for equivalent text, which silently shrinks effective context window and adds a 33% latency penalty.
                </div>
              </div>
            )}
          </div>

          {/* Action to Compare */}
          <div className="pt-2 flex justify-end">
            <Link
              href={`/compare?m1=${selectedModel.id}`}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-[#006D77] dark:bg-[#2DD4BF] hover:opacity-90 text-white dark:text-[#0A0E0F] font-bold text-xs transition-opacity shadow-sm"
            >
              <GitCompare className="w-4 h-4" aria-hidden="true" />
              <span>Compare {selectedModel.name} in Matrix</span>
            </Link>
          </div>
        </section>
      )}
    </div>
  );
}
