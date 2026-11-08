'use client';

import React, { useState, useMemo } from 'react';
import researchData, { BenchmarkItem } from '@/data/researchData';
import DataTable from '@/components/DataTable';
import EvidenceBadge from '@/components/EvidenceBadge';
import HardwareBadge from '@/components/HardwareBadge';
import IncompatibilityAlert from '@/components/IncompatibilityAlert';
import { ColumnDef } from '@tanstack/react-table';
import {
  BarChart2,
  CheckCircle2,
  AlertCircle,
  FileText,
  ExternalLink,
  Layers,
  ShieldAlert,
  Info,
  Sliders
} from 'lucide-react';

export default function BenchmarkExplorerPage() {
  const { benchmarks } = researchData;
  const [selectedBenchmark, setSelectedBenchmark] = useState<BenchmarkItem | null>(benchmarks[0]);
  const [selectedTrackFilter, setSelectedTrackFilter] = useState<string>('all');

  const tracks = useMemo(() => {
    return [
      { label: 'All Tracks', value: 'all' },
      { label: 'Track A (Inference)', value: 'Track A — Inference efficiency' },
      { label: 'Track B (Robustness)', value: 'Track B — Model quality & robustness' },
      { label: 'Track C (Long-Context)', value: 'Track C — Long-context capability' },
      { label: 'Track D (Concurrency)', value: 'Track D — Concurrency & serving' },
      { label: 'Track F (Defensive Cyber)', value: 'Track F — Defensive cybersecurity' },
    ];
  }, []);

  const filteredBenchmarks = useMemo(() => {
    if (selectedTrackFilter === 'all') return benchmarks;
    return benchmarks.filter((b) => b.track.includes(selectedTrackFilter.split(' ')[1]));
  }, [benchmarks, selectedTrackFilter]);

  const columns: ColumnDef<BenchmarkItem>[] = useMemo(
    () => [
      {
        accessorKey: 'title',
        header: 'Benchmark Suite',
        cell: ({ row }) => {
          const item = row.original;
          const isSelected = selectedBenchmark?.id === item.id;
          return (
            <div
              onClick={() => setSelectedBenchmark(item)}
              className="cursor-pointer group py-1"
            >
              <div className="font-semibold text-[#0E1415] dark:text-[#F2F5F5] group-hover:text-[#006D77] dark:group-hover:text-[#2DD4BF] transition-colors flex items-center gap-1.5">
                <span>{item.title}</span>
                {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-[#006D77] dark:bg-[#2DD4BF]" />}
              </div>
              <div className="text-[11px] text-[#526063] dark:text-[#98A8AA] font-mono mt-0.5">{item.track}</div>
            </div>
          );
        }
      },
      {
        accessorKey: 'evidence_status',
        header: 'Evidence Status',
        cell: ({ row }) => <EvidenceBadge status={row.original.evidence_status} />
      },
      {
        accessorKey: 'hardware',
        header: 'Hardware Host',
        cell: () => <HardwareBadge />
      },
      {
        accessorKey: 'sample_size',
        header: 'Sample (n)',
        cell: ({ row }) => (
          <span className="font-mono text-[#475456] dark:text-[#98A8AA]">
            n = {row.original.sample_size}
          </span>
        )
      },
      {
        accessorKey: 'results_summary',
        header: 'Observed Outcome',
        cell: ({ row }) => (
          <div className="max-w-md text-[11px] text-[#475456] dark:text-[#98A8AA] leading-snug">
            <span className="font-semibold text-[#0E1415] dark:text-[#F2F5F5]">{row.original.metric_name}: </span>
            <span>{row.original.results_summary}</span>
          </div>
        )
      },
      {
        id: 'actions',
        header: 'Details',
        cell: ({ row }) => (
          <button
            onClick={() => setSelectedBenchmark(row.original)}
            className="text-[11px] font-semibold text-[#006D77] dark:text-[#2DD4BF] hover:underline"
          >
            Inspect
          </button>
        )
      }
    ],
    [selectedBenchmark]
  );

  return (
    <div className="space-y-8">
      {/* Header (Epoch AI Editorial Authority) */}
      <div className="space-y-2 border-b border-[#E2E5E5] dark:border-[#242F32] pb-6">
        <div className="flex items-center gap-2 text-xs font-mono text-[#006D77] dark:text-[#2DD4BF]">
          <BarChart2 className="w-4 h-4" />
          <span>EXPERIMENTAL EVIDENCE REPOSITORY</span>
        </div>
        <h1 className="text-2xl sm:text-4xl font-serif font-medium tracking-tight text-[#0E1415] dark:text-[#F2F5F5]">
          Benchmark & Evaluation Explorer
        </h1>
        <p className="text-xs sm:text-sm text-[#475456] dark:text-[#98A8AA] max-w-3xl leading-relaxed">
          Filterable matrix of measured performance, robustness, grammar constraints, tool-calling longevity,
          and defensive cybersecurity evaluations. Every metric links directly to source artifacts.
        </p>
      </div>

      {/* Track Filter Pills */}
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        {tracks.map((t) => (
          <button
            key={t.value}
            onClick={() => setSelectedTrackFilter(t.value)}
            className={`px-3 py-1.5 rounded-md border font-medium transition-colors ${
              selectedTrackFilter === t.value
                ? 'bg-[#006D77] dark:bg-[#2DD4BF] text-white dark:text-[#0A0E0F] border-[#006D77] dark:border-[#2DD4BF] font-semibold shadow-sm'
                : 'bg-white dark:bg-[#121719] text-[#475456] dark:text-[#98A8AA] border-[#E2E5E5] dark:border-[#242F32] hover:bg-[#F5F5F3] dark:hover:bg-[#182022]'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Main Benchmarks Table */}
      <section className="space-y-4">
        <DataTable
          columns={columns}
          data={filteredBenchmarks}
          searchPlaceholder="Search benchmark title, metric, or outcome..."
        />
      </section>

      {/* Selected Benchmark Deep-Dive Card */}
      {selectedBenchmark && (
        <section className="p-6 rounded-xl bg-white dark:bg-[#121719] border border-[#006D77]/30 dark:border-[#2DD4BF]/30 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E2E5E5] dark:border-[#242F32] pb-4">
            <div>
              <span className="text-[10px] font-mono uppercase tracking-wider text-[#006D77] dark:text-[#2DD4BF] font-semibold">
                {selectedBenchmark.track}
              </span>
              <h3 className="text-xl sm:text-2xl font-serif font-bold text-[#0E1415] dark:text-[#F2F5F5] tracking-tight">
                {selectedBenchmark.title}
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <EvidenceBadge status={selectedBenchmark.evidence_status} />
              <HardwareBadge />
            </div>
          </div>

          {/* If ready benchmark, show clear notice */}
          {selectedBenchmark.evidence_status === 'ready' && (
            <IncompatibilityAlert
              type="info"
              title="Ready Benchmark Specification (Unmeasured Model)"
            >
              This benchmark specification and deterministic evaluator are tested and ready in the repository. No model
              execution run has been performed against this suite yet; zero synthetic results have been fabricated.
            </IncompatibilityAlert>
          )}

          {/* Details Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs sm:text-sm">
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold text-[#0E1415] dark:text-[#F2F5F5] mb-1 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-[#0E7A5A] dark:text-[#34D399]" />
                  <span>Protocol & Primary Outcome</span>
                </h4>
                <div className="bg-[#F5F5F3] dark:bg-[#182022] p-3.5 rounded-lg border border-[#E2E5E5] dark:border-[#242F32] text-[#475456] dark:text-[#98A8AA] leading-relaxed font-sans">
                  <div className="font-mono text-xs text-[#006D77] dark:text-[#2DD4BF] mb-1 font-semibold">
                    Metric: {selectedBenchmark.metric_name} (n = {selectedBenchmark.sample_size})
                  </div>
                  <div className="text-[#0E1415] dark:text-[#F2F5F5]">{selectedBenchmark.results_summary}</div>
                  <div className="mt-2 text-xs text-[#526063] dark:text-[#98A8AA]">{selectedBenchmark.details}</div>
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-[#0E1415] dark:text-[#F2F5F5] mb-1 flex items-center gap-1.5">
                  <FileText className="w-4 h-4 text-[#006D77] dark:text-[#2DD4BF]" />
                  <span>Source Documentation & Report</span>
                </h4>
                <a
                  href={`https://github.com/AndersonTavares0/llm-research-bench/blob/main/${selectedBenchmark.source_doc}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 p-2.5 rounded-md bg-[#F5F5F3] dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32] text-xs font-mono text-[#006D77] dark:text-[#2DD4BF] hover:opacity-80 transition-opacity"
                >
                  <span>{selectedBenchmark.source_doc}</span>
                  <ExternalLink className="w-3.5 h-3.5 opacity-70" />
                </a>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <h4 className="font-semibold text-[#0E1415] dark:text-[#F2F5F5] mb-1 flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4 text-[#B45309] dark:text-[#FBBF24]" />
                  <span>Documented Scientific Limitations</span>
                </h4>
                <div className="bg-[#FEF3C7]/50 dark:bg-[#382806]/40 p-3.5 rounded-lg border border-[#B45309]/30 dark:border-[#FBBF24]/30 text-[#B45309] dark:text-[#FBBF24] leading-relaxed text-xs">
                  {selectedBenchmark.limitations}
                </div>
              </div>

              {selectedBenchmark.raw_paths && selectedBenchmark.raw_paths.length > 0 && (
                <div>
                  <h4 className="font-semibold text-[#0E1415] dark:text-[#F2F5F5] mb-1 flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-[#006D77] dark:text-[#2DD4BF]" />
                    <span>Raw Evidence Directories</span>
                  </h4>
                  <div className="space-y-1 font-mono text-[11px]">
                    {selectedBenchmark.raw_paths.map((p) => (
                      <div
                        key={p}
                        className="p-1.5 rounded-md bg-[#F5F5F3] dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32] text-[#475456] dark:text-[#98A8AA] truncate"
                      >
                        {p}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
