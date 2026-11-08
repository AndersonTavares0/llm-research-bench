'use client';

import React, { useState, useMemo, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import researchData from '@/data/researchData';
import EvidenceBadge from '@/components/EvidenceBadge';
import HardwareBadge from '@/components/HardwareBadge';
import IncompatibilityAlert from '@/components/IncompatibilityAlert';
import {
  Layers,
  CheckCircle2,
  AlertCircle,
  FileText,
  ExternalLink,
  Cpu,
  BarChart2,
  TrendingDown,
  Database,
  ArrowRight
} from 'lucide-react';
import type * as echarts from 'echarts';

const EChartWrapper = dynamic(() => import('@/components/EChartWrapper'), { ssr: false });

interface ExperimentDef {
  id: string;
  shortTitle: string;
  fullTitle: string;
  track: string;
  evidence_status: 'measured' | 'partial' | 'analytical' | 'ready';
  hardware: string;
  hypothesis: string;
  protocol: string;
  findings: string;
  limitations: string;
  source_doc: string;
  raw_paths: string[];
  renderChart: () => echarts.EChartsOption;
  tableData?: { headers: string[]; rows: (string | number)[][] };
}

function ExperimentsContent() {
  const searchParams = useSearchParams();
  const initialExp = searchParams.get('exp') || 'h1-kv-scaling';

  const [activeExpId, setActiveExpId] = useState<string>(initialExp);

  const experiments: ExperimentDef[] = useMemo(
    () => [
      {
        id: 'h1-kv-scaling',
        shortTitle: '1. KV Cache Physics (H1)',
        fullTitle: 'H1 Context × KV Cache Scaling & Precision Frontier',
        track: 'Track A — Inference Efficiency',
        evidence_status: 'measured',
        hardware: 'GTX 1050 Ti (4 GiB GDDR5)',
        hypothesis:
          'Quantizing the KV cache to q8_0 will substantially reduce memory growth per token without causing needle retrieval degradation in long contexts.',
        protocol:
          'Evaluated Qwen3-1.7B at 2048, 4096, and 8192 context lengths under f16 and q8_0 KV precision on pinned llama.cpp b12024. Measured 250ms VRAM telemetry.',
        findings:
          'Confirmed. Memory slope drops from ≈113.0 KiB/token (f16) to 60.3 KiB/token (q8_0), with a fixed base model allocation of ~1206 MiB. At 8192 context, peak VRAM drops from 2,110.1 MiB to 1,694.1 MiB (-19.6%). Perfect 30/30 needle retrieval preserved across depths d10, d50, and d90.',
        limitations:
          '30/30 needle retrieval ceiling cannot bound subtle semantic comprehension degradation. Paired n=20 quality evaluation (ARC .35→.40, HellaSwag .40→.40) is underpowered.',
        source_doc: 'docs/benchmarks/h1-context-kv-results.md',
        raw_paths: [
          'results/sweeps/ctxkv2',
          'results/campaigns/gpu-lab-longctx-needle-kv-f16-d10',
          'results/campaigns/gpu-lab-longctx-needle-kv-q8-d10'
        ],
        tableData: {
          headers: ['Context (Tokens)', 'KV Precision', 'Peak VRAM (MiB)', 'Duration (s)', 'Status'],
          rows: [
            [2048, 'f16', 1432.1, 6.1, 'measured'],
            [2048, 'q8_0', 1332.1, 5.3, 'measured'],
            [4096, 'f16', 1658.1, 5.2, 'measured'],
            [4096, 'q8_0', 1452.1, 5.3, 'measured'],
            [8192, 'f16', 2110.1, 5.2, 'measured'],
            [8192, 'q8_0', 1694.1, 5.3, 'measured']
          ]
        },
        renderChart: () => ({
          tooltip: { trigger: 'axis' },
          legend: { data: ['KV f16 (113 KiB/tok)', 'KV q8_0 (60 KiB/tok)'], textStyle: { color: '#94a3b8' } },
          xAxis: {
            type: 'category',
            data: ['2,048 Tokens', '4,096 Tokens', '8,192 Tokens'],
            axisLabel: { color: '#cbd5e1' }
          },
          yAxis: {
            type: 'value',
            min: 1000,
            max: 2400,
            name: 'Peak VRAM (MiB)',
            axisLabel: { color: '#cbd5e1' },
            splitLine: { lineStyle: { color: '#1e293b' } }
          },
          series: [
            {
              name: 'KV f16 (113 KiB/tok)',
              type: 'line',
              data: [1432.1, 1658.1, 2110.1],
              itemStyle: { color: '#38bdf8' },
              lineStyle: { width: 3 }
            },
            {
              name: 'KV q8_0 (60 KiB/tok)',
              type: 'line',
              data: [1332.1, 1452.1, 1694.1],
              itemStyle: { color: '#10b981' },
              lineStyle: { width: 3 }
            }
          ]
        })
      },
      {
        id: 'generation-budget',
        shortTitle: '2. Completion Cap & Truncation',
        fullTitle: 'Completion Token Budget Truncation Audit (256 vs 512)',
        track: 'Track C — Long-Context Capability',
        evidence_status: 'measured',
        hardware: 'GTX 1050 Ti (4 GiB GDDR5)',
        hypothesis:
          'Long-context structured schema extraction failures were caused by completion token budget exhaustion rather than model capability collapse.',
        protocol:
          'Evaluated the exact same 30 deterministic prompts under two conditions: completion cap 256 tokens vs 512 tokens.',
        findings:
          'Raising the completion cap from 256 to 512 resolved 100% of observed truncations. 24/30 valid at cap 256 → 30/30 valid at cap 512. All 6 failures at cap 256 ended with finish_reason="length" and subsequently finished validly at 261–321 tokens. Paired exact McNemar p = .03125.',
        limitations:
          'One deterministic 30-item fixed set, single model and config. Demonstrates these exact truncation failures, not universal completion cap dynamics.',
        source_doc: 'docs/benchmarks/generation-budget-longctx-full30.md',
        raw_paths: [
          'results/campaigns/gpu-lab-longctx-audit-reason-256',
          'results/campaigns/gpu-lab-longctx-audit-reason-512-full30'
        ],
        tableData: {
          headers: ['Condition', 'Cap', 'Valid Outputs', 'Length Truncations', 'McNemar p-value'],
          rows: [
            ['Cap 256 Arm', '256 tokens', '24 / 30 (80.0%)', '6 / 30 (20.0%)', 'Baseline'],
            ['Cap 512 Arm', '512 tokens', '30 / 30 (100.0%)', '0 / 30 (0.0%)', 'p = .03125']
          ]
        },
        renderChart: () => ({
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: ['Cap 256 Tokens', 'Cap 512 Tokens'], axisLabel: { color: '#cbd5e1' } },
          yAxis: { type: 'value', max: 30, name: 'Items', axisLabel: { color: '#cbd5e1' }, splitLine: { lineStyle: { color: '#1e293b' } } },
          series: [
            {
              name: 'Valid Schema Output',
              type: 'bar',
              stack: 'total',
              data: [24, 30],
              itemStyle: { color: '#10b981' }
            },
            {
              name: 'Truncated (finish_reason=length)',
              type: 'bar',
              stack: 'total',
              data: [6, 0],
              itemStyle: { color: '#f43f5e' }
            }
          ]
        })
      },
      {
        id: 'constraint-formatting',
        shortTitle: '3. Grammar Constraints',
        fullTitle: 'JSON Schema vs Generic JSON-Object Formatting at 7k Context',
        track: 'Track C — Long-Context Capability',
        evidence_status: 'measured',
        hardware: 'GTX 1050 Ti (4 GiB GDDR5)',
        hypothesis:
          'Strict grammar enforcement via JSON Schema prevents syntactic breakdown in 7,000-token contexts compared to unconstrained json_object mode.',
        protocol:
          '30 paired structured extraction cases evaluated under identical prompt text; only the response_format grammar parameter was altered. Repeated across two runs.',
        findings:
          'JSON Schema achieved 30/30 validity in both run 1 and run 2. Generic json_object collapsed to 18/30 in each run (12/0 discordance, exact McNemar p = .000488).',
        limitations:
          'Syntactic schema conformance does not imply semantic factual correctness. Single prompt and model family.',
        source_doc: 'docs/benchmarks/constraint-format-7k.md',
        raw_paths: [
          'results/campaigns/gpu-lab-longctx-grammar7k-json-schema',
          'results/campaigns/gpu-lab-longctx-grammar7k-json-object'
        ],
        tableData: {
          headers: ['Format Arm', 'Run 1 Valid', 'Run 2 Valid', 'Discordant Pairs', 'McNemar p-value'],
          rows: [
            ['JSON Schema', '30 / 30', '30 / 30', '12 / 0 (in favor of Schema)', 'p = .000488'],
            ['json_object', '18 / 30', '18 / 30', '-', 'Baseline']
          ]
        },
        renderChart: () => ({
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: ['JSON Schema (Grammar)', 'Generic json_object'], axisLabel: { color: '#cbd5e1' } },
          yAxis: { type: 'value', max: 30, name: 'Valid Extractions', axisLabel: { color: '#cbd5e1' }, splitLine: { lineStyle: { color: '#1e293b' } } },
          series: [
            {
              name: 'Valid Extractions (n=30)',
              type: 'bar',
              data: [30, 18],
              itemStyle: {
                color: (params: any) => (params.dataIndex === 0 ? '#10b981' : '#f59e0b')
              }
            }
          ]
        })
      },
      {
        id: 'tool-calling',
        shortTitle: '4. Tool Calling Longevity',
        fullTitle: 'Native vs JSON-Mediated Tool Calling Across Context Lengths',
        track: 'Track C — Long-Context Capability',
        evidence_status: 'measured',
        hardware: 'GTX 1050 Ti (4 GiB GDDR5)',
        hypothesis:
          'Native server-side tool calling retains dispatch fidelity as context expands from 1.9k to 7k tokens, while prompt-injected JSON wrappers degrade.',
        protocol:
          '3 diagnostic tools evaluated across 18 synthetic test cases at ~1.9k, ~3.8k, and ~7k tokens.',
        findings:
          'Native tool calling achieved 18/18 (100%) valid dispatches. JSON-mediated wrapper variants scored only 2 to 8 out of 18, collapsing under long contexts.',
        limitations:
          'System prompts and schemas differ between native and JSON wrapper arms; fixed synthetic test set.',
        source_doc: 'docs/benchmarks/tool-calling-long-context.md',
        raw_paths: [
          'results/campaigns/gpu-lab-toolctx-n1900',
          'results/campaigns/gpu-lab-toolctx-n3800',
          'results/campaigns/gpu-lab-toolctx-n7k'
        ],
        tableData: {
          headers: ['Protocol Arm', 'Context ~1.9k', 'Context ~3.8k', 'Context ~7k', 'Total Rate'],
          rows: [
            ['Native Tool Calling', '6 / 6 (100%)', '6 / 6 (100%)', '6 / 6 (100%)', '18 / 18 (100%)'],
            ['JSON-Mediated Wrapper', '4 / 6 (66.7%)', '2 / 6 (33.3%)', '2 / 6 (33.3%)', '8 / 18 (44.4%)']
          ]
        },
        renderChart: () => ({
          tooltip: { trigger: 'axis' },
          legend: { data: ['Native Tool Calling', 'JSON-Mediated Wrapper'], textStyle: { color: '#94a3b8' } },
          xAxis: { type: 'category', data: ['~1.9k Context', '~3.8k Context', '~7k Context'], axisLabel: { color: '#cbd5e1' } },
          yAxis: { type: 'value', max: 6, name: 'Successful Invocations', axisLabel: { color: '#cbd5e1' }, splitLine: { lineStyle: { color: '#1e293b' } } },
          series: [
            {
              name: 'Native Tool Calling',
              type: 'bar',
              data: [6, 6, 6],
              itemStyle: { color: '#38bdf8' }
            },
            {
              name: 'JSON-Mediated Wrapper',
              type: 'bar',
              data: [4, 2, 2],
              itemStyle: { color: '#f59e0b' }
            }
          ]
        })
      },
      {
        id: 'gpu-offload',
        shortTitle: '5. Partial GPU Offload',
        fullTitle: 'Llama-3.2-3B Partial GPU Layer Offloading Frontier',
        track: 'Track A — Inference Efficiency',
        evidence_status: 'measured',
        hardware: 'GTX 1050 Ti + System DDR4 (PCIe 3.0 x16)',
        hypothesis:
          'Partial layer offloading allows fitting models exceeding VRAM headroom, but PCIe bus transfers induce non-linear decode throughput penalties.',
        protocol:
          'Evaluated Llama-3.2-3B at 2048 context with q8_0 KV cache across 99 (all GPU), 32, 24, and 16 offloaded layers.',
        findings:
          '99 layers (all GPU) consumed 2364 MiB taking 30.4s. Offloading to 24 layers saved 290 MiB at ~26% lower decode. Offloading to 16 layers saved 752 MiB (1612 MiB VRAM) but incurred a ~48% decode throughput penalty (51.5s).',
        limitations:
          'Model-specific layer boundary; dependent on host DDR4 bus speed and motherboard PCIe 3.0 latency.',
        source_doc: 'docs/benchmarks/h2-h4-kv-results.md',
        raw_paths: ['results/sweeps/offload2'],
        tableData: {
          headers: ['GPU Layers', 'Peak VRAM (MiB)', 'Duration (s)', 'VRAM Savings', 'Throughput Penalty'],
          rows: [
            ['99 layers (All GPU)', 2364.1, 30.4, 'Baseline', 'Baseline'],
            ['32 layers', 2364.1, 30.9, '0 MiB', '-1.6%'],
            ['24 layers', 2074.1, 38.6, '-290.0 MiB (-12.3%)', '-26.9%'],
            ['16 layers', 1612.1, 51.5, '-752.0 MiB (-31.8%)', '-48.3%']
          ]
        },
        renderChart: () => ({
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: ['99 Layers (Full)', '32 Layers', '24 Layers', '16 Layers'], axisLabel: { color: '#cbd5e1' } },
          yAxis: [
            { type: 'value', name: 'Peak VRAM (MiB)', axisLabel: { color: '#cbd5e1' }, splitLine: { lineStyle: { color: '#1e293b' } } },
            { type: 'value', name: 'Duration (s)', axisLabel: { color: '#f59e0b' }, splitLine: { show: false } }
          ],
          series: [
            { name: 'Peak VRAM (MiB)', type: 'bar', data: [2364.1, 2364.1, 2074.1, 1612.1], itemStyle: { color: '#0284c7' } },
            { name: 'Duration (s)', type: 'line', yAxisIndex: 1, data: [30.4, 30.9, 38.6, 51.5], itemStyle: { color: '#f59e0b' }, lineStyle: { width: 3 } }
          ]
        })
      },
      {
        id: 'concurrency-scaling',
        shortTitle: '6. Concurrency Slots',
        fullTitle: 'Continuous Batching & Multi-Slot Concurrency (1 vs 2 vs 4 Slots)',
        track: 'Track D — Concurrency & Serving',
        evidence_status: 'partial',
        hardware: 'GTX 1050 Ti (4 GiB GDDR5)',
        hypothesis:
          'Continuous multi-slot serving increases aggregate request throughput on GTX 1050 Ti without causing VRAM fragmentation or OOM.',
        protocol:
          'Evaluated Qwen3-1.7B at 2048 context and q8_0 KV cache across 1, 2, and 4 concurrency slots with --cache-ram 0.',
        findings:
          'Scaling from 1 to 4 slots increased aggregate request throughput by +20.4%, reducing sweep batch duration from 35.1s to 21.3s while peak VRAM remained stable at 1530.1 MiB.',
        limitations:
          'Per-slot context was reduced (8192→2048) between configurations, so not fully context-equivalent; n=3 leases per arm is exploratory.',
        source_doc: 'docs/benchmarks/h4-concurrency-repeats.md',
        raw_paths: ['results/sweeps/concurrency', 'results/sweeps/h4-par1-r1', 'results/sweeps/h4-par4-r3'],
        tableData: {
          headers: ['Concurrency Slots', 'Duration (s)', 'Peak VRAM (MiB)', 'Throughput Gain', 'Status'],
          rows: [
            ['1 Slot (Sequential)', 35.1, 1530.1, 'Baseline', 'measured'],
            ['2 Slots', 32.5, 1530.1, '+7.4%', 'measured'],
            ['4 Slots (Parallel)', 21.3, 1530.1, '+20.4% aggregate', 'measured']
          ]
        },
        renderChart: () => ({
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: ['1 Slot (par=1)', '2 Slots (par=2)', '4 Slots (par=4)'], axisLabel: { color: '#cbd5e1' } },
          yAxis: { type: 'value', name: 'Sweep Duration (s) - Lower is Faster', axisLabel: { color: '#cbd5e1' }, splitLine: { lineStyle: { color: '#1e293b' } } },
          series: [
            {
              name: 'Duration (s)',
              type: 'bar',
              data: [35.1, 32.5, 21.3],
              itemStyle: {
                color: (params: any) => ['#0284c7', '#38bdf8', '#10b981'][params.dataIndex]
              }
            }
          ]
        })
      },
      {
        id: 'hotpotqa-pilot',
        shortTitle: '7. HotpotQA Support-Order',
        fullTitle: 'HotpotQA Support-Order Multi-Hop RAG Pilot (Interrupted)',
        track: 'Track C — Long-Context Capability',
        evidence_status: 'partial',
        hardware: 'GTX 1050 Ti (4 GiB GDDR5)',
        hypothesis:
          'Moving supporting passages from first to last position in natural multi-hop contexts degrades answer exact match in small models.',
        protocol:
          'Planned 100-item paired study across 20 five-question batches; interleaved bridge and comparison hard items. Halted after 15 items during operational route verification check.',
        findings:
          'Batches 1–3 completed (15 paired questions). Support-first: 8/15 EM; Support-last: 7/15 EM. Descriptive pilot only; does not provide a representative population estimate.',
        limitations:
          'Interrupted pilot. Model mapping verification halted further GPU execution until route, mapping, and recovery procedure are confirmed by project owner.',
        source_doc: 'docs/benchmarks/hotpotqa-support-order-partial.md',
        raw_paths: ['results/campaigns/gpu-lab-rag-hotpotqa-pilot'],
        tableData: {
          headers: ['Batch', 'Support-First EM', 'Support-Last EM', 'Items', 'Status'],
          rows: [
            ['Batch 1 (5 items)', '3 / 5 (60.0%)', '3 / 5 (60.0%)', '5', 'completed'],
            ['Batch 2 (5 items)', '2 / 5 (40.0%)', '2 / 5 (40.0%)', '5', 'completed'],
            ['Batch 3 (5 items)', '3 / 5 (60.0%)', '2 / 5 (40.0%)', '5', 'completed'],
            ['Batch 4–20', 'Halted', 'Halted', '85', 'halted (verification check)']
          ]
        },
        renderChart: () => ({
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: ['Batch 1', 'Batch 2', 'Batch 3', 'Pilot Total (n=15)'], axisLabel: { color: '#cbd5e1' } },
          yAxis: { type: 'value', max: 5, name: 'Exact Match Count', axisLabel: { color: '#cbd5e1' }, splitLine: { lineStyle: { color: '#1e293b' } } },
          series: [
            { name: 'Support-First', type: 'bar', data: [3, 2, 3, 8], itemStyle: { color: '#38bdf8' } },
            { name: 'Support-Last', type: 'bar', data: [3, 2, 2, 7], itemStyle: { color: '#f59e0b' } }
          ]
        })
      }
    ],
    []
  );

  const activeExp = useMemo(() => {
    return experiments.find((e) => e.id === activeExpId) || experiments[0];
  }, [experiments, activeExpId]);

  return (
    <div className="space-y-8">
      {/* Header (Epoch AI Editorial Authority) */}
      <div className="space-y-2 border-b border-[#E2E5E5] dark:border-[#242F32] pb-6">
        <div className="flex items-center gap-2 text-xs font-mono text-[#006D77] dark:text-[#2DD4BF]">
          <Layers className="w-4 h-4" />
          <span>METHODOLOGICAL DEEP-DIVES</span>
        </div>
        <h1 className="text-2xl sm:text-4xl font-serif font-medium tracking-tight text-[#0E1415] dark:text-[#F2F5F5]">
          Experimental Studies & Sweeps
        </h1>
        <p className="text-xs sm:text-sm text-[#475456] dark:text-[#98A8AA] max-w-3xl leading-relaxed">
          Comprehensive breakdowns of hypotheses, protocols, raw measurements, chart visualizations,
          and documented scientific limitations across all 7 empirical campaign sweeps on NVIDIA GTX 1050 Ti.
        </p>
      </div>

      {/* Experiment Selector Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2 scrollbar-none border-b border-[#E2E5E5] dark:border-[#242F32]">
        {experiments.map((e) => {
          const isActive = activeExp.id === e.id;
          return (
            <button
              key={e.id}
              onClick={() => setActiveExpId(e.id)}
              className={`px-3.5 py-2 rounded-md text-xs font-medium whitespace-nowrap transition-colors flex items-center gap-2 ${
                isActive
                  ? 'bg-[#006D77] dark:bg-[#2DD4BF] text-white dark:text-[#0A0E0F] font-semibold shadow-sm'
                  : 'bg-white dark:bg-[#121719] text-[#475456] dark:text-[#98A8AA] border border-[#E2E5E5] dark:border-[#242F32] hover:bg-[#F5F5F3] dark:hover:bg-[#182022] hover:text-[#0E1415] dark:hover:text-[#F2F5F5]'
              }`}
            >
              <span>{e.shortTitle}</span>
              <EvidenceBadge status={e.evidence_status} showIcon={false} className="py-0 px-1.5 text-[10px]" />
            </button>
          );
        })}
      </div>

      {/* Main Experiment View */}
      <div className="space-y-6">
        {/* Title & Metadata Banner */}
        <div className="p-6 rounded-xl bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E2E5E5] dark:border-[#242F32] pb-4">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-wider text-[#006D77] dark:text-[#2DD4BF] font-semibold">
                {activeExp.track}
              </span>
              <h2 className="text-xl sm:text-2xl font-serif font-bold text-[#0E1415] dark:text-[#F2F5F5] tracking-tight">
                {activeExp.fullTitle}
              </h2>
            </div>
            <div className="flex items-center gap-2 self-start sm:self-auto">
              <EvidenceBadge status={activeExp.evidence_status} />
              <HardwareBadge />
            </div>
          </div>

          {/* Hypothesis & Protocol Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs sm:text-sm">
            <div className="bg-[#E6F3F4]/50 dark:bg-[#0D2C28]/40 p-4 rounded-lg border border-[#006D77]/25 dark:border-[#2DD4BF]/30 space-y-1.5">
              <span className="font-bold text-[#006D77] dark:text-[#2DD4BF] text-xs font-mono uppercase tracking-wider">
                Scientific Hypothesis
              </span>
              <p className="text-[#475456] dark:text-[#98A8AA] leading-relaxed font-sans">{activeExp.hypothesis}</p>
            </div>
            <div className="bg-[#F5F5F3] dark:bg-[#182022] p-4 rounded-lg border border-[#E2E5E5] dark:border-[#242F32] space-y-1.5">
              <span className="font-bold text-[#0E1415] dark:text-[#F2F5F5] text-xs font-mono uppercase tracking-wider">
                Experimental Protocol
              </span>
              <p className="text-[#475456] dark:text-[#98A8AA] leading-relaxed font-sans">{activeExp.protocol}</p>
            </div>
          </div>
        </div>

        {/* Interactive Chart Container */}
        <div className="p-6 rounded-xl bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] shadow-sm space-y-3">
          <div className="flex items-center justify-between border-b border-[#E2E5E5] dark:border-[#242F32] pb-3">
            <h3 className="text-base font-serif font-bold text-[#0E1415] dark:text-[#F2F5F5] flex items-center gap-2">
              <BarChart2 className="w-5 h-5 text-[#006D77] dark:text-[#2DD4BF]" />
              <span>Observed Empirical Behavior</span>
            </h3>
            <span className="text-xs font-mono text-[#526063] dark:text-[#98A8AA]">Interactive Visualization</span>
          </div>

          <EChartWrapper options={activeExp.renderChart()} height={360} />
        </div>

        {/* Findings and Raw Table */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          {/* Findings & Limitations */}
          <div className="space-y-4">
            <div className="p-5 rounded-xl bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] space-y-2">
              <h4 className="font-bold text-[#0E1415] dark:text-[#F2F5F5] flex items-center gap-2 text-sm">
                <CheckCircle2 className="w-4 h-4 text-[#0E7A5A] dark:text-[#34D399]" />
                <span>Documented Findings</span>
              </h4>
              <p className="text-xs sm:text-sm text-[#475456] dark:text-[#98A8AA] leading-relaxed">{activeExp.findings}</p>
            </div>

            <div className="p-5 rounded-xl bg-[#FEF3C7]/50 dark:bg-[#382806]/40 border border-[#B45309]/30 dark:border-[#FBBF24]/30 space-y-2">
              <h4 className="font-bold text-[#B45309] dark:text-[#FBBF24] flex items-center gap-2 text-sm">
                <AlertCircle className="w-4 h-4 text-[#B45309] dark:text-[#FBBF24]" />
                <span>Known Limitations & Caveats</span>
              </h4>
              <p className="text-xs sm:text-sm text-[#B45309] dark:text-[#FBBF24] leading-relaxed">{activeExp.limitations}</p>
            </div>

            <div className="p-4 rounded-xl bg-[#F5F5F3] dark:bg-[#182022] border border-[#E2E5E5] dark:border-[#242F32] space-y-2">
              <span className="text-xs font-semibold text-[#475456] dark:text-[#98A8AA] flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-[#006D77] dark:text-[#2DD4BF]" />
                <span>Markdown Evidence Record</span>
              </span>
              <a
                href={`https://github.com/AndersonTavares0/llm-research-bench/blob/main/${activeExp.source_doc}`}
                target="_blank"
                rel="noreferrer"
                className="text-xs font-mono text-[#006D77] dark:text-[#2DD4BF] hover:underline flex items-center gap-1 truncate"
              >
                <span>{activeExp.source_doc}</span>
                <ExternalLink className="w-3 h-3 opacity-70" />
              </a>
            </div>
          </div>

          {/* Raw Data Table */}
          {activeExp.tableData && (
            <div className="p-5 rounded-xl bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] space-y-3">
              <h4 className="font-bold text-[#0E1415] dark:text-[#F2F5F5] flex items-center gap-2 text-sm">
                <Database className="w-4 h-4 text-[#006D77] dark:text-[#2DD4BF]" />
                <span>Committed Sweep Rows & Provenance</span>
              </h4>

              <div className="rounded-lg border border-[#E2E5E5] dark:border-[#242F32] overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-[#F5F5F3] dark:bg-[#182022] text-[#475456] dark:text-[#98A8AA] text-[11px]">
                    <tr>
                      {activeExp.tableData.headers.map((h) => (
                        <th key={h} className="p-2.5">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#ECEEED] dark:divide-[#1C2426] text-[#0E1415] dark:text-[#F2F5F5]">
                    {activeExp.tableData.rows.map((row, idx) => (
                      <tr key={idx} className="hover:bg-[#F5F5F3] dark:hover:bg-[#182022]">
                        {row.map((cell, cidx) => (
                          <td key={cidx} className="p-2.5">
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {activeExp.raw_paths && activeExp.raw_paths.length > 0 && (
                <div className="pt-2 text-[11px] text-slate-500 dark:text-slate-400 font-mono space-y-1">
                  <div className="text-slate-700 dark:text-slate-300 font-semibold">Raw Artifact Paths:</div>
                  {activeExp.raw_paths.map((p) => (
                    <div key={p} className="truncate">
                      • {p}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ExperimentsPage() {
  return (
    <Suspense fallback={<div className="text-slate-400 text-xs">Loading experiment data...</div>}>
      <ExperimentsContent />
    </Suspense>
  );
}
