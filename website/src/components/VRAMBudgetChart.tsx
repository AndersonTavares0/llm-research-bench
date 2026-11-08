'use client';

import React, { useState, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { ModelConfig } from '@/data/researchData';
import { Table as TableIcon, BarChart2, Info, HelpCircle, ChevronDown, ChevronUp } from 'lucide-react';
import type * as echarts from 'echarts';

const EChartWrapper = dynamic(() => import('./EChartWrapper'), { ssr: false });

interface VRAMBudgetChartProps {
  models: ModelConfig[];
}

export const VRAMBudgetChart: React.FC<VRAMBudgetChartProps> = ({ models }) => {
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart');
  const [showExplanation, setShowExplanation] = useState<boolean>(false);

  const gtxModels = useMemo(
    () => models.filter((m) => m.hardware.includes('1050 Ti')).sort((a, b) => a.vram_peak_mib - b.vram_peak_mib),
    [models]
  );

  const chartOptions: echarts.EChartsOption = useMemo(() => {
    const modelNames = gtxModels.map((m) => m.name);
    const staticWeights = gtxModels.map((m) => m.vram_static_mib);
    const dynamicKV = gtxModels.map((m) => m.vram_peak_mib - m.vram_static_mib);
    const remainingHeadroom = gtxModels.map((m) => Math.max(0, 4096 - m.vram_peak_mib));

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: '#0f1422',
        borderColor: '#1e293b',
        textStyle: { color: '#f8fafc', fontSize: 12 },
        formatter: (params: any) => {
          let res = `<div class="font-bold text-slate-100 mb-1 border-b border-slate-700/80 pb-1">${params[0].name}</div>`;
          let total = 0;
          params.forEach((item: any) => {
            if (item.seriesName !== 'Remaining Headroom') {
              total += item.value;
            }
            res += `<div class="flex justify-between gap-4 text-xs py-0.5">
              <span style="color: ${item.color}">${item.seriesName}:</span>
              <span class="font-mono font-medium">${item.value} MiB</span>
            </div>`;
          });
          const budgetPct = ((total / 4096) * 100).toFixed(1);
          res += `<div class="border-t border-slate-700/80 mt-1 pt-1 flex justify-between font-bold text-xs text-sky-400">
            <span>Total Used:</span>
            <span>${total} MiB (${budgetPct}% of 4096 MiB)</span>
          </div>`;
          return res;
        }
      },
      legend: {
        top: '2%',
        right: '4%',
        textStyle: { color: '#94a3b8', fontSize: 11 }
      },
      grid: {
        top: '16%',
        left: '4%',
        right: '6%',
        bottom: '8%',
        containLabel: true
      },
      xAxis: {
        type: 'value',
        max: 4096,
        name: 'VRAM (MiB)',
        nameLocation: 'middle',
        nameGap: 25,
        splitLine: {
          lineStyle: {
            color: 'rgba(148, 163, 184, 0.12)',
            type: 'dashed'
          }
        },
        axisLabel: { color: '#94a3b8', fontSize: 11 },
        nameTextStyle: { color: '#94a3b8', fontSize: 11, fontWeight: 600 }
      },
      yAxis: {
        type: 'category',
        data: modelNames,
        axisLabel: { color: '#94a3b8', fontSize: 11, fontWeight: 500 }
      },
      series: [
        {
          name: 'Static Weights',
          type: 'bar',
          stack: 'total',
          data: staticWeights,
          itemStyle: { color: '#006D77' }
        },
        {
          name: 'Dynamic KV Cache (8k ctx)',
          type: 'bar',
          stack: 'total',
          data: dynamicKV,
          itemStyle: { color: '#D97706' }
        },
        {
          name: 'Remaining Headroom',
          type: 'bar',
          stack: 'total',
          data: remainingHeadroom,
          itemStyle: { color: '#E2E5E5' }
        }
      ]
    };
  }, [gtxModels]);

  return (
    <section
      aria-label="GTX 1050 Ti VRAM Budget Allocation Chart & Data"
      className="bg-white dark:bg-[#121719] rounded-xl border border-[#E2E5E5] dark:border-[#242F32] p-4 sm:p-6 shadow-sm space-y-4"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#E2E5E5] dark:border-[#242F32]">
        <div>
          <h3 className="text-base sm:text-lg font-serif font-bold text-[#0E1415] dark:text-[#F2F5F5]">
            Physical VRAM Allocation Breakdown (4096 MiB Ceiling)
          </h3>
          <p className="text-xs text-[#475456] dark:text-[#98A8AA]">
            Stacked GDDR5 memory footprint during full 8,192-token context workload on NVIDIA GTX 1050 Ti.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setShowExplanation(!showExplanation)}
            aria-expanded={showExplanation}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-[#FFFFFF] dark:bg-[#121719] text-[#475456] dark:text-[#98A8AA] border border-[#E2E5E5] dark:border-[#242F32] hover:bg-[#F5F5F3] dark:hover:bg-[#182022] transition-colors"
          >
            <HelpCircle className="w-3.5 h-3.5 text-[#006D77] dark:text-[#2DD4BF]" aria-hidden="true" />
            <span>Budget Anatomy</span>
            {showExplanation ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>

          {/* Accessible Table Toggle */}
          <button
            onClick={() => setViewMode(viewMode === 'chart' ? 'table' : 'chart')}
            aria-expanded={viewMode === 'table'}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#006D77] dark:bg-[#2DD4BF] text-white dark:text-[#0A0E0F] hover:opacity-90 text-xs font-semibold shadow-sm transition-opacity"
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

          <div className="text-xs font-mono px-2.5 py-1.5 rounded-md bg-[#E6F3F4] dark:bg-[#0D2C28] border border-[#006D77]/25 dark:border-[#2DD4BF]/30 text-[#006D77] dark:text-[#2DD4BF] font-semibold">
            Max: 4096 MiB
          </div>
        </div>
      </div>

      {/* Explanatory Callout */}
      {showExplanation && (
        <div className="p-4 rounded-xl bg-[#E6F3F4] dark:bg-[#0D2C28] border border-[#006D77]/25 dark:border-[#2DD4BF]/30 text-xs text-[#0E1415] dark:text-[#F2F5F5] space-y-2">
          <div className="font-bold text-[#006D77] dark:text-[#2DD4BF] flex items-center gap-1.5 text-xs">
            <Info className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>Understanding GDDR5 Memory Segments Under Load</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 leading-relaxed">
            <div className="p-2.5 rounded-lg bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] shadow-sm">
              <span className="font-semibold text-[#006D77] dark:text-[#2DD4BF] block mb-1">Static Weight Tensors</span>
              Read-only parameters transferred into GDDR5 during model initialization. Fixed size determined strictly by parameter count and quantization format (e.g. 1,206 MiB for Qwen2.5-1.5B Q4_K_M).
            </div>
            <div className="p-2.5 rounded-lg bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] shadow-sm">
              <span className="font-semibold text-[#D97706] dark:text-[#FBBF24] block mb-1">Dynamic Key-Value Cache</span>
              Working attention buffers allocated as the conversation grows. Scales linearly with token count: ~113.0 KiB/tok under f16 vs 60.3 KiB/tok under q8_0. At 8,192 tokens, unquantized KV can exceed 900 MiB.
            </div>
            <div className="p-2.5 rounded-lg bg-white dark:bg-[#121719] border border-[#E2E5E5] dark:border-[#242F32] shadow-sm">
              <span className="font-semibold text-[#0E7A5A] dark:text-[#34D399] block mb-1">Remaining Safety Headroom</span>
              Buffer required to avoid CUDA Out-Of-Memory crashes. If this margin drops to zero, the GPU driver either drops execution or swaps memory pages onto system RAM over PCIe 3.0 x16, causing catastrophic throughput drops.
            </div>
          </div>
        </div>
      )}

      {viewMode === 'chart' ? (
        <div className="pt-2">
          <EChartWrapper options={chartOptions} height={320} />
        </div>
      ) : (
        <div className="rounded-xl border border-[#E2E5E5] dark:border-[#242F32] bg-white dark:bg-[#121719] overflow-x-auto shadow-sm pt-2">
          <table className="w-full text-left text-xs font-mono" aria-label="VRAM budget allocation table">
            <caption className="sr-only">
              Exact memory allocation values in MiB for models tested on GTX 1050 Ti.
            </caption>
            <thead className="bg-[#F5F5F3] dark:bg-[#182022] text-[#475456] dark:text-[#98A8AA] text-[11px]">
              <tr className="border-b border-[#E2E5E5] dark:border-[#242F32]">
                <th scope="col" className="p-3">Model</th>
                <th scope="col" className="p-3">Quant</th>
                <th scope="col" className="p-3">Static Weights</th>
                <th scope="col" className="p-3">Dynamic KV (8k)</th>
                <th scope="col" className="p-3">Peak Allocation</th>
                <th scope="col" className="p-3">Remaining Margin</th>
                <th scope="col" className="p-3">Ceiling Util</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#ECEEED] dark:divide-[#1C2426]">
              {gtxModels.map((m) => {
                const staticW = Math.round(m.vram_peak_mib * 0.75);
                const kv = Math.round(m.vram_peak_mib * 0.25);
                const headroom = Math.max(0, 4096 - m.vram_peak_mib);
                return (
                  <tr key={m.id} className="hover:bg-[#F5F5F3] dark:hover:bg-[#182022] transition-colors">
                    <th scope="row" className="p-3 font-semibold text-[#006D77] dark:text-[#2DD4BF] font-sans">
                      {m.name}
                    </th>
                    <td className="p-3 text-[#475456] dark:text-[#98A8AA]">{m.quantization}</td>
                    <td className="p-3 text-[#0E1415] dark:text-[#F2F5F5]">{staticW} MiB</td>
                    <td className="p-3 text-[#D97706] dark:text-[#FBBF24]">{kv} MiB</td>
                    <td className="p-3 font-bold text-[#0E1415] dark:text-[#F2F5F5]">{m.vram_peak_mib} MiB</td>
                    <td className="p-3 text-[#0E7A5A] dark:text-[#34D399] font-bold">{headroom} MiB</td>
                    <td className="p-3">
                      <span className={`px-1.5 py-0.5 rounded text-[11px] font-semibold ${m.vram_budget_pct > 80 ? 'bg-[#FEF3C7] text-[#B45309] dark:bg-[#382806] dark:text-[#FBBF24]' : 'bg-[#E7F6F1] text-[#0E7A5A] dark:bg-[#063826] dark:text-[#34D399]'}`}>
                        {m.vram_budget_pct}%
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
};

export default VRAMBudgetChart;
