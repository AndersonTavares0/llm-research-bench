'use client';

import React, { useState, useMemo } from 'react';
import researchData from '@/data/researchData';
import EvidenceBadge from '@/components/EvidenceBadge';
import HardwareBadge from '@/components/HardwareBadge';
import {
  Activity,
  CheckCircle2,
  AlertCircle,
  FileText,
  ExternalLink,
  ShieldCheck,
  Search,
  Filter,
  Download,
  BookOpen,
  ArrowRight
} from 'lucide-react';

export default function MethodologyPage() {
  const { research_questions } = researchData;

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTrackFilter, setSelectedTrackFilter] = useState('all');
  const [selectedStatusFilter, setSelectedStatusFilter] = useState('all');

  const tracks = useMemo(() => {
    return [
      { label: 'All Tracks (A–F)', value: 'all' },
      { label: 'Track A (Inference)', value: 'Track A' },
      { label: 'Track B (Quality)', value: 'Track B' },
      { label: 'Track C (Context)', value: 'Track C' },
      { label: 'Track D (Concurrency)', value: 'Track D' },
      { label: 'Track E (Physics)', value: 'Track E' },
      { label: 'Track F (Cyber)', value: 'Track F' },
    ];
  }, []);

  const statuses = useMemo(() => {
    return [
      { label: 'All Evidence Statuses', value: 'all' },
      { label: 'Measured Only', value: 'measured' },
      { label: 'Partial Only', value: 'partial' },
      { label: 'Analytical Only', value: 'analytical' },
      { label: 'Ready Only', value: 'ready' },
    ];
  }, []);

  const filteredRQs = useMemo(() => {
    return research_questions.filter((rq) => {
      const matchStatus = selectedStatusFilter === 'all' || rq.status === selectedStatusFilter;
      const matchTrack = selectedTrackFilter === 'all' || rq.track.startsWith(selectedTrackFilter);
      const matchSearch =
        rq.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        rq.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        rq.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
        rq.findings_summary.toLowerCase().includes(searchQuery.toLowerCase());
      return matchStatus && matchTrack && matchSearch;
    });
  }, [research_questions, selectedStatusFilter, selectedTrackFilter, searchQuery]);

  return (
    <div className="space-y-12">
      {/* Header (Epoch AI Editorial Authority) */}
      <div className="space-y-3 border-b border-[#E2E5E5] dark:border-[#242F32] pb-6">
        <div className="flex items-center gap-2 text-xs font-mono text-[#006D77] dark:text-[#2DD4BF]">
          <Activity className="w-4 h-4" />
          <span>SCIENTIFIC CHARTER & RIGOROUS EVIDENCE TAXONOMY</span>
        </div>
        <h1 className="text-2xl sm:text-4xl font-serif font-medium tracking-tight text-[#0E1415] dark:text-[#F2F5F5]">
          Research Methodology & Questions
        </h1>
        <p className="text-xs sm:text-sm text-[#475456] dark:text-[#98A8AA] max-w-3xl leading-relaxed">
          The SLM-Limits research program consolidates 24 deduplicated research questions across 6 core tracks.
          Every conclusion is categorized according to strict evidence classifications to ensure scientific reproducibility.
        </p>
      </div>

      {/* Central Question Callout */}
      <section className="p-6 rounded-xl bg-white dark:bg-[#121719] border-l-4 border-l-[#006D77] dark:border-l-[#2DD4BF] border border-[#E2E5E5] dark:border-[#242F32] shadow-sm space-y-3">
        <div className="flex items-center gap-2 text-[#006D77] dark:text-[#2DD4BF]">
          <ShieldCheck className="w-5 h-5" />
          <h2 className="text-base sm:text-lg font-serif font-bold tracking-tight">
            Central Research Question
          </h2>
        </div>
        <blockquote className="text-base sm:text-lg font-serif font-medium text-[#0E1415] dark:text-[#F2F5F5] italic pl-2 py-1 leading-relaxed">
          &ldquo;What are the practical limits of Small Language Models (≈0.5B–4B parameters) on legacy constrained
          hardware — primarily one GTX 1050 Ti with 4096 MiB VRAM — and how can their efficiency, capabilities,
          reliability, and security be improved within those limits?&rdquo;
        </blockquote>
      </section>

      {/* Evidence Taxonomy Guide */}
      <section className="space-y-4">
        <h2 className="text-xl font-serif font-semibold text-[#0E1415] dark:text-[#F2F5F5] tracking-tight">
          Evidence Classification Hierarchy
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
          <div className="p-4 rounded-xl bg-white dark:bg-[#121719] border border-[#0E7A5A]/30 dark:border-[#34D399]/40 space-y-2 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[#0E7A5A] dark:text-[#34D399]">① Measured</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#E7F6F1] dark:bg-[#063826] text-[#0E7A5A] dark:text-[#34D399] font-semibold">Empirical</span>
            </div>
            <p className="text-[#475456] dark:text-[#98A8AA] leading-relaxed">
              Recorded in results/ on real physical hardware. Single-host, exploratory observations unless replicated.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-white dark:bg-[#121719] border border-[#B45309]/30 dark:border-[#FBBF24]/40 space-y-2 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[#B45309] dark:text-[#FBBF24]">② Partial</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#FEF3C7] dark:bg-[#382806] text-[#B45309] dark:text-[#FBBF24] font-semibold">Ongoing</span>
            </div>
            <p className="text-[#475456] dark:text-[#98A8AA] leading-relaxed">
              Measured but incomplete campaign designs, ongoing grids, or halted pilot studies (e.g. HotpotQA).
            </p>
          </div>

          <div className="p-4 rounded-xl bg-white dark:bg-[#121719] border border-[#4338CA]/30 dark:border-[#818CF8]/40 space-y-2 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[#4338CA] dark:text-[#818CF8]">③ Analytical</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#EEF2FF] dark:bg-[#181C38] text-[#4338CA] dark:text-[#818CF8] font-semibold">Model/Math</span>
            </div>
            <p className="text-[#475456] dark:text-[#98A8AA] leading-relaxed">
              Computed mathematical model assumptions (e.g. Roofline proxy, Kn cache math), not measured bus utilization.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] space-y-2 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[#475456] dark:text-[#98A8AA]">④ Ready</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#F5F5F3] dark:bg-[#182022] text-[#475456] dark:text-[#98A8AA] font-semibold">Unmeasured</span>
            </div>
            <p className="text-[#475456] dark:text-[#98A8AA] leading-relaxed">
              Benchmark specification & deterministic evaluator verified; NO model has been run; 0 fabricated scores.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] space-y-2 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[#526063] dark:text-[#98A8AA]">⑤ Unknown</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#F5F5F3] dark:bg-[#182022] text-[#526063] dark:text-[#98A8AA] font-semibold">Unstudied</span>
            </div>
            <p className="text-[#475456] dark:text-[#98A8AA] leading-relaxed">
              Not explored in this repository (e.g. fine-tuning, LoRA adaptation, wattage/energy instrumentation).
            </p>
          </div>
        </div>
      </section>

      {/* 24 Research Questions Explorer */}
      <section className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-xl sm:text-2xl font-serif font-semibold text-[#0E1415] dark:text-[#F2F5F5] tracking-tight">
              The 24 Deduplicated Research Questions
            </h2>
            <p className="text-xs sm:text-sm text-[#475456] dark:text-[#98A8AA]">
              Interactive inquiry catalog across Tracks A (Inference), B (Quality), C (Long-Context), D (Concurrency), E (Physics), and F (Cybersecurity).
            </p>
          </div>
          <span className="text-xs font-mono px-2.5 py-1 rounded bg-[#F5F5F3] dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32] text-[#006D77] dark:text-[#2DD4BF] font-semibold">
            Showing {filteredRQs.length} of {research_questions.length} RQs
          </span>
        </div>

        {/* Filter Controls Bar */}
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
          {/* Search Bar */}
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-[#526063] dark:text-[#98A8AA]" aria-hidden="true" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search RQs by ID, title, or findings..."
              aria-label="Search research questions by ID or title"
              className="w-full pl-9 pr-4 py-2 text-xs bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] rounded-md text-[#0E1415] dark:text-[#F2F5F5] placeholder-[#526063] dark:placeholder-[#98A8AA] focus:outline-none focus:border-[#006D77] focus:ring-1 focus:ring-[#006D77] dark:focus:border-[#2DD4BF] dark:focus:ring-[#2DD4BF]"
            />
          </div>

          {/* Track Filter */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <select
              value={selectedTrackFilter}
              onChange={(e) => setSelectedTrackFilter(e.target.value)}
              aria-label="Filter by research track"
              className="bg-white dark:bg-[#121719] text-[#0E1415] dark:text-[#F2F5F5] border border-[#E2E5E5] dark:border-[#242F32] px-3 py-2 rounded-md outline-none cursor-pointer focus:border-[#006D77] dark:focus:border-[#2DD4BF]"
            >
              {tracks.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>

            {/* Status Filter */}
            <select
              value={selectedStatusFilter}
              onChange={(e) => setSelectedStatusFilter(e.target.value)}
              aria-label="Filter by evidence status"
              className="bg-white dark:bg-[#121719] text-[#0E1415] dark:text-[#F2F5F5] border border-[#E2E5E5] dark:border-[#242F32] px-3 py-2 rounded-md outline-none cursor-pointer focus:border-[#006D77] dark:focus:border-[#2DD4BF]"
            >
              {statuses.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* RQs Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredRQs.map((rq) => (
            <div
              key={rq.id}
              className="p-5 rounded-xl bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] hover:border-[#006D77] dark:hover:border-[#2DD4BF]/60 transition-colors flex flex-col justify-between space-y-3 shadow-sm"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-[#006D77] dark:text-[#2DD4BF] bg-[#E6F3F4] dark:bg-[#0D2C28] px-2 py-0.5 rounded border border-[#006D77]/20 dark:border-[#2DD4BF]/30">
                    {rq.id}
                  </span>
                  <EvidenceBadge status={rq.status} />
                </div>
                <div className="text-[11px] font-mono text-[#526063] dark:text-[#98A8AA]">{rq.track}</div>
                <h3 className="text-base font-serif font-bold text-[#0E1415] dark:text-[#F2F5F5]">{rq.title}</h3>
                <p className="text-xs sm:text-sm text-[#475456] dark:text-[#98A8AA] font-sans leading-relaxed">
                  {rq.question}
                </p>
              </div>

              <div className="pt-3 border-t border-[#ECEEED] dark:border-[#1C2426] space-y-1.5 text-xs">
                <div className="flex items-center gap-1.5 text-[11px] font-mono text-[#475456] dark:text-[#98A8AA]">
                  <span className="text-[#526063] dark:text-[#98A8AA]">Metric:</span>
                  <span className="text-[#0E1415] dark:text-[#F2F5F5] font-semibold truncate">{rq.primary_metric}</span>
                </div>
                <div className="bg-[#F5F5F3] dark:bg-[#182022] p-2.5 rounded border border-[#E2E5E5] dark:border-[#242F32] text-[11px] text-[#475456] dark:text-[#98A8AA] leading-normal">
                  <span className="font-semibold text-[#0E1415] dark:text-[#F2F5F5]">Current Findings: </span>
                  <span>{rq.findings_summary}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Reports & PDF Downloads */}
      <section className="p-6 rounded-xl bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] space-y-4 shadow-sm">
        <div className="flex items-center justify-between border-b border-[#E2E5E5] dark:border-[#242F32] pb-3">
          <div className="flex items-center gap-2 text-[#0E1415] dark:text-[#F2F5F5] font-serif font-bold text-base">
            <Download className="w-5 h-5 text-[#006D77] dark:text-[#2DD4BF]" />
            <span>Comprehensive Scientific Reports (LaTeX / PDF)</span>
          </div>
          <span className="text-xs font-mono text-[#526063] dark:text-[#98A8AA]">Compiled with Tectonic</span>
        </div>

        <p className="text-xs sm:text-sm text-[#475456] dark:text-[#98A8AA] leading-relaxed">
          The complete findings, statistical interval bounds, thermal drift curves, and architectural derivations
          are compiled into twin English and Portuguese publication-ready reports.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
          <a
            href="https://github.com/AndersonTavares0/llm-research-bench/blob/main/reports/en-US/report_en-US.pdf"
            target="_blank"
            rel="noreferrer"
            className="p-4 rounded-xl bg-[#F5F5F3] dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32] hover:border-[#006D77] dark:hover:border-[#2DD4BF] transition-colors flex items-center justify-between group shadow-sm"
          >
            <div className="space-y-1">
              <div className="font-serif font-bold text-[#0E1415] dark:text-[#F2F5F5] group-hover:text-[#006D77] dark:group-hover:text-[#2DD4BF] transition-colors flex items-center gap-1.5">
                <FileText className="w-4 h-4 text-[#006D77] dark:text-[#2DD4BF]" />
                <span>English Research Report</span>
              </div>
              <div className="text-xs text-[#526063] dark:text-[#98A8AA] font-mono">reports/en-US/report_en-US.pdf</div>
            </div>
            <ExternalLink className="w-4 h-4 text-[#526063] group-hover:text-[#006D77] dark:group-hover:text-[#2DD4BF] transition-colors" />
          </a>

          <a
            href="https://github.com/AndersonTavares0/llm-research-bench/blob/main/reports/pt-BR/report_pt-BR.pdf"
            target="_blank"
            rel="noreferrer"
            className="p-4 rounded-xl bg-[#F5F5F3] dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32] hover:border-[#0E7A5A] dark:hover:border-[#34D399] transition-colors flex items-center justify-between group shadow-sm"
          >
            <div className="space-y-1">
              <div className="font-serif font-bold text-[#0E1415] dark:text-[#F2F5F5] group-hover:text-[#0E7A5A] dark:group-hover:text-[#34D399] transition-colors flex items-center gap-1.5">
                <FileText className="w-4 h-4 text-[#0E7A5A] dark:text-[#34D399]" />
                <span>Relatório Técnico em Português</span>
              </div>
              <div className="text-xs text-[#526063] dark:text-[#98A8AA] font-mono">reports/pt-BR/report_pt-BR.pdf</div>
            </div>
            <ExternalLink className="w-4 h-4 text-[#526063] group-hover:text-[#0E7A5A] dark:group-hover:text-[#34D399] transition-colors" />
          </a>
        </div>
      </section>
    </div>
  );
}
