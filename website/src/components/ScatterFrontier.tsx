'use client';

import React, { useState, useMemo, useEffect } from 'react';
import { ModelConfig } from '@/data/researchData';
import EChartWrapper from './EChartWrapper';
import type * as echarts from 'echarts';
import {
  TrendingUp,
  SlidersHorizontal,
  Table as TableIcon,
  BarChart2,
  Sparkles,
  HelpCircle,
  Info,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

interface ScatterFrontierProps {
  models: ModelConfig[];
  onSelectModel?: (model: ModelConfig) => void;
  initialX?: MetricKey;
  initialY?: MetricKey;
}

export const MODEL_VISUAL_CONFIG: Record<
  string,
  {
    shortName: string;
    family: string;
    color: string;
    borderColor: string;
    darkColor: string;
    darkBorderColor: string;
    symbol: 'circle' | 'rect' | 'triangle' | 'diamond' | 'pin';
    symbolSize: number;
    labelPosition: 'top' | 'bottom' | 'left' | 'right';
  }
> = {
  'qwen25-05b': {
    shortName: 'Qwen2.5:0.5B',
    family: 'Qwen',
    color: '#0284C7',
    borderColor: '#BAE6FD',
    darkColor: '#38BDF8',
    darkBorderColor: '#0369A1',
    symbol: 'circle',
    symbolSize: 20,
    labelPosition: 'right'
  },
  'smollm2-17b': {
    shortName: 'SmolLM2:1.7B',
    family: 'SmolLM',
    color: '#059669',
    borderColor: '#A7F3D0',
    darkColor: '#34D399',
    darkBorderColor: '#047857',
    symbol: 'diamond',
    symbolSize: 22,
    labelPosition: 'top'
  },
  'gemma4-e2b': {
    shortName: 'Gemma-4:E2B (MTP)',
    family: 'Gemma',
    color: '#EA580C',
    borderColor: '#FED7AA',
    darkColor: '#F97316',
    darkBorderColor: '#9A3412',
    symbol: 'triangle',
    symbolSize: 22,
    labelPosition: 'left'
  },
  'gemma4-base': {
    shortName: 'Gemma-4:E2B (Base)',
    family: 'Gemma',
    color: '#D97706',
    borderColor: '#FDE68A',
    darkColor: '#FBBF24',
    darkBorderColor: '#B45309',
    symbol: 'diamond',
    symbolSize: 20,
    labelPosition: 'bottom'
  },
  'qwen35-2b': {
    shortName: 'Qwen3.5:2B',
    family: 'Qwen',
    color: '#006D77',
    borderColor: '#99F6E4',
    darkColor: '#2DD4BF',
    darkBorderColor: '#004F56',
    symbol: 'circle',
    symbolSize: 20,
    labelPosition: 'right'
  },
  'llama32-3b': {
    shortName: 'Llama-3.2:3B',
    family: 'Llama',
    color: '#6366F1',
    borderColor: '#C7D2FE',
    darkColor: '#818CF8',
    darkBorderColor: '#4338CA',
    symbol: 'rect',
    symbolSize: 20,
    labelPosition: 'top'
  },
  'qwen35-4b': {
    shortName: 'Qwen3.5:4B',
    family: 'Qwen',
    color: '#9333EA',
    borderColor: '#E9D5FF',
    darkColor: '#C084FC',
    darkBorderColor: '#6B21A8',
    symbol: 'circle',
    symbolSize: 22,
    labelPosition: 'top'
  }
};

export type MetricKey =
  | 'vram_peak_mib'
  | 'generation_tok_s'
  | 'prompt_eval_tok_s'
  | 'ttft_ms'
  | 'parameters_b'
  | 'memory_efficiency'
  | 'quality_arc'
  | 'quality_gsm8k';

interface MetricDef {
  key: MetricKey;
  label: string;
  unit: string;
  higherIsBetter: boolean;
  getValue: (m: ModelConfig) => number;
}

export const METRICS: MetricDef[] = [
  {
    key: 'generation_tok_s',
    label: 'Decode Speed (Generation)',
    unit: 'tok/s',
    higherIsBetter: true,
    getValue: (m) => m.generation_tok_s
  },
  {
    key: 'vram_peak_mib',
    label: 'Peak VRAM Footprint',
    unit: 'MiB',
    higherIsBetter: false,
    getValue: (m) => m.vram_peak_mib
  },
  {
    key: 'quality_arc',
    label: 'ARC-Challenge Zero-Shot',
    unit: '%',
    higherIsBetter: true,
    getValue: (m) => +(m.quality_scores.arc_challenge * 100).toFixed(1)
  },
  {
    key: 'quality_gsm8k',
    label: 'GSM8K Flex Zero-Shot',
    unit: '%',
    higherIsBetter: true,
    getValue: (m) => +(m.quality_scores.gsm8k_flex * 100).toFixed(1)
  },
  {
    key: 'prompt_eval_tok_s',
    label: 'Prefill Speed (Prompt Eval)',
    unit: 'tok/s',
    higherIsBetter: true,
    getValue: (m) => m.prompt_eval_tok_s
  },
  {
    key: 'ttft_ms',
    label: 'Time to First Token (TTFT)',
    unit: 'ms',
    higherIsBetter: false,
    getValue: (m) => m.ttft_ms
  },
  {
    key: 'parameters_b',
    label: 'Parameter Size',
    unit: 'B',
    higherIsBetter: false,
    getValue: (m) => m.parameters_b
  },
  {
    key: 'memory_efficiency',
    label: 'Memory Efficiency',
    unit: 'tok/s per GiB',
    higherIsBetter: true,
    getValue: (m) => m.memory_efficiency_tok_s_gib
  }
];

export const ScatterFrontier: React.FC<ScatterFrontierProps> = ({
  models,
  onSelectModel,
  initialX = 'vram_peak_mib',
  initialY = 'generation_tok_s'
}) => {
  const [xMetricKey, setXMetricKey] = useState<MetricKey>(initialX as MetricKey);
  const [yMetricKey, setYMetricKey] = useState<MetricKey>(initialY as MetricKey);
  const [showPareto, setShowPareto] = useState<boolean>(true);
  const [showExplanation, setShowExplanation] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart');
  const [isDark, setIsDark] = useState<boolean>(false);

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains('dark'));
    const observer = new MutationObserver(() => {
      setIsDark(document.documentElement.classList.contains('dark'));
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

  const xMetric = useMemo(() => METRICS.find((m) => m.key === xMetricKey)!, [xMetricKey]);
  const yMetric = useMemo(() => METRICS.find((m) => m.key === yMetricKey)!, [yMetricKey]);

  // All models are GTX 1050 Ti primary testbed
  const gtxModels = useMemo(() => models.filter((m) => m.hardware.includes('1050 Ti')), [models]);

  // Compute non-dominated Pareto Frontier
  const paretoPoints = useMemo(() => {
    if (!showPareto || gtxModels.length < 2) return [];

    const pts = gtxModels.map((m) => ({
      x: xMetric.getValue(m),
      y: yMetric.getValue(m),
      model: m
    }));

    pts.sort((a, b) => a.x - b.x);

    const frontier: [number, number][] = [];
    for (const pt of pts) {
      let isDominated = false;
      for (const other of pts) {
        if (other === pt) continue;
        const otherBetterX = xMetric.higherIsBetter ? other.x >= pt.x : other.x <= pt.x;
        const otherBetterY = yMetric.higherIsBetter ? other.y >= pt.y : other.y <= pt.y;
        const otherStrictlyBetter =
          (xMetric.higherIsBetter ? other.x > pt.x : other.x < pt.x) ||
          (yMetric.higherIsBetter ? other.y > pt.y : other.y < pt.y);

        if (otherBetterX && otherBetterY && otherStrictlyBetter) {
          isDominated = true;
          break;
        }
      }
      if (!isDominated) {
        frontier.push([pt.x, pt.y]);
      }
    }

    frontier.sort((a, b) => a[0] - b[0]);
    return frontier;
  }, [gtxModels, xMetric, yMetric, showPareto]);

  const seriesData = useMemo(() => {
    const points = gtxModels.map((m) => {
      const cfg = MODEL_VISUAL_CONFIG[m.id] || {
        shortName: m.name,
        family: m.family,
        color: '#006D77',
        borderColor: '#99F6E4',
        darkColor: '#2DD4BF',
        darkBorderColor: '#004F56',
        symbol: 'circle' as const,
        symbolSize: 20,
        labelPosition: 'top' as const
      };

      const dotColor = isDark ? cfg.darkColor : cfg.color;
      const dotBorder = isDark ? cfg.darkBorderColor : cfg.borderColor;
      const labelBg = isDark ? 'rgba(10, 14, 15, 0.90)' : 'rgba(255, 255, 255, 0.94)';
      const labelText = isDark ? '#F2F5F5' : '#0E1415';
      const labelBorder = isDark ? cfg.darkBorderColor : cfg.borderColor;

      // Dynamic collision avoidance depending on active metrics
      let dynamicPos: 'top' | 'bottom' | 'left' | 'right' = cfg.labelPosition;
      let dynamicDistance = 7;

      if (xMetricKey === 'parameters_b') {
        // At 2.0B, Gemma variants and Qwen3.5:2B share the exact same X=2.0B
        if (m.id === 'gemma4-e2b') {
          dynamicPos = 'right';
        } else if (m.id === 'gemma4-base') {
          dynamicPos = 'bottom';
        } else if (m.id === 'qwen35-2b') {
          dynamicPos = 'top';
        } else if (m.id === 'smollm2-17b') {
          dynamicPos = 'top';
        } else if (m.id === 'qwen25-05b') {
          dynamicPos = 'top';
          dynamicDistance = 9;
        } else if (m.id === 'qwen35-4b') {
          dynamicPos = 'left';
        }
      } else if (xMetricKey === 'vram_peak_mib') {
        if (m.id === 'gemma4-e2b') dynamicPos = 'left';
        else if (m.id === 'gemma4-base') dynamicPos = 'bottom';
        else if (m.id === 'qwen35-2b') dynamicPos = 'right';
        else if (m.id === 'qwen25-05b') dynamicPos = 'right';
        else if (m.id === 'smollm2-17b') dynamicPos = 'top';
        else if (m.id === 'qwen35-4b') dynamicPos = 'top';
      }

      return {
        name: m.name,
        value: [xMetric.getValue(m), yMetric.getValue(m)],
        model: m,
        symbol: cfg.symbol,
        symbolSize: cfg.symbolSize,
        itemStyle: {
          color: dotColor,
          borderColor: dotBorder,
          borderWidth: 2,
          shadowBlur: 10,
          shadowColor: isDark ? 'rgba(0, 0, 0, 0.6)' : 'rgba(0, 0, 0, 0.15)'
        },
        label: {
          show: true,
          position: dynamicPos,
          formatter: () => cfg.shortName,
          fontSize: 11,
          fontWeight: 600,
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          color: labelText,
          backgroundColor: labelBg,
          borderColor: labelBorder,
          borderWidth: 1,
          borderRadius: 4,
          padding: [3, 6],
          distance: dynamicDistance
        },
        emphasis: {
          scale: 1.35,
          itemStyle: {
            borderWidth: 3,
            shadowBlur: 16
          },
          label: {
            show: true,
            fontWeight: 700,
            borderColor: dotColor,
            borderWidth: 1.5
          }
        }
      };
    });

    const series: any[] = [
      {
        name: 'Evaluated Models (GTX 1050 Ti)',
        type: 'scatter',
        data: points,
        z: 2
      }
    ];

    if (showPareto && paretoPoints.length > 0) {
      series.push({
        name: 'Pareto Optimal Frontier',
        type: 'line',
        data: paretoPoints,
        smooth: false,
        lineStyle: {
          color: '#10b981',
          width: 2.5,
          type: 'dashed'
        },
        symbol: 'none',
        z: 1
      });
    }

    return series;
  }, [gtxModels, xMetric, yMetric, showPareto, paretoPoints, isDark]);

  const chartOptions: echarts.EChartsOption = useMemo(() => {
    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: '#0f1422',
        borderColor: '#1e293b',
        borderWidth: 1,
        padding: 12,
        textStyle: {
          color: '#f8fafc',
          fontSize: 12
        },
        formatter: (params: any) => {
          if (params.seriesType === 'line') {
            return `<div class="font-bold text-emerald-400">Pareto Optimal Frontier</div><div class="text-[11px] text-slate-400">Configurations non-dominated in speed vs footprint</div>`;
          }
          const m: ModelConfig = params.data.model;
          if (!m) return '';

          return `
            <div class="space-y-1.5 font-sans min-w-[210px] max-w-[260px] text-left">
              <div class="flex items-center justify-between border-b border-slate-700/80 pb-1.5 gap-2">
                <span class="font-bold text-slate-100 text-xs truncate">${m.name}</span>
                <span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-teal-950 text-teal-300 shrink-0 font-semibold">${m.quantization}</span>
              </div>
              <div class="text-[11px] text-slate-300 space-y-1 pt-0.5">
                <div class="flex justify-between gap-2">
                  <span class="text-slate-400">${xMetric.label}:</span>
                  <span class="font-mono font-medium text-slate-100 shrink-0">${params.data.value[0]} ${xMetric.unit}</span>
                </div>
                <div class="flex justify-between gap-2">
                  <span class="text-slate-400">${yMetric.label}:</span>
                  <span class="font-mono font-medium text-slate-100 shrink-0">${params.data.value[1]} ${yMetric.unit}</span>
                </div>
                <div class="flex justify-between border-t border-slate-800/80 pt-1 gap-2">
                  <span class="text-slate-400">VRAM Budget:</span>
                  <span class="font-mono font-medium text-sky-400 shrink-0">${m.vram_budget_pct}% (4096 MiB)</span>
                </div>
                <div class="flex justify-between gap-2">
                  <span class="text-slate-400">Host Hardware:</span>
                  <span class="font-mono text-[10px] text-slate-300 shrink-0">GTX 1050 Ti (CT 108)</span>
                </div>
              </div>
            </div>
          `;
        }
      },
      legend: {
        top: '2%',
        right: '4%',
        textStyle: {
          color: '#94a3b8',
          fontSize: 11
        }
      },
      grid: {
        top: '14%',
        left: '6%',
        right: '6%',
        bottom: '12%',
        containLabel: true
      },
      xAxis: {
        name: `${xMetric.label} (${xMetric.unit})`,
        nameLocation: 'middle',
        nameGap: 30,
        type: 'value',
        scale: true,
        splitLine: {
          lineStyle: {
            color: 'rgba(148, 163, 184, 0.12)'
          }
        },
        axisLabel: {
          color: '#94a3b8',
          fontSize: 11
        },
        nameTextStyle: {
          color: '#94a3b8',
          fontSize: 11,
          fontWeight: 600
        }
      },
      yAxis: {
        name: `${yMetric.label} (${yMetric.unit})`,
        type: 'value',
        scale: true,
        splitLine: {
          lineStyle: {
            color: 'rgba(148, 163, 184, 0.12)'
          }
        },
        axisLabel: {
          color: '#94a3b8',
          fontSize: 11
        },
        nameTextStyle: {
          color: '#94a3b8',
          fontSize: 11,
          fontWeight: 600
        }
      },
      series: seriesData
    };
  }, [xMetric, yMetric, seriesData, showPareto, paretoPoints]);

  const handleChartEvents = useMemo(() => {
    return {
      click: (params: any) => {
        if (params.data && params.data.model && onSelectModel) {
          onSelectModel(params.data.model);
        }
      }
    };
  }, [onSelectModel]);

  const presets = [
    { label: 'Quality vs Speed', x: 'generation_tok_s' as MetricKey, y: 'quality_arc' as MetricKey },
    { label: 'Speed vs VRAM', x: 'vram_peak_mib' as MetricKey, y: 'generation_tok_s' as MetricKey },
    { label: 'Memory Efficiency', x: 'vram_peak_mib' as MetricKey, y: 'memory_efficiency' as MetricKey },
    { label: 'Latency vs Size', x: 'parameters_b' as MetricKey, y: 'ttft_ms' as MetricKey }
  ];

  return (
    <section aria-labelledby="frontier-chart-title" className="p-4 sm:p-6 rounded-xl bg-white dark:bg-[#0f1422] border border-slate-200 dark:border-slate-800 shadow-md space-y-4">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" aria-hidden="true" />
            <h2 id="frontier-chart-title" className="text-base sm:text-lg font-bold text-slate-900 dark:text-white">
              Hardware Performance Frontier
            </h2>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
            Interactive multi-metric Pareto trade-offs across 6 evaluated small models on NVIDIA GTX 1050 Ti (4 GiB).
          </p>
        </div>

        {/* View Mode & Explanation Toggles */}
        <div className="flex items-center gap-2 self-start md:self-auto flex-wrap">
          <button
            onClick={() => setShowExplanation(!showExplanation)}
            aria-expanded={showExplanation}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-[#FFFFFF] dark:bg-[#121719] text-[#475456] dark:text-[#98A8AA] border border-[#E2E5E5] dark:border-[#242F32] hover:bg-[#F5F5F3] dark:hover:bg-[#182022] transition-colors"
          >
            <HelpCircle className="w-3.5 h-3.5 text-[#006D77] dark:text-[#2DD4BF]" aria-hidden="true" />
            <span>How to Read Frontier</span>
            {showExplanation ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>

          <button
            onClick={() => setViewMode(viewMode === 'chart' ? 'table' : 'chart')}
            aria-expanded={viewMode === 'table'}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-[#006D77] dark:bg-[#2DD4BF] text-white dark:text-[#0A0E0F] shadow-sm hover:opacity-90 transition-opacity"
          >
            {viewMode === 'chart' ? (
              <>
                <TableIcon className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Accessible Table</span>
              </>
            ) : (
              <>
                <BarChart2 className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Interactive Chart</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Explanatory Context Callout (Physically Grounded Explanation) */}
      {showExplanation && (
        <div className="p-4 rounded-xl bg-[#E6F3F4] dark:bg-[#0D2C28] border border-[#006D77]/25 dark:border-[#2DD4BF]/30 text-xs text-[#0E1415] dark:text-[#F2F5F5] space-y-2.5">
          <div className="font-bold text-[#006D77] dark:text-[#2DD4BF] flex items-center gap-1.5 text-xs">
            <Info className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>Physical Significance & Pareto Frontier Methodology</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 leading-relaxed">
            <div className="p-2.5 rounded-lg bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] shadow-sm">
              <span className="font-semibold text-[#006D77] dark:text-[#2DD4BF] block mb-1">1. The 4096 MiB Boundary</span>
              The GTX 1050 Ti features 4 GiB GDDR5 memory with 112 GB/s bus bandwidth. Unlike larger workstations, when total allocation (weights + KV cache + CUDA runtime context) hits 4096 MiB, execution halts with CUDA OOM or falls off onto system RAM over PCIe 3.0 x16.
            </div>
            <div className="p-2.5 rounded-lg bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] shadow-sm">
              <span className="font-semibold text-[#0E7A5A] dark:text-[#34D399] block mb-1">2. Pareto Dominance Line (Green)</span>
              The dashed emerald curve connects <em>non-dominated</em> configurations. A model configuration is Pareto-optimal if no other evaluated configuration achieves higher throughput with a smaller VRAM footprint. Models beneath the line are dominated.
            </div>
            <div className="p-2.5 rounded-lg bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] shadow-sm">
              <span className="font-semibold text-[#006D77] dark:text-[#2DD4BF] block mb-1">3. Generation vs Prefill</span>
              Decode speed (tok/s) is strictly memory-bandwidth bounded (b=1), transferring entire model weights from GDDR5 for every token. Prefill speed evaluates prompts in parallel and is compute-bound by the GP107 SM core count (768 CUDA cores).
            </div>
          </div>
        </div>
      )}

      {/* Preset Buttons & Dynamic Metric Controls (Spacious, Uncrowded 2-Row Layout) */}
      <div className="space-y-3 pt-1">
        {/* Row 1: Presets (Wrapping naturally with full visibility, zero clipping) */}
        <div className="flex flex-wrap items-center gap-2 text-xs" role="group" aria-label="Chart preset views">
          <span className="text-[11px] font-mono uppercase tracking-wider text-[#526063] dark:text-[#98A8AA] shrink-0 mr-1 flex items-center gap-1 font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-[#006D77] dark:text-[#2DD4BF]" aria-hidden="true" />
            Presets:
          </span>
          {presets.map((p) => {
            const isActive = xMetricKey === p.x && yMetricKey === p.y;
            return (
              <button
                key={p.label}
                onClick={() => {
                  setXMetricKey(p.x);
                  setYMetricKey(p.y);
                }}
                aria-pressed={isActive}
                className={`px-3 py-1.5 rounded-md font-medium transition-colors text-xs whitespace-nowrap ${
                  isActive
                    ? 'bg-[#006D77] dark:bg-[#2DD4BF] text-white dark:text-[#0A0E0F] font-semibold shadow-sm'
                    : 'bg-[#F5F5F3] dark:bg-[#182022] text-[#475456] dark:text-[#98A8AA] border border-[#E2E5E5] dark:border-[#242F32] hover:bg-[#ECEEED] dark:hover:bg-[#1D2629]'
                }`}
              >
                {p.label}
              </button>
            );
          })}
        </div>

        {/* Row 2: Metric Pickers & Pareto Toggle */}
        <div className="flex flex-wrap items-center justify-between gap-2.5 pt-2 border-t border-[#E2E5E5] dark:border-[#242F32]">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <div className="flex items-center gap-1.5 bg-[#F5F5F3] dark:bg-[#182022] px-2.5 py-1.5 rounded-md border border-[#E2E5E5] dark:border-[#242F32]">
              <label htmlFor="x-metric-select" className="text-[#526063] dark:text-[#98A8AA] font-semibold shrink-0">
                X-Axis:
              </label>
              <select
                id="x-metric-select"
                value={xMetricKey}
                onChange={(e) => setXMetricKey(e.target.value as MetricKey)}
                aria-label="Select metric for X-axis"
                className="bg-transparent text-[#0E1415] dark:text-[#F2F5F5] outline-none cursor-pointer text-xs font-medium"
              >
                {METRICS.map((m) => (
                  <option key={m.key} value={m.key} className="bg-white dark:bg-[#0A0E0F] text-[#0E1415] dark:text-[#F2F5F5]">
                    {m.label} ({m.unit})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-1.5 bg-[#F5F5F3] dark:bg-[#182022] px-2.5 py-1.5 rounded-md border border-[#E2E5E5] dark:border-[#242F32]">
              <label htmlFor="y-metric-select" className="text-[#526063] dark:text-[#98A8AA] font-semibold shrink-0">
                Y-Axis:
              </label>
              <select
                id="y-metric-select"
                value={yMetricKey}
                onChange={(e) => setYMetricKey(e.target.value as MetricKey)}
                aria-label="Select metric for Y-axis"
                className="bg-transparent text-[#0E1415] dark:text-[#F2F5F5] outline-none cursor-pointer text-xs font-medium"
              >
                {METRICS.map((m) => (
                  <option key={m.key} value={m.key} className="bg-white dark:bg-[#0A0E0F] text-[#0E1415] dark:text-[#F2F5F5]">
                    {m.label} ({m.unit})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Pareto Toggle */}
          <button
            onClick={() => setShowPareto(!showPareto)}
            aria-pressed={showPareto}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border text-xs font-semibold transition-colors ${
              showPareto
                ? 'bg-[#E6F3F4] dark:bg-[#0D2C28] text-[#006D77] dark:text-[#2DD4BF] border-[#006D77]/30 dark:border-[#2DD4BF]/40'
                : 'bg-[#F5F5F3] dark:bg-[#182022] text-[#526063] dark:text-[#98A8AA] border-[#E2E5E5] dark:border-[#242F32]'
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Pareto Line</span>
          </button>
        </div>
      </div>

      {/* Model Legend Bar (Direct visual identification & differentiation) */}
      <div className="flex items-center gap-1.5 overflow-x-auto py-2 scrollbar-none border-t border-[#E2E5E5] dark:border-[#242F32] text-xs">
        <span className="text-[10px] font-mono uppercase tracking-wider text-[#526063] dark:text-[#98A8AA] shrink-0 mr-1">
          Evaluated Models:
        </span>
        {gtxModels.map((m) => {
          const cfg = MODEL_VISUAL_CONFIG[m.id];
          if (!cfg) return null;
          const dotColor = isDark ? cfg.darkColor : cfg.color;
          return (
            <button
              key={m.id}
              onClick={() => onSelectModel?.(m)}
              className="flex items-center gap-1.5 px-2 py-1 rounded bg-[#FFFFFF] dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] hover:border-[#006D77] dark:hover:border-[#2DD4BF] transition-colors shrink-0 text-left group"
              title={`Click to inspect ${m.name} telemetry`}
            >
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0 shadow-sm"
                style={{ backgroundColor: dotColor }}
                aria-hidden="true"
              />
              <span className="font-mono text-xs font-semibold text-[#0E1415] dark:text-[#F2F5F5] group-hover:text-[#006D77] dark:group-hover:text-[#2DD4BF]">
                {cfg.shortName}
              </span>
              <span className="text-[10px] text-[#526063] dark:text-[#98A8AA] font-mono">
                {m.quantization}
              </span>
            </button>
          );
        })}
      </div>

      {/* View Switch: Interactive Canvas or Equivalent Accessible Table */}
      {viewMode === 'chart' ? (
        <div className="pt-2">
          <EChartWrapper options={chartOptions} height={420} onEvents={handleChartEvents} />
          <div className="mt-2 text-right text-[11px] text-slate-500 dark:text-slate-400">
            Hardware: NVIDIA GTX 1050 Ti (4096 MiB GDDR5, PVE CT 108). Click any point to inspect detailed telemetry.
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0f1422] overflow-x-auto shadow-md pt-2">
          <table className="w-full text-left text-xs font-mono" aria-label={`Frontier data table comparing ${xMetric.label} vs ${yMetric.label}`}>
            <caption className="sr-only">
              Accessible equivalent table for the performance frontier chart: {xMetric.label} vs {yMetric.label}.
            </caption>
            <thead className="bg-slate-50 dark:bg-[#161d31] text-slate-700 dark:text-slate-300 text-[11px]">
              <tr>
                <th scope="col" className="p-3">Model</th>
                <th scope="col" className="p-3">Family</th>
                <th scope="col" className="p-3">Quant</th>
                <th scope="col" className="p-3">{xMetric.label} ({xMetric.unit})</th>
                <th scope="col" className="p-3">{yMetric.label} ({yMetric.unit})</th>
                <th scope="col" className="p-3">VRAM %</th>
                <th scope="col" className="p-3">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-800 dark:text-slate-200">
              {gtxModels.map((m) => (
                <tr key={m.id} className="hover:bg-[#F5F5F3] dark:hover:bg-[#182022] transition-colors">
                  <th scope="row" className="p-3 font-semibold text-[#006D77] dark:text-[#2DD4BF] font-sans">
                    {m.name}
                  </th>
                  <td className="p-3 text-[#475456] dark:text-[#98A8AA] font-sans">{m.family}</td>
                  <td className="p-3 text-[#475456] dark:text-[#98A8AA]">{m.quantization}</td>
                  <td className="p-3 font-bold text-[#0E1415] dark:text-[#F2F5F5]">{xMetric.getValue(m)}</td>
                  <td className="p-3 font-bold text-[#0E7A5A] dark:text-[#34D399]">{yMetric.getValue(m)}</td>
                  <td className="p-3 text-[#475456] dark:text-[#98A8AA]">{m.vram_budget_pct}%</td>
                  <td className="p-3">
                    <button
                      onClick={() => onSelectModel && onSelectModel(m)}
                      aria-label={`Inspect detailed telemetry for ${m.name}`}
                      className="text-[#006D77] dark:text-[#2DD4BF] hover:underline font-sans text-xs font-semibold"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
};

export default ScatterFrontier;
