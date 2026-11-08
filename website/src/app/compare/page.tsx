'use client';

import React, { useState, useMemo, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import researchData, { ModelConfig } from '@/data/researchData';
import HardwareBadge from '@/components/HardwareBadge';
import EvidenceBadge from '@/components/EvidenceBadge';
import IncompatibilityAlert from '@/components/IncompatibilityAlert';
import { GitCompare, ArrowRight, Zap, Check, AlertTriangle, Layers, Globe } from 'lucide-react';

function CompareContent() {
  const searchParams = useSearchParams();
  const { models } = researchData;

  const initialM1 = searchParams.get('m1') || models[0].id;
  const initialM2 = searchParams.get('m2') || models[2]?.id || models[1].id;

  const [modelId1, setModelId1] = useState<string>(initialM1);
  const [modelId2, setModelId2] = useState<string>(initialM2);
  const [modelId3, setModelId3] = useState<string>('none');

  const model1 = useMemo(() => models.find((m) => m.id === modelId1) || models[0], [models, modelId1]);
  const model2 = useMemo(() => models.find((m) => m.id === modelId2) || models[1], [models, modelId2]);
  const model3 = useMemo(() => (modelId3 !== 'none' ? models.find((m) => m.id === modelId3) || null : null), [models, modelId3]);

  const activeModels = useMemo(() => {
    return [model1, model2, ...(model3 ? [model3] : [])];
  }, [model1, model2, model3]);

  const calcDelta = (valA: number, valB: number) => {
    const diff = valB - valA;
    const pct = valA !== 0 ? ((diff / valA) * 100).toFixed(1) : '0';
    return { diff: diff.toFixed(1), pct, isPositive: diff > 0 };
  };

  return (
    <div className="space-y-8">
      {/* Header (Epoch AI Editorial Authority) */}
      <div className="space-y-2 border-b border-[#E2E5E5] dark:border-[#242F32] pb-6">
        <div className="flex items-center gap-2 text-xs font-mono text-[#006D77] dark:text-[#2DD4BF]">
          <GitCompare className="w-4 h-4" />
          <span>SIDE-BY-SIDE ARCHITECTURAL COMPARISON</span>
        </div>
        <h1 className="text-2xl sm:text-4xl font-serif font-medium tracking-tight text-[#0E1415] dark:text-[#F2F5F5]">
          Model Differential Analysis
        </h1>
        <p className="text-xs sm:text-sm text-[#475456] dark:text-[#98A8AA] max-w-3xl leading-relaxed">
          Compare memory envelopes, throughput trade-offs, tokenizer fertility penalties, and zero-shot benchmark scores.
          Evaluated under identical single-host testbed controls (NVIDIA GTX 1050 Ti 4GB, PVE CT 108).
        </p>
      </div>

      {/* Model Pickers */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-white dark:bg-[#121719] p-4 rounded-xl border border-[#E2E5E5] dark:border-[#242F32] shadow-sm">
        <div>
          <label htmlFor="model-arm-a" className="block text-xs font-mono uppercase tracking-wider text-[#0E1415] dark:text-[#F2F5F5] mb-1.5 font-semibold">
            Model Arm A (Baseline)
          </label>
          <select
            id="model-arm-a"
            aria-label="Select Model Arm A (Baseline)"
            value={modelId1}
            onChange={(e) => setModelId1(e.target.value)}
            className="w-full bg-[#F5F5F3] dark:bg-[#182022] text-[#0E1415] dark:text-[#F2F5F5] border border-[#E2E5E5] dark:border-[#242F32] rounded-md p-2.5 text-xs outline-none focus:border-[#006D77] focus:ring-1 focus:ring-[#006D77] dark:focus:border-[#2DD4BF] dark:focus:ring-[#2DD4BF]"
          >
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} ({m.quantization})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="model-arm-b" className="block text-xs font-mono uppercase tracking-wider text-[#0E1415] dark:text-[#F2F5F5] mb-1.5 font-semibold">
            Model Arm B (Candidate)
          </label>
          <select
            id="model-arm-b"
            aria-label="Select Model Arm B (Candidate)"
            value={modelId2}
            onChange={(e) => setModelId2(e.target.value)}
            className="w-full bg-[#F5F5F3] dark:bg-[#182022] text-[#0E1415] dark:text-[#F2F5F5] border border-[#E2E5E5] dark:border-[#242F32] rounded-md p-2.5 text-xs outline-none focus:border-[#006D77] focus:ring-1 focus:ring-[#006D77] dark:focus:border-[#2DD4BF] dark:focus:ring-[#2DD4BF]"
          >
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} ({m.quantization})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="model-arm-c" className="block text-xs font-mono uppercase tracking-wider text-[#0E1415] dark:text-[#F2F5F5] mb-1.5 font-semibold">
            Model Arm C (Optional)
          </label>
          <select
            id="model-arm-c"
            aria-label="Select Model Arm C (Optional)"
            value={modelId3}
            onChange={(e) => setModelId3(e.target.value)}
            className="w-full bg-[#F5F5F3] dark:bg-[#182022] text-[#0E1415] dark:text-[#F2F5F5] border border-[#E2E5E5] dark:border-[#242F32] rounded-md p-2.5 text-xs outline-none focus:border-[#006D77] focus:ring-1 focus:ring-[#006D77] dark:focus:border-[#2DD4BF] dark:focus:ring-[#2DD4BF]"
          >
            <option value="none">-- None (2-way comparison) --</option>
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} ({m.quantization})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Comparison Table */}
      <div className="rounded-xl border border-[#E2E5E5] dark:border-[#242F32] bg-white dark:bg-[#121719] overflow-x-auto shadow-sm">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-[#E2E5E5] dark:border-[#242F32] bg-[#F5F5F3] dark:bg-[#182022]">
              <th className="py-4 px-4 text-[#475456] dark:text-[#98A8AA] font-mono uppercase tracking-wider text-[11px] w-1/4">
                Metric / Property
              </th>
              {activeModels.map((m, idx) => (
                <th key={m.id} className="py-4 px-4 text-[#0E1415] dark:text-[#F2F5F5] font-bold text-sm">
                  <div className="flex flex-col gap-1">
                    <span className="text-xs font-mono text-[#006D77] dark:text-[#2DD4BF]">Arm {String.fromCharCode(65 + idx)}</span>
                    <span className="font-serif">{m.name}</span>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#F5F5F3] dark:bg-[#182022] text-[#475456] dark:text-[#98A8AA] font-medium border border-[#E2E5E5] dark:border-[#242F32]">
                        {m.quantization}
                      </span>
                      <HardwareBadge showDetails={false} />
                    </div>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#ECEEED] dark:divide-[#1C2426] font-mono">
            {/* Model Architecture */}
            <tr className="bg-[#E6F3F4]/50 dark:bg-[#0D2C28]/40">
              <td colSpan={1 + activeModels.length} className="py-2.5 px-4 font-bold text-[#006D77] dark:text-[#2DD4BF] text-[11px] uppercase tracking-wider font-sans">
                1. System Envelope & Parameters
              </td>
            </tr>
            <tr className="hover:bg-[#F5F5F3] dark:hover:bg-[#182022]">
              <td className="py-3 px-4 text-[#475456] dark:text-[#98A8AA] font-sans">Parameter Count</td>
              {activeModels.map((m) => (
                <td key={m.id} className="py-3 px-4 font-bold text-[#0E1415] dark:text-[#F2F5F5]">
                  {m.parameters_b}B
                </td>
              ))}
            </tr>
            <tr className="hover:bg-[#F5F5F3] dark:hover:bg-[#182022]">
              <td className="py-3 px-4 text-[#475456] dark:text-[#98A8AA] font-sans">Static Weights VRAM</td>
              {activeModels.map((m) => (
                <td key={m.id} className="py-3 px-4 text-[#0E1415] dark:text-[#F2F5F5]">
                  {m.vram_static_mib} MiB
                </td>
              ))}
            </tr>
            <tr className="hover:bg-[#F5F5F3] dark:hover:bg-[#182022]">
              <td className="py-3 px-4 text-[#475456] dark:text-[#98A8AA] font-sans">Peak VRAM (8k ctx)</td>
              {activeModels.map((m, idx) => {
                const delta = idx > 0 ? calcDelta(activeModels[0].vram_peak_mib, m.vram_peak_mib) : null;
                return (
                  <td key={m.id} className="py-3 px-4">
                    <span className="font-bold text-[#0E1415] dark:text-[#F2F5F5]">{m.vram_peak_mib} MiB</span>
                    <span className="text-[#526063] dark:text-[#98A8AA] text-[11px] ml-1">({m.vram_budget_pct}%)</span>
                    {delta && (
                      <div className={`text-[10px] font-semibold ${delta.isPositive ? 'text-[#BE123C] dark:text-[#FB7185]' : 'text-[#0E7A5A] dark:text-[#34D399]'}`}>
                        {delta.isPositive ? '+' : ''}{delta.diff} MiB ({delta.pct}%)
                      </div>
                    )}
                  </td>
                );
              })}
            </tr>
            <tr className="hover:bg-[#F5F5F3] dark:hover:bg-[#182022]">
              <td className="py-3 px-4 text-[#475456] dark:text-[#98A8AA] font-sans">Remaining Headroom (4 GiB)</td>
              {activeModels.map((m) => {
                const headroom = Math.max(0, 4096 - m.vram_peak_mib);
                return (
                  <td key={m.id} className="py-3 px-4 font-bold text-[#0E7A5A] dark:text-[#34D399]">
                    {headroom} MiB
                  </td>
                );
              })}
            </tr>

            {/* Throughput & Latency */}
            <tr className="bg-[#E6F3F4]/50 dark:bg-[#0D2C28]/40">
              <td colSpan={1 + activeModels.length} className="py-2.5 px-4 font-bold text-[#006D77] dark:text-[#2DD4BF] text-[11px] uppercase tracking-wider font-sans">
                2. Inference Speed & Latency
              </td>
            </tr>
            <tr className="hover:bg-[#F5F5F3] dark:hover:bg-[#182022]">
              <td className="py-3 px-4 text-[#475456] dark:text-[#98A8AA] font-sans">Decode Speed (Generation)</td>
              {activeModels.map((m, idx) => {
                const delta = idx > 0 ? calcDelta(activeModels[0].generation_tok_s, m.generation_tok_s) : null;
                return (
                  <td key={m.id} className="py-3 px-4">
                    <span className="text-base font-extrabold text-[#0E1415] dark:text-[#F2F5F5]">{m.generation_tok_s}</span>
                    <span className="text-[#526063] dark:text-[#98A8AA] text-xs ml-1">tok/s</span>
                    {delta && (
                      <div className={`text-[10px] font-semibold ${delta.isPositive ? 'text-[#0E7A5A] dark:text-[#34D399]' : 'text-[#BE123C] dark:text-[#FB7185]'}`}>
                        {delta.isPositive ? '+' : ''}{delta.diff} tok/s ({delta.pct}%)
                      </div>
                    )}
                  </td>
                );
              })}
            </tr>
            <tr className="hover:bg-[#F5F5F3] dark:hover:bg-[#182022]">
              <td className="py-3 px-4 text-[#475456] dark:text-[#98A8AA] font-sans">Prefill Speed (Prompt Eval)</td>
              {activeModels.map((m) => (
                <td key={m.id} className="py-3 px-4 text-[#0E1415] dark:text-[#F2F5F5]">
                  {m.prompt_eval_tok_s} tok/s
                </td>
              ))}
            </tr>
            <tr className="hover:bg-[#F5F5F3] dark:hover:bg-[#182022]">
              <td className="py-3 px-4 text-[#475456] dark:text-[#98A8AA] font-sans">Time to First Token (TTFT)</td>
              {activeModels.map((m) => (
                <td key={m.id} className="py-3 px-4 text-[#0E1415] dark:text-[#F2F5F5]">
                  {m.ttft_ms} ms
                </td>
              ))}
            </tr>
            <tr className="hover:bg-[#F5F5F3] dark:hover:bg-[#182022]">
              <td className="py-3 px-4 text-[#475456] dark:text-[#98A8AA] font-sans">Speculative Decoding (MTP)</td>
              {activeModels.map((m) => (
                <td key={m.id} className="py-3 px-4">
                  {m.speculative_decoding ? (
                    <span className="text-[#006D77] dark:text-[#2DD4BF] font-bold">Enabled (+25.6%)</span>
                  ) : (
                    <span className="text-[#526063] dark:text-[#98A8AA]">Disabled</span>
                  )}
                </td>
              ))}
            </tr>

            {/* Zero-Shot Quality Integration */}
            <tr className="bg-[#E6F3F4]/50 dark:bg-[#0D2C28]/40">
              <td colSpan={1 + activeModels.length} className="py-2.5 px-4 font-bold text-[#006D77] dark:text-[#2DD4BF] text-[11px] uppercase tracking-wider font-sans">
                3. Zero-Shot Quality Observations
              </td>
            </tr>
            <tr className="hover:bg-[#F5F5F3] dark:hover:bg-[#182022]">
              <td className="py-3 px-4 text-[#475456] dark:text-[#98A8AA] font-sans">ARC-Challenge (Zero-Shot)</td>
              {activeModels.map((m) => (
                <td key={m.id} className="py-3 px-4 text-[#0E1415] dark:text-[#F2F5F5] font-bold">
                  {(m.quality_scores.arc_challenge * 100).toFixed(1)}%
                </td>
              ))}
            </tr>
            <tr className="hover:bg-[#F5F5F3] dark:hover:bg-[#182022]">
              <td className="py-3 px-4 text-[#475456] dark:text-[#98A8AA] font-sans">HellaSwag (Zero-Shot)</td>
              {activeModels.map((m) => (
                <td key={m.id} className="py-3 px-4 text-[#0E1415] dark:text-[#F2F5F5] font-bold">
                  {(m.quality_scores.hellaswag * 100).toFixed(1)}%
                </td>
              ))}
            </tr>
            <tr className="hover:bg-[#F5F5F3] dark:hover:bg-[#182022]">
              <td className="py-3 px-4 text-[#475456] dark:text-[#98A8AA] font-sans">GSM8K (Flex Matching)</td>
              {activeModels.map((m) => (
                <td key={m.id} className="py-3 px-4 text-[#0E1415] dark:text-[#F2F5F5] font-bold">
                  {(m.quality_scores.gsm8k_flex * 100).toFixed(1)}%
                </td>
              ))}
            </tr>
            <tr className="hover:bg-[#F5F5F3] dark:hover:bg-[#182022]">
              <td className="py-3 px-4 text-[#475456] dark:text-[#98A8AA] font-sans">IFEval (Prompt Strict)</td>
              {activeModels.map((m) => (
                <td key={m.id} className="py-3 px-4 text-[#0E1415] dark:text-[#F2F5F5] font-bold">
                  {(m.quality_scores.ifeval_strict * 100).toFixed(1)}%
                </td>
              ))}
            </tr>

            {/* Tokenizer Fertility */}
            <tr className="bg-[#E6F3F4]/50 dark:bg-[#0D2C28]/40">
              <td colSpan={1 + activeModels.length} className="py-2.5 px-4 font-bold text-[#006D77] dark:text-[#2DD4BF] text-[11px] uppercase tracking-wider font-sans">
                4. Tokenizer Fertility Penalty (pt-BR vs en-US)
              </td>
            </tr>
            <tr className="hover:bg-[#F5F5F3] dark:hover:bg-[#182022]">
              <td className="py-3 px-4 text-[#475456] dark:text-[#98A8AA] font-sans">Portuguese Fertility Ratio</td>
              {activeModels.map((m) => {
                const pt = m.fertility?.find((f) => f.language === 'pt-BR');
                return (
                  <td key={m.id} className="py-3 px-4 text-[#B45309] dark:text-[#FBBF24] font-bold">
                    {pt ? `${pt.fertility_ratio}x` : 'N/A'}
                  </td>
                );
              })}
            </tr>
            <tr className="hover:bg-[#F5F5F3] dark:hover:bg-[#182022]">
              <td className="py-3 px-4 text-[#475456] dark:text-[#98A8AA] font-sans">English Fertility Ratio</td>
              {activeModels.map((m) => {
                const en = m.fertility?.find((f) => f.language === 'en-US');
                return (
                  <td key={m.id} className="py-3 px-4 text-[#475456] dark:text-[#98A8AA]">
                    {en ? `${en.fertility_ratio}x` : 'N/A'}
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<div className="text-[#475456] dark:text-[#98A8AA] text-xs">Loading model comparison...</div>}>
      <CompareContent />
    </Suspense>
  );
}
